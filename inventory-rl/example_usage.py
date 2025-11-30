"""
Simple usage example demonstrating the inventory environment and EOQ baseline.

This script shows how to use the environment and baseline policy without
requiring any training.
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.inventory_env import InventoryEnv
from utils.eoq import EOQBaseline


def run_random_policy():
    """Run a random policy for one episode."""
    print("\n" + "=" * 60)
    print("Example 1: Random Policy")
    print("=" * 60)
    
    env = InventoryEnv()
    obs, _ = env.reset()
    
    total_reward = 0
    inventories = []
    demands = []
    
    for day in range(30):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        
        total_reward += reward
        inventories.append(info['inventory'])
        demands.append(info['demand'])
        
        if day < 5:  # Show first 5 days
            print(f"Day {day+1}: Order {action*5} units, "
                  f"Demand {info['demand']}, "
                  f"Inventory {info['inventory']}, "
                  f"Reward {reward:.1f}")
    
    print(f"...")
    print(f"Total Reward: {total_reward:.1f}/30")
    
    env.close()
    return inventories, demands


def run_eoq_policy():
    """Run EOQ baseline policy for one episode."""
    print("\n" + "=" * 60)
    print("Example 2: EOQ Baseline Policy")
    print("=" * 60)
    
    env = InventoryEnv()
    baseline = EOQBaseline(avg_daily_demand=20, reorder_point=40)
    
    print(f"Baseline: {baseline}")
    
    obs, _ = env.reset()
    
    total_reward = 0
    inventories = []
    demands = []
    
    for day in range(30):
        action = baseline.get_discrete_action(env.inventory, env.max_capacity)
        obs, reward, terminated, truncated, info = env.step(action)
        
        total_reward += reward
        inventories.append(info['inventory'])
        demands.append(info['demand'])
        
        if day < 5:  # Show first 5 days
            print(f"Day {day+1}: Order {action*5} units, "
                  f"Demand {info['demand']}, "
                  f"Inventory {info['inventory']}, "
                  f"Reward {reward:.1f}")
    
    print(f"...")
    print(f"Total Reward: {total_reward:.1f}/30")
    
    env.close()
    return inventories, demands


def visualize_comparison(random_inv, eoq_inv):
    """Visualize random vs EOQ policies."""
    print("\n" + "=" * 60)
    print("Generating comparison plot...")
    print("=" * 60)
    
    days = range(1, 31)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.plot(days, random_inv, marker='o', label='Random Policy', alpha=0.7)
    ax.plot(days, eoq_inv, marker='s', label='EOQ Baseline', alpha=0.7)
    ax.axhline(y=100, color='red', linestyle='--', label='Max Capacity', alpha=0.5)
    ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    
    ax.set_xlabel('Day', fontsize=12)
    ax.set_ylabel('Inventory Level', fontsize=12)
    ax.set_title('Random Policy vs EOQ Baseline', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save to results if it exists, otherwise current directory
    save_path = "example_comparison.png"
    if os.path.exists("../results"):
        save_path = "../results/example_comparison.png"
    
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to {save_path}")
    plt.close()


def main():
    """Run examples."""
    print("=" * 60)
    print("Inventory Management - Usage Examples")
    print("=" * 60)
    
    # Example 1: Random policy
    random_inv, random_demand = run_random_policy()
    
    # Example 2: EOQ baseline
    eoq_inv, eoq_demand = run_eoq_policy()
    
    # Visualize
    visualize_comparison(random_inv, eoq_inv)
    
    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)
    print("\nKey Observations:")
    print("- Random policy often violates constraints (stockouts/overstocks)")
    print("- EOQ baseline provides more stable inventory levels")
    print("- RL agents (DQN/PPO) should outperform both after training")
    print("\nNext steps:")
    print("  python agents/train_dqn.py")
    print("  python agents/train_ppo.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
