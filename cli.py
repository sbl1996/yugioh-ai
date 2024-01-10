import time
import itertools
import random
import sqlite3
import argparse
import re
from collections import defaultdict
from _duel import ffi, lib

try:
    # needed on Python 3.7
    re._pattern_type = re.Pattern
except AttributeError:
    pass

from ygo import duel as dm
from ygo import globals as glb
from ygo.language_handler import LanguageHandler
from ygo.duel_reader import DuelReader
from ygo.constants import LOCATION


class Response:
    def __init__(self, text):
        self.text = text


class FakePlayer:
    def __init__(self, i, deck, language):
        self.deck = {"cards": deck}
        self.duel_player = i
        self.cdb = glb.db
        self.language = language
        self.seen_waiting = False
        self.soundpack = False

    _ = lambda self, t: t

    def notify(self, arg1, *args, **kwargs):
        if arg1 == DuelReader:
            func = args[0]
            chosen = input()
            func(Response(chosen))
        else:
            print(self.duel_player, arg1)

    @property
    def strings(self):
        return glb.language_handler.get_strings(self.language)


class RandomAI(FakePlayer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.statistic = defaultdict(int)

    def notify(self, arg1, *args, **kwargs):
        if arg1 == DuelReader:
            func, options = args[0], args[1]

            msg = re.search(r'<function (\w+)\.<locals>\.', str(func)).group(1)
            self.statistic[msg] += 1
            # print(msg)
                # chosen = input()
            chosen = random.choice(options)
            # print(self.duel_player, "chose", chosen, "in", options)
            caller = Response(chosen)
            func(caller)
        else:
            pass
            # print(self.duel_player, arg1)


# from ygo/utils.py
def process_duel(d):
    while d.started:
        res = d.process()
        if res & 0x20000:
            break

def load_deck(fn):
    with open(fn) as f:
        lines = f.readlines()
        noside = itertools.takewhile(lambda x: "side" not in x, lines)
        deck = [int(line) for line in  noside if line[:-1].isdigit()]
        return deck

global g_duel

def show_duel(duel):
    players = (0, 1)
    cards = []
    for i in players:
        for j in (
            LOCATION.HAND,
            LOCATION.MZONE,
            LOCATION.SZONE,
            LOCATION.GRAVE,
            LOCATION.EXTRA,
        ):
            cards.extend(duel.get_cards_in_location(i, j))
    specs = set(card.get_spec(duel.players[duel.tp]) for card in cards)


def main():
    player_factory = {
        'manual': FakePlayer,
        'random': RandomAI
    }
    lang_short = {
        'english': 'en',
        'chinese': 'zh'
    }
    parser = argparse.ArgumentParser()
    parser.add_argument("--deck1", help="deck for player 1", type=str, required=True)
    parser.add_argument("--deck2", help="deck for player 2", type=str, required=True)
    parser.add_argument("--lp1", help="starting lp for player 1", type=int, default=8000)
    parser.add_argument("--lp2", help="starting lp for player 2", type=int, default=8000)
    parser.add_argument("--p1", help="type of player 1", type=str, default='random', choices=player_factory.keys())
    parser.add_argument("--p2", help="type of player 1", type=str, default='random', choices=player_factory.keys())
    parser.add_argument("--preload", help="path to preload script", type=str, default=None)
    parser.add_argument("--lang", help="language", type=str, default="english")
    parser.add_argument("--seed", help="random seed", type=int, default=None)
    args = parser.parse_args()
    if args.seed is None:
        args.seed = int(time.time())
    print("seed: ", args.seed)
    random.seed(args.seed)
    decks = [load_deck(args.deck1), load_deck(args.deck2)]

    lang = args.lang
    short = lang_short[lang]

    glb.language_handler = LanguageHandler()
    glb.language_handler.add(lang, short)
    glb.language_handler.set_primary_language(lang)
    glb.db = sqlite3.connect(f"locale/{short}/cards.cdb")
    glb.db.row_factory = sqlite3.Row

    duel = dm.Duel()
    global g_duel
    g_duel = duel
    config = {"players": ["Alice", "Bob"], "decks": decks}
    players = [player_factory[args.p1](0, config["decks"][0], lang), player_factory[args.p2](1, config["decks"][1], lang)]
    cards = []
    for i, name in enumerate(config["players"]):
        players[i].nickname = name
        i_cards = duel.load_deck(players[i])
        cards.extend(i_cards)
    card_codes = set()
    unique_cards = []
    for card in cards:
        if card.code not in card_codes:
            card_codes.add(card.code)
            unique_cards.append(card)

    duel.unique_cards = unique_cards
    duel.players = players
    duel.set_player_info(0, args.lp1)
    duel.set_player_info(1, args.lp2)
    # rules = 1, Traditional
    # rules = 0, Default
    # rules = 4, Link
    # rules = 5, MR5
    rules = 5
    options = 0
    if args.preload:
        fn = args.preload
        fn_buff = ffi.new("char[]", fn.encode('ascii'))
        lib.preload_script(duel.duel, fn_buff, len(fn))
    duel.start(((rules & 0xFF) << 16) + (options & 0xFFFF))
    process_duel(duel)
    print(duel.lp)
    print(players[0].statistic)
    print(players[1].statistic)


if __name__ == "__main__":
    main()
