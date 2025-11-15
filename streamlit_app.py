import streamlit as st
import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from env import InventoryEnv

LOG_DIR = Path("logs")
STREAM_FILE = LOG_DIR / "stream_data.json"
MANUAL_MODE_FILE = LOG_DIR / "manual_mode.json"

st.set_page_config(layout="wide", page_title="RL Inventory Dashboard")

# Initialize session state
if 'mode' not in st.session_state:
    st.session_state.mode = 'training'
if 'manual_env' not in st.session_state:
    st.session_state.manual_env = None
if 'manual_history' not in st.session_state:
    st.session_state.manual_history = {
        'days': [],
        'stocks': [],
        'demands': [],
        'orders': [],
        'rewards': [],
        'overstock': [],
        'understock': []
    }

# Sidebar for mode selection
st.sidebar.title("🎮 Control Panel")
mode = st.sidebar.radio("Select Mode", ["Training Mode", "Manual Testing Mode"], 
                        index=0 if st.session_state.mode == 'training' else 1)

if mode == "Manual Testing Mode":
    st.session_state.mode = 'manual'
else:
    st.session_state.mode = 'training'

st.title("🤖 RL Inventory Management Dashboard")

def load_stream():
    if STREAM_FILE.exists():
        try:
            with open(STREAM_FILE, "r") as f:
                return json.load(f)
        except:
            return None
    return None

def save_manual_state(env, history):
    """Save manual mode state"""
    data = {
        'env_state': {
            'stocks': env.stocks.tolist(),
            'last_demand': env.last_demand.tolist(),
            'outstanding': env.outstanding.tolist(),
            'days_passed': int(env.days_passed),
            'avg_daily': env.avg_daily.tolist(),
            'safety_stock': env.safety_stock.tolist(),
            'lead_time': env.lead_time.tolist(),
        },
        'history': history,
        'timestamp': time.time()
    }
    with open(MANUAL_MODE_FILE, 'w') as f:
        json.dump(data, f)

