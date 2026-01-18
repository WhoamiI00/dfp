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
