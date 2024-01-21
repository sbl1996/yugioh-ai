import numpy as np

import gymnasium as gym
from gymnasium import spaces

from ygo.envs.duel import Player, Duel, ActionRequired, lib
from ygo.envs import glb
from ygo.utils import load_deck
from ygo.constants import LOCATION, location2str, position2str, type2str, attribute2str, race2str, PHASES


float2ids = {
    i: np.unpackbits(np.array([i], dtype=np.uint16).view(np.uint8)).reshape(16)
    for i in range(0, 100000 // 25)
}

def float2feat(x):
    return float2ids[int(x) // 25]

def one_hot(x, n):
    return np.eye(n, dtype=np.uint8)[x]

_types = np.array(list(type2str.keys()), dtype=np.uint32)

def type2id(v):
    return np.minimum((_types & v).astype(np.uint8), 1)

phase2id = {
    p: one_hot(i, 10)
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


class FakePlayer(Player):

    def notify(self, arg1, *args, **kwargs):
        if self.verbose:
            print(self.duel_player, arg1)
    

class YGOEnv(gym.Env):

    def __init__(self, deck1, deck2, player=0, mode='single', verbose=False, max_actions=16):
        self.mode = mode
        self.verbose = verbose
        self.max_actions = max_actions

        self.observation_space = spaces.Dict(
            {
                "cards": spaces.Box(0, 255, shape=(55 * 2, 65), dtype=np.uint8),
                "global": spaces.Box(0, 255, shape=(44,), dtype=np.uint8),
                "actions": spaces.Box(0, 255, shape=(max_actions, 7), dtype=np.uint8),
            }
        )

        self.action_space = spaces.Discrete(max_actions)

        self._player = player

        self.deck1 = load_deck(deck1)
        self.deck2 = load_deck(deck2)

        self._action_required: ActionRequired = None

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
                feat[offset:offset+n_cards, 1] = 1
                feat[offset:offset+n_cards, 2] = location2id[location]
                offset += n_cards
            else:
                cards = duel.get_cards_in_location(player, location)
                for card in cards:
                    seq = card.sequence + 1
                    feat[offset, 0] = glb.db.get_id(card.code)
                    feat[offset, 1] = 1 if opponent else 0
                    feat[offset, 2] = location2id[card.location]
                    feat[offset, 3] = seq
                    feat[offset, 4] = position2id[card.position]
                    feat[offset, 5] = attribute2id[card.attribute]
                    feat[offset, 6] = race2id[card.race]
                    feat[offset, 7] = card.level
                    feat[offset, 8:33] = type2id(card.type)
                    feat[offset, 33:49] = float2feat(card.attack // 25)
                    feat[offset, 49:65] = float2feat(card.defense // 25)
                    offset += 1

                    spec = "o" if opponent else ""
                    spec += location2spec[card.location]
                    spec += str(seq)
                    spec2index[spec] = offset

    def _set_obs_of_global(self, feat, player, opponent):
        duel = self.duel
        me, oppo = (player, 1 - player) if not opponent else (1 - player, player)
        feat[0:16] = float2feat(duel.lp[me])
        feat[16:32] = float2feat(duel.lp[oppo])
        feat[32:42] = phase2id[self.duel.current_phase]
        feat[42] = 1 if me == 0 else 0
        feat[43] = me == duel.tp

    def _set_obs_of_action(
        self, feat, i, msg, spec=None, act=None, yesno=None, phase=None, cancel=None, position=None):
        if spec is not None:
            feat[i, 0] = self._spec2index[spec]
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

    def _set_obs_of_actions(self, feat):
        ar = self._action_required
        msg = ar.msg
        options = ar.options
        if len(options) > self.max_actions:
            print(msg, options)
            raise NotImplementedError("Too many options")
        if msg == 'idle_action':
            for i, option in enumerate(options):
                if option in ['b', 'e']:
                    self._set_obs_of_action(feat, i, msg, phase=option)
                else:
                    spec, act = option.split(" ")
                    self._set_obs_of_action(feat, i, msg, spec=spec, act=act)
        elif msg == 'select_chain':
            for i, option in enumerate(options):
                if option == 'c':
                    self._set_obs_of_action(feat, i, msg, cancel=option)
                else:
                    self._set_obs_of_action(feat, i, msg, spec=option)
        elif msg == 'select_card' or msg == 'select_tribute':
            # TODO: Multi-select
            for i, option in enumerate(options):
                spec = option.split(" ")[0]
                self._set_obs_of_action(feat, i, msg, spec=spec)
        elif msg == 'select_position':
            for i, option in enumerate(options):
                self._set_obs_of_action(feat, i, msg, position=option)
        elif msg == 'select_effectyn' or msg == 'yesno':
            for i, option in enumerate(options):
                self._set_obs_of_action(feat, i, msg, yesno=option)
        elif msg == 'select_battlecmd':
            for i, option in enumerate(options):
                if option in ['m', 'e']:
                    self._set_obs_of_action(feat, i, msg, phase=option)
                else:
                    spec, act = option.split(" ")
                    self._set_obs_of_action(feat, i, msg, spec=spec, act=act)
        else:
            raise NotImplementedError(f"Unknown message: {msg}")

    def _get_obs(self):
        card_feats = np.zeros((55 * 2, 65), dtype=np.uint8)
        global_feats = np.zeros(44, dtype=np.uint8)
        action_feats = np.zeros((self.max_actions, 7), dtype=np.uint8)

        if self.duel.duel is not None:
            self._spec2index = {}
            self._set_obs_of_card(card_feats, self._spec2index, self._player, False)
            self._set_obs_of_card(card_feats, self._spec2index, 1 - self._player, True)
            self._set_obs_of_global(global_feats, self._player, False)
            self._set_obs_of_actions(action_feats)
        return {"cards": card_feats, "global": global_feats, "actions": action_feats}

    def _get_info(self):
        options = None
        if self._action_required:
            options = self._action_required.options
        return {
            "options": options,
        }

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        configs = [
            ["Alice", self.deck1, 8000],
            ["Bob", self.deck2, 8000],
        ]
        players = [
            FakePlayer(deck, nickname, lp)
            for nickname, deck, lp in configs
        ]

        self._action_required = None
        self._res = None
        self._terminated = False

        self.duel = Duel(seed=seed, verbose=self.verbose)
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
                self.res = res
            else:
                skip_process = False
            while data:
                msg = int(data[0])
                fn = glb.message_map.get(msg, None)
                if fn:
                    ret = fn(self.duel, data)
                    if isinstance(ret, ActionRequired):
                        ar = ret
                        if self.duel.tp == self._player:
                            if ret.msg == 'select_place':
                                ar.callback(Response(ar.options[0]))
                                data = ar.data
                            elif len(ar.options) == 1:
                                ar.callback(Response(ar.options[0]))
                                data = ar.data
                            else:
                                self._action_required = ar
                                return
                        else:
                            ar.callback(Response(ar.options[0]))
                            data = ar.data
                    else:
                        data = ret
                else:
                    data = b''
            if self.res & 0x20000:
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
        data = ar.data

        self.next(process_first=False, data=data)

        terminated = self._terminated
        reward = 1 if terminated and self.duel.winner == self._player else 0

        observation = self._get_obs()
        info = self._get_info()

        return observation, reward, terminated, False, info

    def close(self):
        pass