def load_manual_state():
    """Load manual mode state"""
    if MANUAL_MODE_FILE.exists():
        try:
            with open(MANUAL_MODE_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

# ============================================
# MANUAL TESTING MODE
# ============================================
if st.session_state.mode == 'manual':
    st.subheader("🎯 Manual Order Testing - See How Your Decisions Impact Inventory")
    
    # Initialize or reset environment
    col_control1, col_control2 = st.columns([1, 3])
    with col_control1:
        if st.button("🔄 Reset Environment", use_container_width=True):
            st.session_state.manual_env = InventoryEnv(num_products=10, max_days=100, seed=42)
            st.session_state.manual_env.reset()
            st.session_state.manual_history = {
                'days': [],
                'stocks': [],
                'demands': [],
                'orders': [],
                'rewards': [],
                'overstock': [],
                'understock': []
            }
            st.success("Environment reset!")
            st.rerun()
    
    # Initialize environment if needed
    if st.session_state.manual_env is None:
        st.session_state.manual_env = InventoryEnv(num_products=10, max_days=100, seed=42)
        st.session_state.manual_env.reset()
    
    env = st.session_state.manual_env
    
    # Current state display
    st.write("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Day", f"{env.days_passed}/100")
    with col2:
        total_stock = int(env.stocks.sum())
        st.metric("Total Stock", total_stock)
    with col3:
        if st.session_state.manual_history['rewards']:
            st.metric("Last Reward", f"{st.session_state.manual_history['rewards'][-1]:.2f}")
        else:
            st.metric("Last Reward", "N/A")
    with col4:
        if st.session_state.manual_history['days']:
            perfect = sum(1 for i in range(len(st.session_state.manual_history['overstock'])) 
                         if st.session_state.manual_history['overstock'][i] == 0 
                         and st.session_state.manual_history['understock'][i] == 0)
            perfect_pct = (perfect / len(st.session_state.manual_history['days'])) * 100
            st.metric("Perfect Days", f"{perfect_pct:.1f}%")
        else:
            st.metric("Perfect Days", "0%")
    
    # Order input section
    st.write("---")
    st.subheader("📦 Place Your Orders")
    
    # Show current state in expandable section
    with st.expander("📊 Current Inventory State", expanded=True):
        current_df = pd.DataFrame({
            'Product': [f'P{i}' for i in range(10)],
            'Stock': env.stocks.astype(int),
            'Avg Daily Demand': env.avg_daily.astype(int),
            'Safety Stock': env.safety_stock.astype(int),
            'Outstanding Orders': env.outstanding.astype(int),
            'Lead Time (days)': env.lead_time.astype(int),
        })
        st.dataframe(current_df, use_container_width=True, height=250)
    
    # Order input form
    st.write("**Enter order quantities for each product (0-200):**")
    order_cols = st.columns(5)
    orders = []
    
    for i in range(10):
        with order_cols[i % 5]:
            # Suggest order based on simple logic
            suggested = max(0, int((env.avg_daily[i] * 3) - env.stocks[i] - env.outstanding[i]))
            order = st.number_input(
                f"P{i}", 
                min_value=0, 
                max_value=200, 
                value=min(suggested, 200),
                step=10,
                key=f"order_{i}"
            )
            orders.append(order)
    
    col_submit1, col_submit2, col_submit3 = st.columns([1, 1, 2])
    with col_submit1:
        submit_btn = st.button("✅ Submit Orders & Advance Day", use_container_width=True, type="primary")
    with col_submit2:
        if st.button("🤖 Use AI Suggestion", use_container_width=True):
            st.info("AI suggestion applied to order fields above!")
    
    # Process orders when submitted
    if submit_btn:
        action = np.array(orders, dtype=np.float32)
        obs, reward, terminated, truncated, info = env.step(action)
        
        # Record history
        st.session_state.manual_history['days'].append(env.days_passed - 1)
        st.session_state.manual_history['stocks'].append(env.stocks.copy().tolist())
        st.session_state.manual_history['demands'].append(env.last_demand.copy().tolist())
        st.session_state.manual_history['orders'].append(orders)
        st.session_state.manual_history['rewards'].append(float(reward))
        st.session_state.manual_history['overstock'].append(info['has_overstock'])
        st.session_state.manual_history['understock'].append(info['has_understock'])
        
        # Save state
        save_manual_state(env, st.session_state.manual_history)
        
        # Show feedback
        if info['has_overstock'] == 0 and info['has_understock'] == 0:
            st.success(f"🎉 Perfect Day! Reward: {reward:.2f}")
        elif info['has_understock'] > 0:
            st.warning(f"⚠️ Stockout on {info['has_understock']} products! Reward: {reward:.2f}")
        elif info['has_overstock'] > 0:
            st.warning(f"📦 Overstock on {info['has_overstock']} products! Reward: {reward:.2f}")
        
        if terminated:
            st.info("Episode completed! Reset environment to continue.")
        
        st.rerun()
    
    # Visualization of manual mode
    if len(st.session_state.manual_history['days']) > 0:
        st.write("---")
        st.subheader("📈 Performance History")
        
        hist = st.session_state.manual_history
        
        # Charts
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Reward over time
            fig_reward = go.Figure()
            fig_reward.add_trace(go.Scatter(
                x=hist['days'], 
                y=hist['rewards'],
                mode='lines+markers',
                name='Reward',
                line=dict(color='blue', width=2)
            ))
            fig_reward.update_layout(title='Rewards Over Time', xaxis_title='Day', yaxis_title='Reward', height=300)
            st.plotly_chart(fig_reward, use_container_width=True)
            
            # Stock levels over time (average)
            avg_stocks = [np.mean(s) for s in hist['stocks']]
            fig_stock = go.Figure()
            fig_stock.add_trace(go.Scatter(
                x=hist['days'],
                y=avg_stocks,
                mode='lines+markers',
                name='Avg Stock',
                line=dict(color='green', width=2)
            ))
            fig_stock.update_layout(title='Average Stock Level Over Time', xaxis_title='Day', yaxis_title='Units', height=300)
            st.plotly_chart(fig_stock, use_container_width=True)
        
        with chart_col2:
            # Issues tracking
            fig_issues = go.Figure()
            fig_issues.add_trace(go.Bar(x=hist['days'], y=hist['overstock'], name='Overstock', marker_color='orange'))
            fig_issues.add_trace(go.Bar(x=hist['days'], y=hist['understock'], name='Understock', marker_color='red'))
            fig_issues.update_layout(title='Inventory Issues Over Time', xaxis_title='Day', yaxis_title='# Products', height=300)
            st.plotly_chart(fig_issues, use_container_width=True)
            
            # Demand vs Orders
            avg_demands = [np.mean(d) for d in hist['demands']]
            avg_orders = [np.mean(o) for o in hist['orders']]
            fig_do = go.Figure()
            fig_do.add_trace(go.Scatter(x=hist['days'], y=avg_demands, mode='lines', name='Avg Demand', line=dict(color='purple')))
            fig_do.add_trace(go.Scatter(x=hist['days'], y=avg_orders, mode='lines', name='Avg Orders', line=dict(color='teal')))
            fig_do.update_layout(title='Demand vs Orders', xaxis_title='Day', yaxis_title='Units', height=300)
            st.plotly_chart(fig_do, use_container_width=True)
        
        # Detailed table
        with st.expander("📋 Detailed History Table"):
            history_df = pd.DataFrame({
                'Day': hist['days'],
                'Reward': [f"{r:.2f}" for r in hist['rewards']],
                'Overstock Products': hist['overstock'],
                'Understock Products': hist['understock'],
                'Avg Stock': [f"{np.mean(s):.1f}" for s in hist['stocks']],
                'Avg Demand': [f"{np.mean(d):.1f}" for d in hist['demands']],
                'Avg Order': [f"{np.mean(o):.1f}" for o in hist['orders']],
            })
            st.dataframe(history_df, use_container_width=True, height=300)

# ============================================
# TRAINING MODE (Original Dashboard)
# ============================================
else:
    st.subheader("🚀 Live Training Visualization")
    
    # Create layout
    col1, col2, col3, col4 = st.columns(4)
    metric_row = st.container()
    charts_row = st.container()
    table_row = st.container()

    # Metrics placeholders
    with col1:
        timestep_metric = st.empty()
        episode_metric = st.empty()
    with col2:
        day_metric = st.empty()
        reward_metric = st.empty()
    with col3:
        perfect_days_metric = st.empty()
        avg_reward_metric = st.empty()
    with col4:
        overstock_metric = st.empty()
        understock_metric = st.empty()

    # Charts placeholders
    with charts_row:
        col_left, col_right = st.columns(2)
        with col_left:
            stock_chart = st.empty()
            order_chart = st.empty()
        with col_right:
            demand_chart = st.empty()
            issues_chart = st.empty()

    # Table placeholder
    with table_row:
        product_table = st.empty()

    last_ts = 0
    history = {'rewards': [], 'overstock': [], 'understock': [], 'perfect': []}

    while True:
        sd = load_stream()
        if sd is None:
            st.info("⏳ Waiting for training to start...")
            time.sleep(1)
            continue

        if sd["timestamp"] == last_ts:
            time.sleep(0.3)
            continue
        last_ts = sd["timestamp"]

        # Update metrics
        timestep_metric.metric("Timestep", f"{sd.get('timestep', 0):,}")
        episode_metric.metric("Episode", f"{sd.get('episode', 0)}")
        day_metric.metric("Day", f"{sd['day']}/{sd.get('max_days', 30)}")
        reward_metric.metric("Recent Reward", f"{sd['recent_reward']:.2f}")
        
        perfect_pct = (sd['perfect_days'] / max(sd['day'], 1)) * 100
        perfect_days_metric.metric("Perfect Days", f"{sd['perfect_days']} ({perfect_pct:.1f}%)")
        avg_reward_metric.metric("Avg Reward (100 eps)", f"{sd.get('avg_reward', 0):.2f}")
        
        overstock_metric.metric("Overstock Days", sd['overstock_days'], 
                               delta=f"{sd['has_overstock']} products" if sd.get('has_overstock', 0) > 0 else None,
                               delta_color="inverse")
        understock_metric.metric("Understock Days", sd['understock_days'],
                                delta=f"{sd['has_understock']} products" if sd.get('has_understock', 0) > 0 else None,
                                delta_color="inverse")

        # Update history
        history['rewards'].append(sd['recent_reward'])
        history['overstock'].append(sd.get('has_overstock', 0))
        history['understock'].append(sd.get('has_understock', 0))
        history['perfect'].append(1 if sd.get('has_overstock', 0) == 0 and sd.get('has_understock', 0) == 0 else 0)
        
        # Keep last 100 points
        for key in history:
            if len(history[key]) > 100:
                history[key] = history[key][-100:]

        # Stock levels chart
        stocks = np.array(sd['stocks'])
        avg_daily = np.array(sd.get('avg_daily_demand', [5]*10))
        safety = np.array(sd.get('safety_stock', [3]*10))
        products = [f"P{i}" for i in range(len(stocks))]
        
        fig_stock = go.Figure()
        fig_stock.add_trace(go.Bar(x=products, y=stocks, name='Current Stock', marker_color='lightblue'))
        fig_stock.add_trace(go.Scatter(x=products, y=3*avg_daily, name='Max Stock (3x avg)', 
                                       mode='lines', line=dict(color='red', dash='dash')))
        fig_stock.add_trace(go.Scatter(x=products, y=safety, name='Safety Stock', 
                                       mode='lines', line=dict(color='orange', dash='dot')))
        fig_stock.update_layout(title='Current Stock Levels vs Targets', height=300, showlegend=True)
        stock_chart.plotly_chart(fig_stock, use_container_width=True)

        # Order decisions chart
        last_order = np.array(sd['last_order'])
        outstanding = np.array(sd['outstanding'])
        
        fig_order = go.Figure()
        fig_order.add_trace(go.Bar(x=products, y=last_order, name='Last Order', marker_color='green'))
        fig_order.add_trace(go.Bar(x=products, y=outstanding, name='Outstanding', marker_color='yellow'))
        fig_order.update_layout(title='Order Decisions & Outstanding Orders', height=300, barmode='group')
        order_chart.plotly_chart(fig_order, use_container_width=True)

        # Demand vs Sales chart
        last_demand = np.array(sd['last_demand'])
        cumulative_sold = np.array(sd['cumulative_sold'])
        
        fig_demand = go.Figure()
        fig_demand.add_trace(go.Bar(x=products, y=last_demand, name='Last Demand', marker_color='purple'))
        fig_demand.add_trace(go.Bar(x=products, y=avg_daily, name='Avg Daily Demand', marker_color='lightgray'))
        fig_demand.update_layout(title='Demand Pattern', height=300, barmode='group')
        demand_chart.plotly_chart(fig_demand, use_container_width=True)

        # Issues over time
        fig_issues = go.Figure()
        x_axis = list(range(len(history['rewards'])))
        fig_issues.add_trace(go.Scatter(x=x_axis, y=history['rewards'], name='Reward', 
                                        mode='lines', line=dict(color='blue')))
        issues_chart.plotly_chart(fig_issues, use_container_width=True)

        # Product details table
        df = pd.DataFrame({
            'Product': products,
            'Stock': stocks.astype(int),
            'Last Demand': last_demand.astype(int),
            'Avg Demand': avg_daily.astype(int),
            'Safety Stock': safety.astype(int),
            'Last Order': last_order.astype(int),
            'Outstanding': outstanding.astype(int),
            'Lead Time': np.array(sd.get('lead_time', [2]*10)).astype(int),
            'Total Sold': cumulative_sold.astype(int),
        })
        
        # Color code based on status
        def highlight_issues(row):
            if row['Stock'] < row['Safety Stock']:
                return ['background-color: #ffcccc'] * len(row)  # Red for understock
            elif row['Stock'] > 3 * row['Avg Demand']:
                return ['background-color: #fff4cc'] * len(row)  # Yellow for overstock
            else:
                return ['background-color: #ccffcc'] * len(row)  # Green for good
        
        styled_df = df.style.apply(highlight_issues, axis=1)
        product_table.dataframe(styled_df, use_container_width=True, height=400)

        time.sleep(0.3)
