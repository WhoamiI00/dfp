"""
Streamlit Dashboard for Inventory Management RL

Interactive web interface for simulating and comparing different inventory policies:
- Random policy
- EOQ baseline
- Trained RL models (DQN/PPO)

Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from env.inventory_env import InventoryEnv
from utils.eoq import EOQBaseline
from utils.heatmap import StateHeatmap

# Try to import Stable-Baselines3 (may not be available)
try:
    from stable_baselines3 import DQN, PPO
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    st.warning("Stable-Baselines3 not available. RL models cannot be loaded.")

# Set page config
st.set_page_config(
    page_title="Inventory RL Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Set plotting style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)


def load_rl_model(model_path):
    """
    Load a trained RL model.
    
    Args:
        model_path: Path to the model file
        
    Returns:
        Loaded model or None if failed
    """
    if not SB3_AVAILABLE:
        return None
    
    if not os.path.exists(model_path):
        return None
    
    try:
        # Try DQN first
        try:
            model = DQN.load(model_path)
            return model
        except:
            # Try PPO
            model = PPO.load(model_path)
            return model
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None


def run_episode(env, policy_type, model=None, baseline=None, seed=None):
    """
    Run a single episode with the specified policy.
    
    Args:
        env: InventoryEnv instance
        policy_type: "random", "eoq", or "rl"
        model: Trained RL model (for policy_type="rl")
        baseline: EOQBaseline instance (for policy_type="eoq")
        seed: Random seed for reproducibility
        
    Returns:
        dict: Episode data including metrics and history
    """
    obs, _ = env.reset(seed=seed)
    
    episode_data = {
        'days': [],
        'day_of_week': [],
        'inventory_start': [],
        'orders': [],
        'demand': [],
        'inventory_end': [],
        'sold': [],
        'unmet_demand': [],
        'rewards': []
    }
    
    total_reward = 0
    total_demand = 0
    total_sold = 0
    stockout_days = 0
    overstock_days = 0
    
    for day in range(30):
        # Store start inventory
        inventory_start = env.inventory
        
        # Select action based on policy
        if policy_type == "random":
            action = env.action_space.sample()
        elif policy_type == "eoq":
            action = baseline.get_discrete_action(env.inventory, env.max_capacity)
        elif policy_type == "rl":
            if model is not None:
                action, _ = model.predict(obs, deterministic=True)
            else:
                action = env.action_space.sample()
        else:
            action = 0
        
        # Step environment
        obs, reward, terminated, truncated, info = env.step(action)
        
        # Track metrics
        total_reward += reward
        total_demand += info['demand']
        total_sold += info['sold']
        
        if info['unmet_demand'] > 0:
            stockout_days += 1
        if env.inventory > env.max_capacity:
            overstock_days += 1
        
        # Store episode data
        episode_data['days'].append(day + 1)
        episode_data['day_of_week'].append(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][info.get('day', day) % 7])
        episode_data['inventory_start'].append(inventory_start)
        episode_data['orders'].append(info['order_qty'])
        episode_data['demand'].append(info['demand'])
        episode_data['inventory_end'].append(info['inventory'])
        episode_data['sold'].append(info['sold'])
        episode_data['unmet_demand'].append(info['unmet_demand'])
        episode_data['rewards'].append(reward)
    
    # Calculate service level
    service_level = (total_sold / total_demand * 100) if total_demand > 0 else 100
    
    # Calculate average ending inventory
    avg_inventory = np.mean(episode_data['inventory_end'])
    
    return {
        'episode_data': episode_data,
        'total_reward': total_reward,
        'stockout_days': stockout_days,
        'overstock_days': overstock_days,
        'service_level': service_level,
        'avg_inventory': avg_inventory,
        'total_demand': total_demand,
        'total_sold': total_sold
    }


def run_multiple_episodes(env, policy_type, num_episodes, model=None, baseline=None, seed=None):
    """
    Run multiple episodes and aggregate results.
    
    Args:
        env: InventoryEnv instance
        policy_type: "random", "eoq", or "rl"
        num_episodes: Number of episodes to run
        model: Trained RL model (optional)
        baseline: EOQBaseline instance (optional)
        seed: Base random seed (optional)
        
    Returns:
        tuple: (list of results, last episode data)
    """
    results = []
    last_episode = None
    
    for i in range(num_episodes):
        episode_seed = seed + i if seed is not None else None
        result = run_episode(env, policy_type, model, baseline, episode_seed)
        results.append(result)
        last_episode = result
    
    return results, last_episode


def plot_inventory_trajectory(episode_data):
    """Plot inventory levels over time."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    days = episode_data['days']
    inventory = episode_data['inventory_end']
    
    ax.plot(days, inventory, marker='o', linewidth=2, color='blue', label='Inventory Level')
    ax.axhline(y=100, color='red', linestyle='--', label='Max Capacity', alpha=0.5)
    ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    
    ax.set_xlabel('Day', fontsize=12)
    ax.set_ylabel('Units', fontsize=12)
    ax.set_title('Inventory Levels Over 30 Days', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


def plot_demand_orders(episode_data):
    """Plot demand vs orders over time."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    days = episode_data['days']
    demand = episode_data['demand']
    orders = episode_data['orders']
    sold = episode_data['sold']
    
    ax.plot(days, demand, marker='o', linewidth=2, label='Demand', color='orange')
    ax.plot(days, orders, marker='s', linewidth=2, label='Orders Placed', color='green')
    ax.plot(days, sold, marker='^', linewidth=2, label='Units Sold', color='blue', alpha=0.7)
    
    ax.set_xlabel('Day', fontsize=12)
    ax.set_ylabel('Units', fontsize=12)
    ax.set_title('Demand, Orders, and Sales', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


def plot_daily_rewards(episode_data):
    """Plot rewards per day."""
    fig, ax = plt.subplots(figsize=(12, 5))
    
    days = episode_data['days']
    rewards = episode_data['rewards']
    
    colors = ['green' if r > 0 else 'red' for r in rewards]
    ax.bar(days, rewards, color=colors, alpha=0.7, edgecolor='black')
    
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.set_xlabel('Day', fontsize=12)
    ax.set_ylabel('Reward', fontsize=12)
    ax.set_title('Daily Rewards (+1 = Perfect Day, -1 = Violation)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    return fig


def generate_state_heatmap(env, policy_type, num_episodes, model=None, baseline=None):
    """Generate a state visitation heatmap."""
    heatmap = StateHeatmap()
    
    for episode in range(num_episodes):
        obs, _ = env.reset()
        done = False
        
        while not done:
            # Get action
            if policy_type == "random":
                action = env.action_space.sample()
            elif policy_type == "eoq":
                action = baseline.get_discrete_action(env.inventory, env.max_capacity)
            elif policy_type == "rl" and model is not None:
                action, _ = model.predict(obs, deterministic=True)
            else:
                action = 0
            
            # Track state
            inventory = obs[0] * 100
            day = env.day_index
            heatmap.update(inventory, day)
            
            # Step
            obs, _, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
    
    # Create plot
    fig = heatmap.plot(title=f"State Visitation Heatmap ({num_episodes} episodes)")
    return fig


def main():
    """Main Streamlit app."""
    
    # Title
    st.title("📦 Inventory Management RL Dashboard")
    st.markdown("Interactive simulation and comparison of inventory policies")
    
    # Sidebar
    st.sidebar.header("⚙️ Configuration")
    
    # Policy selection
    policy_options = ["Random Policy", "EOQ Baseline"]
    
    # Check for trained models
    models_dir = project_root / "models"
    available_models = []
    
    if models_dir.exists():
        for model_file in ["best_model.zip", "dqn_inventory.zip", "ppo_inventory.zip"]:
            model_path = models_dir / model_file
            if model_path.exists():
                available_models.append(model_file)
    
    if available_models and SB3_AVAILABLE:
        policy_options.append("Trained RL Policy")
    
    policy_type = st.sidebar.selectbox(
        "Select Policy",
        policy_options,
        help="Choose which policy to simulate"
    )
    
    # Model selection if RL policy chosen
    selected_model_file = None
    if policy_type == "Trained RL Policy":
        if len(available_models) > 1:
            selected_model_file = st.sidebar.selectbox(
                "Select Model",
                available_models,
                help="Choose which trained model to use"
            )
        else:
            selected_model_file = available_models[0]
            st.sidebar.info(f"Using model: {selected_model_file}")
    
    # Number of episodes
    num_episodes = st.sidebar.slider(
        "Number of Episodes",
        min_value=1,
        max_value=50,
        value=10,
        help="Number of 30-day episodes to simulate"
    )
    
    # Seed
    use_seed = st.sidebar.checkbox("Use Random Seed", value=False)
    seed = None
    if use_seed:
        seed = st.sidebar.number_input(
            "Seed Value",
            min_value=0,
            max_value=9999,
            value=42,
            help="Random seed for reproducibility"
        )
    
    # Environment parameters
    st.sidebar.subheader("Environment Settings")
    initial_inventory = st.sidebar.number_input(
        "Initial Inventory",
        min_value=0,
        max_value=200,
        value=100,
        help="Starting inventory level"
    )
    
    max_capacity = st.sidebar.number_input(
        "Max Capacity",
        min_value=50,
        max_value=200,
        value=100,
        help="Maximum inventory capacity"
    )
    
    trend_strength = st.sidebar.slider(
        "Demand Trend Strength",
        min_value=0,
        max_value=10,
        value=5,
        help="Strength of demand growth over time"
    )
    
    # Run simulation button
    run_button = st.sidebar.button("🚀 Run Simulation", type="primary")
    
    # Show heatmap option
    show_heatmap = st.sidebar.checkbox("Show State Heatmap", value=False)
    
    # Main area
    if run_button:
        with st.spinner("Running simulation..."):
            # Create environment
            env = InventoryEnv(
                initial_inventory=initial_inventory,
                max_capacity=max_capacity,
                episode_length=30,
                trend_strength=trend_strength
            )
            
            # Prepare policy
            model = None
            baseline = None
            policy_key = ""
            
            if policy_type == "Random Policy":
                policy_key = "random"
                st.info("🎲 Using Random Policy")
            elif policy_type == "EOQ Baseline":
                policy_key = "eoq"
                baseline = EOQBaseline(avg_daily_demand=20, reorder_point=40)
                st.info(f"📊 Using EOQ Baseline: {baseline}")
            elif policy_type == "Trained RL Policy":
                policy_key = "rl"
                model_path = models_dir / selected_model_file
                model = load_rl_model(str(model_path))
                if model is None:
                    st.error(f"❌ Failed to load model from {model_path}")
                    st.stop()
                st.success(f"🤖 Using Trained RL Model: {selected_model_file}")
            
            # Run episodes
            results, last_episode = run_multiple_episodes(
                env, policy_key, num_episodes, model, baseline, seed
            )
            
            # Display aggregate metrics
            st.header("📊 Aggregate Metrics")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            avg_reward = np.mean([r['total_reward'] for r in results])
            avg_stockouts = np.mean([r['stockout_days'] for r in results])
            avg_overstocks = np.mean([r['overstock_days'] for r in results])
            avg_service = np.mean([r['service_level'] for r in results])
            avg_inv = np.mean([r['avg_inventory'] for r in results])
            
            col1.metric("Avg Total Reward", f"{avg_reward:.2f}")
            col2.metric("Avg Stockout Days", f"{avg_stockouts:.1f}")
            col3.metric("Avg Overstock Days", f"{avg_overstocks:.1f}")
            col4.metric("Avg Service Level", f"{avg_service:.1f}%")
            col5.metric("Avg Inventory", f"{avg_inv:.1f}")
            
            # Episode statistics
            st.subheader("📈 Episode Statistics")
            stats_df = pd.DataFrame({
                'Episode': range(1, num_episodes + 1),
                'Total Reward': [r['total_reward'] for r in results],
                'Stockouts': [r['stockout_days'] for r in results],
                'Overstocks': [r['overstock_days'] for r in results],
                'Service Level (%)': [r['service_level'] for r in results],
                'Avg Inventory': [r['avg_inventory'] for r in results]
            })
            st.dataframe(stats_df, use_container_width=True)
            
            # Visualizations for last episode
            st.header("📉 Last Episode Details")
            
            episode_data = last_episode['episode_data']
            
            # Inventory trajectory
            st.subheader("Inventory Trajectory")
            fig1 = plot_inventory_trajectory(episode_data)
            st.pyplot(fig1)
            plt.close()
            
            # Demand and orders
            st.subheader("Demand, Orders, and Sales")
            fig2 = plot_demand_orders(episode_data)
            st.pyplot(fig2)
            plt.close()
            
            # Daily rewards
            st.subheader("Daily Rewards")
            fig3 = plot_daily_rewards(episode_data)
            st.pyplot(fig3)
            plt.close()
            
            # Daily details table
            st.subheader("📋 Daily Details")
            details_df = pd.DataFrame({
                'Day': episode_data['days'],
                'DOW': episode_data['day_of_week'],
                'Start Inv': episode_data['inventory_start'],
                'Order': episode_data['orders'],
                'Demand': episode_data['demand'],
                'Sold': episode_data['sold'],
                'Unmet': episode_data['unmet_demand'],
                'End Inv': episode_data['inventory_end'],
                'Reward': episode_data['rewards']
            })
            st.dataframe(details_df, use_container_width=True)
            
            # State heatmap (optional)
            if show_heatmap:
                st.header("🗺️ State Visitation Heatmap")
                with st.spinner("Generating heatmap..."):
                    # Create fresh environment for heatmap
                    env_heatmap = InventoryEnv(
                        initial_inventory=initial_inventory,
                        max_capacity=max_capacity,
                        episode_length=30,
                        trend_strength=trend_strength
                    )
                    fig_heatmap = generate_state_heatmap(
                        env_heatmap, policy_key, 
                        min(num_episodes, 10),  # Limit to 10 for performance
                        model, baseline
                    )
                    st.pyplot(fig_heatmap)
                    plt.close()
                    env_heatmap.close()
            
            env.close()
            
        st.success("✅ Simulation complete!")
    
    else:
        # Welcome message
        st.info("👈 Configure settings in the sidebar and click 'Run Simulation' to start")
        
        st.markdown("""
        ### 🎯 How to Use
        
        1. **Select a Policy**: Choose between Random, EOQ Baseline, or Trained RL model
        2. **Configure Parameters**: Adjust number of episodes, seed, and environment settings
        3. **Run Simulation**: Click the button to simulate inventory management
        4. **Analyze Results**: View metrics, charts, and detailed daily logs
        
        ### 📚 Policy Types
        
        - **Random Policy**: Randomly selects order quantities (baseline for comparison)
        - **EOQ Baseline**: Uses Economic Order Quantity formula for systematic ordering
        - **Trained RL Policy**: Uses a trained Deep Q-Network or PPO agent
        
        ### 📊 Demand Model
        
        - **Monday-Friday**: 0-15 units
        - **Saturday**: 15-30 units
        - **Sunday**: 30-50 units
        - Plus a trend factor that increases demand over time
        
        ### 📊 Key Metrics
        
        - **Total Reward**: Sum of daily rewards (+1 for perfect days, -1 for violations)
        - **Stockout Days**: Days where demand exceeded available inventory
        - **Overstock Days**: Days where inventory exceeded maximum capacity
        - **Service Level**: Percentage of demand that was fulfilled
        - **Avg Inventory**: Average ending inventory across the episode
        
        ### 🚀 Getting Started
        
        If you haven't trained a model yet, run:
        ```bash
        python agents/train_dqn.py
        ```
        or
        ```bash
        python agents/train_ppo.py
        ```
        """)


if __name__ == "__main__":
    main()
