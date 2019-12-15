import logging

from bot.db.base import DatabaseBot, DatabaseChatList, DatabaseChat
from common.students import parse_selection

logger = logging.getLogger()


class StudentDatabaseBot(DatabaseBot):
    def __init__(self, api_token, db_connection):
        super().__init__(api_token, StudentDatabaseChatList(db_connection, "students", self))


class StudentDatabaseChatList(DatabaseChatList):
    def _chat_from_row(self, row):
        return StudentDatabaseChat.from_row(self._connection, row, self.bot)

    def _new_chat(self, chat_id):
        return StudentDatabaseChat(self.bot, self._connection, chat_id)


class StudentDatabaseChat(DatabaseChat):
    def __init__(self, bot: DatabaseBot, connection,
                 chat_id: int, status="", db_selection=None, send_news=True,
                 send_absent_classes=True, send_absent_teachers=True, sent_messages=None):
        super().__init__(bot, connection, chat_id, status, db_selection, send_news, send_absent_classes,
                         send_absent_teachers, sent_messages)
        if not db_selection:
            self._parsed_selection = []
        else:
            self._parsed_selection = parse_selection(db_selection)

    @staticmethod
    def from_row(connection, row, bot):
        return StudentDatabaseChat(bot, connection, *row)

    def get_parsed_selection(self):
        return self._parsed_selection

    def get_pretty_selection(self):
        return ", ".join(self._parsed_selection)

    def set_selection_from_string(self, text: str):
        self._parsed_selection = parse_selection(text)
        super().set_selection_from_string(",".join(self._parsed_selection))
