import random
from dataclasses import dataclass

import gymnasium as gym
import numpy as np
import optree
import tyro

import torch

from ygo.rl.utils import RecordEpisodeStatistics
from ygo.envs import glb
from ygo.rl.agent import Agent


@dataclass
class Args:
    seed: int = 2
    """seed of the experiment"""
    torch_deterministic: bool = True
    """if toggled, `torch.backends.cudnn.deterministic=False`"""
    cuda: bool = True
    """if toggled, cuda will be enabled by default"""

    env_id: str = "yugioh-ai/YGO-v0"
    """the id of the environment"""
    num_episodes: int = 16
    """the number of episodes to run"""
    num_envs: int = 4
    """the number of parallel game environments"""
    eps: float = 0.0
    """the probability of random action"""

    deck: str = "../deck/OldSchool.ydk"
    """the deck to use"""
    checkpoint: str = "checkpoints/agent.pt"
    """the checkpoint to load"""
    compile: bool = False
    """if toggled, the model will be compiled"""


def make_env(env_id, deck, seed):
    def thunk():
        env = gym.make(
            env_id,
            deck1=deck,
            deck2=deck,
        )
        env.action_space.seed(seed)
        return env
    return thunk


if __name__ == "__main__":
    args = tyro.cli(Args)

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.backends.cudnn.deterministic = args.torch_deterministic
    torch.set_float32_matmul_precision('high')

    device = torch.device("cuda" if torch.cuda.is_available() and args.cuda else "cpu")

    glb.init("english")
    deck = args.deck
    glb.db.init_from_deck(deck)

    envs = gym.vector.SyncVectorEnv(
        [make_env(args.env_id, deck, args.seed + i) for i in range(args.num_envs)]
    )
    envs = RecordEpisodeStatistics(envs)
    obs_, infos_ = envs.reset(seed=args.seed)
    print(obs_['cards'][0, 94])

    agent = Agent(128, 2, 2).to(device)
    state_dict = torch.load(args.checkpoint, map_location=device)

    if args.compile:
        agent = torch.compile(agent, mode='reduce-overhead')
    else:
        prefix = "_orig_mod."
        state_dict = {k[len(prefix):] if k.startswith(prefix) else k: v for k, v in state_dict.items()}
    agent.load_state_dict(state_dict)

    episode_rewards = []
    episode_lengths = []
    obs, infos = envs.reset(seed=args.seed)
    while True:
        obs = optree.tree_map(lambda x: torch.from_numpy(x).to(device=device), obs)
        with torch.no_grad():
            values = agent(obs)
        actions = torch.argmax(values, dim=1).cpu().numpy()
        obs, rewards, dones, infos = envs.step(actions)

        for idx, d in enumerate(dones):
            if d:
                episode_length = infos['l'][idx]
                episode_reward = infos['r'][idx]
                if episode_reward == -1:
                    episode_reward = 0

                episode_lengths.append(episode_length)
                episode_rewards.append(episode_reward)
                print(f"Episode {len(episode_lengths)}: length={episode_length}, reward={episode_reward}")
        if len(episode_lengths) >= args.num_episodes:
            print(f"avg_length={np.mean(episode_lengths)}, win_rate={np.mean(episode_rewards)}")
            break
