"""
10x10 State Heatmap Visualization

Discretizes continuous state space into a 10x10 grid for visualization.
Useful for debugging and understanding agent behavior.
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


class StateHeatmap:
    """
    Tracks and visualizes state visitation in a 10x10 grid.
    
    Discretizes:
    - Inventory: 0-100 → 10 bins (rows)
    - Day index: 0-30 → 10 bins (columns)
    """
    
    def __init__(self, max_inventory=100, max_days=30):
        """
        Initialize the heatmap tracker.
        
        Args:
            max_inventory: Maximum inventory value (default: 100)
            max_days: Maximum day index (default: 30)
        """
        self.max_inventory = max_inventory
        self.max_days = max_days
        
        # 10x10 grid to count state visits
        self.grid = np.zeros((10, 10))
        
    def discretize_inventory(self, inventory):
        """
        Discretize inventory into 10 bins.
        
        Args:
            inventory: Current inventory level (0-100)
            
        Returns:
            int: Bin index (0-9)
        """
        bin_idx = int((inventory / self.max_inventory) * 10)
        return min(bin_idx, 9)  # Ensure we don't exceed index 9
    
    def discretize_day(self, day):
        """
        Discretize day index into 10 bins.
        
        Args:
            day: Current day index (0-30)
            
        Returns:
            int: Bin index (0-9)
        """
        bin_idx = int((day / self.max_days) * 10)
        return min(bin_idx, 9)
    
    def update(self, inventory, day):
        """
        Record a state visit.
        
        Args:
            inventory: Current inventory level
            day: Current day index
        """
        row = self.discretize_inventory(inventory)
        col = self.discretize_day(day)
        self.grid[row, col] += 1
    
    def reset(self):
        """Clear the heatmap grid."""
        self.grid = np.zeros((10, 10))
    
    def plot(self, title="State Visitation Heatmap", save_path=None):
        """
        Plot the state visitation heatmap.
        
        Args:
            title: Plot title (default: "State Visitation Heatmap")
            save_path: Path to save the figure (optional)
            
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create heatmap
        sns.heatmap(
            self.grid,
            annot=True,
            fmt='.0f',
            cmap='YlOrRd',
            cbar_kws={'label': 'Visit Count'},
            ax=ax
        )
        
        # Labels
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('Day Progress (bins)', fontsize=12)
        ax.set_ylabel('Inventory Level (bins)', fontsize=12)
        
        # Add bin labels
        day_labels = [f"{i*3}-{(i+1)*3}" for i in range(10)]
        inventory_labels = [f"{i*10}-{(i+1)*10}" for i in range(10)]
        
        ax.set_xticklabels(day_labels, rotation=45)
        ax.set_yticklabels(inventory_labels, rotation=0)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Heatmap saved to {save_path}")
        
        return fig


def generate_heatmap_from_episodes(env, policy, num_episodes=10, save_path=None):
    """
    Generate a heatmap by running episodes with a given policy.
    
    Args:
        env: Gymnasium environment instance
        policy: Policy function that takes observation and returns action
        num_episodes: Number of episodes to run (default: 10)
        save_path: Path to save the figure (optional)
        
    Returns:
        StateHeatmap: The populated heatmap object
    """
    heatmap = StateHeatmap()
    
    for episode in range(num_episodes):
        obs, _ = env.reset()
        done = False
        
        while not done:
            # Get action from policy
            action = policy(obs)
            
            # Track current state
            # Extract inventory from observation (first element, denormalized)
            inventory = obs[0] * 100
            day = env.day_index
            
            heatmap.update(inventory, day)
            
            # Step environment
            obs, _, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
    
    # Plot the heatmap
    heatmap.plot(
        title=f"State Visitation Heatmap ({num_episodes} episodes)",
        save_path=save_path
    )
    
    return heatmap


def generate_heatmap_from_model(env, model, num_episodes=10, save_path=None):
    """
    Generate a heatmap by running episodes with a trained SB3 model.
    
    Args:
        env: Gymnasium environment instance
        model: Trained Stable-Baselines3 model
        num_episodes: Number of episodes to run (default: 10)
        save_path: Path to save the figure (optional)
        
    Returns:
        StateHeatmap: The populated heatmap object
    """
    heatmap = StateHeatmap()
    
    for episode in range(num_episodes):
        obs, _ = env.reset()
        done = False
        
        while not done:
            # Get action from model
            action, _ = model.predict(obs, deterministic=True)
            
            # Track current state
            inventory = obs[0] * 100
            day = env.day_index
            
            heatmap.update(inventory, day)
            
            # Step environment
            obs, _, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
    
    # Plot the heatmap
    heatmap.plot(
        title=f"State Visitation Heatmap ({num_episodes} episodes)",
        save_path=save_path
    )
    
    return heatmap
