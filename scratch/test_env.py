import time
import random

import numpy as np
import gymnasium as gym

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

agent = Agent(128, 2, 2)

n = 10000
start = time.time()

avg_returns = []
lengths = []

obs = env.reset()[0]

action = 0
j = 0
for i in range(n):
    obs, reward, terminated, trunc, info = env.step(action)
    done = terminated or trunc
    j += 1
    if done:
        env.reset()
        action = 0
        avg_returns.append(reward)
        lengths.append(j)
        print(f"episodic_length={j}, win_rate={np.average(avg_returns)}")
        j = 0
    else:
        action = random.randint(0, len(info['options']) - 1)
        # action = 0


total_time = time.time() - start
print(f"FPS: {n / total_time}")
print(f"avg_episodic_length={np.average(lengths)}")