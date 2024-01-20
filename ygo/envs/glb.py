import os

from ygo.envs.db import CardDataset
from ygo.envs.strings import StringsDatabase
from ygo.utils import get_root_directory

db: CardDataset = None
strings: StringsDatabase = None

_languages = {
    "english": "en",
    "chinese": "cn",
}

def init(lang):
    global db, strings
    short = _languages[lang]

    database = os.path.join(get_root_directory(), 'locale', short, 'cards.cdb')
    db = CardDataset(database)
    strings = StringsDatabase()
    strings.add(lang, short)
