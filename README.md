# RL Inventory Management Project

This project contains:
- A custom 10‑product inventory RL environment (`env.py`)
- A PPO training script with TensorBoard logging (`train.py`)
- A Streamlit dashboard that visualizes training in real time (`streamlit_app.py`)
- Utility helpers (`utils.py`)

## Running

### 1. Install dependencies
```
pip install -r requirements.txt
```

### 2. Start training
```
python train.py --total-timesteps 200000
```

### 3. Launch Streamlit dashboard
```
streamlit run streamlit_app.py
```

### 4. View TensorBoard
```
tensorboard --logdir logs/tensorboard
```
