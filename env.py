import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Tuple

class InventoryEnv(gym.Env):
    metadata = {"render_modes": ["human"], "render_fps": 4}

    def __init__(self, num_products: int = 10, max_days: int = 30, seed: int = 42):
        super().__init__()
        self.num_products = num_products
        self.max_days = max_days
        self.days_passed = 0
        self.rng = np.random.default_rng(seed)

        self.features = 10
        self.observation_space = spaces.Box(low=0, high=1e6, shape=(self.num_products, self.features), dtype=np.float32)

        self.max_order = 200.0
        self.action_space = spaces.Box(low=0.0, high=self.max_order, shape=(self.num_products,), dtype=np.float32)

        self._reset_internal()

        self.holding_cost = 0.01
        self.stockout_penalty = 1.0
        self.overstock_penalty = 0.1
        self.no_issue_bonus = 10.0

    def _reset_internal(self):
        self.stocks = self.rng.integers(10, 50, size=self.num_products).astype(float)
        self.last_demand = np.zeros(self.num_products)
        self.outstanding = np.zeros(self.num_products)
        self.lead_time = self.rng.integers(1, 5, size=self.num_products).astype(float)
        self.safety_stock = np.maximum(2, self.rng.integers(1, 8, size=self.num_products)).astype(float)
        self.avg_daily = np.maximum(1, self.rng.integers(1, 10, size=self.num_products)).astype(float)
        self.last_order = np.zeros(self.num_products)
        self.days_until_delivery = np.zeros(self.num_products)
        self.cumulative_sold = np.zeros(self.num_products)
        self.product_id = np.arange(self.num_products)
        self.days_passed = 0

    def reset(self, *, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self._reset_internal()
        return self._get_obs(), {}

    def _get_obs(self):
        obs = np.zeros((self.num_products, self.features))
        obs[:, 0] = self.stocks
        obs[:, 1] = self.last_demand
        obs[:, 2] = self.outstanding
        obs[:, 3] = self.lead_time
        obs[:, 4] = self.safety_stock
        obs[:, 5] = self.avg_daily
        obs[:, 6] = self.last_order
        obs[:, 7] = self.days_until_delivery
        obs[:, 8] = self.cumulative_sold
        obs[:, 9] = self.product_id
        return obs

    def step(self, action):
        action = np.clip(action, self.action_space.low, self.action_space.high)

        arrivals = np.zeros_like(self.stocks)
        self.days_until_delivery = np.maximum(0, self.days_until_delivery - 1)

        arriving = (self.days_until_delivery == 0) & (self.outstanding > 0)
        if arriving.any():
            arrivals[arriving] = self.outstanding[arriving]
            self.stocks[arriving] += self.outstanding[arriving]
            self.outstanding[arriving] = 0

        qty = action
        mask = qty > 0
        self.outstanding[mask] += qty[mask]
        self.days_until_delivery[mask] = np.ceil(self.lead_time[mask])
        self.last_order = qty

        demand = self.rng.poisson(lam=self.avg_daily)
        self.last_demand = demand

        sold = np.minimum(self.stocks, demand)
        unmet = demand - sold

        self.stocks -= sold
        self.cumulative_sold += sold

        holding_cost = self.holding_cost * self.stocks.sum()
        overstock_amount = np.maximum(0, self.stocks - (3 * self.avg_daily)).sum()
        total_unmet = unmet.sum()

        reward = (
            -holding_cost
            - self.stockout_penalty * total_unmet
            - self.overstock_penalty * overstock_amount
        )

        if total_unmet == 0 and overstock_amount == 0:
            reward += self.no_issue_bonus

        self.days_passed += 1
        terminated = self.days_passed >= self.max_days

        info = {
            "sold": sold.tolist(),
            "unmet": unmet.tolist(),
            "arrivals": arrivals.tolist(),
            "stocks": self.stocks.tolist(),
            "outstanding": self.outstanding.tolist(),
            "last_order": self.last_order.tolist(),
        }

        return self._get_obs(), float(reward), terminated, False, info

    def render(self):
        print("Stocks:", self.stocks)
