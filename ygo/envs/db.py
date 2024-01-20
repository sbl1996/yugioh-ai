import sqlite3

from ygo.utils import load_deck


class CardDataset:

    def __init__(self, database):
        database = sqlite3.connect(database)
        database.row_factory = sqlite3.Row

        self.database = database

        self.cards = {}
        self.texts = {}
    
    def init_from_deck(self, deck):
        codes = load_deck(deck)
        for code in codes:
            if code not in self.cards:
                row = self.database.execute('select * from datas where id=?', (code,)).fetchone()
                if row is None:
                    raise ValueError("Card %d not found in datas" % code)
                self.cards[code] = row
            if code not in self.texts:
                row = self.database.execute('select * from texts where id = ?', (code, )).fetchone()
                if row is None:
                    raise ValueError("Card %d not found in texts" % code)
                self.texts[code] = row

    def get_card(self, code):
        return self.cards[code]

    def get_text(self, code):
        return self.texts[code]