import time
import os
import random
from typing import Optional, Literal
from dataclasses import dataclass

import envpool2
import numpy as np

import optree

import tyro

import torch

from ygo.utils import init_ygopro
from ygo.rl.utils import RecordEpisodeStatistics
from ygo.rl.agent import Agent


@dataclass
class Args:
    seed: int = 1
    """the random seed"""
    torch_deterministic: bool = True
    """if toggled, `torch.backends.cudnn.deterministic=False`"""
    cuda: bool = True
    """if toggled, cuda will be enabled by default"""

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

    num_episodes: int = 1024
    """the number of episodes to run"""
    num_envs: int = 64
    """the number of parallel game environments"""
    verbose: bool = False
    """whether to print debug information"""
    play: bool = False
    """whether to play the game"""

    bot_strategy: Literal["random", "greedy"] = "greedy"
    """the strategy to use for the bot if agent is not used"""

    agent: bool = False
    """whether to use the agent"""
    checkpoint: str = "checkpoints/agent.pt"
    """the checkpoint to load"""
    embedding_file: str = "embeddings_en.npy"
    """the embedding file for card embeddings"""

    compile: bool = False
    """if toggled, the model will be compiled"""
    torch_threads: Optional[int] = None
    """the number of threads to use for torch, defaults to ($OMP_NUM_THREADS or 2) * world_size"""
    env_threads: Optional[int] = 16
    """the number of threads to use for envpool, defaults to `num_envs`"""


if __name__ == "__main__":
    args = tyro.cli(Args)
    args.env_threads = min(args.env_threads or args.num_envs, args.num_envs)
    args.torch_threads = args.torch_threads or int(os.getenv("OMP_NUM_THREADS", "4"))

    if args.play:
        args.num_envs = 1
        args.verbose = True

    deck = init_ygopro(args.lang, args.deck, args.code_list_file)

    seed = args.seed
    random.seed(seed)
    np.random.seed(seed)

    if args.agent:
        torch.manual_seed(args.seed)
        torch.backends.cudnn.deterministic = args.torch_deterministic

        torch.set_num_threads(args.torch_threads)
        torch.set_float32_matmul_precision('high')

        device = torch.device("cuda" if torch.cuda.is_available() and args.cuda else "cpu")

    num_envs = args.num_envs

    envs = envpool2.make(
        task_id=args.env_id,
        env_type="gymnasium",
        num_envs=num_envs,
        num_threads=args.env_threads,
        deck1=deck,
        deck2=deck,
        seed=seed,
        verbose=args.verbose,
        play_mode='human' if args.play else 'bot',
    )
    envs.num_envs = num_envs
    envs = RecordEpisodeStatistics(envs)

    if args.agent:
        embeddings = np.load(args.embedding_file)
        agent = Agent(128, 2, 2, 0, embeddings.shape).to(device)
        agent = agent.eval()
        state_dict = torch.load(args.checkpoint, map_location=device)

        if args.compile:
            agent = torch.compile(agent, mode='reduce-overhead')
            agent.load_state_dict(state_dict)
        else:
            prefix = "_orig_mod."
            state_dict = {k[len(prefix):] if k.startswith(prefix) else k: v for k, v in state_dict.items()}
            agent.load_state_dict(state_dict)

            obs = optree.tree_map(lambda x: torch.from_numpy(x).to(device=device), envs.reset()[0])
            with torch.no_grad():
                traced_model = torch.jit.trace(agent, (obs,), check_tolerance=False, check_trace=False)
            agent = torch.jit.optimize_for_inference(traced_model)

    obs, infos = envs.reset()

    episode_rewards = []
    episode_lengths = []

    step = 0
    start = time.time()
    start_step = step

    model_time = env_time = 0
    while True:
        if start_step == 0 and len(episode_lengths) > int(args.num_episodes * 0.1):
            start = time.time()
            start_step = step
            model_time = env_time = 0

        if args.agent:
            _start = time.time()
            obs = optree.tree_map(lambda x: torch.from_numpy(x).to(device=device), obs)
            with torch.no_grad():
                values = agent(obs)[0]
            actions = torch.argmax(values, dim=1).cpu().numpy()
            model_time += time.time() - _start
        else:
            if args.bot_strategy == "random":
                actions = np.random.randint(infos['num_options'])
            else:
                actions = np.zeros(num_envs, dtype=np.int32)

        _start = time.time()
        obs, rewards, dones, infos = envs.step(actions)
        env_time += time.time() - _start

        step += 1

        for idx, d in enumerate(dones):
            if d:
                episode_length = infos['l'][idx]
                episode_reward = infos['r'][idx]
                if episode_reward == -1:
                    episode_reward = 0

                episode_lengths.append(episode_length)
                episode_rewards.append(episode_reward)
                # print(f"Episode {len(episode_lengths)}: length={episode_length}, reward={episode_reward}")
        if len(episode_lengths) >= args.num_episodes:
            break

    print(f"avg_length={np.mean(episode_lengths)}, win_rate={np.mean(episode_rewards)}")
    if not args.play:
        total_time = time.time() - start
        total_steps = (step - start_step) * num_envs
        print(f"SPS: {total_steps / total_time:.0f}, total_steps: {total_steps}")
        print(f"total: {total_time:.4f}, model: {model_time:.4f}, env: {env_time:.4f}")
    