import streamlit as st
import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from env import RealInventoryEnv

LOG_DIR = Path("logs")
STREAM_FILE = LOG_DIR / "stream_data.json"

st.set_page_config(layout="wide", page_title="Real Inventory AI Dashboard")

# Initialize session state
if 'mode' not in st.session_state:
    st.session_state.mode = 'training'
if 'manual_env' not in st.session_state:
    st.session_state.manual_env = None
if 'manual_history' not in st.session_state:
    st.session_state.manual_history = {
        'days': [], 'stocks': [], 'demands': [], 'orders': [], 'sales': [],
        'rewards': [], 'overstock': [], 'understock': [], 'efficiency': [],
        'holding_cost': [], 'stockout_cost': [], 'ordering_cost': []
    }

# Sidebar
st.sidebar.title("🎮 Control Panel")
mode = st.sidebar.radio("Select Mode", ["🚀 Training Mode", "🎯 Manual Testing"], 
                        index=0 if st.session_state.mode == 'training' else 1)

if "Manual" in mode:
    st.session_state.mode = 'manual'
else:
    st.session_state.mode = 'training'

st.title("📦 Real-World Inventory Management AI")

def load_stream():
    if STREAM_FILE.exists():
        try:
            with open(STREAM_FILE, "r") as f:
                return json.load(f)
        except:
            return None
    return None

