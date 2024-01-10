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
from ygo import server
from ygo.language_handler import LanguageHandler
from ygo.duel_reader import DuelReader
from ygo.duel_menu import DuelMenu
from ygo.parsers.yes_or_no_parser import yes_or_no_parser
from ygo.constants import LOCATION


class Connection:
    def __init__(self, pl):
        self.player = pl
        self.parser = None


class Response:
    def __init__(self, text, pl):
        self.text = text
        self.connection = Connection(pl)


class FakeRoom:
    def announce_draw(self):
        pass

    def announce_victory(self, player):
        pass

    def restore(self, player):
        pass

    def process(self):
        pass


class FakePlayer:
    def __init__(self, i, deck, language):
        self.deck = {"cards": deck}
        self.duel_player = i
        self.cdb = glb.server.db
        self.language = language
        self.watching = False
        self.seen_waiting = False
        self.soundpack = False
        self.connection = Connection(self)

    _ = lambda self, t: t

    def notify(self, arg1, *args, **kwargs):
        if arg1 == DuelReader:
            func = args[0]
            chosen = input()
            func(Response(chosen, self))
        elif isinstance(arg1, DuelMenu):
            chosen = input()
            arg1.huh(Response(chosen, self))
        elif arg1 == yes_or_no_parser:
            opt, yes = args[0], args[1]
            chosen = input()
            yes_or_no_parser(opt, yes, **kwargs).huh(Response(chosen, self))
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
        should_decide = arg1 == DuelReader or isinstance(arg1, DuelMenu) or arg1 == yes_or_no_parser
        if should_decide:
            if arg1 == DuelReader:
                func, options = args[0], args[1]

                msg = re.search(r'<function (\w+)\.<locals>\.', str(func)).group(1)
                if msg == 'handle_error':
                    msg = "select_sum"
                self.statistic[msg] += 1
                print(msg)
                    # chosen = input()
                chosen = random.choice(options)
                print(self.duel_player, "chose", chosen, "in", options)
                caller = Response(chosen, self)
                func(caller)

            elif isinstance(arg1, DuelMenu):
                title = arg1.title
                if title.startswith("Select option"):
                    msg = "select_option"
                elif title.startswith("Select position"):
                    msg = "select_position"
                else:
                    raise ValueError("DuelMenu with unknown title: ", title)
                self.statistic[msg] += 1
                print(msg)

                options = [ str(x + 1) for x in range(len(arg1.items))]
                chosen = random.choice(options)
                print(self.duel_player, "chose", chosen, "in", options)
                caller = Response(chosen, self)
                arg1.huh(caller)

            elif arg1 == yes_or_no_parser:
                opt, yes = args[0], args[1]

                if "effect" in opt:
                    msg = "select_effectyn"
                else:
                    msg = "yesno"
                self.statistic[msg] += 1
                print(msg)

                options = ["y", "n"]
                chosen = random.choice(options)
                print(self.duel_player, "chose", chosen, "in", options)
                caller = Response(chosen, self)
                yes_or_no_parser(opt, yes, **kwargs).huh(caller)
        else:
            print(self.duel_player, arg1)


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
    args = parser.parse_args()

    decks = [load_deck(args.deck1), load_deck(args.deck2)]

    lang = args.lang
    short = lang_short[lang]

    glb.language_handler = LanguageHandler()
    glb.language_handler.add(lang, short)
    glb.language_handler.set_primary_language(lang)
    glb.server = server.Server()
    glb.server.db = sqlite3.connect(f"locale/{short}/cards.cdb")
    glb.server.db.row_factory = sqlite3.Row

    duel = dm.Duel()
    global g_duel
    g_duel = duel
    duel.room = FakeRoom()
    config = {"players": ["Alice", "Bob"], "decks": decks}
    players = [player_factory[args.p1](0, config["decks"][0], lang), player_factory[args.p2](1, config["decks"][1], lang)]
    for i, name in enumerate(config["players"]):
        players[i].nickname = name
        duel.load_deck(players[i])
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
