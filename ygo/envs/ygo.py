import random
import numpy as np

import gymnasium as gym
from gymnasium import spaces

from ygo.envs.duel import Player, Duel, ActionRequired, lib
from ygo.envs import glb
from ygo.utils import load_deck
from ygo.constants import LOCATION, location2str, position2str, type2str, attribute2str, race2str, PHASES


_types = np.array(list(type2str.keys()), dtype=np.uint32)

def type2id(v):
    return np.minimum((_types & v).astype(np.uint8), 1)

phase2id = {
    p: i
    for i, p in enumerate(PHASES)
}

position2id = {
    p: i + 1
    for i, p in enumerate(position2str)
}

location2id = {
    l: i + 1
    for i, l in enumerate(location2str)
}

location2spec = {
    LOCATION.DECK: "",
    LOCATION.HAND: "h",
    LOCATION.MZONE: "m",
    LOCATION.SZONE: "s",
    LOCATION.GRAVE: "g",
    LOCATION.EXTRA: "x",
    LOCATION.REMOVED: "r",
}

attribute2id = {
    a: i + 1
    for i, a in enumerate(list(attribute2str)[2:])
}
attribute2id[0] = 0

race2id = {
    r: i + 1
    for i, r in enumerate(list(race2str)[1:])
}
race2id[0] = 0


msg2id = {
    m: i + 1 for i, m in enumerate([
        "idle_action", "select_chain", "select_card", "select_tribute", "select_position", "select_effectyn", "yesno", "select_battlecmd",
    ])
}

cmd_act2id = {
    a: i + 1 for i, a in enumerate([
        "t", "r", "v", "c", "s", "m", "a",
    ])
}

cmd_phase2id = {
    a: i + 1 for i, a in enumerate([
        "b", "m", "e"
    ])
}

cmd_cancel2id = {
    a: i + 1 for i, a in enumerate([
        "c"
    ])
}

cmd_yesno2id = {
    a: i + 1 for i, a in enumerate([
        "y", "n"
    ])
}

class Response:
    def __init__(self, text):
        self.text = text


class GreedyAI(Player):

    def notify(self, arg1, *args, **kwargs):
        if isinstance(arg1, ActionRequired):
            ar = arg1
            chosen = ar.options[0]
            ar.callback(Response(chosen))
            return chosen
        elif self.verbose:
            print(self.duel_player, arg1)


class HumanPlayer(Player):

    def notify(self, arg1, *args, **kwargs):
        if isinstance(arg1, ActionRequired):
            ar = arg1
            options = ar.options
            print(self.duel_player, ar.msg)
            while True:
                chosen = input()
                if chosen in options:
                    break
                else:
                    print(self.duel_player, "Choose from ", options)
            ar.callback(Response(chosen))
        elif self.verbose:
            print(self.duel_player, arg1)


def float_transform(x):
    return divmod(x % 65536, 256)


