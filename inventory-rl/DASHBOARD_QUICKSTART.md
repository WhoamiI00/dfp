# 🚀 Quick Start: Streamlit Dashboard

## One-Line Launch

If you already have dependencies installed:
```bash
streamlit run streamlit_app.py
```

Or use the helper script:
```bash
python run_dashboard.py
```

## First Time Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- gymnasium (environment)
- stable-baselines3 (RL algorithms)
- streamlit (web dashboard)
- matplotlib, seaborn (visualizations)
- numpy, pandas (data processing)

### 2. Launch Dashboard
```bash
streamlit run streamlit_app.py
```

### 3. Open Browser
Navigate to: `http://localhost:8501`

## Using the Dashboard

### First Run (No Trained Models)
1. Select "**Random Policy**" or "**EOQ Baseline**"
2. Click "**Run Simulation**"
3. Explore the visualizations

### After Training a Model
```bash
# Train a model first
python agents/train_dqn.py

# Then launch dashboard
streamlit run streamlit_app.py
```

Now you can select "**Trained RL Policy**" and compare it to baselines!

## What You'll See

### Top: Aggregate Metrics
- Average Total Reward
- Average Stockout Days
- Average Overstock Days
- Service Level
- Average Inventory

### Middle: Visualizations
- **Inventory Trajectory**: How inventory changes over 30 days
- **Demand vs Orders**: Order strategy vs actual demand
- **Daily Rewards**: Which days were perfect vs violations

### Bottom: Data Tables
- **Episode Statistics**: Summary of all runs
- **Daily Details**: Complete day-by-day breakdown

## Tips

**Compare Policies**
Run simulations with each policy type and compare metrics:
1. Random Policy (worst)
2. EOQ Baseline (good)
3. Trained RL (best, after training)

**Experiment with Parameters**
- Increase "Demand Trend Strength" to see how policies handle growth
- Adjust "Initial Inventory" to test different starting conditions
- Lower "Max Capacity" to create more constraints

**Use Seeds for Reproducibility**
Check "Use Random Seed" and set to 42 for consistent results across runs.

**Enable Heatmap**
Check "Show State Heatmap" to see which states the policy visits most.

## Troubleshooting

**Port already in use?**
```bash
streamlit run streamlit_app.py --server.port 8502
```

**Can't find modules?**
Make sure you're in the `inventory-rl/` directory:
```bash
cd inventory-rl
streamlit run streamlit_app.py
```

**No trained models show up?**
Train a model first:
```bash
python agents/train_dqn.py
```

## Stop the Server

Press `Ctrl+C` in the terminal where Streamlit is running.

## Demand Model

The environment uses realistic demand patterns:
- **Monday-Friday**: 0-15 units
- **Saturday**: 15-30 units
- **Sunday**: 30-50 units
- **Trend Factor**: Demand increases over the 30-day episode

## Next Steps

After exploring the dashboard:
1. Train better models with adjusted hyperparameters
2. Compare different training algorithms (DQN vs PPO)
3. Analyze which policies work best for your scenarios
4. Export interesting results for reports

Enjoy! 🎉
