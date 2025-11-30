"""
Inventory Management Environment using Gymnasium

This environment simulates a single-product inventory management system where:
- Episodes last 30 days
- Initial inventory = 100 units
- Demand varies by weekday/weekend with a trend component
- Agent decides daily order quantities
- Rewards encourage maintaining optimal inventory levels
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces


class InventoryEnv(gym.Env):
    """
    Custom Gymnasium environment for inventory management.
    
    The agent must decide daily order quantities to avoid stockouts and overstocking.
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(self, 
                 initial_inventory=100,
                 max_capacity=100,
                 episode_length=30,
                 trend_strength=5):
        """
        Initialize the inventory environment.
        
        Args:
            initial_inventory: Starting inventory level (default: 100)
            max_capacity: Maximum inventory capacity (default: 100)
            episode_length: Number of days per episode (default: 30)
            trend_strength: Strength of demand trend over time (default: 5)
        """
        super().__init__()
        
        self.initial_inventory = initial_inventory
        self.max_capacity = max_capacity
        self.episode_length = episode_length
        self.trend_strength = trend_strength
        
        # Action space: 11 discrete actions (0, 5, 10, ..., 50 units)
        self.action_space = spaces.Discrete(11)
        
        # Observation space: [inventory_norm, day_norm, dow_norm]
        # All values normalized to [0, 1]
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, 0.0]),
            high=np.array([1.0, 1.0, 1.0]),
            dtype=np.float32
        )
        
        # State variables
        self.inventory = initial_inventory
        self.day_index = 0
        self.day_of_week = 0  # 0=Monday, 6=Sunday
        
        # Tracking
        self.demand_history = []
        self.inventory_history = []
        self.action_history = []
        
    def _get_demand(self):
        """
        Generate demand based on day of week and trend.
        
        Demand ranges:
        - Monday-Friday: 0-10 units
        - Saturday: 10-20 units
        - Sunday: 20-30 units
        
        Plus a trend component that increases over the episode.
        
        Returns:
            int: Demand for the current day
        """
        # Base demand by day of week
        if self.day_of_week < 5:  # Monday-Friday
            base_demand = np.random.randint(0, 11)
        elif self.day_of_week == 5:  # Saturday
            base_demand = np.random.randint(10, 21)
        else:  # Sunday
            base_demand = np.random.randint(20, 31)
        
        # Add trend component
        trend = self.day_index / self.episode_length
        demand_with_trend = base_demand + int(trend * self.trend_strength)
        
        return max(0, demand_with_trend)
    
    def _get_observation(self):
        """
        Get the current state observation.
        
        Returns:
            np.array: Normalized observation [inventory/100, day/30, dow/6]
        """
        obs = np.array([
            self.inventory / self.max_capacity,
            self.day_index / self.episode_length,
            self.day_of_week / 6.0
        ], dtype=np.float32)
        
        return obs
    
    def reset(self, seed=None, options=None):
        """
        Reset the environment to initial state.
        
        Args:
            seed: Random seed for reproducibility
            options: Additional options (not used)
            
        Returns:
            tuple: (observation, info)
        """
        super().reset(seed=seed)
        
        self.inventory = self.initial_inventory
        self.day_index = 0
        self.day_of_week = 0
        
        self.demand_history = []
        self.inventory_history = []
        self.action_history = []
        
        observation = self._get_observation()
        info = {}
        
        return observation, info
    
    def step(self, action):
        """
        Execute one time step in the environment.
        
        Args:
            action: Integer from 0-10, representing order quantity (action * 5 units)
            
        Returns:
            tuple: (observation, reward, terminated, truncated, info)
        """
        # Convert action to order quantity (0, 5, 10, ..., 50)
        order_qty = action * 5
        
        # Add order to inventory
        self.inventory += order_qty
        
        # Generate demand
        demand = self._get_demand()
        
        # Calculate sales (cannot sell more than available)
        sold = min(self.inventory, demand)
        unmet_demand = demand - sold
        
        # Update inventory
        self.inventory -= sold
        
        # Calculate reward
        # +1 for perfect day (no stockout, no overstock, inventory > 0)
        # -1 otherwise
        if unmet_demand == 0 and self.inventory <= self.max_capacity and self.inventory > 0:
            reward = 1.0
        else:
            reward = -1.0
        
        # Track history
        self.demand_history.append(demand)
        self.inventory_history.append(self.inventory)
        self.action_history.append(order_qty)
        
        # Advance time
        self.day_index += 1
        self.day_of_week = (self.day_of_week + 1) % 7
        
        # Check if episode is done
        terminated = self.day_index >= self.episode_length
        truncated = False
        
        # Get next observation
        observation = self._get_observation()
        
        # Info dict
        info = {
            'demand': demand,
            'sold': sold,
            'unmet_demand': unmet_demand,
            'inventory': self.inventory,
            'order_qty': order_qty,
            'day': self.day_index
        }
        
        return observation, reward, terminated, truncated, info
    
    def render(self):
        """Print current state (optional)."""
        print(f"Day {self.day_index}: Inventory={self.inventory}, DOW={self.day_of_week}")
