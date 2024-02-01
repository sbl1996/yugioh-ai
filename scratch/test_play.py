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


envs = envpool2.make(
    task_id='YGOPro-v0',
    env_type="gymnasium",
    num_envs=1,
    seed=seed,
    deck1="OldSchool",
    deck2="OldSchool",
    verbose=True,
    play_mode='human',
)
envs.num_envs = 1
envs = RecordEpisodeStatistics(envs)

next_obs, infos = envs.reset()

while True:
    num_options = infos['num_options']
    actions = [np.random.randint(0, num_options[i]) for i in range(len(num_options))]
    actions = np.array(actions)
    obs = next_obs
    next_obs, rewards, dones, infos = envs.step(actions)
    # print(obs, next_obs, rewards, dones, infos)
    
    for idx, d in enumerate(dones):
        if d:
            infos['num_options'][idx] = 1