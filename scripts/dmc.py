import os
import random
import time
from typing import Optional
from dataclasses import dataclass

import envpool2
import numpy as np

import optree

import tyro

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from ygo.utils import init_ygopro
from ygo.rl.utils import RecordEpisodeStatistics
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

    # Algorithm specific arguments
    env_id: str = "YGOPro-v0"
    """the id of the environment"""
    deck: str = "../deck/OldSchool.ydk"
    """the deck file to use"""
    code_list_file: str = "code_list.txt"
    """the code list file for card embeddings"""
    embedding_file: str = "embeddings_en.npy"
    """the embedding file for card embeddings"""
    max_options: int = 24
    """the maximum number of options"""

    total_timesteps: int = 100000000
    """total timesteps of the experiments"""
    learning_rate: float = 2.5e-4
    """the learning rate of the optimizer"""
    num_envs: int = 64
    """the number of parallel game environments"""
    num_steps: int = 100
    """the number of steps per env per iteration"""
    buffer_size: int = 200000
    """the replay memory buffer size"""
    gamma: float = 0.99
    """the discount factor gamma"""
    minibatch_size: int = 256
    """the mini-batch size"""
    eps: float = 0.05
    """the epsilon for exploration"""
    max_grad_norm: float = 1.0
    """the maximum norm for the gradient clipping"""

    compile: bool = True
    """if toggled, model will be compiled for better performance"""
    torch_threads: Optional[int] = None
    """the number of threads to use for torch, defaults to ($OMP_NUM_THREADS or 2) * world_size"""
    env_threads: Optional[int] = 32
    """the number of threads to use for envpool, defaults to `num_envs`"""


    # to be filled in runtime
    num_iterations: int = 0
    """the number of iterations (computed in runtime)"""


if __name__ == "__main__":

    args = tyro.cli(Args)
    args.batch_size = args.num_envs * args.num_steps
    args.num_iterations = args.total_timesteps // args.batch_size
    args.env_threads = args.env_threads or args.num_envs
    args.torch_threads = args.torch_threads or int(os.getenv("OMP_NUM_THREADS", "4"))

    torch.set_num_threads(args.torch_threads)
    torch.set_float32_matmul_precision('high')

    timestamp = int(time.time())
    run_name = f"{args.env_id}__{args.exp_name}__{args.seed}__{timestamp}"

    from torch.utils.tensorboard import SummaryWriter
    writer = SummaryWriter(f"runs/{run_name}")
    writer.add_text(
        "hyperparameters",
        "|param|value|\n|-|-|\n%s" % ("\n".join([f"|{key}|{value}|" for key, value in vars(args).items()])),
    )

    # TRY NOT TO MODIFY: seeding
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if args.torch_deterministic:
        torch.backends.cudnn.deterministic = True
    else:
        torch.backends.cudnn.benchmark = True
    torch.set_float32_matmul_precision('high')

    device = torch.device("cuda" if torch.cuda.is_available() and args.cuda else "cpu")

    deck = init_ygopro("english", args.deck, args.code_list_file)

    # env setup
    envs = envpool2.make(
        task_id=args.env_id,
        env_type="gymnasium",
        num_envs=args.num_envs,
        num_threads=args.env_threads,
        seed=args.seed,
        deck1=deck,
        deck2=deck,
        max_options=args.max_options,
    )
    envs.num_envs = args.num_envs
    obs_space = envs.observation_space
    action_space = envs.action_space
    print(f"obs_space={obs_space}, action_space={action_space}")

    envs = RecordEpisodeStatistics(envs)

    embeddings = np.load(args.embedding_file)

    agent = Agent(128, 2, 2, 1, embeddings.shape).to(device)
    agent.load_embeddings(embeddings)

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
    obs, infos = envs.reset()
    num_options = infos['num_options']
    for iteration in range(1, args.num_iterations + 1):
        agent.eval()
        model_time = 0
        env_time = 0
        buffer_time = 0

        collect_start = time.time()
        for step in range(args.num_steps):
            global_step += args.num_envs

            obs = optree.tree_map(lambda x: torch.from_numpy(x).to(device=device), obs)
            if random.random() < args.eps:
                actions_ = np.random.randint(num_options)
                actions = torch.from_numpy(actions_).to(device)
            else:
                _start = time.time()
                with torch.no_grad():
                    values = agent(obs)[0]
                actions = torch.argmax(values, dim=1)
                actions_ = actions.cpu().numpy()
                model_time += time.time() - _start

            _start = time.time()
            next_obs, rewards, dones, infos = envs.step(actions_)
            env_time += time.time() - _start
            num_options = infos['num_options']

            _start = time.time()
            rb.add(obs, actions, rewards)
            buffer_time += time.time() - _start
            obs = next_obs

            for idx, d in enumerate(dones):
                if d:
                    _start = time.time()
                    rb.mark_episode(idx, gamma)
                    buffer_time += time.time() - _start

                    if random.random() < 0.1:
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
        print(f"global_step={global_step}, collect_time={collect_time}, model_time={model_time}, env_time={env_time}, buffer_time={buffer_time}")

        agent.train()
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
            outputs, valid = agent(mb_obs)
            outputs = torch.gather(outputs, 1, mb_actions).squeeze(1)
            outputs = torch.where(valid, outputs, mb_returns)
            loss = F.mse_loss(mb_returns, outputs)
            loss = loss * (args.minibatch_size / valid.float().sum())

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(agent.parameters(), args.max_grad_norm)
            optimizer.step()
            model_time += time.time() - _start
        
        train_time = time.time() - train_start
        print(f"global_step={global_step}, train_time={train_time}, model_time={model_time}, sample_time={sample_time}")

        writer.add_scalar("losses/value_loss", loss, global_step)
        writer.add_scalar("losses/q_values", outputs.mean().item(), global_step)

        if iteration == 10:
            warmup_steps = global_step
            start_time = time.time()
        if iteration > 10:
            SPS = int((global_step - warmup_steps) / (time.time() - start_time))
            print("SPS:", SPS)
            writer.add_scalar("charts/SPS", SPS, global_step)

        if iteration % 100 == 0:
            save_path = f"checkpoints/agent.pt"
            print(f"Saving model to {save_path}")
            torch.save(agent.state_dict(), save_path)

    envs.close()
    writer.close()