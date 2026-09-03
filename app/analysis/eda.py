import pandas as pd
import numpy as np
from app.analysis.cleaning import build_clean_merged_table

def load_analysis_table():
    """Load the clean merged NHS table."""
    df = build_clean_merged_table()
    df["month"] = pd.to_datetime(df["month"])
    return df.sort_values("month").reset_index(drop=True)

def summary_statistics(df):
    """Return key descriptive statistics."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return df[numeric_cols].describe().T

def year_over_year_change(df, value_col):
    """Compute year-over-year % change for a given column."""
    df = df.copy()
    df["year"] = df["month"].dt.year
    df["month_num"] = df["month"].dt.month
    yearly = df.groupby(["year", "month_num"])[value_col].mean().reset_index()
    yearly["prev_year_val"] = yearly.groupby("month_num")[value_col].shift(1)
    yearly["yoy_change_pct"] = (yearly[value_col] - yearly["prev_year_val"]) / yearly["prev_year_val"] * 100
    return yearly

def correlation_matrix(df):
    """Correlation between all numeric columns."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return df[numeric_cols].corr()

def detect_seasonality(df, value_col):
    """Calculate average value by month across all years."""
    df = df.copy()
    df["month_name"] = df["month"].dt.month_name()
    return df.groupby("month_name")[value_col].mean()

def run_eda():
    df = load_analysis_table()
    if df.empty:
        return {}
    results = {
        "summary": summary_statistics(df),
        "correlation": correlation_matrix(df),
        "ae_yoy": year_over_year_change(df, "ae_attendances"),
        "ae_seasonality": detect_seasonality(df, "ae_attendances"),
        "data": df,
        "latest_month": df["month"].max()
    }
    return results
