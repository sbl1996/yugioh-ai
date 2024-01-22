import random
import numpy as np

import gymnasium as gym
import optree
import torch

from ygo.envs import glb
from ygo.rl.agent import Agent
from ygo.rl.utils import CompatEnv


if __name__ == "__main__":
    seed = 0
    device = torch.device("cuda")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.set_float32_matmul_precision('high')


    lang = "chinese"
    glb.init(lang)
    deck = "deck/OldSchool.ydk"
    glb.db.init_from_deck(deck)

    env = gym.make(
        "yugioh-ai/YGO-v0",
        deck1=deck,
        deck2=deck,
        player=0,
        verbose=True,
        mode='eval',
    )
    env = CompatEnv(env)


    agent = Agent(128, 2, 2).to(device)
    agent = torch.compile(agent, mode='reduce-overhead')
    agent.load_state_dict(torch.load("scratch/checkpoints/1.pt", map_location=device))

    obs, info = env.reset(seed=seed)

    done = False
    while not done:
        obs = optree.tree_map(lambda x: torch.from_numpy(x).unsqueeze(0).to(device=device), obs)
        with torch.no_grad():
            values = agent(obs)
        
        action = torch.argmax(values, dim=1).cpu().numpy()[0]
        next_obs, reward, done, info = env.step(action)
        obs = next_obs
    print(reward)
