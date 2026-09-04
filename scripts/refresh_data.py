import sys
sys.path.insert(0, "app")
from ingestion.nhs_data import fetch_all_data
from analysis.cleaning import build_clean_merged_table
from database.db import store_data, init_db
from datetime import datetime

if __name__ == "__main__":
    print(f"Starting data refresh at {datetime.now().isoformat()}")
    data = fetch_all_data()
    init_db()
    store_data(data)
    merged = build_clean_merged_table()
    print(f"Data refresh complete. Merged table shape: {merged.shape}")
