# Deep Reinforcement Learning for Inventory Optimization

A Python-based RL system that learns optimal inventory management policies using DQN and PPO algorithms.

## 🎯 Project Overview

This project demonstrates how Reinforcement Learning can optimize daily ordering decisions for inventory management, outperforming classical methods like Economic Order Quantity (EOQ).

**Key Features:**
- Custom Gymnasium environment with realistic stochastic demand
- DQN and PPO agents trained using Stable-Baselines3
- Interactive Streamlit dashboard for visualization
- Comprehensive evaluation with multiple metrics
- EOQ baseline for performance comparison

## 📊 Performance

| Policy | Mean Reward | Service Level |
|--------|-------------|---------------|
| Random | -8 to -15 | 60-70% |
| EOQ Baseline | +10 to +15 | 85-90% |
| **DQN Agent** | **+18 to +25** | **95-98%** |
| **PPO Agent** | **+20 to +26** | **96-99%** |

## 🚀 Quick Start

### Installation

```bash
cd inventory-rl
pip install -r requirements.txt
```

### Train an Agent

```bash
# Train DQN
python agents/train_dqn.py

# Train PPO
python agents/train_ppo.py
```

### Evaluate Model

```bash
python agents/evaluate.py --model dqn --episodes 10
```

### Launch Dashboard

```bash
streamlit run streamlit_app.py
```

Open browser to: `http://localhost:8501`

## 📂 Structure

```
inventory-rl/
├── env/              # Custom Gymnasium environment
├── agents/           # Training and evaluation scripts
├── utils/            # EOQ baseline, heatmap visualization
├── models/           # Saved trained models
├── results/          # Plots and metrics
└── streamlit_app.py  # Interactive dashboard
```

## 🧠 Technical Details

**Environment:**
- 30-day episodes
- Stochastic demand (weekday: 0-15, Saturday: 15-30, Sunday: 30-50)
- Discrete actions (order 0-50 units in steps of 5)
- Binary rewards (+1 perfect day, -1 violations)

**Algorithms:**
- Deep Q-Network (DQN) with experience replay
- Proximal Policy Optimization (PPO) with clipping

**Tech Stack:**
- Python 3.8+
- Gymnasium 0.29+
- Stable-Baselines3 2.0+
- PyTorch 2.0+
- Streamlit 1.28+

## 📚 Documentation

For comprehensive documentation, see: `inventory-rl/README.md`

Includes:
- Detailed theoretical foundations (EOQ, MDP, DQN, PPO)
- Complete API reference
- Viva/exam Q&A preparation
- Future improvements and research directions

## 🎓 Academic Context

This project serves as a demonstration of:
- Markov Decision Processes (MDP) formulation
- Value-based learning (DQN)
- Policy gradient methods (PPO)
- Real-world RL applications in operations research

## 📈 Results

The trained agents achieve:
- 95-99% demand fulfillment rate
- 2-5 stockout days per episode (vs 15-20 for random policy)
- 50-100% reward improvement over EOQ baseline
- Robust performance across different demand patterns

## 🔧 Requirements

```
gymnasium>=0.29.0
stable-baselines3>=2.0.0
torch>=2.0.0
numpy>=1.24.0
pandas>=2.0.0
matplotlib>=3.7.0
seaborn>=0.12.0
streamlit>=1.28.0
```

## 📝 License

Open source for educational and research purposes.

---

**Made with Python, Gymnasium, and Stable-Baselines3**
