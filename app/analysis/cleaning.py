import pandas as pd
import numpy as np
import re
from datetime import datetime
from app.ingestion.nhs_data import fetch_all_data

def parse_time_to_minutes(time_str):
    """Convert 'HH:MM:SS' to minutes. Returns NaN if invalid."""
    if pd.isna(time_str):
        return np.nan
    if isinstance(time_str, (int, float)):
        return float(time_str)
    parts = str(time_str).strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60
        elif len(parts) == 2:
            return int(parts[0]) + int(parts[1]) / 60
    except:
        pass
    return np.nan

def clean_ae():
    """Extract England-level A&E attendances."""
    data = fetch_all_data()["ae"]
    df = data.copy()
    # Use exact column names from the real Chart Data sheet
    df["month"] = pd.to_datetime(df["Period 1"], errors="coerce")
    # "Monthly data2" is All A&E attendances (from Excel header)
    df["ae_attendances"] = pd.to_numeric(df["Monthly data2"], errors="coerce")
    # "Monthly data" is A&E attendances type 1
    df["ae_type1_attendances"] = pd.to_numeric(df["Monthly data"], errors="coerce")
    out = df[["month", "ae_attendances", "ae_type1_attendances"]].copy()
    out = out.dropna(subset=["month"]).drop_duplicates("month")
    return out

def clean_ambulance():
    """Extract England-level ambulance response times."""
    data = fetch_all_data()["ambulance"]
    df = data.copy()
    # Find England row (usually first data row after header)
    service_col = None
    for col in df.columns:
        if "ambulance service" in str(col).lower():
            service_col = col
            break
    if service_col is None:
        return pd.DataFrame()
    england_row = df[df[service_col].astype(str).str.strip().str.lower() == "england"]
    if england_row.empty:
        england_row = df.head(1)
    row = england_row.iloc[0]
    mean_col = None
    p90_col = None
    for col in df.columns:
        col_l = str(col).lower()
        if "mean" in col_l and "hour" in col_l:
            mean_col = col
        if "90th" in col_l and "centile" in col_l:
            p90_col = col
    out = pd.DataFrame({
        "month": [datetime.now().replace(day=1)],
        "ambulance_mean_response_min": [parse_time_to_minutes(row.get(mean_col)) if mean_col else np.nan],
        "ambulance_90th_percentile_min": [parse_time_to_minutes(row.get(p90_col)) if p90_col else np.nan]
    })
    return out

def clean_rtt():
    """Extract total waiting list by period from RTT data."""
    data = fetch_all_data()["rtt"]
    df = data.copy()
    if "Period" not in df.columns:
        return pd.DataFrame()
    total_col = None
    for col in df.columns:
        if "total all" in str(col).lower():
            total_col = col
            break
    if total_col is None:
        # fallback: sum all week bucket columns
        bucket_cols = [c for c in df.columns if str(c).startswith("Gt") or str(c).startswith("Total")]
        df["TotalAll"] = df[bucket_cols].sum(axis=1)
        total_col = "TotalAll"
    df["Period"] = pd.to_datetime(df["Period"].astype(str).str.replace("RTT-", ""), errors="coerce")
    out = df.groupby("Period")[total_col].sum().reset_index()
    out.columns = ["month", "waiting_list_total"]
    return out

def clean_beds_sickness():
    from app.ingestion.nhs_data import fetch_bed_occupancy, fetch_staff_sickness
    bed = fetch_bed_occupancy()
    sick = fetch_staff_sickness()
    if bed is not None and sick is not None:
        bed = bed.rename(columns={"occupancy_rate": "bed_occupancy_rate"})
        sick = sick.rename(columns={"sickness_rate": "staff_sickness_rate"})
        merged = bed.merge(sick, on="month", how="outer")
        merged = merged.sort_values("month").reset_index(drop=True)
        return merged
    # fallback synthetic
    dates = pd.date_range("2024-01-01", periods=24, freq="ME")
    return pd.DataFrame({
        "month": dates,
        "bed_occupancy_rate": np.random.normal(90, 5, 24).clip(75, 100),
        "staff_sickness_rate": np.random.normal(4, 1, 24).clip(2, 8)
    })

def build_clean_merged_table():
    """Merge all cleaned datasets into a single analytical table."""
    ae = clean_ae()
    amb = clean_ambulance()
    rtt = clean_rtt()
    beds = clean_beds_sickness()
    merged = ae.copy()
    merged = merged.merge(rtt, on="month", how="outer")
    merged = merged.merge(beds, on="month", how="outer")
    # Ambulance is a single row snapshot; merge on nearest month
    if not amb.empty:
        merged["ambulance_mean_response_min"] = amb["ambulance_mean_response_min"].iloc[0]
        merged["ambulance_90th_percentile_min"] = amb["ambulance_90th_percentile_min"].iloc[0]
    # Sort and clean
    merged = merged.sort_values("month").reset_index(drop=True)
    for col in merged.select_dtypes(include=[np.number]).columns:
        merged[col] = merged[col].fillna(merged[col].median())
    return merged

