"""
Evaluation Script for Inventory Management

This script evaluates trained RL models and generates:
- Daily inventory plots
- Demand vs supply curves
- Reward per episode metrics
- State visitation heatmaps
"""

import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from stable_baselines3 import DQN, PPO

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.inventory_env import InventoryEnv
from utils.eoq import EOQBaseline
from utils.heatmap import generate_heatmap_from_model

# Set plotting style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)


def evaluate_model(model, env, num_episodes=10):
    """
    Evaluate a trained model over multiple episodes.
    
    Args:
        model: Trained Stable-Baselines3 model
        env: Gymnasium environment instance
        num_episodes: Number of episodes to evaluate (default: 10)
        
    Returns:
        dict: Evaluation metrics and episode data
    """
    episode_rewards = []
    all_inventory = []
    all_demand = []
    all_actions = []
    all_unmet = []
    
    for episode in range(num_episodes):
        obs, _ = env.reset()
        done = False
        episode_reward = 0
        
        inventory_history = []
        demand_history = []
        action_history = []
        unmet_history = []
        
        while not done:
            # Get action from model
            action, _ = model.predict(obs, deterministic=True)
            
            # Step environment
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            
            episode_reward += reward
            
            # Track metrics
            inventory_history.append(info['inventory'])
            demand_history.append(info['demand'])
            action_history.append(info['order_qty'])
            unmet_history.append(info['unmet_demand'])
        
        episode_rewards.append(episode_reward)
        all_inventory.append(inventory_history)
        all_demand.append(demand_history)
        all_actions.append(action_history)
        all_unmet.append(unmet_history)
    
    return {
        'rewards': episode_rewards,
        'inventory': all_inventory,
        'demand': all_demand,
        'actions': all_actions,
        'unmet': all_unmet,
        'mean_reward': np.mean(episode_rewards),
        'std_reward': np.std(episode_rewards)
    }


def evaluate_baseline(baseline, env, num_episodes=10):
    """
    Evaluate EOQ baseline policy over multiple episodes.
    
    Args:
        baseline: EOQBaseline policy instance
        env: Gymnasium environment instance
        num_episodes: Number of episodes to evaluate (default: 10)
        
    Returns:
        dict: Evaluation metrics and episode data
    """
    episode_rewards = []
    all_inventory = []
    all_demand = []
    all_actions = []
    all_unmet = []
    
    for episode in range(num_episodes):
        obs, _ = env.reset()
        done = False
        episode_reward = 0
        
        inventory_history = []
        demand_history = []
        action_history = []
        unmet_history = []
        
        while not done:
            # Get action from baseline
            action = baseline.get_discrete_action(env.inventory, env.max_capacity)
            
            # Step environment
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            
            episode_reward += reward
            
            # Track metrics
            inventory_history.append(info['inventory'])
            demand_history.append(info['demand'])
            action_history.append(info['order_qty'])
            unmet_history.append(info['unmet_demand'])
        
        episode_rewards.append(episode_reward)
        all_inventory.append(inventory_history)
        all_demand.append(demand_history)
        all_actions.append(action_history)
        all_unmet.append(unmet_history)
    
    return {
        'rewards': episode_rewards,
        'inventory': all_inventory,
        'demand': all_demand,
        'actions': all_actions,
        'unmet': all_unmet,
        'mean_reward': np.mean(episode_rewards),
        'std_reward': np.std(episode_rewards)
    }


