import time

import numpy as np
import gymnasium as gym

import torch
import optree

from ygo.rl.utils import RecordEpisodeStatistics
from ygo.envs import glb
from ygo.rl.agent import Agent


lang = "english"

glb.init(lang)

deck = "../deck/OldSchool.ydk"
glb.db.init_from_deck(deck)


def make_env():
    env = gym.make(
        "yugioh-ai/YGO-v0",
        deck1=deck,
        deck2=deck,
        player=0,
        verbose=False
    )
    return env


env = make_env()
env.reset()

agent = Agent(128, 2, 2)

m = 16
env = gym.vector.AsyncVectorEnv([make_env for _ in range(m)])
env = RecordEpisodeStatistics(env)

obs = env.reset()
obs['global'] = obs['global'].astype(np.float32)
obs = optree.tree_map(lambda x: torch.from_numpy(x), obs)
output = agent(obs)
print(output.shape)

env.close()