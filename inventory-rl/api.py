"""
Inventory AI API Server for AnyLogic Integration
================================================
This API serves the trained Reinforcement Learning model to the AnyLogic simulation.

HOW THE AI WORKS (Warehouse Perspective):
-----------------------------------------
The AI has been trained for 100,000+ timesteps to learn optimal ordering:

1. OBSERVATIONS (What the AI sees):
   - Current inventory level (0-100 units)
   - Day of week (Mon-Sun have different demand patterns)
   - Day in episode (trend: demand increases over time)

2. DEMAND PATTERNS (What the AI learned):
   - Weekdays (Mon-Fri): Low demand (0-15 units/day)
   - Saturday: Medium demand (15-30 units/day)
   - Sunday: High demand (30-50 units/day)

3. DECISIONS (What the AI outputs):
   - Order quantity: 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, or 50 units
   - Goal: Keep inventory between 20-80 to avoid:
     * Stockouts (inventory = 0, can't fulfill orders)
     * Overstocking (inventory > 100, storage overflow)

4. REWARD SYSTEM (How it was trained):
   - +1 if: No stockout AND no overstock AND inventory > 0
   - -1 otherwise
   - This teaches the AI to maintain safe inventory levels
"""

import os
import sys
from datetime import datetime
from typing import Optional
import numpy as np

# FastAPI setup
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("ERROR: Missing dependencies. Run:")
    print("  pip install fastapi uvicorn pydantic")
    sys.exit(1)

# Model loading
MODEL_LOADED = False
model = None

try:
    from stable_baselines3 import DQN, PPO
    
    # Try to find the best model
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_paths = [
        os.path.join(script_dir, "models", "best_model.zip"),
        os.path.join(script_dir, "models", "dqn_inventory.zip"),
        os.path.join(script_dir, "models", "ppo_inventory.zip"),
    ]
    
    for path in model_paths:
        if os.path.exists(path):
            if "ppo" in path.lower() or "best" in path.lower():
                model = PPO.load(path)
                print(f"✅ Loaded PPO model: {path}")
            else:
                model = DQN.load(path)
                print(f"✅ Loaded DQN model: {path}")
            MODEL_LOADED = True
            break
    
    if not MODEL_LOADED:
        print("⚠️ No trained model found. Using fallback heuristic.")
        
except ImportError:
    print("⚠️ stable-baselines3 not found. Using fallback heuristic.")

