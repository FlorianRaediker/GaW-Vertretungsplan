import asyncio
import json
import logging
import sqlite3

import asynctelebot

logger = logging.getLogger()


class DatabaseBot(asynctelebot.Bot):
    chats: "DatabaseChatList"

    def __init__(self, api_token, chat_list):
        self.chats = chat_list
        super().__init__(api_token)


# noinspection SqlNoDataSourceInspection,SqlResolve
class DatabaseChatList:
    CLASS_CHAT = None

    def __init__(self, connection, table_name, bot: DatabaseBot):
        self._connection = connection
        self.table_name = table_name
        self.cursor = self._connection.cursor()
        self.bot = bot

    def try_create_table(self):
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS {} (
                                chat_id INTEGER primary key,
                                status TEXT,
                                selection TEXT,
                                send_format TEXT,
                                send_news INTEGER,
                                send_absent_classes INTEGER,
                                send_absent_teachers INTEGER,
                                sent_messages TEXT)""".format(self.table_name))

    def _chat_from_row(self, row):
        raise NotImplementedError

    def _new_chat(self, chat_id):
        raise NotImplementedError

    def get(self, chat_id: int) -> "DatabaseChat":
        logger.debug("Get chat '" + str(chat_id) + "'")
        self.cursor.execute("""SELECT * FROM {} WHERE chat_id=?""".format(self.table_name), (chat_id,))
        chat = self.cursor.fetchone()
        if chat is None:
            logger.debug("Unknown chat, creating new")
            self.cursor.execute("""INSERT INTO {} VALUES (?,?,?,?,?,?,?,?)""".format(self.table_name),
                                (chat_id, "", "", "text", 1, 1, 1, ""))
            return self._new_chat(chat_id)
        return self._chat_from_row(chat)

    def get_from_msg(self, message) -> "DatabaseChat":
        return self.get(message.chat.id)

    def all_chats(self):
        self.cursor.execute("""SELECT * FROM {}""".format(self.table_name))
        for row in self.cursor.fetchall():
            yield self._chat_from_row(row)

    def reset_chat(self, chat_id: int):
        self.cursor.execute("""DELETE FROM {} WHERE chat_id=?""".format(self.table_name), (chat_id,))

    async def remove_old_messages(self, min_time):
        print(await asyncio.gather(*(chat.remove_old_messages(min_time) for chat in self.all_chats())))


# noinspection SqlNoDataSourceInspection,SqlResolve
class DatabaseChat:
    cursor: sqlite3.Cursor

    def __init__(self, bot: DatabaseBot, cursor,
                 chat_id: int, status="", selection=None, send_format="text", send_news=True,
                 send_absent_classes=True, send_absent_teachers=True, sent_messages=None):
        self.bot = bot
        self.cursor = cursor
        self._chat_id = chat_id
        self._status = status
        if selection is None:
            self._selection = ""
        else:
            self._selection = selection
        self._send_format = send_format
        self._send_news = send_news
        self._send_absent_classes = send_absent_classes
        self._send_absent_teachers = send_absent_teachers
        if not sent_messages:
            self._sent_messages = {}
        else:
            self._sent_messages = json.loads(sent_messages)

    def __repr__(self):
        return """Chat(bot={}, 
    chat_id={},
    status={},
    selection={},
    send_format={},
    send_news={},
    send_absent_classes={},
    send_absent_teachers={},
    sent_messages={}
)""".format(repr(self.bot), repr(self._chat_id), repr(self._status), repr(self._selection),
            repr(self._send_format), repr(self._send_news), repr(self._send_absent_classes),
            repr(self._send_absent_teachers), repr(self._sent_messages))

    @staticmethod
    def from_row(cursor, row, bot):
        raise NotImplementedError

    def reset_status(self):
        self.cursor.execute("""UPDATE {} SET status='' WHERE chat_id=?""".format(self.bot.chats.table_name),
                            (self._chat_id,))

    async def send(self, text, reply_markup=None, parse_mode=None):
        return await self.bot.send_message(self.chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

    async def send_substitution(self, day_timestamp, text, reply_markup=None, parse_mode=None):
        day_timestamp = str(day_timestamp)
        message = await self.send(text, reply_markup, parse_mode)
        try:
            self.sent_messages[day_timestamp].append(message.message_id)
        except KeyError:
            self.sent_messages[day_timestamp] = [message.message_id]
        logger.debug("Sent substitution to {}: {}".format(self.chat_id, message.message_id))
        self.save_sent_messages()

    def save_sent_messages(self):
        logger.debug(f"Set sent substitutions of {self.chat_id} to {repr(self.sent_messages)}")
        self.cursor.execute("UPDATE {} SET sent_messages=? WHERE chat_id=?".format(self.bot.chats.table_name),
                            (json.dumps(self.sent_messages), self._chat_id))

    def remove_all_messages(self):
        for day, messages in self._sent_messages.items():
            for message_id in messages:
                yield self.bot.edit_message_text("Alte Nachrichten zum Vertretungsplan werden gelöscht. ",
                                                 self.chat_id, message_id)

    async def remove_old_messages(self, min_time):
        async def one_task(message_id):
            try:
                await self.bot.edit_message_text(
                    "Alte Nachrichten zum Vertretungsplan werden gelöscht. ", self.chat_id, message_id)
            except:
                pass

        new_sent_messages = self.sent_messages.copy()
        tasks = []
        for day, messages in self.sent_messages.items():
            if int(day) <= min_time:
                for message_id in messages:
                    tasks.append(one_task(message_id))
                    logger.info("Deleted {} from {}".format(message_id, self.chat_id))
                del new_sent_messages[day]
        await asyncio.gather(*tasks)
        # self.sent_messages = new_sent_messages
        # self.cursor.execute("UPDATE {} SET sent_messages=? WHERE chat_id=?".format(self.bot.chats.table_name),
        #                    (self._sent_messages, self._chat_id))

    def get(self, property_name):
        return self.__dict__["_" + property_name]

    def set(self, property_name, value):
        self.__dict__["_" + property_name] = value
        assert " " not in property_name
        self.cursor.execute("UPDATE {} SET {}=? WHERE chat_id=?".format(self.bot.chats.table_name, property_name),
                            (value, self._chat_id))

    @property
    def chat_id(self):
        return self._chat_id

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self.set("status", value)

    def has_selection(self):
        return bool(self._selection)

    def set_selection_from_string(self, text):
        self.selection = text
        return text

    def get_pretty_selection(self):
        return self._selection

    def get_parsed_selection(self):
        return self._selection

    @property
    def selection(self):
        return self._selection

    @selection.setter
    def selection(self, value):
        self.set("selection", value)

    @property
    def send_format(self):
        return self._send_format

    @send_format.setter
    def send_format(self, value):
        self.set("send_format", value)

    @property
    def send_news(self):
        return self._send_news

    @send_news.setter
    def send_news(self, value):
        self.set("sent_news", value)

    @property
    def send_absent_classes(self):
        return self._send_absent_classes

    @send_absent_classes.setter
    def send_absent_classes(self, value):
        self.set("send_absent_classes", value)

    @property
    def send_absent_teachers(self):
        return self._send_absent_teachers

    @send_absent_teachers.setter
    def send_absent_teachers(self, value):
        self.set("send_absent_teachers", value)

    @property
    def sent_messages(self):
        return self._sent_messages
