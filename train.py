import argparse
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.logger import configure
import time
from env import InventoryEnv
from utils import write_stream_data, LOG_DIR

class StreamLogger(BaseCallback):
    def _on_step(self):
        env = self.training_env.envs[0]
        stream = {
            'day': int(env.days_passed),
            'stocks': env.stocks.tolist(),
            'last_demand': env.last_demand.tolist(),
            'outstanding': env.outstanding.tolist(),
            'last_order': env.last_order.tolist(),
            'cumulative_sold': env.cumulative_sold.tolist(),
            'recent_reward': float(self.locals.get('rewards', [0])[0]),
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
