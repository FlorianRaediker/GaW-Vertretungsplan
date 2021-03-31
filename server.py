import argparse
import os
import time
from functools import partial

import jinja2
from aiohttp import client, hdrs, http, web
from aiohttp.web_fileresponse import FileResponse

import subs_crawler
from website import config, logger
config.load()
from website.db import SubstitutionPlanDB
from website.stats import Stats
from website.substitution_plan import RESPONSE_HEADERS, SubstitutionPlan

__version__ = "4.0"


WORKING_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.abspath(config.get_str("data_dir"))

logger.init(os.path.join(WORKING_DIR, config.get_str("logfile")))
_LOGGER = logger.get_logger()


REQUEST_USER_AGENT = config.get_str("user_agent", "GaWVertretungBot").format(version=__version__,
                                                                             server_software=http.SERVER_SOFTWARE)
REQUEST_HEADERS = {hdrs.USER_AGENT: REQUEST_USER_AGENT}


STATIC_PATH = os.path.join(WORKING_DIR, "assets/static/")
STATS_PATH = os.path.join(DATA_DIR, "stats/")

stats = Stats(STATS_PATH)

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(WORKING_DIR, "assets/templates")),
    bytecode_cache=jinja2.FileSystemBytecodeCache(os.path.join(DATA_DIR, "template_cache/")),
    enable_async=True,
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
    auto_reload=config.get_bool("dev")
)
TEMPLATE_PRIVACY = env.get_template("privacy.min.html")
TEMPLATE_ABOUT = env.get_template("about.min.html")
TEMPLATE_ERROR404 = env.get_template(config.get_str("template404"))
TEMPLATE_ERROR500 = env.get_template(config.get_str("template500"))


@web.middleware
async def stats_middleware(request: web.Request, handler):
    t1 = time.perf_counter_ns()
    response: web.Response = await handler(request)
    if not response.prepared:
        if type(response) != FileResponse:
            # noinspection PyBroadException
            try:
                await response.prepare(request)
                await response.write_eof()
            except Exception:
                _LOGGER.exception("Exception occurred while preparing and writing response")
        else:
            if request.path.endswith("js"):
                response.content_type = "text/javascript"
            elif request.path.endswith(".css"):
                response.content_type = "text/css"
    await stats.new_request(request, response, time.perf_counter_ns()-t1)
    return response


@web.middleware
async def error_middleware(request: web.Request, handler):
    # noinspection PyBroadException
    try:
        return await handler(request)
    except web.HTTPException as e:
        if e.status == 404:
            return web.Response(text=await TEMPLATE_ERROR404.render_async(), status=404, content_type="text/html",
                                charset="utf-8", headers=RESPONSE_HEADERS)
        raise e from None
    except Exception:
        _LOGGER.exception(f"{request.method} {request.path} Exception while handling request")
    except BaseException as e:
        _LOGGER.exception(f"{request.method} {request.path} BaseException while handling request")
        raise e
    return web.Response(text=await TEMPLATE_ERROR500.render_async(), status=500, content_type="text/html",
                        charset="utf-8", headers=RESPONSE_HEADERS)


def template_handler(template: jinja2.Template):
    # noinspection PyUnusedLocal
    async def handler(request: web.Request):
        return web.Response(text=await template.render_async(), content_type="text/html", headers=RESPONSE_HEADERS)
    return handler


async def report_js_error_handler(request: web.Request):
    if request.content_length < 10000:
        # noinspection PyBroadException
        try:
            data = await request.post()
            await stats.new_js_error(
                data.get("name", ""), data.get("message", ""), data.get("description", ""), data.get("number", ""),
                data.get("filename", ""), data.get("lineno", ""), data.get("colno", ""), data.get("stack", ""),
                data.get("user_agent", ""))
        except Exception:
            _LOGGER.exception("Exception while handling JS error report")
    else:
        _LOGGER.warn(f"JS error report body too long ({request.content_length})")
    return web.Response()


async def client_session_context(app: web.Application):
    _LOGGER.debug(f"Create ClientSession (headers: {REQUEST_HEADERS})")
    session = client.ClientSession(headers=REQUEST_HEADERS)
    for substitution_plan in app["substitution_plans"].values():
        substitution_plan.client_session = session
    yield
    await session.close()


async def databases_context(app: web.Application):
    db = SubstitutionPlanDB(os.path.join(DATA_DIR, "storage/db.sqlite3"))
    for substitution_plan in app["substitution_plans"].values():
        substitution_plan.db = db
    yield
    db.close()


async def app_factory(dev_mode=False):
    if config.get("substitution_plans") is None:
        raise ValueError("No substitution_plans configured")
    if config.get("default_plan") is None:
        raise ValueError("No default_plan configured")
    app = web.Application(middlewares=[logger.logging_middleware, stats_middleware, error_middleware])
    app["substitution_plans"] = {}
    for plan_id, plan_config in config.get("substitution_plans").items():
        crawler_id = plan_config["crawler"]["name"]
        try:
            crawler_class = subs_crawler.CRAWLERS[crawler_id]
        except KeyError:
            raise ValueError(f"Invalid crawler id '{crawler_id}")
        parser_id = plan_config["parser"]["name"]
        try:
            parser_class = subs_crawler.PARSERS[parser_id]
        except KeyError:
            raise ValueError(f"Invalid parser id '{parser_id}'")
        crawler_options = plan_config["crawler"].get("options", {})
        parser_options = plan_config["parser"].get("options", {})
        template_options = plan_config.get("template_options", {})
        crawler = crawler_class(parser_class, parser_options, **crawler_options)
        crawler.on_status_changed = partial(stats.add_last_site, plan_id)
        plan = SubstitutionPlan(plan_id, crawler, env.get_template("substitution-plan.min.html"),
                                env.get_template("error-500-substitution-plan.min.html"), template_options,
                                plan_config.get("uppercase_selection", False))

        await plan.deserialize(os.path.join(DATA_DIR, f"substitutions/{plan_id}.pickle"))

        app.add_subapp(f"/{plan_id}/",
                       plan.create_app(os.path.abspath("assets/static/" + plan_id) if config.get_bool("dev") else None))

        app["substitution_plans"][plan_id] = plan

    async def root_handler(request: web.Request):
        location = f"/{config.get('default_plan')}/"
        if request.query_string:
            location += "?" + request.query_string
        raise web.HTTPPermanentRedirect(location=location)

    app.add_routes([
        web.get("/", root_handler),
        web.get("/privacy", template_handler(TEMPLATE_PRIVACY)),
        web.get("/about", template_handler(TEMPLATE_ABOUT)),
        web.post("/api/report-error", report_js_error_handler)
    ])

    if dev_mode:
        app.router.add_static("/", STATIC_PATH)

    app.cleanup_ctx.extend((client_session_context, databases_context))

    return app


def run(path, host, port, dev_mode=False):
    _LOGGER.info(f"Starting server on {path if path else str(host) + ':' + str(port)}"
                 f"{' in dev mode' if dev_mode else ''}")
    web.run_app(app_factory(dev_mode), path=path, host=host, port=port, print=_LOGGER.info)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="gawvertretung server")
    parser.add_argument("--path")
    parser.add_argument("--host")
    parser.add_argument("--port")
    args = parser.parse_args()
    if args.path:
        path = args.path
        host = None
        port = None
    else:
        path = None
        host = args.host if args.host else config.get_str("host", "localhost")
        port = args.port if args.port else config.get_int("port", 8080)
    run(path, host, port, config.get_bool("dev"))
