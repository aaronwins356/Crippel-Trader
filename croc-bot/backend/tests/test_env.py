import numpy as np

from croc.rl.env import TradingEnv


def test_env_step_contract():
    env = TradingEnv()
    obs, info = env.reset()
    assert obs.shape == (4,)
    assert info == {}
    action = np.array([0.5], dtype=np.float32)
    next_obs, reward, terminated, truncated, info = env.step(action)
    assert next_obs.shape == (4,)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert "pnl" in info and "drawdown" in info
    steps = 0
    while not (terminated or truncated):
        next_obs, reward, terminated, truncated, info = env.step(action)
        steps += 1
        if steps > 10:
            break
    assert steps > 0
