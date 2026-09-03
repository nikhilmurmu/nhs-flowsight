import pandas as pd
import numpy as np
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, kpss

def decompose_series(df, value_col="ae_attendances", period=12):
    """
    Decompose time series into trend, seasonal, and residual components.
    Returns a dict with each component as a pandas Series indexed by month.
    """
    series = df.set_index("month")[value_col].resample("MS").mean().interpolate()
    decomposition = seasonal_decompose(series, model="additive", period=period, extrapolate_trend="freq")
    return {
        "original": series,
        "trend": decomposition.trend,
        "seasonal": decomposition.seasonal,
        "residual": decomposition.resid
    }

def test_stationarity(series, alpha=0.05):
    """
    Run Augmented Dickey-Fuller and KPSS tests for stationarity.
    Returns dict with test statistics and conclusions.
    """
    clean = series.dropna()
    adf_result = adfuller(clean, autolag="AIC")
    kpss_result = kpss(clean, regression="c", nlags="auto")
    return {
        "adf_statistic": adf_result[0],
        "adf_pvalue": adf_result[1],
        "adf_stationary": adf_result[1] < alpha,
        "kpss_statistic": kpss_result[0],
        "kpss_pvalue": kpss_result[1],
        "kpss_stationary": kpss_result[1] > alpha
    }
