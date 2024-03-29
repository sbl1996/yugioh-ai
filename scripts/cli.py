import os
import time
import itertools
import random
import sqlite3
import argparse
import re
from collections import defaultdict

from ygo.game import duel as dm
from ygo.game import globals as glb
from ygo.game.language_handler import LanguageHandler
from ygo.utils import get_root_directory


class Response:
    def __init__(self, text):
        self.text = text


class HumanPlayer(dm.Player):

    def notify(self, arg1, *args, **kwargs):
        if arg1 == dm.Decision:
            func = args[0]
            chosen = input()
            func(Response(chosen))
        else:
            print(self.duel_player, arg1)


class RandomAI(dm.Player):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.statistic = defaultdict(int)

    def notify(self, arg1, *args, **kwargs):
        if arg1 == dm.Decision:
            func, options = args[0], args[1]

            func_name = re.search(r'<function (\w+)\.<locals>\.', str(func)).group(1)
            self.statistic[func_name] += 1
            chosen = random.choice(options)
            if self.verbose:
                print(f"Action: {func_name}")
                print(self.duel_player, "chose", chosen, "in", options)
            caller = Response(chosen)
            func(caller)
        else:
            if self.verbose:
                print(self.duel_player, arg1)


class GreedyAI(dm.Player):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.statistic = defaultdict(int)

    def notify(self, arg1, *args, **kwargs):
        if arg1 == dm.Decision:
            func, options = args[0], args[1]

            func_name = re.search(r'<function (\w+)\.<locals>\.', str(func)).group(1)
            self.statistic[func_name] += 1
            chosen = options[0]
            if self.verbose:
                print(f"Action: {func_name}")
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


def main():
    player_factory = {
        'manual': HumanPlayer,
        'random': RandomAI,
        'greedy': GreedyAI,
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
    parser.add_argument("--p1", help="type of player 1", type=str, default='greedy', choices=player_factory.keys())
    parser.add_argument("--p2", help="type of player 1", type=str, default='greedy', choices=player_factory.keys())
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
    database = os.path.join(get_root_directory(), 'locale', short, 'cards.cdb')
    glb.db = sqlite3.connect(database)
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

    results = [0, 0]
    reasons = defaultdict(int)

    for i in range(args.repeat):
        duel = dm.Duel()
        duel.verbose = args.verbose
        for j, player in enumerate(players):
            duel.set_player(j, player)
            player.duel = duel
        duel.build_unique_cards()

        duel.start()

        results[duel.winner] += 1
        reasons[duel.win_reason] += 1

        if duel.verbose:
            print(duel.lp)
            for i in range(2):
                print(duel.players[i].statistic)
                duel.players[i].statistic = defaultdict(int)
        print([ r / (i + 1) for r in results], reasons)
    print(results)
    print(reasons)

if __name__ == "__main__":
    main()