"""
DQN Training Script for Inventory Management

This script trains a Deep Q-Network (DQN) agent to manage inventory
using the custom Gymnasium environment.
"""

import os
import sys
import numpy as np
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.inventory_env import InventoryEnv


def make_env():
    """
    Create and wrap the inventory environment.
    
    Returns:
        Monitor: Wrapped environment for tracking episode statistics
    """
    env = InventoryEnv(
        initial_inventory=100,
        max_capacity=100,
        episode_length=30,
        trend_strength=5
    )
    env = Monitor(env)
    return env


def train_dqn(
    total_timesteps=100000,
    learning_rate=1e-3,
    buffer_size=50000,
    learning_starts=1000,
    batch_size=32,
    gamma=0.99,
    exploration_fraction=0.1,
    exploration_final_eps=0.05,
    target_update_interval=500,
    save_path="../models/dqn_inventory",
    log_path="../logs/dqn"
):
    """
    Train a DQN agent on the inventory management environment.
    
    Args:
        total_timesteps: Total number of timesteps to train (default: 100000)
        learning_rate: Learning rate for optimizer (default: 1e-3)
        buffer_size: Size of replay buffer (default: 50000)
        learning_starts: Steps before learning starts (default: 1000)
        batch_size: Minibatch size for training (default: 32)
        gamma: Discount factor (default: 0.99)
        exploration_fraction: Fraction of training for exploration (default: 0.1)
        exploration_final_eps: Final epsilon for exploration (default: 0.05)
        target_update_interval: Steps between target network updates (default: 500)
        save_path: Path to save the model (default: "../models/dqn_inventory")
        log_path: Path for TensorBoard logs (default: "../logs/dqn")
    
    Returns:
        DQN: Trained DQN model
    """
    # Create directories if they don't exist
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    os.makedirs(log_path, exist_ok=True)
    
    # Create training environment
    train_env = make_env()
    
    # Create evaluation environment
    eval_env = make_env()
    
    print("=" * 60)
    print("Training DQN Agent for Inventory Management")
    print("=" * 60)
    print(f"Total timesteps: {total_timesteps}")
    print(f"Learning rate: {learning_rate}")
    print(f"Batch size: {batch_size}")
    print(f"Gamma: {gamma}")
    print(f"Exploration fraction: {exploration_fraction}")
    print("=" * 60)
    
    # Create DQN model
    model = DQN(
        "MlpPolicy",
        train_env,
        learning_rate=learning_rate,
        buffer_size=buffer_size,
        learning_starts=learning_starts,
        batch_size=batch_size,
        gamma=gamma,
        exploration_fraction=exploration_fraction,
        exploration_final_eps=exploration_final_eps,
        target_update_interval=target_update_interval,
        verbose=1,
        tensorboard_log=log_path
    )
    
    # Create callbacks
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=os.path.dirname(save_path),
        log_path=log_path,
        eval_freq=5000,
        deterministic=True,
        render=False,
        n_eval_episodes=10
    )
    
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path=os.path.dirname(save_path),
        name_prefix="dqn_checkpoint"
    )
    
    # Train the model
    print("\nStarting training...")
    model.learn(
        total_timesteps=total_timesteps,
        callback=[eval_callback, checkpoint_callback],
        log_interval=100,
        progress_bar=True
    )
    
    # Save final model
    model.save(save_path)
    print(f"\nTraining complete! Model saved to {save_path}.zip")
    
    # Clean up
    train_env.close()
    eval_env.close()
    
    return model


def main():
    """Main training function."""
    # Get the absolute path to the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    save_path = os.path.join(project_root, "models", "dqn_inventory")
    log_path = os.path.join(project_root, "logs", "dqn")
    
    # Train the model
    model = train_dqn(
        total_timesteps=100000,
        save_path=save_path,
        log_path=log_path
    )
    
    print("\n" + "=" * 60)
    print("To evaluate the trained model, run:")
    print("  python agents/evaluate.py --model dqn")
    print("=" * 60)


if __name__ == "__main__":
    main()
