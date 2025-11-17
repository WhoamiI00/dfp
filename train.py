import argparse
import numpy as np
import torch
from stable_baselines3 import PPO, A2C, DQN
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.logger import configure
import time
from env import RealInventoryEnv
from utils import write_stream_data, LOG_DIR

class RealInventoryCallback(BaseCallback):
    """Callback for real inventory management training"""
    
    def __init__(self, verbose=True):
        super().__init__()
        self.episode_count = 0
        self.episode_rewards = []
        self.episode_perfect_days = []
        self.episode_efficiencies = []
        self.verbose = verbose
        self.last_day_printed = -1
        
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
            infos = self.locals.get('infos', [{}])
            if infos:
                episode_info = infos[0]
                self.episode_rewards.append(episode_info.get('reward', 0))
                self.episode_perfect_days.append(episode_info.get('perfect_days', 0))
                # Compute episode efficiency based on env max_days
                max_days = getattr(actual_env, 'max_days', 1)
                if max_days <= 0:
                    max_days = 1
                ep_eff = float(episode_info.get('perfect_days', 0)) / float(max_days)
                self.episode_efficiencies.append(ep_eff * 100.0)
        
        # Get current info from last step
        infos = self.locals.get('infos', [{}])
        info = infos[0] if infos else {}
        
        # Print detailed step information
        if self.verbose and actual_env.current_day != self.last_day_printed:
            self._print_day_summary(actual_env, info)
            self.last_day_printed = actual_env.current_day
        
        # Calculate efficiency metrics
        total_days = actual_env.current_day if actual_env.current_day > 0 else 1
        efficiency = (actual_env.perfect_days / total_days) * 100
        
        stream = {
            'timestep': int(self.num_timesteps),
            'episode': int(self.episode_count),
            'day': int(actual_env.current_day),
            'max_days': actual_env.max_days,
            
            # Current state
            'stocks': actual_env.stocks.tolist(),
            'yesterday_demand': actual_env.yesterday_demand.tolist(),
            'today_orders': actual_env.pending_orders.tolist(),
            
            # Historical demand
            'avg_7day': np.mean(actual_env.demand_history[-7:], axis=0).tolist(),
            'avg_14day': np.mean(actual_env.demand_history, axis=0).tolist(),
            
            # Performance metrics
            'recent_reward': float(self.locals.get('rewards', [0])[0]),
            'avg_reward': float(np.mean(self.episode_rewards[-100:])) if self.episode_rewards else 0.0,
            'efficiency': float(efficiency),
            'perfect_days': int(actual_env.perfect_days),
            'total_stockouts': int(actual_env.total_stockouts),
            
            # From last step info
            'stockout_products': info.get('stockout_products', 0),
            'total_stock': info.get('total_stock', 0),
            'warehouse_gap': info.get('warehouse_gap', 0),
            
            'timestamp': time.time(),
        }
        
        write_stream_data(stream)
        return True
    
    def _print_day_summary(self, env, info):
        """Print detailed summary for simplified 1-day delivery system"""
        print(f"\n{'='*80}")
        print(f"📅 DAY {env.current_day}/{env.max_days} | Episode {self.episode_count} | Timestep {self.num_timesteps:,}")
        print(f"{'='*80}")
        
        # Product performance
        demand = np.array(info.get('demand', [0]*10))
        fulfilled = np.array(info.get('fulfilled', [0]*10))
        unmet = np.array(info.get('unmet_demand', [0]*10))
        orders = np.array(info.get('orders_placed', [0]*10))
        arrivals = np.array(info.get('arrivals', [0]*10))
        
        print("\n📦 PRODUCT PERFORMANCE:")
        print(f"{'Prod':<6} {'Stock':<7} {'Demand':<8} {'Met':<6} {'Unmet':<7} {'AI Order':<10} {'Arrived':<8}")
        print(f"{'-'*70}")
        
        for i in range(10):
            print(f"P{i:<5} {int(env.stocks[i]):<7} {int(demand[i]):<8} {int(fulfilled[i]):<6} "
                  f"{int(unmet[i]):<7} {int(orders[i]):<10} {int(arrivals[i]):<8}")
        
        # Summary
        total_demand = demand.sum()
        total_fulfilled = fulfilled.sum()
        total_unmet = unmet.sum()
        total_orders = orders.sum()
        fill_rate = (total_fulfilled / max(total_demand, 1)) * 100
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Demand: {int(total_demand)} units (0-20 per product)")
        print(f"   Fulfilled: {int(total_fulfilled)} units ({fill_rate:.1f}% fill rate)")
        print(f"   Unmet: {int(total_unmet)} units")
        print(f"   AI Ordered: {int(total_orders)} units (arrive tomorrow)")
        
        # Warehouse
        total_stock = info.get('total_stock', 0)
        warehouse_gap = info.get('warehouse_gap', 0)
        
        print(f"\n🏢 WAREHOUSE (100 CAPACITY):")
        print(f"   Current Stock: {int(total_stock)}/100 units")
        print(f"   Available Space: {int(warehouse_gap)} units")
        if warehouse_gap > 0:
            print(f"   📈 AI should order ~{int(warehouse_gap)} units to reach 100")
        
        # Reward
        print(f"\n💰 REWARD: {info.get('reward', 0):.2f}")
        
        # Performance
        stockout_count = info.get('stockout_products', 0)
        print(f"\n🎯 PERFORMANCE:")
        print(f"   Perfect Days: {env.perfect_days}/{env.current_day} ({(env.perfect_days/max(env.current_day,1)*100):.1f}%)")
        print(f"   Total Stockouts: {env.total_stockouts}")
        
        if total_unmet == 0:
            print(f"   Today: ✅ PERFECT DAY - All demand met!")
        else:
            print(f"   Today: 🚨 {int(stockout_count)} products had stockouts")
        
        print(f"{'='*80}\n")

