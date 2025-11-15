# 🤖 RL Inventory Management System

A Reinforcement Learning-based inventory management system that learns to optimize stock levels for 10 products, minimizing overstock and understock situations.

## 📋 Overview

This system trains an AI agent using **PPO (Proximal Policy Optimization)** to make intelligent ordering decisions for inventory management. The agent learns to:
- Place orders based on current stock levels, demand patterns, and lead times
- Avoid overstock (excess inventory) and understock (stockouts)
- Maximize rewards by maintaining optimal inventory levels

## 🏗️ System Architecture

### Environment (`env.py`)
- **10 products** in a simulation environment (10×10 matrix)
- **Random demand generation** using Poisson distribution
- **Lead times** (1-5 days) for order delivery
- **Safety stock levels** to prevent stockouts
- **Observation space**: 10 products × 10 features (stock, demand, outstanding orders, etc.)
- **Action space**: Order quantities (0-200 units per product)

### Reward Structure
- ✅ **+10 bonus**: Perfect day (no overstock or understock)
- ❌ **-1 per unit**: Stockout penalty (unmet demand)
- ❌ **-0.1 per unit**: Overstock penalty (excess > 3× avg demand)
- ❌ **-0.01 per unit**: Holding cost (current inventory)

### Key Metrics Tracked
1. **Perfect Days**: Days with no overstock or understock issues
2. **Overstock Days**: Days when any product exceeds 3× average demand
3. **Understock Days**: Days when demand couldn't be met
4. **Episode Reward**: Cumulative reward per episode
5. **Order Decisions**: AI's ordering quantities per product

## 🚀 Usage

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Training
```bash
python train.py --total-timesteps 100000
```

### 3. Launch Dashboard (in separate terminal)
```bash
streamlit run streamlit_app.py
```

The dashboard will open at `http://localhost:8501`

### 4. View TensorBoard (optional)
```bash
tensorboard --logdir logs/tensorboard
```

## 📊 Dashboard Features

### Real-time Metrics
- **Timestep & Episode**: Training progress
- **Day Counter**: Current day in episode (max 30)
- **Rewards**: Recent and rolling average (last 100 episodes)
- **Perfect Days**: Percentage of days with optimal inventory

### Visualizations
1. **Stock Levels Chart**: Current inventory vs safety stock and max thresholds
2. **Order Decisions Chart**: AI's last orders and pending deliveries
3. **Demand Pattern Chart**: Recent demand vs average demand
4. **Reward Trend**: Reward progression over last 100 steps

### Product Table
Color-coded table showing per-product details:
- 🟢 **Green**: Optimal stock level
- 🟡 **Yellow**: Overstock (> 3× avg demand)
- 🔴 **Red**: Understock (< safety stock)

## 🎯 How It Works

### Daily Flow (Single Day in Episode)
1. **Receive deliveries**: Orders placed 1-5 days ago arrive based on lead time
2. **AI decides orders**: Based on 10 features per product (stock, demand, outstanding, etc.)
3. **Demand occurs**: Random demand generated (Poisson distribution based on avg_daily)
4. **Sales**: Stock sold up to available quantity
5. **Reward calculated**: Based on overstock/understock/holding costs
6. **State updates**: New observation for next decision

### Episode Structure
- **Length**: 30 days per episode
- **Reset**: At day 30, environment resets with new random parameters
- **Tracking**: Overstock days, understock days, perfect days tracked per episode

### Training Process
- **Algorithm**: PPO (Proximal Policy Optimization)
- **Policy**: Multi-layer perceptron (MLP)
- **Episode length**: 30 days
- **Logging**: Every step logged to `logs/stream_data.json`
- **TensorBoard**: Metrics saved to `logs/tensorboard/`

## 📁 Project Structure
```
dfp/
├── env.py              # Gymnasium environment (inventory simulation)
├── train.py            # Training script with PPO
├── streamlit_app.py    # Real-time dashboard
├── utils.py            # Logging utilities
├── requirements.txt    # Dependencies
├── logs/
│   ├── stream_data.json      # Live training data
│   ├── sb3_logs/             # Stable Baselines3 logs
│   └── tensorboard/          # TensorBoard logs
└── README.md
```

## 🔧 Configuration

### Environment Parameters (env.py)
```python
num_products = 10        # Number of products
max_days = 30           # Episode length
max_order = 200         # Maximum order quantity
holding_cost = 0.01     # Cost per unit held
stockout_penalty = 1.0  # Penalty per unmet demand
overstock_penalty = 0.1 # Penalty per excess unit
no_issue_bonus = 10.0   # Bonus for perfect days
```

### Training Parameters (train.py)
```bash
python train.py --total-timesteps 200000  # Default
python train.py --total-timesteps 100000  # Faster training
```

## 📈 Expected Results

As training progresses, you should observe:
1. **Increasing perfect days**: More days without inventory issues (target: >70%)
2. **Decreasing overstock/understock**: Better inventory optimization
3. **Rising average reward**: Improved decision-making (negative → positive)
4. **Smarter orders**: Orders closer to actual demand patterns

### Example Training Progression
- **Episodes 0-100**: Random exploration, many overstock/understock issues
- **Episodes 100-500**: Learning patterns, improving reward
- **Episodes 500+**: Stabilizing, achieving 60-80% perfect days

## 🛠️ Troubleshooting

### Training exits with error
- Check Python version (3.8+)
- Verify all dependencies installed: `pip install -r requirements.txt`
- Ensure `logs/` directory exists (created automatically)

### Dashboard shows "Waiting for training"
- Start training first: `python train.py`
- Check that `logs/stream_data.json` exists
- Refresh the dashboard (F5)

### Slow training
- Reduce `--total-timesteps` (try 50000)
- Use GPU if available (PyTorch with CUDA)
- Adjust `max_days` in environment (try 20 instead of 30)

## 📚 Key Concepts

### Reinforcement Learning
- **Agent**: AI making ordering decisions
- **Environment**: 10-product inventory simulation  
- **State**: Stock levels, demand, outstanding orders (10×10 matrix)
- **Action**: Order quantities for each product
- **Reward**: Immediate feedback on inventory performance

### Inventory Management
- **Lead Time**: Days between order placement and delivery (1-5 days)
- **Safety Stock**: Minimum buffer to prevent stockouts
- **Overstock**: Inventory > 3× average daily demand
- **Understock**: Unable to meet customer demand (stockout)
- **Outstanding Orders**: Orders placed but not yet delivered

## 🎓 Next Steps & Extensions

1. **Tune rewards**: Adjust penalties/bonuses in `env.py` for your business case
2. **Add complexity**: 
   - Variable lead times based on supplier
   - Seasonal demand patterns
   - Multi-warehouse coordination
3. **Test policies**: Evaluate trained model on test scenarios
4. **Real data**: Replace random demand with historical sales data
5. **Cost analysis**: Add actual costs (ordering, shipping, storage)
6. **Demand forecasting**: Integrate ML-based demand prediction

## 📝 Development Phase Features

The current implementation shows:
- ✅ **Real-time parameter changes**: Stock levels, orders, demand updated live
- ✅ **Overstock/Understock tracking**: Per-product and episode-level metrics
- ✅ **Reward decomposition**: See holding costs, penalties, bonuses separately
- ✅ **Order decisions**: Visualize AI's ordering strategy
- ✅ **Training progress**: Episode count, timesteps, average rewards

---

**Built with**: Stable-Baselines3, Gymnasium, Streamlit, Plotly, NumPy