# ============================================
# MANUAL TESTING MODE
# ============================================
if st.session_state.mode == 'manual':
    st.subheader("🎯 Manual Order Testing - Learn from Daily Trends")
    
    # Control buttons
    col_c1, col_c2, col_c3 = st.columns([1, 1, 2])
    with col_c1:
        if st.button("🔄 New Session", use_container_width=True):
            st.session_state.manual_env = RealInventoryEnv(num_products=10, max_days=365, seed=int(time.time()))
            st.session_state.manual_env.reset()
            st.session_state.manual_history = {
                'days': [], 'stocks': [], 'demands': [], 'orders': [], 'sales': [],
                'rewards': [], 'overstock': [], 'understock': [], 'efficiency': [],
                'holding_cost': [], 'stockout_cost': [], 'ordering_cost': []
            }
            st.success("New session started!")
            st.rerun()
    
    # Initialize environment
    if st.session_state.manual_env is None:
        st.session_state.manual_env = RealInventoryEnv(num_products=10, max_days=365)
        st.session_state.manual_env.reset()
    
    env = st.session_state.manual_env
    
    # Current metrics
    st.write("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_days = max(env.current_day, 1)
    efficiency = (env.perfect_days / total_days) * 100
    
    with col1:
        st.metric("📅 Day", f"{env.current_day}")
    with col2:
        st.metric("📈 Efficiency", f"{efficiency:.1f}%")
    with col3:
        st.metric("✅ Perfect Days", f"{env.perfect_days}/{total_days}")
    with col4:
        st.metric("📦 Total Stock", f"{int(env.stocks.sum())}/100")
    with col5:
        st.metric("🚨 Stockouts", env.total_stockouts, delta_color="inverse")
    
    # Yesterday's results (if available)
    if env.current_day > 0:
        st.write("---")
        st.subheader("📊 Yesterday's Performance Analysis")
        
        col_y1, col_y2, col_y3 = st.columns(3)
        with col_y1:
            if st.session_state.manual_history['rewards']:
                last_reward = st.session_state.manual_history['rewards'][-1]
                st.metric("💰 Reward", f"${last_reward:.2f}")
        with col_y2:
            if st.session_state.manual_history['understock']:
                last_understock = st.session_state.manual_history['understock'][-1]
                status = "🟢 Good" if last_understock == 0 else f"🔴 {last_understock} products"
                st.metric("Stockouts", status)
        with col_y3:
            total_stock = int(env.stocks.sum())
            st.metric("Stock Level", f"{total_stock}/100")
    
    # Current state
    st.write("---")
    st.subheader("📋 Today's Inventory State & Sales Trends")
    
    # Calculate trends
    avg_7day = np.mean(env.demand_history[-7:], axis=0)
    avg_14day = np.mean(env.demand_history, axis=0)
    recent_avg = avg_7day
    older_avg = avg_14day
    trend = ((recent_avg / np.maximum(1, older_avg)) - 1) * 100
    
    current_df = pd.DataFrame({
        'Product': [f'P{i}' for i in range(10)],
        'Stock': env.stocks.astype(int),
        'Yesterday Demand': env.yesterday_demand.astype(int),
        '7-Day Avg': avg_7day.astype(int),
        '14-Day Avg': avg_14day.astype(int),
        'Trend %': [f"{t:+.1f}%" for t in trend],
    })
    
    def highlight_stock_status(row):
        stock = row['Stock']
        avg = row['7-Day Avg']
        if stock < avg:
            return ['background-color: #ffcccc'] * len(row)  # Red - low stock
        elif stock > 5 * avg:
            return ['background-color: #fff4cc'] * len(row)  # Yellow - overstock
        else:
            return ['background-color: #ccffcc'] * len(row)  # Green - good
    
    styled_df = current_df.style.apply(highlight_stock_status, axis=1)
    st.dataframe(styled_df, use_container_width=True, height=300)
    
    st.info("💡 **Color Guide**: 🟢 Green = Good Stock | 🟡 Yellow = Overstock Risk | 🔴 Red = Low Stock Risk")
    
    # Order placement
    st.write("---")
    st.subheader("🛒 Place Today's Orders")
    st.write("**Based on trends above, how much should you order for each product?**")
    
    order_cols = st.columns(5)
    orders = []
    
    for i in range(10):
        with order_cols[i % 5]:
            # Suggest order: 7-day avg - current stock (simple)
            suggested = max(0, int(avg_7day[i] - env.stocks[i]))
            suggested = min(suggested, 100)
            
            order = st.number_input(
                f"P{i}", 
                min_value=0, 
                max_value=100, 
                value=suggested,
                step=5,
                key=f"order_{i}",
                help=f"Suggested: {suggested} (1-day delivery)"
            )
            orders.append(order)
    
    col_submit1, col_submit2 = st.columns([1, 3])
    with col_submit1:
        submit_btn = st.button("✅ Submit Orders & Next Day", use_container_width=True, type="primary")
    
    # Process orders
    if submit_btn:
        action = np.array(orders, dtype=np.float32)
        obs, reward, terminated, truncated, info = env.step(action)
        
        # Record history
        hist = st.session_state.manual_history
        hist['days'].append(env.current_day - 1)
        hist['stocks'].append(env.stocks.copy().tolist())
        hist['demands'].append(info['demand'])
        hist['sales'].append(info['fulfilled'])
        hist['orders'].append(orders)
        hist['rewards'].append(float(reward))
        hist['overstock'].append(0)  # Simplified - no overstock tracking
        hist['understock'].append(info['stockout_products'])
        hist['efficiency'].append((env.perfect_days / env.current_day) * 100)
        hist['holding_cost'].append(0)
        hist['stockout_cost'].append(info['total_unmet'] * 20)
        hist['ordering_cost'].append(0)
        
        # Show feedback
        if info['stockout_products'] == 0:
            st.success(f"🎉 Perfect Day! All demand met! Reward: ${reward:.2f}")
        else:
            st.warning(f"🚨 Stockout on {info['stockout_products']} products | Reward: ${reward:.2f}")
        
        if terminated:
            st.info("📊 Year completed! Start new session to continue.")
        
        time.sleep(1)
        st.rerun()
    
    # Performance charts
    if len(st.session_state.manual_history['days']) > 0:
        st.write("---")
        st.subheader("📊 Your Performance Over Time")
        
        hist = st.session_state.manual_history
        
        # Main metrics
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            # Efficiency trend
            fig_eff = go.Figure()
            fig_eff.add_trace(go.Scatter(
                x=hist['days'], y=hist['efficiency'],
                mode='lines+markers', name='Efficiency',
                line=dict(color='green', width=3)
            ))
            fig_eff.update_layout(
                title='Efficiency Trend (% Perfect Days)',
                xaxis_title='Day', yaxis_title='Efficiency %',
                height=300
            )
            st.plotly_chart(fig_eff, use_container_width=True)
            
            # Cost breakdown
            fig_cost = go.Figure()
            fig_cost.add_trace(go.Scatter(x=hist['days'], y=np.cumsum(hist['holding_cost']), 
                                         name='Holding', stackgroup='one', fillcolor='lightblue'))
            fig_cost.add_trace(go.Scatter(x=hist['days'], y=np.cumsum(hist['stockout_cost']), 
                                         name='Stockout', stackgroup='one', fillcolor='red'))
            fig_cost.add_trace(go.Scatter(x=hist['days'], y=np.cumsum(hist['ordering_cost']), 
                                         name='Ordering', stackgroup='one', fillcolor='orange'))
            fig_cost.update_layout(
                title='Cumulative Costs Breakdown',
                xaxis_title='Day', yaxis_title='Total Cost ($)',
                height=300
            )
            st.plotly_chart(fig_cost, use_container_width=True)
        
        with col_chart2:
            # Daily rewards
            fig_reward = go.Figure()
            fig_reward.add_trace(go.Scatter(
                x=hist['days'], y=hist['rewards'],
                mode='lines', name='Daily Reward',
                line=dict(color='blue', width=2)
            ))
            # Add moving average
            if len(hist['rewards']) > 7:
                ma7 = pd.Series(hist['rewards']).rolling(7).mean()
                fig_reward.add_trace(go.Scatter(
                    x=hist['days'], y=ma7,
                    mode='lines', name='7-Day MA',
                    line=dict(color='red', width=2, dash='dash')
                ))
            fig_reward.update_layout(
                title='Daily Rewards',
                xaxis_title='Day', yaxis_title='Reward ($)',
                height=300
            )
            st.plotly_chart(fig_reward, use_container_width=True)
            
            # Issues
            fig_issues = go.Figure()
            fig_issues.add_trace(go.Bar(x=hist['days'], y=hist['overstock'], 
                                       name='Overstock', marker_color='orange'))
            fig_issues.add_trace(go.Bar(x=hist['days'], y=hist['understock'], 
                                       name='Understock', marker_color='red'))
            fig_issues.update_layout(
                title='Daily Issues',
                xaxis_title='Day', yaxis_title='# Products',
                height=300, barmode='group'
            )
            st.plotly_chart(fig_issues, use_container_width=True)

# ============================================
# TRAINING MODE
# ============================================
else:
    st.subheader("🚀 AI Training - Learning from Daily Trends")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    timestep_m = st.empty()
    episode_m = st.empty()
    day_m = st.empty()
    efficiency_m = st.empty()
    reward_m = st.empty()
    
    with col1:
        timestep_metric = timestep_m
    with col2:
        episode_metric = episode_m
    with col3:
        day_metric = day_m
    with col4:
        efficiency_metric = efficiency_m
    with col5:
        reward_metric = reward_m
    
    col_chart1, col_chart2 = st.columns(2)
    stock_chart = col_chart1.empty()
    trend_chart = col_chart1.empty()
    order_chart = col_chart2.empty()
    performance_chart = col_chart2.empty()
    
    product_table = st.empty()
    
    last_ts = 0
    history = {'rewards': [], 'efficiency': [], 'overstock': [], 'understock': []}
    
    while True:
        sd = load_stream()
        if sd is None:
            st.info("⏳ Waiting for training to start... Run: python train_real.py --total-timesteps 100000")
            time.sleep(1)
            continue
        
        if sd["timestamp"] == last_ts:
            time.sleep(0.3)
            continue
        last_ts = sd["timestamp"]
        
        # Update metrics
        timestep_metric.metric("Timestep", f"{sd.get('timestep', 0):,}")
        episode_metric.metric("Episode", f"{sd.get('episode', 0)}")
        day_metric.metric("Day", f"{sd['day']}/{sd.get('max_days', 365)}")
        efficiency_metric.metric("Efficiency", f"{sd.get('efficiency', 0):.1f}%")
        reward_metric.metric("Avg Reward", f"${sd.get('avg_reward', 0):.2f}")
        
        # Update history
        history['rewards'].append(sd['recent_reward'])
        history['efficiency'].append(sd.get('efficiency', 0))
        history['overstock'].append(sd.get('overstock_count', 0))
        history['understock'].append(sd.get('understock_count', 0))
        
        if len(history['rewards']) > 100:
            for key in history:
                history[key] = history[key][-100:]
        
        # Charts
        stocks = np.array(sd['stocks'])
        avg_7day = np.array(sd.get('avg_7day', [0]*10))
        avg_14day = np.array(sd.get('avg_14day', [0]*10))
        products = [f"P{i}" for i in range(10)]
        
        # Stock levels
        fig_stock = go.Figure()
        fig_stock.add_trace(go.Bar(x=products, y=stocks, name='Stock', marker_color='lightblue'))
        fig_stock.add_trace(go.Scatter(x=products, y=avg_7day*2, name='2x 7-Day Avg',
                                       mode='lines', line=dict(color='orange', dash='dash')))
        fig_stock.update_layout(title='Current Stock Levels', height=250)
        stock_chart.plotly_chart(fig_stock, use_container_width=True)
        
        # Demand trends
        yesterday = np.array(sd.get('yesterday_demand', [0]*10))
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(x=products, y=yesterday, name='Yesterday', marker_color='purple'))
        fig_trend.add_trace(go.Bar(x=products, y=avg_7day, name='7-Day Avg', marker_color='orange'))
        fig_trend.add_trace(go.Bar(x=products, y=avg_14day, name='14-Day Avg', marker_color='green'))
        fig_trend.update_layout(title='Demand Trends', height=250, barmode='group')
        trend_chart.plotly_chart(fig_trend, use_container_width=True)
        
        # Orders
        orders = np.array(sd.get('today_orders', [0]*10))
        fig_order = go.Figure()
        fig_order.add_trace(go.Bar(x=products, y=orders, name='Today Orders (Arrive Tomorrow)', 
                                   marker_color='green'))
        fig_order.update_layout(title='AI Order Decisions', height=250)
        order_chart.plotly_chart(fig_order, use_container_width=True)
        
        # Performance
        fig_perf = go.Figure()
        x_axis = list(range(len(history['efficiency'])))
        fig_perf.add_trace(go.Scatter(x=x_axis, y=history['efficiency'], 
                                      name='Efficiency', line=dict(color='green', width=2)))
        fig_perf.update_layout(title='Efficiency Over Time', height=250, 
                              yaxis_title='Efficiency %')
        performance_chart.plotly_chart(fig_perf, use_container_width=True)
        
        # Table
        df = pd.DataFrame({
            'Product': products,
            'Stock': stocks.astype(int),
            'Yesterday': yesterday.astype(int),
            '7-Day Avg': avg_7day.astype(int),
            '14-Day Avg': avg_14day.astype(int),
            'Today Order': orders.astype(int),
        })
        
        product_table.dataframe(df, use_container_width=True, height=300)
        
        time.sleep(0.3)
