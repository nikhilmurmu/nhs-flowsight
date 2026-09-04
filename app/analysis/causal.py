import pandas as pd
from statsmodels.tsa.stattools import grangercausalitytests

def test_granger_causality(df, cause_col, effect_col, max_lag=4):
    """
    Test whether cause_col Granger-causes effect_col.
    Returns p-values for each lag and whether any lag is significant at 0.05.
    """
    data = df[[cause_col, effect_col]].dropna()
    if len(data) < max_lag + 10:
        return {"error": "Not enough data for Granger test"}

    # Call without the unsupported verbose keyword
    results = grangercausalitytests(data, maxlag=max_lag)

    p_values = {}
    for lag in range(1, max_lag + 1):
        p = results[lag][0]["ssr_chi2test"][1]
        p_values[lag] = round(p, 4)

    significant_lags = [lag for lag, p in p_values.items() if p < 0.05]
    return {
        "p_values": p_values,
        "significant_lags": significant_lags,
        "is_causal": len(significant_lags) > 0
    }
