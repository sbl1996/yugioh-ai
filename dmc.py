import os
import random
import time
from collections import deque
from dataclasses import dataclass

import gymnasium as gym
import numpy as np

import optree

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import tyro
from torch.utils.tensorboard import SummaryWriter

from ygo.rl.utils import RecordEpisodeStatistics
from ygo.rl.buffer import DMCDictBuffer
from ygo.envs import glb
from ygo.rl.agent import Agent


@dataclass
class Args:
    exp_name: str = os.path.basename(__file__)[: -len(".py")]
    """the name of this experiment"""
    seed: int = 1
    """seed of the experiment"""
    torch_deterministic: bool = True
    """if toggled, `torch.backends.cudnn.deterministic=False`"""
    cuda: bool = True
    """if toggled, cuda will be enabled by default"""

    # Algorithm specific arguments
    env_id: str = "yugioh-ai/YGO-v0"
    """the id of the environment"""
    total_timesteps: int = 500000
    """total timesteps of the experiments"""
    learning_rate: float = 2.5e-4
    """the learning rate of the optimizer"""
    num_envs: int = 4
    """the number of parallel game environments"""
    num_steps: int = 200
    """the number of steps per env per iteration"""
    max_steps: int = 200
    """the maximum number of steps per episode"""
    buffer_size: int = 5000
    """the replay memory buffer size"""
    gamma: float = 0.99
    """the discount factor gamma"""
    minibatch_size: int = 32
    """the mini-batch size"""
    eps: float = 0.05
    """the epsilon for exploration"""
    max_grad_norm: float = 0.5
    """the maximum norm for the gradient clipping"""

    # to be filled in runtime
    num_iterations: int = 0
    """the number of iterations (computed in runtime)"""

def layer_init(layer, std=np.sqrt(2), bias_const=0.0):
    torch.nn.init.orthogonal_(layer.weight, std)
    torch.nn.init.constant_(layer.bias, bias_const)
    return layer


def make_env(env_id, deck, seed):
    def thunk():
        env = gym.make(
            env_id,
            deck1=deck,
            deck2=deck,
            player=0,
            verbose=False
        )
        env = gym.wrappers.RecordEpisodeStatistics(env)
        env.action_space.seed(seed)

        return env

    return thunk


def linear_schedule(start_e: float, end_e: float, duration: int, t: int):
    slope = (end_e - start_e) / duration
    return max(slope * t + start_e, end_e)


if __name__ == "__main__":

    args = tyro.cli(Args)
    args.batch_size = args.num_envs * args.num_steps
    args.num_iterations = args.total_timesteps // args.batch_size

    run_name = f"{args.env_id}__{args.exp_name}__{args.seed}__{int(time.time())}"

    writer = SummaryWriter(f"runs/{run_name}")
    writer.add_text(
        "hyperparameters",
        "|param|value|\n|-|-|\n%s" % ("\n".join([f"|{key}|{value}|" for key, value in vars(args).items()])),
    )

    # TRY NOT TO MODIFY: seeding
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.backends.cudnn.deterministic = args.torch_deterministic

    device = torch.device("cuda" if torch.cuda.is_available() and args.cuda else "cpu")

    lang = "english"
    glb.init(lang)
    deck = "../deck/OldSchool.ydk"
    glb.db.init_from_deck(deck)

    # env setup
    envs = gym.vector.SyncVectorEnv(
        [make_env(args.env_id, deck, args.seed + i) for i in range(args.num_envs)]
    )
    envs = RecordEpisodeStatistics(envs)

    agent = Agent(128, 2, 2).to(device)
    agent = torch.compile(agent, mode='reduce-overhead')
    optimizer = optim.Adam(agent.parameters(), lr=args.learning_rate, eps=1e-5)

    avg_returns = deque(maxlen=20)

    rb = DMCDictBuffer(
        args.buffer_size,
        envs.single_observation_space,
        envs.single_action_space,
        device=device,
        n_envs=args.num_envs,
    )

    gamma = np.float32(args.gamma)

    global_step = 0
    start_time = time.time()
    warmup_steps = 0
    obs = envs.reset(seed=args.seed)
    for iteration in range(1, args.num_iterations + 1):
        for step in range(args.num_steps):
            global_step += args.num_envs

            obs = optree.tree_map(lambda x: torch.from_numpy(x).to(device), obs)
            if random.random() < args.eps:
                actions_ = np.array([envs.single_action_space.sample() for _ in range(envs.num_envs)])
                actions = torch.from_numpy(actions_).to(device)
            else:
                with torch.no_grad():
                    values, mask = agent(obs)
                    print(obs['actions'])
                    print(mask)
                values = values.masked_fill_(mask, -torch.inf)
                actions = torch.argmax(values, dim=1)
                actions_ = actions.cpu().numpy()

            next_obs, rewards, dones, infos = envs.step(actions_)
            rb.add(obs, actions, rewards)
            obs = next_obs

            for idx, d in enumerate(dones):
                if d:
                    rb.mark_episode(idx, gamma)

                    episode_length = infos['l'][idx]
                    episode_reward = infos['r'][idx]
                    print(f"global_step={global_step}, e_ret={episode_reward}, e_len={episode_length}")
                    writer.add_scalar("charts/episodic_return", episode_reward, global_step)
                    writer.add_scalar("charts/episodic_length", episode_length, global_step)
                    avg_returns.append(episode_reward)
                    writer.add_scalar("charts/avg_episodic_return", np.average(avg_returns), global_step)

        # ALGO LOGIC: training.
        b_inds = rb.get_data_indices()
        np.random.shuffle(b_inds)
        for start in range(0, len(b_inds), args.minibatch_size):
            end = start + args.minibatch_size
            mb_inds = b_inds[start:end]

            mb_obs, mb_actions, mb_returns = rb._get_samples(mb_inds)
            outputs, mask = agent(mb_obs)
            outputs = torch.gather(outputs, 1, mb_actions).squeeze(1)
            loss = F.mse_loss(mb_returns, outputs, reduction='none')
            valid_mask = (1 - mask).to(loss.dtype)
            loss = (loss * valid_mask).sum() / valid_mask.sum()

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(agent.parameters(), args.max_grad_norm)
            optimizer.step()

        writer.add_scalar("losses/value_loss", loss, global_step)
        writer.add_scalar("losses/q_values", outputs.mean().item(), global_step)

        if iteration == 10:
            warmup_steps = global_step
            start_time = time.time()
        if iteration > 10:
            SPS = int((global_step - warmup_steps) / (time.time() - start_time))
            print("SPS:", SPS)
            writer.add_scalar("charts/SPS", SPS, global_step)


    envs.close()
    writer.close()