# ============ API Setup ============
app = FastAPI(
    title="Warehouse Inventory AI",
    description="AI-powered inventory ordering decisions for AnyLogic simulation",
    version="2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Request/Response Models ============
class InventoryState(BaseModel):
    inventory: float
    day_index: int
    day_of_week: int
    previous_demand: Optional[float] = None
    previous_sold: Optional[float] = None

class PredictionResponse(BaseModel):
    action: int
    order_quantity: int
    reasoning: str
    inventory_status: str
    demand_forecast: str
    formatted_log: str

# ============ Tracking ============
request_count = 0
total_ordered = 0
last_orders = []

# ============ Helper Functions ============
def get_inventory_status(inv: float) -> str:
    """Classify inventory level."""
    if inv <= 0:
        return "🔴 CRITICAL: Stockout!"
    elif inv < 20:
        return "🟠 LOW: Risk of stockout"
    elif inv < 50:
        return "🟢 OPTIMAL: Good level"
    elif inv < 80:
        return "🟡 HIGH: Getting full"
    else:
        return "🔴 DANGER: Near overflow!"

def get_demand_forecast(dow: int) -> str:
    """Predict expected demand based on day of week."""
    if dow < 5:  # Mon-Fri
        return f"Weekdays (Day {dow}): Expect LOW demand (5-15 units)"
    elif dow == 5:  # Saturday
        return "Saturday: Expect MEDIUM demand (15-30 units)"
    else:  # Sunday
        return "Sunday: Expect HIGH demand (30-50 units)"

def get_reasoning(inv: float, dow: int, order: int) -> str:
    """Explain why the AI made this decision."""
    if order == 0:
        if inv > 60:
            return "Inventory is high. No order needed."
        else:
            return "Demand seems manageable. Holding off on ordering."
    elif order <= 15:
        return "Small top-up order to maintain safety stock."
    elif order <= 30:
        return "Medium order to prepare for upcoming demand."
    else:
        if dow >= 5:
            return "Large order! Preparing for weekend rush."
        else:
            return "Large order to replenish after stockout or heavy demand."

def fallback_heuristic(inventory: float, day_of_week: int) -> int:
    """Simple rule-based ordering when no AI model is available."""
    # Target inventory: 50 units
    target = 50
    
    # Predict demand based on day of week
    if day_of_week < 5:
        expected_demand = 10  # Weekday
    elif day_of_week == 5:
        expected_demand = 22  # Saturday
    else:
        expected_demand = 40  # Sunday
    
    # Calculate order to reach target + cover expected demand
    needed = max(0, target + expected_demand - inventory)
    
    # Round to nearest action (multiple of 5)
    action = min(10, int(round(needed / 5)))
    
    return action

# ============ API Endpoints ============
@app.get("/")
def root():
    return {
        "status": "online",
        "model_loaded": MODEL_LOADED,
        "requests_served": request_count,
        "total_units_ordered": total_ordered,
        "last_5_orders": last_orders[-5:]
    }

@app.get("/health")
def health():
    return {"status": "healthy", "model_loaded": MODEL_LOADED}

@app.post("/predict", response_model=PredictionResponse)
def predict(state: InventoryState):
    global request_count, total_ordered, last_orders
    request_count += 1
    
    # Normalize observation for model
    obs = np.array([
        state.inventory / 100.0,
        state.day_index / 30.0,
        state.day_of_week / 6.0
    ], dtype=np.float32)
    
    # Get action from model or fallback
    if MODEL_LOADED and model is not None:
        action, _ = model.predict(obs, deterministic=True)
        action = int(action)
        method = "AI Model"
    else:
        action = fallback_heuristic(state.inventory, state.day_of_week)
        method = "Heuristic"
    
    order_quantity = action * 5
    
    # Generate explanations
    inv_status = get_inventory_status(state.inventory)
    demand_forecast = get_demand_forecast(state.day_of_week)
    reasoning = get_reasoning(state.inventory, state.day_of_week, order_quantity)
    
    # Update tracking
    total_ordered += order_quantity
    last_orders.append(order_quantity)
    if len(last_orders) > 10:
        last_orders.pop(0)

    # --- Generate Formatted Log ---
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Header line with Day and previous day stats (if available)
    header_info = f"Day {state.day_index} ({state.day_of_week})"
    if state.previous_demand is not None:
        header_info += f" | Demand: {state.previous_demand:.0f}"
    if state.previous_sold is not None:
        header_info += f" | Sold: {state.previous_sold:.0f}"
    
    # Create the structured log message
    log_lines = []
    log_lines.append("="*60)
    log_lines.append(f"📦 REQUEST #{request_count} [{timestamp}]")
    log_lines.append(f"{header_info}")
    log_lines.append("-" * 30)
    log_lines.append(f"🤖 DECISION ({method}):")
    log_lines.append(f"     {inv_status}")
    log_lines.append(f"     📊 {demand_forecast}")
    log_lines.append(f"     📦 ORDER: {order_quantity} units")
    log_lines.append(f"     💭 Reasoning: {reasoning}")
    log_lines.append("-" * 30)
    log_lines.append(f"  📊 DEBUG: Inv={state.inventory:.0f} | Obs={obs.tolist()}")
    log_lines.append("="*60)
    
    # Combine into single string
    formatted_log = "\n".join(log_lines)
    
    # Print to terminal
    print("\n" + formatted_log + "\n")
    
    return PredictionResponse(
        action=action,
        order_quantity=order_quantity,
        reasoning=reasoning,
        inventory_status=inv_status,
        demand_forecast=demand_forecast,
        formatted_log=formatted_log
    )

@app.post("/reset")
def reset_stats():
    global request_count, total_ordered, last_orders
    request_count = 0
    total_ordered = 0
    last_orders = []
    return {"status": "reset", "message": "Statistics cleared"}


# ============ Simulation endpoint (replaces streamlit dashboard) ============
#
# Runs N 30-day episodes of the InventoryEnv under one of three policies
# (random / EOQ / trained RL). Returns aggregate metrics + per-day details
# of the last episode so the React UI can render the same charts the
# Streamlit dashboard did, without needing a second server / iframe.

class SimulateRequest(BaseModel):
    policy: str = "rl"  # "random" | "eoq" | "rl"
    episodes: int = 10
    seed: Optional[int] = None
    initial_inventory: int = 100
    max_capacity: int = 100
    trend_strength: int = 5
    # EOQ tunables (ignored for other policies)
    eoq_avg_demand: int = 20
    eoq_reorder_point: int = 40


class EpisodeDay(BaseModel):
    day: int
    day_of_week: str
    inventory_start: float
    order_qty: int
    demand: int
    sold: int
    unmet_demand: int
    inventory_end: float
    reward: float


class EpisodeStat(BaseModel):
    episode: int
    total_reward: float
    stockout_days: int
    overstock_days: int
    service_level: float
    avg_inventory: float


class SimulateAggregate(BaseModel):
    avg_total_reward: float
    avg_stockout_days: float
    avg_overstock_days: float
    avg_service_level: float
    avg_inventory: float


class SimulateResponse(BaseModel):
    policy: str
    policy_label: str
    episodes_run: int
    aggregate: SimulateAggregate
    per_episode: list[EpisodeStat]
    last_episode_days: list[EpisodeDay]
    used_model: bool
    notes: str = ""
    # 10x10 state-visitation grid: rows = inventory bins (0-9 = 0-100 in steps of 10),
    # cols = day bins (0-9 = days 0-29 in steps of 3). Same discretization as
    # utils.heatmap.StateHeatmap so the visualization is faithful to the
    # streamlit dashboard's heatmap.
    heatmap: list[list[int]] = []


_DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _run_one_episode(env, policy_key: str, model, baseline, seed, heatmap=None):
    """Roll out one 30-day episode. Mirrors the streamlit run_episode().

    If `heatmap` is provided (a StateHeatmap instance), each pre-step state
    (inventory, day) is recorded so the caller can visualize coverage."""
    obs, _ = env.reset(seed=seed)
    days_log: list[EpisodeDay] = []
    total_reward = 0.0
    total_demand = 0
    total_sold = 0
    stockout_days = 0
    overstock_days = 0
    inv_end_history: list[float] = []

    for day in range(env.episode_length):
        inv_start = float(env.inventory)
        if heatmap is not None:
            heatmap.update(env.inventory, env.day_index)
        if policy_key == "random":
            action = env.action_space.sample()
        elif policy_key == "eoq":
            action = baseline.get_discrete_action(env.inventory, env.max_capacity)
        elif policy_key == "rl" and model is not None:
            a, _ = model.predict(obs, deterministic=True)
            action = int(a)
        else:
            action = 0  # Fallback: do nothing.

        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += float(reward)
        total_demand += int(info["demand"])
        total_sold += int(info["sold"])
        if info["unmet_demand"] > 0:
            stockout_days += 1
        if env.inventory > env.max_capacity:
            overstock_days += 1
        inv_end_history.append(float(info["inventory"]))
        days_log.append(EpisodeDay(
            day=day + 1,
            day_of_week=_DOW_LABELS[(info.get("day", day) - 1) % 7],
            inventory_start=inv_start,
            order_qty=int(info["order_qty"]),
            demand=int(info["demand"]),
            sold=int(info["sold"]),
            unmet_demand=int(info["unmet_demand"]),
            inventory_end=float(info["inventory"]),
            reward=float(reward),
        ))
        if terminated or truncated:
            break

    service_level = (total_sold / total_demand * 100.0) if total_demand > 0 else 100.0
    avg_inv = float(np.mean(inv_end_history)) if inv_end_history else 0.0
    return {
        "days": days_log,
        "total_reward": total_reward,
        "stockout_days": stockout_days,
        "overstock_days": overstock_days,
        "service_level": service_level,
        "avg_inventory": avg_inv,
    }


@app.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest):
    """Run N episodes under a chosen policy and return aggregate + last-
    episode details. Replaces the standalone Streamlit dashboard."""
    if req.episodes < 1 or req.episodes > 50:
        raise HTTPException(status_code=400, detail="episodes must be in [1, 50]")
    if req.policy not in ("random", "eoq", "rl"):
        raise HTTPException(status_code=400, detail="policy must be random|eoq|rl")

    # Local imports so the module loads even if these aren't installed —
    # /predict still works in fallback mode.
    try:
        from env.inventory_env import InventoryEnv
        from utils.eoq import EOQBaseline
        from utils.heatmap import StateHeatmap
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"inventory-rl env unavailable: {e}",
        )

    used_model = False
    notes = ""
    baseline = None
    eval_model = None
    policy_label = req.policy

    if req.policy == "rl":
        if MODEL_LOADED and model is not None:
            eval_model = model
            used_model = True
            policy_label = "Trained RL"
        else:
            notes = "RL model not loaded; falling back to random actions."
            policy_label = "RL (no model — random fallback)"
    elif req.policy == "eoq":
        baseline = EOQBaseline(
            avg_daily_demand=req.eoq_avg_demand,
            reorder_point=req.eoq_reorder_point,
        )
        policy_label = f"EOQ (Q≈{baseline.eoq:.0f}, reorder={baseline.reorder_point})"
    else:
        policy_label = "Random"

    env = InventoryEnv(
        initial_inventory=req.initial_inventory,
        max_capacity=req.max_capacity,
        episode_length=30,
        trend_strength=req.trend_strength,
    )

    heatmap = StateHeatmap(max_inventory=req.max_capacity, max_days=30)
    per_ep: list[EpisodeStat] = []
    last_days: list[EpisodeDay] = []
    rewards = []
    stockouts = []
    overstocks = []
    services = []
    avgs = []
    for i in range(req.episodes):
        s = req.seed + i if req.seed is not None else None
        out = _run_one_episode(env, req.policy, eval_model, baseline, s, heatmap=heatmap)
        per_ep.append(EpisodeStat(
            episode=i + 1,
            total_reward=out["total_reward"],
            stockout_days=out["stockout_days"],
            overstock_days=out["overstock_days"],
            service_level=out["service_level"],
            avg_inventory=out["avg_inventory"],
        ))
        rewards.append(out["total_reward"])
        stockouts.append(out["stockout_days"])
        overstocks.append(out["overstock_days"])
        services.append(out["service_level"])
        avgs.append(out["avg_inventory"])
        last_days = out["days"]

    return SimulateResponse(
        policy=req.policy,
        policy_label=policy_label,
        episodes_run=req.episodes,
        aggregate=SimulateAggregate(
            avg_total_reward=float(np.mean(rewards)),
            avg_stockout_days=float(np.mean(stockouts)),
            avg_overstock_days=float(np.mean(overstocks)),
            avg_service_level=float(np.mean(services)),
            avg_inventory=float(np.mean(avgs)),
        ),
        per_episode=per_ep,
        last_episode_days=last_days,
        used_model=used_model,
        notes=notes,
        heatmap=heatmap.grid.astype(int).tolist(),
    )