class YGOEnv(gym.Env):

    def __init__(self, deck1, deck2, player='random', mode='train', verbose=False, max_actions=16):
        self.mode = mode
        self.verbose = verbose
        self.max_actions = max_actions
        self.player = player

        self.observation_space = spaces.Dict(
            {
                "cards": spaces.Box(0, 255, shape=(55 * 2, 37), dtype=np.uint8),
                "global": spaces.Box(0, 255, shape=(7,), dtype=np.uint8),
                "actions": spaces.Box(0, 255, shape=(max_actions, 7), dtype=np.uint8),
            }
        )

        self.action_space = spaces.Discrete(max_actions)

        self.deck1 = load_deck(deck1)
        self.deck2 = load_deck(deck2)

        self._player = None
        self._action_required: ActionRequired = None
        self._previous_action_feat = None
        self._previous_action_cids = np.zeros((self.max_actions,), dtype=np.uint32)

    def _set_obs_of_card(self, feat, spec2index, player, opponent):
        duel = self.duel
        offset = 55 if opponent else 0
        for location, hide_for_opponent in [
            (LOCATION.DECK, True),
            (LOCATION.HAND, True),
            (LOCATION.MZONE, False),
            (LOCATION.SZONE, False),
            (LOCATION.GRAVE, False),
            (LOCATION.REMOVED, False),
            (LOCATION.EXTRA, True),
            # (LOCATION.FZONE, False),
        ]:
            if opponent and hide_for_opponent:
                n_cards = lib.query_field_count(duel.duel, player, location)
                feat[offset:offset+n_cards, 1] = location2id[location]
                feat[offset:offset+n_cards, 3] = 1
                offset += n_cards
            else:
                cards = duel.get_cards_in_location(player, location)
                for card in cards:
                    # if offset == 94:
                    #     print(player, opponent, card.location, card.position, card.name)
                    seq = card.sequence + 1
                    feat[offset, 0] = glb.db.get_id(card.code)
                    feat[offset, 1] = location2id[card.location]
                    feat[offset, 2] = seq
                    feat[offset, 3] = 1 if opponent else 0
                    feat[offset, 4] = position2id[card.position]
                    feat[offset, 5] = attribute2id[card.attribute]
                    feat[offset, 6] = race2id[card.race]
                    feat[offset, 7] = card.level
                    feat[offset, 8:10] = float_transform(card.attack)
                    feat[offset, 10:12] = float_transform(card.defense)
                    feat[offset, 12:37] = type2id(card.type)
                    offset += 1

                    spec = "o" if opponent else ""
                    spec += location2spec[card.location]
                    spec += str(seq)
                    spec2index[spec] = offset

    def _set_obs_of_global(self, feat, player):
        duel = self.duel
        me, oppo = player, 1 - player
        feat[0:2] = float_transform(duel.lp[me])
        feat[2:4] = float_transform(duel.lp[oppo])
        feat[4] = phase2id[duel.current_phase]
        feat[5] = 1 if me == 0 else 0
        feat[6] = me == duel.tp

    def _set_obs_of_action_(
        self, feat, i, msg, spec=None, act=None, yesno=None, phase=None, cancel=None, position=None, spec2index=None):
        if spec is not None:
            feat[i, 0] = spec2index[spec]
        feat[i, 1] = msg2id[msg]
        if act is not None:
            feat[i, 2] = cmd_act2id[act]
        if yesno is not None:
            feat[i, 3] = cmd_yesno2id[yesno]
        if phase is not None:
            feat[i, 4] = cmd_phase2id[phase]
        if cancel is not None:
            feat[i, 5] = cmd_cancel2id[cancel]
        if position is not None:
            feat[i, 6] = int(position)

    def _set_obs_of_action(self, feat, i, msg, option):
        if msg == 'idle_action':
            if option in ['b', 'e']:
                self._set_obs_of_action_(feat, i, msg, phase=option)
            else:
                spec, act = option.split(" ")
                self._set_obs_of_action_(feat, i, msg, spec=spec, act=act, spec2index=self._spec2index)
        elif msg == 'select_chain':
            if option == 'c':
                self._set_obs_of_action_(feat, i, msg, cancel=option)
            else:
                self._set_obs_of_action_(feat, i, msg, spec=option, spec2index=self._spec2index)
        elif msg == 'select_card' or msg == 'select_tribute':
            # TODO: Multi-select
            spec = option.split(" ")[0]
            self._set_obs_of_action_(feat, i, msg, spec=spec, spec2index=self._spec2index)
        elif msg == 'select_position':
            self._set_obs_of_action_(feat, i, msg, position=option)
        elif msg == 'select_effectyn' or msg == 'yesno':
            self._set_obs_of_action_(feat, i, msg, yesno=option)
        elif msg == 'select_battlecmd':
            if option in ['m', 'e']:
                self._set_obs_of_action_(feat, i, msg, phase=option)
            else:
                spec, act = option.split(" ")
                self._set_obs_of_action_(feat, i, msg, spec=spec, act=act, spec2index=self._spec2index)
        else:
            raise NotImplementedError(f"Unknown message: {msg}")

    def _set_obs_of_actions(self, feat):
        ar = self._action_required
        msg = ar.msg
        options = ar.options
        if len(options) > self.max_actions:
            print(msg, options)
            options = random.sample(options, self.max_actions)
        for i, option in enumerate(options):
            self._set_obs_of_action(feat, i, msg, option)

    def _get_obs(self):
        feats = {
            key: np.zeros(space.shape, dtype=space.dtype)
            for key, space in self.observation_space.spaces.items()
        }

        if self.duel.duel is not None:
            self._spec2index = {}
            self._set_obs_of_card(feats["cards"], self._spec2index, self._player, False)
            self._set_obs_of_card(feats["cards"], self._spec2index, 1 - self._player, True)
            self._set_obs_of_global(feats["global"], self._player)
            self._set_obs_of_actions(feats["actions"])
        return feats

    def _get_info(self):
        options = None
        if self._action_required:
            options = self._action_required.options
        return {
            "options": options,
        }

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        if self.player == 'random':
            self._player = self._np_random.choice([0, 1])
        else:
            self._player = self.player
        configs = [
            ["Alice", self.deck1, 8000],
            ["Bob", self.deck2, 8000],
        ]
        player1 = GreedyAI
        player2 = GreedyAI if self.mode == 'train' else HumanPlayer
        if self._player == 1:
            player1, player2 = player2, player1
        configs[0].append(player1)
        configs[1].append(player2)
        players = [
            player_cls(deck, nickname, lp)
            for nickname, deck, lp, player_cls in configs
        ]

        self._action_required = None
        self._previous_action_feat = None
        self._res = None
        self._terminated = False

        self.duel = Duel(seed=seed, verbose=self.verbose, np_random=self._np_random)
        self.duel.init(players)

        self.next(process_first=True)

        observation = self._get_obs()
        info = self._get_info()
        return observation, info

    def next(self, process_first=True, data=None):
        if not process_first:
            assert data is not None
        skip_process = not process_first
        while self.duel.started:
            if not skip_process:
                res, data = self.duel.lib_process()
                self._res = res
            else:
                skip_process = False
            while data:
                msg = int(data[0])
                fn = glb.message_map.get(msg, None)
                if fn:
                    ret = fn(self.duel, data)
                    if isinstance(ret, ActionRequired):
                        ar = ret
                        if ar.player == self._player:
                            if ar.msg == 'select_place':
                                ar.callback(Response(ar.options[0]))
                                data = ar.data
                            elif len(ar.options) == 1:
                                ar.callback(Response(ar.options[0]))
                                data = ar.data
                            else:
                                self._action_required = ar
                                return
                        else:
                            self.duel.players[ar.player].notify(ar)
                            data = ar.data
                    else:
                        data = ret
                else:
                    data = b''
            if self._res & 0x20000:
                break
        self._terminated = True
        self._action_required = None

    def step(self, action):
        if self._terminated:
            raise RuntimeError("Episode is terminated")

        ar = self._action_required
        options = ar.options
        option = options[action]
        ar.callback(Response(option))
        if self.verbose:
            print("Action:", ar.msg)
            print(self._player, "chose", option, "in", options)
        data = ar.data

        self.next(process_first=False, data=data)

        terminated = self._terminated
        if terminated:
            reward = 1 if self.duel.winner == self._player else -1
        else:
            reward = 0

        observation = self._get_obs()
        info = self._get_info()

        return observation, reward, terminated, False, info

    def close(self):
        pass