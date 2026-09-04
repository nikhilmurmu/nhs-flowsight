import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "nhs_flightsight.db"

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ae (
            month TEXT,
            trust_name TEXT,
            ae_attendances INTEGER,
            four_hour_target_pct REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ambulance (
            month TEXT,
            trust_name TEXT,
            mean_response_min REAL,
            p90_response_min REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rtt (
            month TEXT,
            trust_name TEXT,
            waiting_list_size INTEGER,
            percent_over_18_weeks REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS beds (
            month TEXT,
            trust_name TEXT,
            occupancy_rate REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sickness (
            month TEXT,
            trust_name TEXT,
            sickness_rate REAL
        )
    """)
    conn.commit()
    conn.close()

def store_data(data: dict):
    """Store all DataFrames into SQLite."""
    init_db()
    conn = get_connection()
    for name, df in data.items():
        # Standardise column names
        df = df.copy()
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
        # Map to table schema
        table = name
        df.to_sql(table, conn, if_exists="replace", index=False)
    conn.close()
    print("Data stored in SQLite database.")
