import argparse
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.logger import configure
import time
from env import InventoryEnv
from utils import write_stream_data, LOG_DIR

class StreamLogger(BaseCallback):
    def __init__(self):
        super().__init__()
        self.episode_count = 0
        self.total_rewards = []
        self.episode_lengths = []
        
    def _on_step(self):
        env = self.training_env.envs[0]
        # Unwrap Monitor to get actual environment
        if hasattr(env, 'env'):
            actual_env = env.env
        else:
            actual_env = env
        
        # Check if episode ended
        if self.locals.get('dones', [False])[0]:
            self.episode_count += 1
            episode_reward = sum(actual_env.episode_rewards) if hasattr(actual_env, 'episode_rewards') else 0
            self.total_rewards.append(episode_reward)
            self.episode_lengths.append(actual_env.days_passed)
        
        # Get current info from last step
        infos = self.locals.get('infos', [{}])
        info = infos[0] if infos else {}
        
        stream = {
            'timestep': int(self.num_timesteps),
            'episode': int(self.episode_count),
            'day': int(actual_env.days_passed),
            'stocks': actual_env.stocks.tolist(),
            'last_demand': actual_env.last_demand.tolist(),
            'outstanding': actual_env.outstanding.tolist(),
            'last_order': actual_env.last_order.tolist(),
            'cumulative_sold': actual_env.cumulative_sold.tolist(),
            'recent_reward': float(self.locals.get('rewards', [0])[0]),
            'avg_reward': float(np.mean(self.total_rewards[-100:])) if self.total_rewards else 0.0,
            'overstock_days': int(actual_env.total_overstock_days),
            'understock_days': int(actual_env.total_understock_days),
            'perfect_days': int(actual_env.perfect_days),
            'has_overstock': info.get('has_overstock', 0),
            'has_understock': info.get('has_understock', 0),
            'holding_cost': info.get('holding_cost', 0.0),
            'total_unmet': info.get('total_unmet', 0.0),
            'overstock_amount': info.get('overstock_amount', 0.0),
            'avg_daily_demand': actual_env.avg_daily.tolist(),
            'safety_stock': actual_env.safety_stock.tolist(),
            'lead_time': actual_env.lead_time.tolist(),
            'timestamp': time.time(),
        }
        write_stream_data(stream)
        return True

def make_env():
    return Monitor(InventoryEnv())

def main(args):
    env = DummyVecEnv([make_env])
    model = PPO("MlpPolicy", env, verbose=1, tensorboard_log=str(LOG_DIR / "tensorboard"))
    model.set_logger(configure(str(LOG_DIR / "sb3_logs"), ["stdout", "tensorboard"]))

    callback = StreamLogger()
    model.learn(total_timesteps=args.total_timesteps, callback=callback)
    model.save(str(LOG_DIR / "final_model"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--total-timesteps", type=int, default=200000)
    args = parser.parse_args()
    main(args)
