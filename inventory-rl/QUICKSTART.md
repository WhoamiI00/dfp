# Quick Start Guide

## 🚀 Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Train a Model

**Option A: Train DQN**
```bash
cd agents
python train_dqn.py
```

**Option B: Train PPO**
```bash
cd agents
python train_ppo.py
```

Training will take approximately 10-30 minutes depending on your hardware.
Models are saved to `models/` directory.

### 3. Evaluate the Model

```bash
cd agents
python evaluate.py --model dqn --episodes 10
```

Or for PPO:
```bash
python evaluate.py --model ppo --episodes 10
```

Results will be saved to `results/` directory with visualizations:
- `inventory_plot.png` - Daily inventory levels
- `demand_supply.png` - Demand vs supply comparison
- `reward_comparison.png` - RL vs EOQ baseline
- `heatmap.png` - State visitation heatmap

### 4. View TensorBoard Logs (Optional)

```bash
tensorboard --logdir logs/
```

Then open `http://localhost:6006` in your browser.

## 📝 Key Files

- `env/inventory_env.py` - Custom Gymnasium environment
- `utils/eoq.py` - Economic Order Quantity baseline
- `utils/heatmap.py` - State visualization
- `agents/train_dqn.py` - DQN training
- `agents/train_ppo.py` - PPO training
- `agents/evaluate.py` - Model evaluation

## 🎯 Expected Performance

After training for 100,000 timesteps:
- RL agents typically achieve mean rewards of 10-25 per episode
- EOQ baseline typically achieves mean rewards of 5-15 per episode
- Perfect performance would be +30 (one perfect day for each of 30 days)

## 🔧 Customization

To modify environment parameters, edit `env/inventory_env.py`:
- `initial_inventory` - Starting inventory (default: 100)
- `max_capacity` - Maximum inventory (default: 100)
- `episode_length` - Days per episode (default: 30)
- `trend_strength` - Demand trend intensity (default: 5)

## 📊 Understanding Results

**Reward Function:**
- +1 for each perfect day (no stockout, no overstock, inventory > 0)
- -1 for constraint violations

**Demand Patterns:**
- Monday-Friday: 0-10 units
- Saturday: 10-20 units
- Sunday: 20-30 units
- Increasing trend over 30 days

**Action Space:**
- 11 discrete actions (0, 5, 10, 15, ..., 50 units)

## 🐛 Troubleshooting

**Import errors:**
```bash
# Make sure you're in the project root or agents/ directory
cd inventory-rl
python -m agents.train_dqn
```

**CUDA/GPU issues:**
The code works on CPU. If you have GPU issues, stable-baselines3 will automatically fall back to CPU.

**Model not found:**
Make sure to train a model first before evaluation.
