import asyncio
import base64
import datetime
import logging
import re
from html.parser import HTMLParser
from typing import Type, List

import aiohttp

from common.base import SubstitutionDay
from common.utils import create_date_timestamp, sort_classes
from website.snippets import Snippets
from website.stats import Stats

logger = logging.getLogger()


class BaseSubstitutionParser(HTMLParser):
    REGEX_TITLE = re.compile(r"(\d+.\d+.\d\d\d\d) (\w+), Woche (\w+)")

    def __init__(self, data: dict, current_timestamp: int):
        super().__init__()
        self.data = data
        self.current_timestamp = current_timestamp
        self.day_timestamp = None
        self.day_data = None
        self.has_read_news_heading = False
        self.current_section = ""
        self.current_substitution = []
        self.current_day_info = None
        self.is_in_tag = False
        self.is_in_td = False
        self.current_news_format_tag = None
        self.next_site = None

    def error(self, message):
        pass

    def _get_attr(self, attrs, name):
        for attr in attrs:
            if attr[0] == name:
                return attr[1]
        return None

    def on_new_substitution_start(self):
        self.current_substitution = []

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            self.is_in_td = True
            if self.current_section == "info-table" and self.current_day_info == "news":
                if "news" in self.day_data:
                    self.day_data["news"] += "<br>"
                else:
                    self.day_data["news"] = ""
        elif tag == "tr":
            if self.current_section == "substitution-table":
                self.on_new_substitution_start()
        elif tag == "table":
            if len(attrs) == 1 and attrs[0][0] == "class":
                if attrs[0][1] == "info":
                    self.current_section = "info-table"
                elif attrs[0][1] == "mon_list":
                    self.current_section = "substitution-table"
        elif tag == "div":
            if len(attrs) == 1 and attrs[0] == ("class", "mon_title"):
                self.current_section = "title"
        elif tag == "meta":
            if len(attrs) == 2 and attrs[0] == ("http-equiv", "refresh") and attrs[1][0] == "content":
                self.next_site = attrs[1][1].split("URL=")[1]
        elif self.current_section == "info-table":
            if (self.current_day_info is None or self.current_day_info == "news") and \
                    tag in ("b", "strong", "i", "em", "code", "pre"):  # all tags supported by Telegram except <a>
                self.current_day_info = "news"
                self.current_news_format_tag = tag
        self.is_in_tag = True

    def get_current_group(self):
        raise NotImplementedError

    def get_current_substitution(self):
        raise NotImplementedError

    def handle_endtag(self, tag):
        if self.current_section == "substitution-table":
            if tag == "tr" and self.current_substitution:
                group = self.get_current_group()
                substitution = self.get_current_substitution()
                try:
                    if substitution not in self.day_data["substitutions"][group]:
                        self.day_data["substitutions"][group].append(substitution)
                except KeyError:
                    self.day_data["substitutions"][group] = [substitution]
        if tag == "td":
            self.is_in_td = False
        self.is_in_tag = False

    def handle_data(self, data):
        if self.is_in_tag and self.current_section == "substitution-table":
            self.handle_substitution_data(data)
        elif self.current_section == "info-table":
            if self.is_in_td:
                if self.current_day_info:
                    if self.current_day_info == "news":
                        if self.current_news_format_tag:
                            self.day_data["news"] += "<" + self.current_news_format_tag + ">" + \
                                                     data + \
                                                     "</" + self.current_news_format_tag + ">"
                            self.current_news_format_tag = None
                        else:
                            # this is not the first, but the second, third, ... td that contains news on this site
                            self.day_data["news"] += data
                    else:
                        self.day_data[self.current_day_info] = data
                        self.current_day_info = None
                else:
                    data_stripped = data.strip()
                    if data_stripped != "Nachrichten zum Tag":
                        if data_stripped == "Abwesende Lehrer":
                            self.current_day_info = "absent-teachers"
                        elif data_stripped == "Abwesende Klassen":
                            self.current_day_info = "absent-classes"
                        else:
                            # data is the first td on the site that contains news
                            self.current_day_info = "news"
                            self.day_data["news"] = data
        elif self.current_section == "title":
            match = self.REGEX_TITLE.search(data)
            if match:
                date = match.group(1)
                self.day_timestamp = create_date_timestamp(datetime.datetime.strptime(date, "%d.%m.%Y"))
                if self.day_timestamp < self.current_timestamp:
                    raise ValueError
                if self.day_timestamp not in self.data:
                    self.day_data = {
                        "date": date,
                        "day_name": match.group(2),
                        "week": match.group(3),
                        "substitutions": {}
                    }
                    self.data[self.day_timestamp] = self.day_data
                else:
                    self.day_data = self.data[self.day_timestamp]
                self.current_section = None
            else:
                raise ValueError("no date detected in title")

    def handle_substitution_data(self, data):
        if self.is_in_td:
            self.current_substitution.append(data)

    def handle_comment(self, data):
        pass

    def handle_decl(self, data):
        pass

    def close(self):
        super().close()

    def is_last_site(self) -> bool:
        return self.next_site == "subst_001.htm"


