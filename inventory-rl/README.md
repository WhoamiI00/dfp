# 📦 Reinforcement Learning–Based Inventory Optimization

**Demand Forecasting + Order Suggestion | 30-Day Episodes | Trend-Aware | EOQ-Guided**

This project implements a **Reinforcement Learning (RL)** environment for **single-product inventory control**, where an agent must decide **daily order quantities** to avoid **overstock** and **understock** situations.

The environment is built using **Gymnasium**, and agents are trained using **Stable-Baselines3** (DQN/PPO).
It includes:

* Weekday/weekend demand patterns
* EOQ-based reference ordering
* Inventory capacity constraints
* Reward for perfect inventory decisions
* 10×10 grid state visualization (optional)
* 30-day episode horizon

---

# 📑 Table of Contents

1. [Project Overview](#project-overview)
2. [Key Problem Definition](#key-problem-definition)
3. [Demand Model](#demand-model)
4. [EOQ Integration](#eoq-integration)
5. [Action & State Spaces](#action--state-spaces)
6. [Reward Function](#reward-function)
7. [Environment Dynamics](#environment-dynamics)
8. [Tech Stack](#tech-stack)
9. [Project Structure](#project-structure)
10. [Installation](#installation)
11. [How to Train](#how-to-train)
12. [How to Evaluate](#how-to-evaluate)
13. [10×10 Heatmap (Optional)](#10x10-heatmap-optional)
14. [Troubleshooting](#troubleshooting)
15. [Future Improvements](#future-improvements)

---

# 1️⃣ Project Overview

The goal is to create an RL agent that learns **daily ordering decisions** for a single product. The environment simulates:

* **30 days per episode**
* **Initial inventory = 100 units**
* **Daily random demand**, influenced by weekdays/weekends
* **Overstock penalty** and **stockout penalty**
* **Reward for "ideal" days** where no constraint violations occur

The project also uses **EOQ (Economic Order Quantity)** as a baseline to compare RL performance.

---

# 2️⃣ Key Problem Definition

**Objective**
Maximize reward by choosing the correct daily order quantity.

**Constraints**

| Type           | Explanation                              |
| -------------- | ---------------------------------------- |
| Stockout       | Demand > available inventory             |
| Overstock      | Inventory exceeds maximum capacity (100) |
| Episode Length | 30 days                                  |
| Single Product | Only quantity decision matters           |

**Goal:**

> Keep inventory in an optimal range while meeting all demand.

---

# 3️⃣ Demand Model

Demand depends on **day of week**:

| Day           | Demand Range |
| ------------- | ------------ |
| Monday–Friday | `0–15`       |
| Saturday      | `15–30`      |
| Sunday        | `30–50`      |

Plus a **trend factor**:

```
trend = t / 30
final_demand = base_demand + int(trend * trend_strength)
```

This simulates realistic, increasing sales patterns.

---

# 4️⃣ EOQ Integration

EOQ provides a reference policy:

$$Q^* = \sqrt{\frac{2DS}{H}}$$

Where:

* `D` = average total demand over 30 days (estimated dynamically)
* `S` = ordering cost
* `H` = holding cost per unit per day

EOQ is used for:

✔ baseline policy comparison
✔ limit action-space bounds
✔ additional observation input (optional)

---

# 5️⃣ Action & State Spaces

## **Action Space**

Discrete:

```
0 → order 0 units
1 → order 5 units
...
10 → order 50 units
```

Total 11 actions.

## **State Space**

Normalized continuous vector:

```
[
  inventory / 100,     # 0–1
  day_index / 30,      # 0–1
  day_of_week / 6      # 0–1
]
```

Optional extensions:

* last_demand
* last_action
* EOQ

---

# 6️⃣ Reward Function

A **simple and strict** reward system:

```python
if unmet_demand == 0 and inventory <= capacity and inventory > 0:
    reward = +1.0      # perfect day
else:
    reward = -1.0      # violation
```

Optional shaping:

```
-2 for stockout
-1 for overstock
+1 for ideal day
```

---

# 7️⃣ Environment Dynamics

Daily steps:

### 1. Agent chooses order quantity

→ `inventory += order_qty`

### 2. Demand generated

→ based on weekday/weekend + trend

### 3. Sales occur

→ `sold = min(inventory, demand)`

### 4. Inventory updated

→ `inventory -= sold`

### 5. Rewards computed

### 6. Episode ends at day 30

---

# 8️⃣ Tech Stack

| Component              | Technology                      |
| ---------------------- | ------------------------------- |
| RL Algorithms          | **Stable-Baselines3** (DQN/PPO) |
| Environment            | **Gymnasium**                   |
| Neural Network Backend | **PyTorch**                     |
| Logging                | TensorBoard / WandB             |
| Visualizations         | Matplotlib, Seaborn             |

---

# 9️⃣ Project Structure

```
inventory-rl/
│
├── env/
│   └── inventory_env.py          # custom Gym environment
│
├── agents/
│   ├── train_dqn.py              # DQN training script
│   ├── train_ppo.py              # PPO training script
│   └── evaluate.py               # evaluation + plots
│
├── utils/
│   ├── eoq.py                    # EOQ formula + baseline
│   └── heatmap.py                # 10×10 state visualization
│
├── models/
│   └── best_model.zip            # saved SB3 models
│
├── results/
│   ├── reward_curve.png
│   ├── inventory_plot.png
│   └── heatmap.png
│
└── README.md                     # this document
```

---

# 🔧 10️⃣ Installation

```bash
git clone <repo-url>
cd inventory-rl

pip install -r requirements.txt
```

`requirements.txt` should include:

```
gymnasium
numpy
stable-baselines3
torch
pandas
matplotlib
seaborn
```

---

# 🏋️ 1️⃣1️⃣ How to Train

## **DQN**

```bash
python agents/train_dqn.py
```

## **PPO**

```bash
python agents/train_ppo.py
```

Model will be saved to:

```
models/best_model.zip
```

---

# 📊 1️⃣2️⃣ How to Evaluate

## **Command Line Evaluation**

```bash
python agents/evaluate.py
```

This will output:

* Daily inventory plot
* Demand vs supply curve
* Reward per episode
* Heatmap of state visitation

## **Interactive Streamlit Dashboard**

```bash
streamlit run streamlit_app.py
```

Features:
* Interactive policy selection (Random, EOQ, Trained RL)
* Real-time visualization of inventory levels, demand, and orders
* Aggregate metrics across multiple episodes
* Daily details table
* State visitation heatmap (optional)
* Configurable environment parameters

---

# 🔲 1️⃣3️⃣ 10×10 Heatmap (Optional)

To discretize states:

```
inventory: 0–100 → 10 bins (row)
day_index: 0–30 → 10 bins (col)
```

Used for:

* debugging policy behavior
* visualizing agent learning regions
* detecting unreachable/rare states

Example heatmap:

```
utils/heatmap.py
results/heatmap.png
```

---

# 🐞 1️⃣4️⃣ Troubleshooting

### **Training stuck at low reward**

* Reduce strictness of reward function
* Add small +reward for partial correctness
* Allow more actions (0–100 units)

### **Inventory collapses to zero**

* Increase trend_strength
* Increase demand randomness
* Expand observation space

### **Model diverges**

* Lower learning rate
* Increase batch_size
* Use PPO instead of DQN

---

# 🚀 1️⃣5️⃣ Future Improvements

* Multi-product inventory
* Multi-agent (warehouse + supplier)
* Continuous action space (SAC)
* Add lead times
* Add costs (holding, ordering, shortage)
* Deploy model using FastAPI
* Train using RLlib for scalability

---

If you want, I can also provide:

✅ Full code for the environment
✅ Full DQN and PPO training scripts
✅ EOQ helper module
✅ Heatmap visualization code
✅ A polished PDF version of this README

Just tell me **"give me the full codebase"** and I'll generate it.
