import time
import random
import numpy as np

import envpool2

from ygo.rl.utils import RecordEpisodeStatistics

from envpool2.ygopro import init_module

db_path = "../locale/zh/cards.cdb"
decks = {
    "OldSchool": "../deck/OldSchool.ydk",
}

init_module(db_path, decks)

seed = 1
random.seed(seed)
np.random.seed(seed)

play = True
num_envs = 64
num_threads = num_envs // 2

envs = envpool2.make(
    task_id='YGOPro-v0',
    env_type="gymnasium",
    num_envs=num_envs,
    num_threads=num_threads,
    seed=seed,
    deck1="OldSchool",
    deck2="OldSchool",
    # verbose=True,
    # play=play,
)
envs.num_envs = num_envs
envs = RecordEpisodeStatistics(envs)

next_obs, infos = envs.reset()

s = 0
max_steps = 1000 if play else 10
warmup_starts = max_steps // 10
start = time.time()
while s < max_steps:
    if s == warmup_starts:
        start = time.time()
    s += 1
    step_start = time.time()
    num_options = infos['num_options']
    actions = np.random.randint(num_options)
    actions = np.array(actions)
    obs = next_obs
    next_obs, rewards, dones, infos = envs.step(actions)
    # print(obs, next_obs, rewards, dones, infos)
    # for k, v in obs.items():
    #     print(k, v.tolist())
    # print(dones, infos)
    
    for idx, d in enumerate(dones):
        if d:
            infos['num_options'][idx] = 1

end = time.time()
total = end - start
print("FPS: ", (max_steps * num_envs) / total)