class BaseSubstitutionLoader:
    def __init__(self, substitutions_parser_class: Type[BaseSubstitutionParser], url: str, stats: Stats = None):
        self.substitutions_parser = substitutions_parser_class
        self.url = url
        self.stats = stats
        self._last_site_num = None

    def _load_new_data(self, new_data, response_data, current_timestamp):
        parser = self.substitutions_parser(new_data, current_timestamp)
        try:
            parser.feed(response_data)
            parser.close()
        except ValueError:
            pass
        return parser.is_last_site()

    async def _load_data_from_site(self, new_data: dict, current_timestamp: int, session: aiohttp.ClientSession,
                                   site_num: int, plan: str):
        async with session.get(self.url.format(site_num)) as response:
            logger.debug(f"Response {response.status} for {plan}/subst_" + str(site_num) + ".htm")
            if response.status != 200:
                return True
            response_data = await response.text("iso-8859-1")
            if self._load_new_data(new_data, response_data, current_timestamp):
                self._last_site_num = site_num
                return True
            return False

    SITE_LOAD_COUNT = 5  # first site has already been loaded (at least for students)

    async def load_data(self, plan: str, first_site: bytes = None):
        new_data = {}
        current_timestamp = create_date_timestamp(datetime.datetime.now())
        if first_site:
            if self._load_new_data(new_data, first_site.decode("iso-8859-1"), current_timestamp):
                return self._data_postprocessing(new_data, 1)
            i = 2
            site_load_count = self.SITE_LOAD_COUNT
        else:
            i = 1
            site_load_count = self.SITE_LOAD_COUNT + 1  # load one site more for teachers

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        session = aiohttp.ClientSession()

        self._last_site_num = None
        while True:
            if True in await asyncio.gather(
                    *(self._load_data_from_site(new_data, current_timestamp, session, site_num, plan)
                      for site_num in range(i, i + site_load_count))):
                await session.close()
                return self._data_postprocessing(new_data, self._last_site_num)
            i += site_load_count

    def _data_postprocessing(self, data: dict, site_count: int):
        if self.stats:
            self.stats.add_last_site(site_count)
        return sorted(
            SubstitutionDay(
                timestamp,
                day["day_name"],
                day["date"],
                day["week"],
                day["news"] if "news" in day else None,
                ", ".join(sorted(set(day["absent-classes"].split(", ")), key=sort_classes))
                    if "absent-classes" in day else None,
                ", ".join(sorted(set(day["absent-teachers"].split(", "))))
                    if "absent-teachers" in day else None,
                self._sort_substitutions(day["substitutions"])
            )
            for timestamp, day in data.items()
        )

    def _sort_substitutions(self, substitutions: dict):
        raise NotImplementedError


class BaseHTMLCreator:
    def __init__(self, snippets: Snippets, snippet_name_base: str, snippets_name_substitution_table: str,
                 snippet_name_notice_selection: str, snippet_name_no_substitutions_reset_selection: str,
                 snippet_name_select: str):
        self.snippets = snippets
        self.snippet_base = snippet_name_base
        self.snippet_substitution_table = snippets_name_substitution_table
        self.snippet_notice_selection = snippet_name_notice_selection
        self.snippet_no_substitutions_reset_selection = snippet_name_no_substitutions_reset_selection
        self.snippet_select = snippet_name_select

    def parse_selection(self, selection: str):
        """
        Parse the selection: Return parsed selection (will be passed to is_selected) and formatted selection for
        display on website
        """
        raise NotImplementedError

    def create_day_container(self, day: SubstitutionDay, substitutions: str):
        absent_classes = (self.snippets.get("absent-classes", absent_classes=day.absent_classes)
                          if day.absent_classes else "")
        absent_teachers = (self.snippets.get("absent-teachers", absent_teachers=day.absent_teachers)
                           if day.absent_teachers else "")
        if day.news:
            day_info = self.snippets.get(
                "day-info-all",
                day_name=day.day_name,
                date=day.date,
                week=day.week,
                news=self.snippets.get("news", news=day.news),
                absent_teachers=absent_teachers,
                absent_classes=absent_classes
            )
        else:
            day_info = self.snippets.get(
                "day-info-only-absent",
                day_name=day.day_name,
                date=day.date,
                week=day.week,
                absent_teachers=absent_teachers,
                absent_classes=absent_classes
            )
        return self.snippets.get(
            "day-container",
            day_info=day_info,
            substitutions=substitutions
        )

    def create_html(self, data: List[SubstitutionDay], status_string: str, selection: str = None):
        if selection:
            parsed_selection, selection_string = self.parse_selection(selection)
        containers = ""
        current_timestamp = create_date_timestamp(datetime.datetime.now())
        i = 0
        for day in data:
            if day.timestamp >= current_timestamp:
                i += 1
                substitution_rows = ""
                groups = day.filter_groups(parsed_selection) if selection else day.substitution_groups
                for substitutions_group in groups:
                    substitution_rows += substitutions_group.substitutions[0].get_html_first_of_group(
                        len(substitutions_group.substitutions), substitutions_group.group_name, self.snippets,
                        i == 1)
                    for substitution in substitutions_group.substitutions[1:]:
                        substitution_rows += substitution.get_html(self.snippets, i == 1)
                if substitution_rows:
                    substitutions = self.snippets.get(self.snippet_substitution_table, content=substitution_rows)
                    if selection:
                        substitutions += self.snippets.get(self.snippet_notice_selection, selection=selection_string)
                else:
                    substitutions = self.snippets.get(self.snippet_no_substitutions_reset_selection,
                                                      selection=selection_string)
                containers += self.create_day_container(day, substitutions)
        if selection:
            telegram_link = "?start=" + base64.urlsafe_b64encode(selection_string.encode("utf-8")).replace(b"=", b"") \
                .decode("utf-8")
        else:
            telegram_link = ""
        return self.snippets.get((self.snippet_base + "-selected") if selection else (self.snippet_base + "-index"),
                                 select_container="" if selection else self.snippets.get(self.snippet_select),
                                 containers=containers, status=status_string,
                                 telegram_link=telegram_link)
