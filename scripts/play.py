import random
from dataclasses import dataclass

import gymnasium as gym
import numpy as np
import optree
import tyro

import torch

from ygo.envs import glb
from ygo.rl.agent import Agent
from ygo.rl.utils import CompatEnv


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

    deck: str = "../deck/OldSchool.ydk"
    """the deck to use"""
    lang: str = "english"
    """the language to use"""
    checkpoint: str = "checkpoints/agent.pt"
    """the checkpoint to load"""
    compile: bool = False
    """if toggled, the model will be compiled"""


if __name__ == "__main__":
    args = tyro.cli(Args)

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.backends.cudnn.deterministic = True
    torch.set_float32_matmul_precision('high')

    device = torch.device("cuda" if torch.cuda.is_available() and args.cuda else "cpu")

    glb.init(args.lang)
    deck = args.deck
    glb.db.init_from_deck(deck)

    env = gym.make(
        "yugioh-ai/YGO-v0",
        deck1=deck,
        deck2=deck,
        player='random',
        verbose=True,
        mode='eval',
    )
    env = CompatEnv(env)

    agent = Agent(128, 2, 2).to(device)
    # state_dict = torch.load(args.checkpoint, map_location=device)

    # if args.compile:
    #     agent = torch.compile(agent, mode='reduce-overhead')
    # else:
    #     prefix = "_orig_mod."
    #     state_dict = {k[len(prefix):] if k.startswith(prefix) else k: v for k, v in state_dict.items()}
    # agent.load_state_dict(state_dict)

    obs, info = env.reset(seed=args.seed)
    done = False
    while not done:
        obs = optree.tree_map(lambda x: torch.from_numpy(x).unsqueeze(0).to(device=device), obs)
        with torch.no_grad():
            values = agent(obs)
        
        action = torch.argmax(values, dim=1).cpu().numpy()[0]
        next_obs, reward, done, info = env.step(action)
        obs = next_obs