import time
import itertools
import random
import sqlite3
import argparse
import re
from collections import defaultdict

from ygo import duel as dm
from ygo import globals as glb
from ygo.language_handler import LanguageHandler
from ygo.constants import LOCATION


class Response:
    def __init__(self, text):
        self.text = text


class FakePlayer(dm.Player):

    def notify(self, arg1, *args, **kwargs):
        if arg1 == dm.Decision:
            func = args[0]
            chosen = input()
            func(Response(chosen))
        else:
            print(self.duel_player, arg1)


class RandomAI(FakePlayer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.statistic = defaultdict(int)

    def notify(self, arg1, *args, **kwargs):
        if arg1 == dm.Decision:
            func, options = args[0], args[1]

            msg = re.search(r'<function (\w+)\.<locals>\.', str(func)).group(1)
            self.statistic[msg] += 1
            chosen = random.choice(options)
            if self.verbose:
                print(msg)
                print(self.duel_player, "chose", chosen, "in", options)
            caller = Response(chosen)
            func(caller)
        else:
            if self.verbose:
                print(self.duel_player, arg1)


def load_deck(fn):
    with open(fn) as f:
        lines = f.readlines()
        noside = itertools.takewhile(lambda x: "side" not in x, lines)
        deck = [int(line) for line in  noside if line[:-1].isdigit()]
        return deck

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
    parser.add_argument("--verbose", help="verbose", action="store_true")
    parser.add_argument("--repeat", help="the number of times to repeat the duel", type=int, default=1)
    args = parser.parse_args()
    if args.seed is None:
        args.seed = int(time.time())
    print("seed: ", args.seed)
    random.seed(args.seed)

    lang = args.lang
    short = lang_short[lang]

    glb.language_handler = LanguageHandler()
    glb.language_handler.add(lang, short)
    glb.language_handler.set_primary_language(lang)
    glb.db = sqlite3.connect(f"locale/{short}/cards.cdb")
    glb.db.row_factory = sqlite3.Row

    configs = [
        # nickname, deck, type, lp
        ["Alice", args.deck1, args.p1, args.lp1],
        ["Bob", args.deck2, args.p2, args.lp2],
    ]
    players = [
        player_factory[type](load_deck(deck), nickname, lp)
        for nickname, deck, type, lp in configs
    ]

    for i in range(args.repeat):
        duel = dm.Duel()
        duel.verbose = args.verbose
        for i, player in enumerate(players):
            duel.set_player(i, player)
        duel.build_unique_cards()

        duel.start()

        print(duel.lp)
    # print(duel.players[0].statistic)
    # print(duel.players[1].statistic)


if __name__ == "__main__":
    main()