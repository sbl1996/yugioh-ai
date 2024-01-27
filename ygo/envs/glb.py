import os

from ygo.envs.db import CardDataset
from ygo.envs.strings import StringsDatabase
from ygo.utils import get_root_directory
import ygo.ocgcore as lib

db: CardDataset = None
strings: StringsDatabase = None
message_map = {}


def register_message(d):
    global message_map
    for msg, callback in d.items():
        if msg in message_map:
            raise ValueError("message already registered")
        message_map[msg] = callback


_languages = {
    "english": "en",
    "chinese": "zh",
}

def init(lang):
    global db, strings
    short = _languages[lang]

    database = os.path.join(get_root_directory(), 'locale', short, 'cards.cdb')
    db = CardDataset(database)
    strings = StringsDatabase()
    strings.add(lang, short)

    lib.init(database)