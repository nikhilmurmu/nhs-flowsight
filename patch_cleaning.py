# patch_cleaning.py
path = 'app/analysis/cleaning.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''def clean_beds_sickness():
    \"\"\"Create synthetic beds and sickness data for now.\"\"\"
    dates = pd.date_range("2024-01-01", periods=24, freq="ME")
    return pd.DataFrame({
        "month": dates,
        "bed_occupancy_rate": np.random.normal(90, 5, 24).clip(75, 100),
        "staff_sickness_rate": np.random.normal(4, 1, 24).clip(2, 8)
    })'''

new = '''def clean_beds_sickness():
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
    })'''

content = content.replace(old, new)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('clean_beds_sickness patched.')
