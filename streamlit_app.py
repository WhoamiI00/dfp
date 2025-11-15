import streamlit as st
import json
import time
import numpy as np
from pathlib import Path
import plotly.graph_objects as go

LOG_DIR = Path("logs")
STREAM_FILE = LOG_DIR / "stream_data.json"

st.set_page_config(layout="wide")
st.title("RL Inventory – Live Dashboard")

heatmap = st.empty()
table = st.empty()
stats = st.empty()

def load_stream():
    if STREAM_FILE.exists():
        try:
            with open(STREAM_FILE, "r") as f:
                return json.load(f)
        except:
            return None
    return None

last_ts = 0
while True:
    sd = load_stream()
    if sd is None:
        st.info("Waiting for training...")
        time.sleep(1)
        continue

    if sd["timestamp"] == last_ts:
        time.sleep(0.5)
        continue
    last_ts = sd["timestamp"]

    stocks = np.array(sd["stocks"])

    fig = go.Figure(data=go.Heatmap(
        z=stocks.reshape((10,1)),
        x=["Stock"],
        y=[f"P{i}" for i in range(10)],
    ))
    heatmap.plotly_chart(fig, use_container_width=True)

    stats.metric("Day", sd["day"])
    stats.metric("Recent Reward", f"{sd['recent_reward']:.2f}")

    time.sleep(0.5)
