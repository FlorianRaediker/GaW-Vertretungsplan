#!/usr/bin/env python3.8
# -*- coding: utf-8 -*-
import asyncio
import datetime
import os
import pickle
import string
import time
import urllib.error
import urllib.parse
import urllib.request

os.chdir(os.path.dirname(__file__))

from website.stats import Stats
from website.substitution_plan_students import StudentHTMLCreator, StudentSubstitutionLoader
from website.substitution_plan_teachers import TeacherHTMLCreator, TeacherSubstitutionLoader
from website.substitution_utils import get_status_string
from logging_tool import create_logger


class Snippets:
    SNIPPET_PATH = "website/snippets/"
    __files = {}

    @staticmethod
    def load():
        Snippets.__files = {}
        for filename in sorted(filename[:-5] for filename in list(os.walk(Snippets.SNIPPET_PATH))[0][2]
                               if filename.endswith(".html") and not filename.startswith(".")):
            with open(Snippets.SNIPPET_PATH + filename + ".html", "r") as f:
                snippet = f.read()
            if snippet.startswith("<!-- extends "):
                first_line, snippet_from_first_line = snippet.split("\n", 1)
                if first_line.endswith(" -->"):
                    snippet = snippet_from_first_line
                    parent_snippet = first_line[13:-4]
                    parent_snippet = Snippets.__files[parent_snippet]
                    snippet_lines = iter(snippet.split("\n"))
                    line = next(snippet_lines)
                    assert line.startswith("<!-- SET ") and line.endswith(" -->")
                    current_key = line[9:-4]
                    current_content = []
                    formatting = {}
                    while True:
                        try:
                            while True:
                                line = next(snippet_lines)
                                if line.startswith("<!-- SET ") and line.endswith(" -->"):
                                    break
                                current_content.append(line)
                        except StopIteration:
                            formatting[current_key] = "\n".join(current_content)
                            break
                        formatting[current_key] = "\n".join(current_content)
                        current_key = line[9:-4]
                        current_content = []
                    snippet = string.Template(parent_snippet)
                    Snippets.__files[filename] = snippet.safe_substitute(formatting)
                    continue
                Snippets.__files[filename] = snippet
            else:
                Snippets.__files[filename] = snippet

    @staticmethod
    def get(name):
        try:
            return Snippets.__files[name]
        except KeyError:
            raise ValueError("Did not find snippet '{}'".format(name))


Snippets.load()


class SubstitutionPlan:
    URL_STUDENTS = "https://gaw-verden.de/images/vertretung/klassen/subst_{:03}.htm"
    URL_TEACHERS = "https://gaw-verden.de/images/vertretung/lehrer/subst_{:03}.htm"

    URL_FIRST_SITE = URL_STUDENTS.format(1)

    FILENAME_SUBSTITUTIONS = "data/substitutions/substitutions.pickle"
    FILENAME_STATS = "data/stats.json"

    def __init__(self, snippets):
        self.stats = Stats(self.FILENAME_STATS)
        self.substitution_loader_students = StudentSubstitutionLoader(self.URL_STUDENTS, self.stats)
        self.substitution_loader_teachers = TeacherSubstitutionLoader(self.URL_TEACHERS)
        self.html_creator_students = StudentHTMLCreator(snippets)
        self.html_creator_teachers = TeacherHTMLCreator(snippets)

        self.current_status_string = ""
        self.current_status_date = datetime.datetime.now().date()
        self.data_students = {}
        self.data_teachers = {}
        self.index_site_students = ""
        self.index_site_teachers = ""

    async def _load_data(self, first_site):
        logger.debug("Creating new data...")
        t1 = time.perf_counter()
        self.data_students, self.data_teachers = await asyncio.gather(
            self.substitution_loader_students.load_data("klassen", first_site),
            self.substitution_loader_teachers.load_data("lehrer")
        )
        t2 = time.perf_counter()
        logger.debug("New data created in {:.3f}".format(t2 - t1))

    def update_data(self):
        logger.debug("Requesting subst_001.htm ...")
        t1 = time.perf_counter()
        with urllib.request.urlopen(self.URL_FIRST_SITE) as site:
            text = site.read()
        t2 = time.perf_counter()
        new_status_string = get_status_string(text)
        logger.debug(f"Got answer in {t2 - t1:.3f}: {new_status_string}")
        logger.debug(f"Old status is {self.current_status_string}")
        if new_status_string != self.current_status_string:
            # status changed, load new data
            self.current_status_string = new_status_string
            self.stats.add_status(self.current_status_string)
            asyncio.run(self._load_data(text))
            logger.debug("Creating site...")
            t1 = time.perf_counter()
            self.index_site_students = self.html_creator_students.create_html(self.data_students,
                                                                              self.current_status_string)
            self.index_site_teachers = self.html_creator_teachers.create_html(self.data_teachers,
                                                                              self.current_status_string)
            t2 = time.perf_counter()
            logger.debug("Site created in {:.3f}".format(t2 - t1))
            with open(self.FILENAME_SUBSTITUTIONS, "wb") as f:
                pickle.dump((
                    self.current_status_string,
                    self.data_students,
                    self.data_teachers
                ), f)
            self.stats.save()
        today = datetime.datetime.now().date()
        if today > self.current_status_date:
            self.current_status_date = today

    def get_site_students(self, storage):
        self.update_data()
        if "classes" in storage:
            selection = storage["classes"][0]
            if selection:
                return self.html_creator_students.create_html(self.data_students,
                                                              self.current_status_string,
                                                              selection)
        return self.index_site_students

    def get_site_teachers(self, storage):
        self.update_data()
        if "teacher" in storage:
            selection = storage["teacher"][0]
            if selection:
                return self.html_creator_teachers.create_html(self.data_teachers,
                                                              self.current_status_string,
                                                              selection)
        return self.index_site_teachers

    def get_current_status(self):
        self.update_data()
        return self.current_status_string


substitution_plan = SubstitutionPlan(Snippets)

logger = create_logger("website")


def application(environ, start_response):
    if environ["PATH_INFO"] == "/":
        storage = urllib.parse.parse_qs(environ["QUERY_STRING"])
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [substitution_plan.get_site_students(storage).encode("utf-8")]

    if environ["PATH_INFO"] == "/teachers":
        storage = urllib.parse.parse_qs(environ["QUERY_STRING"])
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [substitution_plan.get_site_teachers(storage).encode("utf-8")]

    if environ["PATH_INFO"] == "/api/last-status":
        start_response("200 OK", [("Content-Type", "text/text; charset=utf-8")])
        return [substitution_plan.get_current_status().encode("utf-8")]

    start_response("400 NOT FOUND", [("Content-Type", "text/html; charset=utf-8")])
    return [Snippets.get("error-404").encode("utf-8")]
