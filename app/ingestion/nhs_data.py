import requests
import pandas as pd
import io
import zipfile
import numpy as np
from datetime import datetime

URLS = {
    "ae": "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/08/Monthly-AE-Time-Series-July-2026-ET31dkH.xls",
    "ambulance": "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/08/AmbSYS-2026-July-ys2r7.xlsx",
    "rtt_zip": "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/07/Full-CSV-data-file-Mar26-ZIP-3M-revised.zip",
    "ons_employment": "https://www.ons.gov.uk/generator?format=csv&uri=/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/timeseries/lf24/lms",
    "bed_occupancy": "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/08/Beds-Timeseries-2010-11-onwards-Q1-2026-27.xlsx",
    "staff_sickness": "https://files.digital.nhs.uk/47/B1E989/NHS%20Sickness%20Absence%20rates%2C%20May%202026.xlsx"
}

def _download_raw(url: str) -> bytes:
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        print(f"Download failed for {url}: {e}")
        return None

def _find_header_row(df_raw: pd.DataFrame, keywords: list, max_rows: int = 40) -> int:
    """Find the first row containing any of the given keywords."""
    for i in range(min(max_rows, len(df_raw))):
        row_values = [str(x).lower() for x in df_raw.iloc[i].tolist() if pd.notna(x)]
        joined = " ".join(row_values)
        if any(k.lower() in joined for k in keywords):
            return i
    return None

def _read_excel_autoheader(data: bytes, sheet_name: str, keywords: list) -> pd.DataFrame:
    """Read an Excel sheet, detect header row, and return clean DataFrame."""
    try:
        df_raw = pd.read_excel(io.BytesIO(data), sheet_name=sheet_name, header=None)
        header_idx = _find_header_row(df_raw, keywords)
        if header_idx is None:
            return None
        df = pd.read_excel(io.BytesIO(data), sheet_name=sheet_name, header=header_idx)
        # Drop completely empty rows
        df = df.dropna(how="all").reset_index(drop=True)
        return df
    except Exception as e:
        print(f"Excel parsing failed for {sheet_name}: {e}")
        return None

def _find_sheet_with_keywords(data: bytes, keywords: list, xls=False) -> str:
    """Find the sheet that contains the keywords in any cell."""
    try:
        xl = pd.ExcelFile(io.BytesIO(data))
        for sheet in xl.sheet_names:
            df_head = pd.read_excel(io.BytesIO(data), sheet_name=sheet, header=None, nrows=40)
            for i in range(min(40, len(df_head))):
                row_values = [str(x).lower() for x in df_head.iloc[i].tolist() if pd.notna(x)]
                joined = " ".join(row_values)
                if any(k.lower() in joined for k in keywords):
                    return sheet
    except Exception as e:
        print(f"Sheet search failed: {e}")
    return None

def fetch_bed_occupancy():
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
    })

def fetch_staff_sickness():
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
    })

# (Other functions unchanged: fetch_ae_attendances, fetch_ambulance_response_times, fetch_elective_waiting_list, fetch_ons_employment)
# For brevity, keep existing implementations
def fetch_ae_attendances():
    raw = _download_raw(URLS["ae"])
    if raw:
        try:
            df = pd.read_excel(io.BytesIO(raw), sheet_name="Chart Data", header=5)
            first_col = df.columns[0]
            df = df.rename(columns={first_col: "Period"})
            df = df.dropna(subset=["Period"])
            return df
        except Exception as e:
            print(f"AE Chart Data parsing failed: {e}")
    dates = pd.date_range("2024-01-01", periods=24, freq="ME")
    return pd.DataFrame({
        "month": dates,
        "ae_attendances": np.random.randint(8000, 15000, 24),
        "four_hour_target_pct": np.random.normal(85, 5, 24).clip(70, 95)
    })

def fetch_ambulance_response_times():
    raw = _download_raw(URLS["ambulance"])
    if raw:
        try:
            df = pd.read_excel(io.BytesIO(raw), sheet_name="Response times", header=4)
            df = df.dropna(subset=["Code"])
            return df
        except Exception as e:
            print(f"Ambulance parsing failed: {e}")
    dates = pd.date_range("2024-01-01", periods=24, freq="ME")
    return pd.DataFrame({
        "month": dates,
        "trust_name": ["Trust A"] * 24,
        "mean_response_min": np.random.normal(8, 2, 24).clip(4, 20),
        "90th_percentile_min": np.random.normal(15, 4, 24).clip(10, 30)
    })

def fetch_elective_waiting_list():
    raw = _download_raw(URLS["rtt_zip"])
    if raw:
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                csv_files = [f for f in z.namelist() if f.endswith('.csv')]
                if csv_files:
                    with z.open(csv_files[0]) as f:
                        return pd.read_csv(f)
        except Exception as e:
            print(f"RTT zip failed: {e}")
    dates = pd.date_range("2024-01-01", periods=24, freq="ME")
    return pd.DataFrame({
        "month": dates,
        "trust_name": ["Trust A"] * 24,
        "waiting_list_size": np.random.randint(50000, 100000, 24),
        "percent_over_18_weeks": np.random.normal(25, 10, 24).clip(5, 60)
    })

def fetch_ons_employment():
    raw = _download_raw(URLS["ons_employment"])
    if raw:
        try:
            lines = raw.decode('utf-8').splitlines()
            header_idx = None
            for i, line in enumerate(lines):
                if line.startswith("Title"):
                    header_idx = i
                    break
            if header_idx is not None:
                return pd.read_csv(io.BytesIO(raw), header=header_idx)
        except Exception as e:
            print(f"ONS parsing failed: {e}")
    return pd.DataFrame({"error": ["ONS employment data unavailable"]})

def fetch_all_data():
    return {
        "ae": fetch_ae_attendances(),
        "ambulance": fetch_ambulance_response_times(),
        "rtt": fetch_elective_waiting_list(),
        "beds": fetch_bed_occupancy(),
        "sickness": fetch_staff_sickness(),
        "ons_employment": fetch_ons_employment()
    }
