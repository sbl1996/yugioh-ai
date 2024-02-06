import re
import numpy as np
import gymnasium as gym


class RecordEpisodeStatistics(gym.Wrapper):
    def __init__(self, env):
        super().__init__(env)
        self.num_envs = getattr(env, "num_envs", 1)
        self.episode_returns = None
        self.episode_lengths = None

    def reset(self, **kwargs):
        observations, infos = self.env.reset(**kwargs)
        self.episode_returns = np.zeros(self.num_envs, dtype=np.float32)
        self.episode_lengths = np.zeros(self.num_envs, dtype=np.int32)
        self.returned_episode_returns = np.zeros(self.num_envs, dtype=np.float32)
        self.returned_episode_lengths = np.zeros(self.num_envs, dtype=np.int32)
        return observations, infos

    def step(self, action):
        observations, rewards, terminated, truncated, infos = super().step(action)
        dones = np.logical_or(terminated, truncated)
        self.episode_returns += rewards
        self.episode_lengths += 1
        self.returned_episode_returns[:] = self.episode_returns
        self.returned_episode_lengths[:] = self.episode_lengths
        self.episode_returns *= 1 - dones
        self.episode_lengths *= 1 - dones
        infos["r"] = self.returned_episode_returns
        infos["l"] = self.returned_episode_lengths
        return (
            observations,
            rewards,
            dones,
            infos,
        )
    

class CompatEnv(gym.Wrapper):

    def reset(self, **kwargs):
        observations, infos = super().reset(**kwargs)
        return observations, infos

    def step(self, action):
        observations, rewards, terminated, truncated, infos = self.env.step(action)
        dones = np.logical_or(terminated, truncated)
        return (
            observations,
            rewards,
            dones,
            infos,
        )
    

def split_param_groups(model, regex):
    embed_params = []
    other_params = []
    for name, param in model.named_parameters():
        if re.search(regex, name):
            embed_params.append(param)
        else:
            other_params.append(param)
    return [
        {'params': embed_params}, {'params': other_params}
    ]


class Elo:

    def __init__(self, k = 10, r0 = 1500, r1 = 1500):
        self.r0 = r0
        self.r1 = r1
        self.k = k

    def update(self, winner):
        diff = self.k * (1 - self.expect_result(self.r0, self.r1))
        if winner == 1:
            diff = -diff
        self.r0 += diff
        self.r1 -= diff

    def expect_result(self, p0, p1):
        exp = (p0 - p1) / 400.0
        return 1 / ((10.0 ** (exp)) + 1)