def make_env():
    return Monitor(RealInventoryEnv())

def main(args):
    # Setup device (GPU if available)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print(f"\n{'='*80}")
    print(f"🖥️  SYSTEM CONFIGURATION")
    print(f"{'='*80}")
    print(f"PyTorch Version: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        print(f"Using Device: {device} 🚀")
    else:
        print(f"Using Device: {device} (CPU)")
        print(f"⚠️  GPU not detected. Training will use CPU.")
    print(f"{'='*80}\n")
    
    env = DummyVecEnv([make_env])

    # Heavier network and rollout settings can increase GPU utilization
    policy_kwargs = dict(net_arch=[256, 256])
    if args.heavy:
        policy_kwargs = dict(net_arch=[512, 512, 256])

    # Choose algorithm with GPU support
    if args.algorithm == 'ppo':
        ppo_kwargs = dict(
            tensorboard_log=str(LOG_DIR / "tensorboard"),
            device=device,
            verbose=0,
            policy_kwargs=policy_kwargs,
        )
        if args.heavy:
            # Ensure batch_size <= n_steps * n_envs (n_envs=1)
            ppo_kwargs.update(dict(n_steps=4096, batch_size=4096, n_epochs=10))
        model = PPO("MlpPolicy", env, **ppo_kwargs)
    elif args.algorithm == 'a2c':
        a2c_kwargs = dict(
            tensorboard_log=str(LOG_DIR / "tensorboard"),
            device=device,
            verbose=0,
            policy_kwargs=policy_kwargs,
        )
        model = A2C("MlpPolicy", env, **a2c_kwargs)
    else:
        raise ValueError(f"Unknown algorithm: {args.algorithm}")
    
    model.set_logger(configure(str(LOG_DIR / "sb3_logs"), ["stdout", "tensorboard"]))
    
    callback = RealInventoryCallback(verbose=args.verbose)
    
    print(f"\n{'='*80}")
    print(f"🤖 TRAINING SIMPLIFIED 1-DAY DELIVERY INVENTORY AI")
    print(f"{'='*80}")
    print(f"Algorithm: {args.algorithm.upper()}")
    print(f"Total Timesteps: {args.total_timesteps:,}")
    print(f"Products: 10")
    print(f"Warehouse Capacity: 100 units")
    print(f"Episode Length: 30 days")
    print(f"Demand: 0-20 per product per day")
    print(f"Delivery: 1 day (orders arrive next day)")
    print(f"\n📚 LEARNING WORKFLOW:")
    print(f"  1. Start: Day 1 with 10 units per product (100 total)")
    print(f"  2. Each day: Random demand 0-20 per product")
    print(f"  3. AI sees: current stock, demand history")
    print(f"  4. AI orders: products to refill to 100 capacity")
    print(f"  5. Next day: Orders arrive, demand happens, repeat")
    print(f"  Example: After day 1, 40 units left → AI orders 60 units")
    print(f"  AI learns to allocate MORE to high-demand products")
    print(f"{'='*80}\n")
    
    if args.verbose:
        print("📺 Detailed day-by-day output enabled. Starting training...\n")
    else:
        print("💡 Tip: Use --verbose flag to see detailed day-by-day breakdown\n")
    
    # Extra confirmation that policy parameters are on the intended device
    try:
        first_param_device = next(model.policy.parameters()).device
        print(f"Model policy device: {first_param_device}")
    except Exception:
        pass

    model.learn(total_timesteps=args.total_timesteps, callback=callback)
    model.save(str(LOG_DIR / "real_inventory_model"))
    
    print(f"\n{'='*60}")
    print(f"Training Complete!")
    print(f"Model saved to: {LOG_DIR / 'real_inventory_model'}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Real Inventory Management AI")
    parser.add_argument("--total-timesteps", type=int, default=100000, 
                       help="Total training timesteps")
    parser.add_argument("--algorithm", type=str, default="ppo", 
                       choices=['ppo', 'a2c'],
                       help="RL algorithm to use")
    parser.add_argument("--verbose", action="store_true",
                       help="Show detailed day-by-day output with demand, orders, and AI learning")
    parser.add_argument("--heavy", action="store_true",
                       help="Use a larger policy network and rollout sizes to better utilize the GPU")
    args = parser.parse_args()
    main(args)
