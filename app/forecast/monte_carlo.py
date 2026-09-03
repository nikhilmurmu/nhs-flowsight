import numpy as np
import pandas as pd

def monte_carlo_ae(df, n_simulations=1000, periods=12, seed=42):
    """
    Simulate future A&E attendances using Monte Carlo method.
    Returns mean path, 5th and 95th percentile bands, and full simulation matrix.
    """
    np.random.seed(seed)
    series = df.set_index("month")["ae_attendances"].resample("MS").mean()
    daily_returns = series.pct_change().dropna()
    mu = daily_returns.mean()
    sigma = daily_returns.std()
    last_value = series.iloc[-1]

    simulations = np.zeros((periods, n_simulations))
    for i in range(n_simulations):
        values = [last_value]
        for _ in range(periods):
            values.append(values[-1] * (1 + np.random.normal(mu, sigma)))
        simulations[:, i] = values[1:]

    dates = pd.date_range(start=series.index[-1] + pd.DateOffset(months=1), periods=periods, freq="ME")
    sim_df = pd.DataFrame(simulations, index=dates)

    return {
        "simulations": sim_df,
        "mean_path": sim_df.mean(axis=1),
        "lower_5": sim_df.quantile(0.05, axis=1),
        "upper_95": sim_df.quantile(0.95, axis=1)
    }
