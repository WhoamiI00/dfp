import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Tuple

class RealInventoryEnv(gym.Env):
    """
    Ultra-simple 1-day delivery inventory:
    - 100 unit warehouse capacity
    - 10 products
    - Random demand 0-20 per product
    - Orders arrive next day
    - AI must maintain ~100 units total
    """
    metadata = {"render_modes": ["human"], "render_fps": 4}

    def __init__(self, num_products: int = 10, max_days: int = 30, seed: int = 42):
        super().__init__()
        self.num_products = num_products
        self.max_days = max_days
        self.warehouse_capacity = 100
        self.rng = np.random.default_rng(seed)
        
        # Observation: [stock, yesterday_demand, 7day_avg, demand_ratio, total_stock, warehouse_gap]
        # 6 features per product
        self.observation_space = spaces.Box(
            low=0, high=200,
            shape=(self.num_products, 6), 
            dtype=np.float32
        )
        
        # Action: AI outputs allocation fractions (0-1) for each product
        # System scales them by warehouse_gap automatically
        self.action_space = spaces.Box(
            low=0.0, 
            high=1.0,  # Fraction/allocation per product
            shape=(self.num_products,), 
            dtype=np.float32
        )
        
        self._reset_internal()

    def _reset_internal(self):
        """Start with 10 units per product = 100 total"""
        self.current_day = 0
        self.stocks = np.full(self.num_products, 10.0)
        
        # Demand history (14 days)
        self.demand_history = np.zeros((14, self.num_products))
        for i in range(14):
            self.demand_history[i] = self.rng.integers(0, 21, size=self.num_products).astype(float)
        
        self.yesterday_demand = self.demand_history[-1].copy()
        self.pending_orders = np.zeros(self.num_products)
        
        self.perfect_days = 0
        self.total_stockouts = 0

    def reset(self, *, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self._reset_internal()
        return self._get_obs(), {}

    def _get_obs(self) -> np.ndarray:
        """
        [0] Current stock per product
        [1] Yesterday's demand
        [2] 7-day average demand
        [3] Demand ratio (this product / total avg demand)
        [4] Total warehouse stock (same for all)
        [5] Warehouse gap - HOW MUCH TOTAL TO ORDER
        """
        obs = np.zeros((self.num_products, 6))
        
        total_stock = self.stocks.sum()
        warehouse_gap = max(0, self.warehouse_capacity - total_stock)
        avg_7day = np.mean(self.demand_history[-7:], axis=0)
        
        # Calculate demand ratio: what % of total demand is this product?
        total_avg_demand = avg_7day.sum()
        if total_avg_demand > 0:
            demand_ratio = avg_7day / total_avg_demand
        else:
            demand_ratio = np.ones(self.num_products) / self.num_products
        
        obs[:, 0] = self.stocks
        obs[:, 1] = self.yesterday_demand
        obs[:, 2] = avg_7day
        obs[:, 3] = demand_ratio  # KEY: Shows which products need more
        obs[:, 4] = total_stock
        obs[:, 5] = warehouse_gap
        
        return obs.astype(np.float32)

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, dict]:
        """
        Each day:
        1. Yesterday's orders arrive
        2. Demand happens
        3. AI orders new stock (arrives tomorrow)
        """
        # Convert action fractions to actual order quantities
        action = np.clip(action, 0, 1)  # Ensure 0-1 range
        
        # Calculate how much to order based on warehouse gap
        total_stock_before_orders = self.stocks.sum()
        warehouse_gap = max(0, self.warehouse_capacity - total_stock_before_orders)
        
        # AI allocates fractions, we scale by warehouse gap
        if warehouse_gap > 0 and action.sum() > 0:
            allocations = action / action.sum()  # Normalize to sum to 1
            orders = allocations * warehouse_gap  # Scale to fill gap
            orders = np.round(orders).astype(float)  # Round to whole units
        else:
            orders = np.zeros(self.num_products)
        
        # Step 1: Yesterday's orders arrive
        self.stocks += self.pending_orders
        
        # Enforce 100 capacity (scale down if needed)
        total = self.stocks.sum()
        if total > self.warehouse_capacity:
            self.stocks *= (self.warehouse_capacity / total)
        
        # Step 2: Demand happens (0-20 per product)
        demand = self.rng.integers(0, 21, size=self.num_products).astype(float)
        fulfilled = np.minimum(self.stocks, demand)
        unmet = demand - fulfilled
        self.stocks -= fulfilled
        
        # Step 3: AI places orders (arrive tomorrow)
        self.pending_orders = orders.copy()
        
        # Step 4: REWARD - Focus on ordering the RIGHT TOTAL AMOUNT
        total_stock = self.stocks.sum()
        warehouse_gap_after = max(0, self.warehouse_capacity - total_stock)
        total_ordered = orders.sum()
        total_unmet = unmet.sum()
        
        # PRIMARY: Order close to warehouse_gap (before demand)
        if warehouse_gap > 5:
            # How close is total_ordered to warehouse_gap?
            gap_error = abs(total_ordered - warehouse_gap)
            if gap_error < 10:
                order_reward = 2000  # Excellent!
            elif gap_error < 20:
                order_reward = 1000  # Good
            else:
                order_reward = max(0, 500 - gap_error * 5)  # Decreasing
        else:
            order_reward = 1000  # Warehouse full, good!
        
        # SECONDARY: Don't run out of stock
        unmet_penalty = total_unmet * 50
        
        # BONUS: Perfect day
        perfect_bonus = 1000 if total_unmet == 0 else 0
        if total_unmet == 0:
            self.perfect_days += 1
        
        # BONUS: Keep warehouse 80-100
        if 80 <= total_stock <= 100:
            stock_bonus = 300
        elif total_stock < 50:
            stock_bonus = -300
        else:
            stock_bonus = 0
        
        # SMART ALLOCATION BONUS: Reward ordering MORE for high-demand products
        avg_7day = np.mean(self.demand_history[-7:], axis=0)
        total_avg = avg_7day.sum()
        
        if total_avg > 0 and total_ordered > 10:
            # Calculate ideal allocation based on demand patterns
            ideal_allocation = avg_7day / total_avg  # Fraction per product
            actual_allocation = orders / max(1, total_ordered)  # What AI actually ordered
            
            # Reward if allocation matches demand pattern (use correlation)
            allocation_quality = 0
            for i in range(self.num_products):
                if avg_7day[i] > 0:  # Only check products with demand
                    # If high-demand product got high allocation → good!
                    if actual_allocation[i] > 0:
                        ratio = min(actual_allocation[i] / ideal_allocation[i], 
                                  ideal_allocation[i] / actual_allocation[i])
                        allocation_quality += ratio
            
            allocation_bonus = (allocation_quality / self.num_products) * 500
        else:
            allocation_bonus = 0
        
        reward = order_reward - unmet_penalty + perfect_bonus + stock_bonus + allocation_bonus
        
        # Track
        stockout_count = (unmet > 0).sum()
        if total_unmet > 0:
            self.total_stockouts += 1
        
        # Update history
        self.current_day += 1
        self.yesterday_demand = demand.copy()
        self.demand_history = np.roll(self.demand_history, -1, axis=0)
        self.demand_history[-1] = demand
        
        terminated = self.current_day >= self.max_days
        
        info = {
            'day': self.current_day,
            'demand': demand.tolist(),
            'fulfilled': fulfilled.tolist(),
            'unmet_demand': unmet.tolist(),
            'stocks': self.stocks.tolist(),
            'arrivals': self.pending_orders.tolist(),
            'orders_placed': orders.tolist(),
            'stockout_products': int(stockout_count),
            'total_unmet': float(total_unmet),
            'reward': float(reward),
            'perfect_days': self.perfect_days,
            'total_stockouts': self.total_stockouts,
            'total_stock': float(total_stock),
            'warehouse_gap': float(warehouse_gap),
            'total_ordered': float(total_ordered),
            'allocation_quality': float(allocation_bonus) if total_ordered > 10 else 0.0,
        }
        
        return self._get_obs(), float(reward), terminated, False, info

    def render(self):
        total_stock = self.stocks.sum()
        print(f"\nDay {self.current_day}/{self.max_days}")
        print(f"Stock: {int(total_stock)}/100 units")
        print(f"Products: {self.stocks.astype(int)}")
        print(f"Perfect Days: {self.perfect_days}/{self.current_day}")
