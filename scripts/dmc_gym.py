import os
import random
import time
from dataclasses import dataclass

import gymnasium as gym
import numpy as np

import optree

import tyro

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter

from ygo.rl.utils import RecordEpisodeStatistics
from ygo.envs import glb
from ygo.rl.agent import Agent
from ygo.rl.buffer import DMCDictBuffer


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
    compile: bool = True
    """if toggled, model will be compiled for better performance"""

    # Algorithm specific arguments
    env_id: str = "yugioh-ai/YGO-v0"
    """the id of the environment"""
    deck: str = "../deck/OldSchool.ydk"
    """the deck to use"""

    total_timesteps: int = 100000000
    """total timesteps of the experiments"""
    learning_rate: float = 2.5e-4
    """the learning rate of the optimizer"""
    num_envs: int = 32
    """the number of parallel game environments"""
    num_steps: int = 100
    """the number of steps per env per iteration"""
    buffer_size: int = 20000
    """the replay memory buffer size"""
    gamma: float = 0.99
    """the discount factor gamma"""
    minibatch_size: int = 128
    """the mini-batch size"""
    eps: float = 0.05
    """the epsilon for exploration"""
    max_grad_norm: float = 1.0
    """the maximum norm for the gradient clipping"""
    async_envs: bool = True
    """if toggled, will use AsyncVectorEnv instead of SyncVectorEnv"""

    # to be filled in runtime
    num_iterations: int = 0
    """the number of iterations (computed in runtime)"""


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
    args.batch_size = args.num_envs * args.num_steps
    args.num_iterations = args.total_timesteps // args.batch_size

    timestamp = int(time.time())
    run_name = f"{args.env_id}__{args.exp_name}__{args.seed}__{timestamp}"

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
    torch.set_float32_matmul_precision('high')

    device = torch.device("cuda" if torch.cuda.is_available() and args.cuda else "cpu")

    glb.init("english")
    deck = args.deck
    glb.db.init_from_deck(deck)

    # env setup
    VectorEnv = gym.vector.AsyncVectorEnv if args.async_envs else gym.vector.SyncVectorEnv
    envs = VectorEnv(
        [make_env(args.env_id, deck, args.seed + i) for i in range(args.num_envs)]
    )
    obs_space = envs.unwrapped.single_observation_space
    action_space = envs.unwrapped.single_action_space
    envs = RecordEpisodeStatistics(envs)

    # envs_eval = gym.vector.SyncVectorEnv(
    #     [make_env(args.env_id, deck, args.seed + i) for i in range(args.num_envs)]
    # )
    # envs_eval = RecordEpisodeStatistics(envs_eval)

    agent = Agent(128, 2, 2).to(device)
    if args.compile:
        agent = torch.compile(agent, mode='reduce-overhead')
    optimizer = optim.Adam(agent.parameters(), lr=args.learning_rate, eps=1e-5)

    avg_win_rates = []

    rb = DMCDictBuffer(
        args.buffer_size,
        obs_space,
        action_space,
        device=device,
        n_envs=args.num_envs,
    )

    gamma = np.float32(args.gamma)

    global_step = 0
    start_time = time.time()
    warmup_steps = 0
    obs, infos = envs.reset(seed=args.seed)
    action_options = infos['options']
    for iteration in range(1, args.num_iterations + 1):
        model_time = 0
        env_time = 0

        collect_start = time.time()
        for step in range(args.num_steps):
            global_step += args.num_envs

            obs = optree.tree_map(lambda x: torch.from_numpy(x).to(device=device), obs)
            if random.random() < args.eps:
                actions_ = np.array([random.randint(0, len(action_options[i]) - 1) for i in range(envs.num_envs)])
                actions = torch.from_numpy(actions_).to(device)
            else:
                _start = time.time()
                with torch.no_grad():
                    values = agent(obs)
                model_time += time.time() - _start
                actions = torch.argmax(values, dim=1)
                actions_ = actions.cpu().numpy()

            _start = time.time()
            next_obs, rewards, dones, infos = envs.step(actions_)
            env_time += time.time() - _start
            action_options = infos['options']

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
                    avg_win_rates.append(1 if episode_reward == 1 else 0)
                    if len(avg_win_rates) > 100:
                        writer.add_scalar("charts/avg_win_rate", np.mean(avg_win_rates), global_step)
                        avg_win_rates = []

        collect_time = time.time() - collect_start
        print(f"global_step={global_step}, model_time={model_time}, env_time={env_time}, collect_time={collect_time}")

        train_start = time.time()
        model_time = 0
        sample_time = 0

        # ALGO LOGIC: training.
        _start = time.time()
        b_inds = rb.get_data_indices()
        if len(b_inds) < args.minibatch_size:
            continue
        np.random.shuffle(b_inds)
        b_obs, b_actions, b_returns = rb._get_samples(b_inds)
        sample_time += time.time() - _start
        for start in range(0, len(b_inds), args.minibatch_size):
            _start = time.time()
            end = start + args.minibatch_size
            mb_obs = {
                k: v[start:end] for k, v in b_obs.items()
            }
            mb_actions = b_actions[start:end]
            mb_returns = b_returns[start:end]
            sample_time += time.time() - _start

            _start = time.time()
            outputs = agent(mb_obs)
            outputs = torch.gather(outputs, 1, mb_actions).squeeze(1)
            loss = F.mse_loss(mb_returns, outputs)

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(agent.parameters(), args.max_grad_norm)
            optimizer.step()
            model_time += time.time() - _start
        
        train_time = time.time() - train_start
        print(f"global_step={global_step}, train_time={train_time}, model_time={model_time}, sample_time={sample_time}")

        writer.add_scalar("losses/value_loss", loss, global_step)
        writer.add_scalar("losses/q_values", outputs.mean().item(), global_step)

        if iteration == 3:
            warmup_steps = global_step
            start_time = time.time()
        if iteration > 3:
            SPS = int((global_step - warmup_steps) / (time.time() - start_time))
            print("SPS:", SPS)
            writer.add_scalar("charts/SPS", SPS, global_step)

        if iteration % 100 == 0:
            save_path = f"checkpoints/agent.pt"
            print(f"Saving model to {save_path}")
            torch.save(agent.state_dict(), save_path)

        #     episode_rewards = []
        #     episode_lengths = []
        #     obs_, infos_ = envs_eval.reset(seed=args.seed)
        #     while True:
        #         obs_ = optree.tree_map(lambda x: torch.from_numpy(x).to(device=device), obs_)
        #         with torch.no_grad():
        #             values = agent(obs_)
        #         actions = torch.argmax(values, dim=1).cpu().numpy()
        #         obs_, rewards, dones, infos_ = envs_eval.step(actions)

        #         for idx, d in enumerate(dones):
        #             if d:
        #                 episode_length = infos_['l'][idx]
        #                 episode_reward = infos_['r'][idx]
        #                 if episode_reward == -1:
        #                     episode_reward = 0

        #                 episode_lengths.append(episode_length)
        #                 episode_rewards.append(episode_reward)
        #                 print(f"Episode {len(episode_lengths)}: length={episode_length}, reward={episode_reward}")
        #         if len(episode_lengths) >= 128:
        #             print(f"avg_length={np.mean(episode_lengths)}, win_rate={np.mean(episode_rewards)}")
        #             break


    envs.close()
    writer.close()