import pandas as pd
from pathlib import Path

def load_local_csv(filename):
    """Load a CSV from the data/ folder if it exists."""
    path = Path(__file__).parent.parent.parent / "data" / filename
    if path.exists():
        return pd.read_csv(path)
    return None

def fetch_bed_occupancy_real():
    df = load_local_csv("bed_occupancy.csv")
    if df is not None:
        return df
    return None

def fetch_staff_sickness_real():
    df = load_local_csv("staff_sickness.csv")
    if df is not None:
        return df
    return None
