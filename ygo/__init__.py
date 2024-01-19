from gymnasium.envs.registration import register

register(
     id="yugioh-ai/YGO-v0",
     entry_point="ygo.envs:YGOEnv",
     max_episode_steps=300,
)