# --- Policy comparison ------------------------------------------------------
#
# Re-runs the simulation under each of the three policies with shared seed
# + env params so the trained-model advantage is visible side-by-side. The
# UI uses this for a single chart that flexes the model.

class CompareRequest(BaseModel):
    episodes: int = 10
    seed: Optional[int] = 42
    initial_inventory: int = 100
    max_capacity: int = 100
    trend_strength: int = 5
    eoq_avg_demand: int = 20
    eoq_reorder_point: int = 40


class PolicyComparisonRow(BaseModel):
    policy: str
    policy_label: str
    used_model: bool
    aggregate: SimulateAggregate
    per_episode_rewards: list[float]
    notes: str = ""


class CompareResponse(BaseModel):
    rows: list[PolicyComparisonRow]
    episodes: int
    seed: Optional[int]


@app.post("/compare", response_model=CompareResponse)
def compare_policies(req: CompareRequest):
    """Run all three policies (random / EOQ / RL) with the same seed and
    env settings and return aggregate metrics for each. The frontend
    renders this as a side-by-side bar chart."""
    rows: list[PolicyComparisonRow] = []
    for policy in ("random", "eoq", "rl"):
        sim_req = SimulateRequest(
            policy=policy,
            episodes=req.episodes,
            seed=req.seed,
            initial_inventory=req.initial_inventory,
            max_capacity=req.max_capacity,
            trend_strength=req.trend_strength,
            eoq_avg_demand=req.eoq_avg_demand,
            eoq_reorder_point=req.eoq_reorder_point,
        )
        sim = simulate(sim_req)  # reuse the existing endpoint's logic
        rows.append(PolicyComparisonRow(
            policy=sim.policy,
            policy_label=sim.policy_label,
            used_model=sim.used_model,
            aggregate=sim.aggregate,
            per_episode_rewards=[e.total_reward for e in sim.per_episode],
            notes=sim.notes,
        ))
    return CompareResponse(rows=rows, episodes=req.episodes, seed=req.seed)

# ============ Main Entry Point ============
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏭 WAREHOUSE INVENTORY AI SERVER")
    print("="*60)
    print(f"Model Status: {'✅ LOADED' if MODEL_LOADED else '⚠️ Using Fallback Heuristic'}")
    print("Server starting on: http://127.0.0.1:8000")
    print("Endpoints:")
    print("  GET  /        - Server status")
    print("  GET  /health  - Health check")
    print("  POST /predict - Get AI ordering decision")
    print("  POST /reset   - Reset statistics")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
