import os
import json
import time
import numpy as np
import pandas as pd
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def write_stream_data(data: dict):
    fpath = LOG_DIR / "stream_data.json"
    with open(fpath, "w") as f:
        json.dump(data, f, indent=2, default=json_serial)

def append_training_log(row: dict):
    fpath = LOG_DIR / "training_log.csv"
    df = pd.DataFrame([row])
    header = not fpath.exists()
    df.to_csv(fpath, mode="a", header=header, index=False)

def json_serial(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(type(obj))
