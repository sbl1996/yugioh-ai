import time
import random
import numpy as np
from dataclasses import dataclass

import tyro

import envpool2

from ygo.rl.utils import RecordEpisodeStatistics
from ygo.utils import init_ygopro


@dataclass
class Args:
    seed: int = 1
    """the random seed"""
    env_id: str = "YGOPro-v0"
    """the id of the environment"""
    deck: str = "../deck/OldSchool.ydk"
    """the deck file to use"""
    code_list_file: str = "code_list.txt"
    """the code list file for card embeddings"""
    lang: str = "english"
    """the language to use"""
    max_options: int = 24
    """the maximum number of options"""
    max_steps: int = 1000
    """the maximum number of steps"""
    num_envs: int = 1
    """the number of parallel game environments"""
    verbose: bool = False
    """whether to print debug information"""
    play: bool = False
    """whether to play the game"""


if __name__ == "__main__":
    args = tyro.cli(Args)

    if args.play:
        args.num_envs = 1
        args.verbose = True

    deck = init_ygopro(args.lang, args.deck, args.code_list_file)

    seed = args.seed
    random.seed(seed)
    np.random.seed(seed)

    num_envs = args.num_envs

    envs = envpool2.make(
        task_id=args.env_id,
        env_type="gymnasium",
        num_envs=num_envs,
        deck1=deck,
        deck2=deck,
        seed=seed,
        verbose=args.verbose,
        play_mode='human' if args.play else 'bot',
    )
    envs.num_envs = num_envs
    envs = RecordEpisodeStatistics(envs)

    next_obs, infos = envs.reset()

    step = 0
    max_steps = args.max_steps
    start = time.time()
    results = []
    while True:
        if step == int(max_steps * 0.1):
            start = time.time()
            
        num_options = infos['num_options']
        actions = [np.random.randint(0, num_options[i]) for i in range(len(num_options))]
        actions = np.array(actions)
        obs = next_obs
        next_obs, rewards, dones, infos = envs.step(actions)
        # print(obs, next_obs, rewards, dones, infos)
        # print(next_obs['actions_'])
        # print(next_obs['history_actions_'])

        for idx, d in enumerate(dones):
            if d:
                win = 1 if infos['r'][idx] == 1.0 else 0
                results.append(win)

        step += 1
        if not args.play and step > max_steps:
            break
    
    if not args.play and args.verbose:
        end = time.time()
        print("FPS: ", (max_steps * num_envs) / (end - start))
        # print("Win rate: ", np.mean(results))