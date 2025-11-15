import streamlit as st
import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

LOG_DIR = Path("logs")
STREAM_FILE = LOG_DIR / "stream_data.json"

st.set_page_config(layout="wide", page_title="RL Inventory Dashboard")
st.title("🤖 RL Inventory Management - Live Training Dashboard")

def load_stream():
    if STREAM_FILE.exists():
        try:
            with open(STREAM_FILE, "r") as f:
                return json.load(f)
        except:
            return None
    return None

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
