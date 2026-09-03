import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime
from app.analysis.cleaning import build_clean_merged_table

def forecast_ae_next_6_months():
    """Forecast A&E attendances for next 6 months using linear regression."""
    df = build_clean_merged_table()
    df["month"] = pd.to_datetime(df["month"])
    df = df.dropna(subset=["ae_attendances"]).sort_values("month")
    
    if len(df) < 12:
        return None
    
    # Use time index as feature
    df["time_idx"] = np.arange(len(df))
    X = df[["time_idx"]].values
    y = df["ae_attendances"].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    future_idx = np.arange(len(df), len(df) + 6).reshape(-1, 1)
    forecast_vals = model.predict(future_idx)
    
    last_date = df["month"].max()
    future_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=6, freq="ME")
    
    result = pd.DataFrame({
        "month": future_dates,
        "forecasted_ae_attendances": forecast_vals
    })
    return result

def compute_waiting_list_growth():
    """Calculate current waiting list snapshot."""
    df = build_clean_merged_table()
    latest = df["waiting_list_total"].iloc[-1]
    return {"latest_waiting_list": latest}
