# patch_sickness.py
path = 'app/ingestion/nhs_data.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''def fetch_staff_sickness():
    raw = _download_raw(URLS["staff_sickness"])
    if raw:
        sheet = _find_sheet_with_keywords(raw, ["sickness", "absence", "rate"], xls=False)
        if sheet is None:
            sheet = 0
        df = _read_excel_autoheader(raw, sheet, ["period", "month", "date", "sickness", "absence"])
        if df is not None:
            month_col = None
            sick_col = None
            for col in df.columns:
                col_l = str(col).lower()
                if "month" in col_l or "date" in col_l or "period" in col_l:
                    month_col = col
                if "sickness" in col_l or "absence" in col_l or "rate" in col_l:
                    sick_col = col
            if month_col is not None and sick_col is not None:
                out = pd.DataFrame({
                    "month": pd.to_datetime(df[month_col], errors="coerce"),
                    "sickness_rate": pd.to_numeric(df[sick_col], errors="coerce")
                }).dropna()
                return out
    # Fallback synthetic
    dates = pd.date_range("2024-01-01", periods=24, freq="ME")
    return pd.DataFrame({
        "month": dates,
        "trust_name": ["Trust A"] * 24,
        "sickness_rate": np.random.normal(4, 1, 24).clip(2, 8)
    })'''

new = '''def fetch_staff_sickness():
    raw = _download_raw(URLS["staff_sickness"])
    if raw:
        try:
            # Read 'Table 1' sheet with header at row 2
            df = pd.read_excel(io.BytesIO(raw), sheet_name="Table 1", header=2)
            # Columns: 'Month', 'England', then regions...
            df["month"] = pd.to_datetime(df["Month"], format="%B %Y", errors="coerce")
            df["sickness_rate"] = pd.to_numeric(df["England"], errors="coerce")
            out = df[["month", "sickness_rate"]].dropna()
            out = out.sort_values("month").reset_index(drop=True)
            return out
        except Exception as e:
            print(f"Staff sickness parsing failed: {e}")

    # Fallback synthetic
    dates = pd.date_range("2024-01-01", periods=24, freq="ME")
    return pd.DataFrame({
        "month": dates,
        "trust_name": ["Trust A"] * 24,
        "sickness_rate": np.random.normal(4, 1, 24).clip(2, 8)
    })'''

content = content.replace(old, new)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('fetch_staff_sickness updated.')
