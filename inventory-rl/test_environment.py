"""
Simple test script to verify the environment works correctly.

Run this to ensure the environment is properly set up before training.
"""

import sys
import os
import numpy as np

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.inventory_env import InventoryEnv
from utils.eoq import EOQBaseline, calculate_eoq


def test_environment():
    """Test basic environment functionality."""
    print("=" * 60)
    print("Testing Inventory Environment")
    print("=" * 60)
    
    # Create environment
    env = InventoryEnv()
    
    # Reset environment
    obs, info = env.reset()
    print(f"\n✓ Environment created and reset successfully")
    print(f"  Initial observation shape: {obs.shape}")
    print(f"  Initial observation: {obs}")
    print(f"  Observation space: {env.observation_space}")
    print(f"  Action space: {env.action_space}")
    
    # Run a few steps
    print(f"\n✓ Running 5 random steps...")
    for i in range(5):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"  Step {i+1}: action={action} (order {action*5}), "
              f"demand={info['demand']}, inventory={info['inventory']}, reward={reward:.1f}")
    
    # Run full episode
    print(f"\n✓ Running full episode (30 days)...")
    env.reset()
    total_reward = 0
    for day in range(30):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
    
    print(f"  Episode completed! Total reward: {total_reward:.1f}")
    
    env.close()
    print(f"\n✓ Environment test passed!")
    

def test_eoq():
    """Test EOQ module."""
    print("\n" + "=" * 60)
    print("Testing EOQ Module")
    print("=" * 60)
    
    # Test EOQ calculation
    demand = 300  # 10 units/day * 30 days
    ordering_cost = 50
    holding_cost = 1
    
    eoq = calculate_eoq(demand, ordering_cost, holding_cost)
    print(f"\n✓ EOQ calculation successful")
    print(f"  Demand: {demand} units")
    print(f"  Ordering cost: ${ordering_cost}")
    print(f"  Holding cost: ${holding_cost}/unit/day")
    print(f"  EOQ: {eoq:.2f} units")
    
    # Test baseline policy
    baseline = EOQBaseline(avg_daily_demand=10)
    print(f"\n✓ EOQ baseline created: {baseline}")
    
    # Test action selection
    inventory = 20
    action = baseline.get_discrete_action(inventory)
    order_qty = action * 5
    print(f"  At inventory={inventory}, baseline orders {order_qty} units (action={action})")
    
    inventory = 60
    action = baseline.get_discrete_action(inventory)
    order_qty = action * 5
    print(f"  At inventory={inventory}, baseline orders {order_qty} units (action={action})")
    
    print(f"\n✓ EOQ test passed!")


def test_baseline_episode():
    """Run a full episode with EOQ baseline."""
    print("\n" + "=" * 60)
    print("Testing EOQ Baseline on Full Episode")
    print("=" * 60)
    
    env = InventoryEnv()
    baseline = EOQBaseline(avg_daily_demand=20, reorder_point=40)
    
    obs, _ = env.reset()
    total_reward = 0
    stockouts = 0
    overstocks = 0
    
    for day in range(30):
        action = baseline.get_discrete_action(env.inventory, env.max_capacity)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        
        if info['unmet_demand'] > 0:
            stockouts += 1
        if env.inventory > env.max_capacity:
            overstocks += 1
    
    print(f"\n✓ Baseline episode completed!")
    print(f"  Total reward: {total_reward:.1f}")
    print(f"  Stockouts: {stockouts} days")
    print(f"  Overstocks: {overstocks} days")
    print(f"  Perfect days: {30 - stockouts - overstocks} days")
    
    env.close()


def main():
    """Run all tests."""
    try:
        test_environment()
        test_eoq()
        test_baseline_episode()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nYou can now proceed to train models:")
        print("  python agents/train_dqn.py")
        print("  python agents/train_ppo.py")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
