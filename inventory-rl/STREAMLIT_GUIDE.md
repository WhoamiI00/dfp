# 🎨 Streamlit Dashboard Guide

## 📦 Inventory Management Interactive Dashboard

### Overview

The Streamlit dashboard provides an interactive web interface for simulating and comparing different inventory management policies without writing any code.

### Features

#### 1️⃣ **Policy Selection**
- **Random Policy**: Random order quantities (baseline comparison)
- **EOQ Baseline**: Economic Order Quantity formula-based ordering
- **Trained RL Policy**: Uses your trained DQN or PPO model

#### 2️⃣ **Configuration Options**
- Number of episodes (1-50)
- Random seed for reproducibility
- Initial inventory level
- Maximum capacity
- Demand trend strength

#### 3️⃣ **Visualizations**

**Aggregate Metrics Cards**
- Average Total Reward
- Average Stockout Days
- Average Overstock Days
- Average Service Level (%)
- Average Inventory Level

**Episode Statistics Table**
- Per-episode breakdown of all metrics
- Easy comparison across runs

**Inventory Trajectory Chart**
- Line plot of inventory levels over 30 days
- Shows max capacity limit
- Identifies stockouts and overstocks

**Demand, Orders, and Sales Chart**
- Multi-line plot comparing:
  - Daily demand
  - Orders placed
  - Units sold
- Helps visualize ordering strategy

**Daily Rewards Bar Chart**
- Green bars: Perfect days (+1 reward)
- Red bars: Violation days (-1 reward)
- Shows policy performance at a glance

### Demand Model

The environment simulates realistic demand patterns:
- **Weekdays (Mon-Fri)**: 0-15 units per day
- **Saturday**: 15-30 units per day  
- **Sunday**: 30-50 units per day
- **Trend Factor**: Demand gradually increases over the 30-day episode

**Daily Details Table**
- Complete day-by-day breakdown:
  - Day number and day of week
  - Starting inventory
  - Order placed
  - Demand and units sold
  - Unmet demand
  - Ending inventory
  - Daily reward

**State Visitation Heatmap** (optional)
- 10×10 grid showing state space coverage
- Inventory level (rows) vs Day progress (columns)
- Helps debug policy behavior

### How to Use

#### Step 1: Launch the Dashboard
```bash
streamlit run streamlit_app.py
```

#### Step 2: Configure Settings (Sidebar)
1. Select your policy type
2. Choose number of episodes to simulate
3. Optionally set a random seed
4. Adjust environment parameters if needed
5. Enable state heatmap if desired

#### Step 3: Run Simulation
Click the **"🚀 Run Simulation"** button

#### Step 4: Analyze Results
- Review aggregate metrics at the top
- Explore visualizations
- Check daily details table
- Compare different policies by changing settings and re-running

### Tips & Tricks

**Comparing Policies**
1. Run Random Policy first (baseline)
2. Run EOQ Baseline (rule-based)
3. Run Trained RL Policy (learned behavior)
4. Compare the aggregate metrics to see which performs best

**Reproducibility**
- Check "Use Random Seed" and set a consistent seed
- Run the same configuration multiple times to verify consistency

**Performance Analysis**
- Use 10-20 episodes for reliable statistics
- Check service level to ensure demand is being met
- Monitor stockout/overstock days for constraint violations
- Look at daily rewards chart to identify problem days

**Environment Tuning**
- Increase trend_strength to simulate growing demand
- Adjust max_capacity to test different constraints
- Change initial_inventory to test different starting conditions

### Metrics Explained

**Total Reward**
- Sum of daily rewards over 30 days
- +1 for each perfect day (no violations)
- -1 for each day with stockout or overstock
- Maximum possible: +30 (all perfect days)
- Minimum possible: -30 (all violation days)

**Stockout Days**
- Days where demand exceeded available inventory
- Indicates underordering or poor inventory management
- Lower is better

**Overstock Days**
- Days where inventory exceeded maximum capacity
- Indicates overordering
- Lower is better

**Service Level**
- Percentage of total demand that was fulfilled
- 100% means all customer demand was met
- Lower values indicate lost sales due to stockouts

**Average Inventory**
- Mean ending inventory across all days
- Helps understand typical inventory levels
- Balance between too high (waste) and too low (stockouts)

### Troubleshooting

**"No models found" message**
- Train a model first: `python agents/train_dqn.py`
- Ensure model is saved in `models/` directory

**Dashboard won't start**
- Install Streamlit: `pip install streamlit`
- Check you're in the project root directory
- Verify all dependencies are installed

**Model fails to load**
- Check the model file exists in `models/`
- Verify you have stable-baselines3 installed
- Try loading a different model file

**Plots not displaying**
- Refresh the page
- Check matplotlib and seaborn are installed
- Try reducing number of episodes

### Advanced Usage

**Custom Environment Parameters**
Modify sidebar settings to test different scenarios:
- High trend_strength (8-10): Rapidly growing demand
- Low trend_strength (0-2): Stable demand
- Low max_capacity (50-70): Constrained storage
- High initial_inventory (120-150): Overstocked start

**State Heatmap Analysis**
Enable "Show State Heatmap" to visualize:
- Which states the policy visits most often
- Whether the policy explores all regions
- Gaps in state coverage (potential issues)
- Concentration patterns (preferred states)

**Batch Experiments**
Run multiple configurations systematically:
1. Fix all parameters except one
2. Vary that parameter across runs
3. Document results in the episode statistics table
4. Identify optimal configurations

### Next Steps

After using the dashboard:
1. **Improve Training**: If RL policy underperforms, retrain with adjusted hyperparameters
2. **Analyze Patterns**: Look for days where policies fail and understand why
3. **Deploy Best Policy**: Export the best-performing policy for production use
4. **Extend Features**: Add multi-product inventory or lead times

### Support

For issues or questions:
- Check the main README.md
- Review QUICKSTART.md
- Inspect the code in `streamlit_app.py`
- Verify environment setup with `test_environment.py`
