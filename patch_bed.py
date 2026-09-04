# patch_bed.py
path = 'app/ingestion/nhs_data.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''def fetch_bed_occupancy():
    raw = _download_raw(URLS["bed_occupancy"])
    if raw:
        # Try to find the right sheet
        sheet = _find_sheet_with_keywords(raw, ["occupancy", "bed", "available"], xls=False)
        if sheet is None:
            sheet = 0  # fallback first sheet
        df = _read_excel_autoheader(raw, sheet, ["period", "month", "date", "occupancy", "beds"])
        if df is not None:
            # Try to extract month and occupancy columns
            month_col = None
            occ_col = None
            for col in df.columns:
                col_l = str(col).lower()
                if "month" in col_l or "date" in col_l or "period" in col_l:
                    month_col = col
                if "occup" in col_l or "occupancy" in col_l or "bed" in col_l:
                    occ_col = col
            if month_col is not None and occ_col is not None:
                out = pd.DataFrame({
                    "month": pd.to_datetime(df[month_col], errors="coerce"),
                    "occupancy_rate": pd.to_numeric(df[occ_col], errors="coerce")
                }).dropna()
                return out
    # Fallback synthetic
    dates = pd.date_range("2024-01-01", periods=24, freq="ME")
    return pd.DataFrame({
        "month": dates,
        "trust_name": ["Trust A"] * 24,
        "occupancy_rate": np.random.normal(90, 5, 24).clip(75, 100)
    })'''

new = '''def fetch_bed_occupancy():
    raw = _download_raw(URLS["bed_occupancy"])
    if raw:
        try:
            # Read the 'Open Overnight' sheet with header at row 13
            df = pd.read_excel(io.BytesIO(raw), sheet_name="Open Overnight", header=13)
            # Filter for England only
            df = df[df["Org Name"] == "England"].copy()
            if not df.empty:
                def quarter_to_month(year_str, quarter):
                    start_year = int(year_str.split('/')[0])
                    quarter_map = {'Q1': 1, 'Q2': 4, 'Q3': 7, 'Q4': 10}
                    q_month = quarter_map.get(quarter, 1)
                    return f"{start_year}-{q_month:02d}-01"
                df["month"] = df.apply(lambda r: quarter_to_month(r["Year"], r["Period"]), axis=1)
                df["month"] = pd.to_datetime(df["month"])
                # Occupancy rate is the 17th column (index 16)
                df["occupancy_rate"] = pd.to_numeric(df.iloc[:, 16], errors="coerce") * 100
                out = df[["month", "occupancy_rate"]].dropna()
                out = out.sort_values("month").reset_index(drop=True)
                monthly = out.set_index("month").resample("MS").ffill().reset_index()
                return monthly
        except Exception as e:
            print(f"Bed occupancy parsing failed: {e}")

    # Fallback synthetic
    dates = pd.date_range("2024-01-01", periods=24, freq="ME")
    return pd.DataFrame({
        "month": dates,
        "trust_name": ["Trust A"] * 24,
        "occupancy_rate": np.random.normal(90, 5, 24).clip(75, 100)
    })'''

content = content.replace(old, new)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('fetch_bed_occupancy updated.')
