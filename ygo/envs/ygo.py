import numpy as np

import gymnasium as gym
from gymnasium import spaces

from ygo.envs.duel import Player, Duel, ActionRequired
from ygo.envs import glb
from ygo.utils import load_deck


class Response:
    def __init__(self, text):
        self.text = text


class FakePlayer(Player):

    def notify(self, arg1, *args, **kwargs):
        if self.verbose:
            print(self.duel_player, arg1)
    

class YGOEnv(gym.Env):

    def __init__(self, deck1, deck2, player=0, mode='single', verbose=False):
        self.mode = mode
        self.verbose = verbose

        # Observations are dictionaries with the agent's and the target's location.
        # Each location is encoded as an element of {0, ..., `size`}^2, i.e. MultiDiscrete([size, size]).
        self.observation_space = spaces.Dict(
            {
                "agent": spaces.Box(0, 3, shape=(2,), dtype=int),
                "target": spaces.Box(0, 3, shape=(2,), dtype=int),
            }
        )

        # We have 4 actions, corresponding to "right", "up", "left", "down"
        self.action_space = spaces.Discrete(4)

        self._player = player

        self.deck1 = load_deck(deck1)
        self.deck2 = load_deck(deck2)

    def _get_obs(self):
        agent_location = np.random.randint(0, 3, size=(2,))
        target_location = np.random.randint(0, 3, size=(2,))
        return {"agent": agent_location, "target": target_location}

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
                        if self.duel.tp == self._player:
                            self._action_required = ret
                            return
                        else:
                            ar = ret
                            options = ar.options
                            option = options[0]
                            ar.callback(Response(option))
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