import time
import sqlite3
import random

import numpy as np

from ygo import globals as glb
from ygo.language_handler import LanguageHandler


import gymnasium as gym

lang = "english"
short = "en"

glb.language_handler = LanguageHandler()
glb.language_handler.add(lang, short)
glb.language_handler.set_primary_language(lang)
glb.db = sqlite3.connect(f"locale/{short}/cards.cdb")
glb.db.row_factory = sqlite3.Row

deck = "deck/OldSchool.ydk"

def make_env():
    env = gym.make(
        "yugioh-ai/YGO-v0",
        deck1=deck,
        deck2=deck,
        player=0,
        verbose=False
    )
    return env

m = 16
env = gym.vector.AsyncVectorEnv([make_env for _ in range(m)])

n = 100
win = 0
total_step = 0
start = time.time()

for i in range(100):
    env.reset()
    action = np.zeros((m,), dtype=np.int32)
    step = 0
    while True:
        obs, reward, terminated, truncated, info = env.step(action)
        print(info)
        # action = random.randint(0, len(info['action_required'].options) - 1)
        action = np.zeros((m,), dtype=np.int32)
        # print("reward:", reward)
        # print("info:", info)
        done = np.
        done = terminated or truncated
        step += 1
        if done:
            win += reward
            total_step += step
            print(f"Step: {step}, Reward: {reward}, Win rate: {win / (i + 1)}")
            break
total_time = time.time() - start
print(f"Win rate: {win / n}")
print(f"Average step: {total_step / n}")
print(f"FPS: {total_step / total_time}")