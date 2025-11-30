"""
PPO Training Script for Inventory Management

This script trains a Proximal Policy Optimization (PPO) agent to manage
inventory using the custom Gymnasium environment.
"""

import os
import sys
import numpy as np
from stable_baselines3 import PPO
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


def train_ppo(
    total_timesteps=100000,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
    gamma=0.99,
    gae_lambda=0.95,
    clip_range=0.2,
    ent_coef=0.0,
    vf_coef=0.5,
    max_grad_norm=0.5,
    save_path="../models/ppo_inventory",
    log_path="../logs/ppo"
):
    """
    Train a PPO agent on the inventory management environment.
    
    Args:
        total_timesteps: Total number of timesteps to train (default: 100000)
        learning_rate: Learning rate for optimizer (default: 3e-4)
        n_steps: Number of steps to collect before update (default: 2048)
        batch_size: Minibatch size for training (default: 64)
        n_epochs: Number of epochs for each update (default: 10)
        gamma: Discount factor (default: 0.99)
        gae_lambda: Factor for GAE (default: 0.95)
        clip_range: Clipping parameter for PPO (default: 0.2)
        ent_coef: Entropy coefficient (default: 0.0)
        vf_coef: Value function coefficient (default: 0.5)
        max_grad_norm: Maximum gradient norm (default: 0.5)
        save_path: Path to save the model (default: "../models/ppo_inventory")
        log_path: Path for TensorBoard logs (default: "../logs/ppo")
    
    Returns:
        PPO: Trained PPO model
    """
    # Create directories if they don't exist
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    os.makedirs(log_path, exist_ok=True)
    
    # Create training environment
    train_env = make_env()
    
    # Create evaluation environment
    eval_env = make_env()
    
    print("=" * 60)
    print("Training PPO Agent for Inventory Management")
    print("=" * 60)
    print(f"Total timesteps: {total_timesteps}")
    print(f"Learning rate: {learning_rate}")
    print(f"N steps: {n_steps}")
    print(f"Batch size: {batch_size}")
    print(f"N epochs: {n_epochs}")
    print(f"Gamma: {gamma}")
    print("=" * 60)
    
    # Create PPO model
    model = PPO(
        "MlpPolicy",
        train_env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=n_epochs,
        gamma=gamma,
        gae_lambda=gae_lambda,
        clip_range=clip_range,
        ent_coef=ent_coef,
        vf_coef=vf_coef,
        max_grad_norm=max_grad_norm,
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
        name_prefix="ppo_checkpoint"
    )
    
    # Train the model
    print("\nStarting training...")
    model.learn(
        total_timesteps=total_timesteps,
        callback=[eval_callback, checkpoint_callback],
        log_interval=10,
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
    
    save_path = os.path.join(project_root, "models", "ppo_inventory")
    log_path = os.path.join(project_root, "logs", "ppo")
    
    # Train the model
    model = train_ppo(
        total_timesteps=100000,
        save_path=save_path,
        log_path=log_path
    )
    
    print("\n" + "=" * 60)
    print("To evaluate the trained model, run:")
    print("  python agents/evaluate.py --model ppo")
    print("=" * 60)


if __name__ == "__main__":
    main()
