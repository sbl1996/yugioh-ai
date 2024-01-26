import time

import numpy as np
import gymnasium as gym

import torch

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

n = 1000 
global_step = 0
start = time.time()

avg_returns = []

obs = env.reset()[0]
obs['global'] = obs['global'].astype(np.float32)

action = np.zeros((m,), dtype=np.int32)
for i in range(n):
    global_step += m
    obs, reward, dones, info = env.step(action)
    action = np.zeros((m,), dtype=np.int32)

    for idx, d in enumerate(dones):
        if d:
            print(f"global_step={global_step}, episodic_return={info['r'][idx]}")
            avg_returns.append(info["r"][idx])
            print(f"avg_episodic_return={np.average(avg_returns)}")
            print(f"episodic_length={info['l'][idx]}")
            print(f"episodic_return={info['r'][idx]}")

total_time = time.time() - start
print(f"FPS: {global_step / total_time}")