def plot_inventory_trajectory(results, title, save_path):
    """
    Plot inventory levels over time for a single episode.
    
    Args:
        results: Results dictionary from evaluate_model or evaluate_baseline
        title: Plot title
        save_path: Path to save the figure
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Plot first episode
    days = range(1, len(results['inventory'][0]) + 1)
    inventory = results['inventory'][0]
    demand = results['demand'][0]
    
    ax.plot(days, inventory, marker='o', linewidth=2, label='Inventory Level', color='blue')
    ax.plot(days, demand, marker='s', linewidth=2, label='Daily Demand', color='red', alpha=0.7)
    
    # Add horizontal line for capacity
    ax.axhline(y=100, color='green', linestyle='--', label='Max Capacity', alpha=0.5)
    ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    
    ax.set_xlabel('Day', fontsize=12)
    ax.set_ylabel('Units', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Inventory trajectory saved to {save_path}")
    plt.close()


def plot_demand_supply_comparison(results, title, save_path):
    """
    Plot demand vs supply (sold units) for a single episode.
    
    Args:
        results: Results dictionary from evaluate_model or evaluate_baseline
        title: Plot title
        save_path: Path to save the figure
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    
    days = range(1, len(results['demand'][0]) + 1)
    demand = results['demand'][0]
    unmet = results['unmet'][0]
    sold = [d - u for d, u in zip(demand, unmet)]
    
    ax.plot(days, demand, marker='o', linewidth=2, label='Demand', color='orange')
    ax.plot(days, sold, marker='s', linewidth=2, label='Sold (Supply)', color='green')
    ax.bar(days, unmet, alpha=0.3, color='red', label='Unmet Demand')
    
    ax.set_xlabel('Day', fontsize=12)
    ax.set_ylabel('Units', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Demand vs supply plot saved to {save_path}")
    plt.close()


def plot_reward_comparison(rl_results, baseline_results, save_path):
    """
    Plot reward comparison between RL agent and baseline.
    
    Args:
        rl_results: Results from RL agent
        baseline_results: Results from EOQ baseline
        save_path: Path to save the figure
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(2)
    rewards = [rl_results['mean_reward'], baseline_results['mean_reward']]
    stds = [rl_results['std_reward'], baseline_results['std_reward']]
    labels = ['RL Agent', 'EOQ Baseline']
    colors = ['skyblue', 'lightcoral']
    
    bars = ax.bar(x, rewards, yerr=stds, capsize=5, color=colors, alpha=0.8, edgecolor='black')
    
    ax.set_ylabel('Mean Episode Reward', fontsize=12)
    ax.set_title('RL Agent vs EOQ Baseline Performance', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12)
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for i, (bar, reward, std) in enumerate(zip(bars, rewards, stds)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{reward:.2f}±{std:.2f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Reward comparison saved to {save_path}")
    plt.close()


def main():
    """Main evaluation function."""
    parser = argparse.ArgumentParser(description='Evaluate trained RL models')
    parser.add_argument('--model', type=str, default='dqn', choices=['dqn', 'ppo'],
                        help='Model type to evaluate (default: dqn)')
    parser.add_argument('--episodes', type=int, default=10,
                        help='Number of episodes to evaluate (default: 10)')
    
    args = parser.parse_args()
    
    # Get paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    results_dir = os.path.join(project_root, "results")
    models_dir = os.path.join(project_root, "models")
    
    os.makedirs(results_dir, exist_ok=True)
    
    # Load model
    model_path = os.path.join(models_dir, f"{args.model}_inventory.zip")
    
    if not os.path.exists(model_path):
        # Try the best_model.zip path
        model_path = os.path.join(models_dir, "best_model.zip")
    
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}")
        print("Please train a model first using train_dqn.py or train_ppo.py")
        return
    
    print(f"Loading model from {model_path}...")
    if args.model == 'dqn':
        model = DQN.load(model_path)
    else:
        model = PPO.load(model_path)
    
    # Create environment
    env = InventoryEnv()
    
    print(f"\nEvaluating {args.model.upper()} model over {args.episodes} episodes...")
    rl_results = evaluate_model(model, env, num_episodes=args.episodes)
    
    print(f"\nRL Agent Mean Reward: {rl_results['mean_reward']:.2f} ± {rl_results['std_reward']:.2f}")
    
    # Evaluate EOQ baseline
    print("\nEvaluating EOQ baseline...")
    baseline = EOQBaseline(avg_daily_demand=10, reorder_point=30)
    baseline_results = evaluate_baseline(baseline, env, num_episodes=args.episodes)
    
    print(f"EOQ Baseline Mean Reward: {baseline_results['mean_reward']:.2f} ± {baseline_results['std_reward']:.2f}")
    
    # Generate plots
    print("\nGenerating plots...")
    
    plot_inventory_trajectory(
        rl_results,
        f"{args.model.upper()} Agent - Inventory Trajectory",
        os.path.join(results_dir, f"{args.model}_inventory_plot.png")
    )
    
    plot_demand_supply_comparison(
        rl_results,
        f"{args.model.upper()} Agent - Demand vs Supply",
        os.path.join(results_dir, f"{args.model}_demand_supply.png")
    )
    
    plot_reward_comparison(
        rl_results,
        baseline_results,
        os.path.join(results_dir, "reward_comparison.png")
    )
    
    # Generate heatmap
    print("\nGenerating state visitation heatmap...")
    heatmap_path = os.path.join(results_dir, f"{args.model}_heatmap.png")
    generate_heatmap_from_model(env, model, num_episodes=args.episodes, save_path=heatmap_path)
    
    print("\n" + "=" * 60)
    print("Evaluation complete!")
    print(f"Results saved to: {results_dir}")
    print("=" * 60)
    
    env.close()


if __name__ == "__main__":
    main()
