import logging
from functools import partial
from typing import List, NamedTuple

from jinja2 import Environment, FileSystemLoader, select_autoescape, FileSystemBytecodeCache

from substitution_plan.storage import SubstitutionDay

logger = logging.getLogger()


class LoggingLoader(FileSystemLoader):
    def get_source(self, environment, template):
        logger.info(f"Loading template '{template}' from file")
        return super().get_source(environment, template)


class TemplateDescription(NamedTuple):
    name: str
    filename: str


class Templates:
    TEMPLATES = (
        TemplateDescription("about", "about.min.html"),
        TemplateDescription("privacy", "privacy.min.html"),
        TemplateDescription("error_404", "error-404.min.html"),
        TemplateDescription("error_500_students", "error-500-students.min.html"),
        TemplateDescription("error_500_teachers", "error-500-teachers.min.html")
    )

    def __init__(self, template_path, template_cache_path, base_path=""):
        self._jinja_env = Environment(
            loader=LoggingLoader(template_path),
            bytecode_cache=FileSystemBytecodeCache(template_cache_path),
            autoescape=select_autoescape(["html"]),
            enable_async=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.base_path = base_path

        self._template_substitution_plan_students = self._jinja_env.get_template("substitution-plan-students.min.html")
        self._template_substitution_plan_teachers = self._jinja_env.get_template("substitution-plan-teachers.min.html")
        self._template_error_405 = self._jinja_env.get_template("error-405.min.html")

        for template in Templates.TEMPLATES:
            self.__setattr__("render_" + template.name,
                             partial(self._render, template=self._jinja_env.get_template(template.filename)))

    async def _render(self, template):
        return await template.render_async(base_path=self.base_path)

    async def render_substitution_plan_students(self, status: str, days: List[SubstitutionDay], selection=None,
                                                selection_str: str = None):
        return await self._template_substitution_plan_students.render_async(base_path=self.base_path,
                                                                            status=status, days=days,
                                                                            selection=selection,
                                                                            selection_str=selection_str)

    async def render_substitution_plan_teachers(self, status: str, days: List[SubstitutionDay], selection=None,
                                                selection_str: str = None):
        return await self._template_substitution_plan_teachers.render_async(base_path=self.base_path,
                                                                            status=status, days=days,
                                                                            selection=selection,
                                                                            selection_str=selection_str)

    async def render_error_405(self, method: str, path: str):
        return await self._template_error_405.render_async(base_path=self.base_path, method=method, path=path)
