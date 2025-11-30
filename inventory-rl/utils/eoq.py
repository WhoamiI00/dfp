"""
Economic Order Quantity (EOQ) Module

Provides EOQ calculation and baseline policy for inventory management.
EOQ is used as a reference for comparison with RL-based policies.
"""

import numpy as np


def calculate_eoq(demand_total, ordering_cost, holding_cost):
    """
    Calculate Economic Order Quantity using the classic formula.
    
    EOQ = sqrt((2 * D * S) / H)
    
    Where:
        D = Total demand over the period
        S = Ordering cost per order
        H = Holding cost per unit per period
    
    Args:
        demand_total: Total expected demand over the planning period
        ordering_cost: Fixed cost per order
        holding_cost: Cost to hold one unit for one period
        
    Returns:
        float: Optimal order quantity
    """
    if holding_cost <= 0:
        raise ValueError("Holding cost must be positive")
    
    eoq = np.sqrt((2 * demand_total * ordering_cost) / holding_cost)
    return eoq


class EOQBaseline:
    """
    Baseline inventory policy using EOQ.
    
    This provides a simple rule-based policy for comparison with RL agents.
    """
    
    def __init__(self, 
                 avg_daily_demand=10,
                 episode_length=30,
                 ordering_cost=50,
                 holding_cost=1,
                 reorder_point=20):
        """
        Initialize EOQ baseline policy.
        
        Args:
            avg_daily_demand: Average daily demand (default: 10)
            episode_length: Length of planning period in days (default: 30)
            ordering_cost: Fixed cost per order (default: 50)
            holding_cost: Cost per unit per day (default: 1)
            reorder_point: Inventory level that triggers reorder (default: 20)
        """
        self.avg_daily_demand = avg_daily_demand
        self.episode_length = episode_length
        self.ordering_cost = ordering_cost
        self.holding_cost = holding_cost
        self.reorder_point = reorder_point
        
        # Calculate EOQ
        total_demand = avg_daily_demand * episode_length
        self.eoq = calculate_eoq(total_demand, ordering_cost, holding_cost)
        
    def get_action(self, inventory, max_capacity=100):
        """
        Decide order quantity based on EOQ policy.
        
        Strategy:
        - If inventory <= reorder_point, order EOQ quantity
        - Otherwise, order 0
        - Respect maximum capacity constraint
        
        Args:
            inventory: Current inventory level
            max_capacity: Maximum inventory capacity (default: 100)
            
        Returns:
            int: Order quantity (rounded to nearest 5 for consistency)
        """
        if inventory <= self.reorder_point:
            # Order EOQ, but don't exceed capacity
            order_qty = min(self.eoq, max_capacity - inventory)
            # Round to nearest 5 for consistency with action space
            order_qty = round(order_qty / 5) * 5
            return max(0, int(order_qty))
        else:
            return 0
    
    def get_discrete_action(self, inventory, max_capacity=100):
        """
        Get action in the same discrete format as RL agent (0-10).
        
        Args:
            inventory: Current inventory level
            max_capacity: Maximum inventory capacity (default: 100)
            
        Returns:
            int: Discrete action (0-10) where action * 5 = order quantity
        """
        order_qty = self.get_action(inventory, max_capacity)
        # Convert to discrete action (0-10)
        discrete_action = min(order_qty // 5, 10)
        return discrete_action
    
    def __str__(self):
        """String representation of the baseline policy."""
        return f"EOQBaseline(EOQ={self.eoq:.2f}, reorder_point={self.reorder_point})"


def estimate_demand(env, num_episodes=10):
    """
    Estimate average daily demand by running random episodes.
    
    This is useful for dynamically calculating EOQ when actual demand
    distribution is unknown.
    
    Args:
        env: Gymnasium environment instance
        num_episodes: Number of episodes to sample (default: 10)
        
    Returns:
        float: Estimated average daily demand
    """
    total_demand = 0
    total_days = 0
    
    for _ in range(num_episodes):
        env.reset()
        done = False
        
        while not done:
            # Take random action
            action = env.action_space.sample()
            _, _, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            
            total_demand += info.get('demand', 0)
            total_days += 1
    
    avg_demand = total_demand / total_days if total_days > 0 else 10
    return avg_demand
