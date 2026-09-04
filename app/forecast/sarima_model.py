import pandas as pd
import numpy as np
import pmdarima as pm
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_squared_error, mean_absolute_error, mean_absolute_percentage_error
import warnings
warnings.filterwarnings("ignore")

def prepare_data_for_sarima(df):
    """Prepare monthly A&E attendances with exogenous variables."""
    data = df.set_index("month")[["ae_attendances", "staff_sickness_rate", "bed_occupancy_rate"]].resample("MS").mean().interpolate()
    data = data.asfreq("MS")
    return data

def train_sarimax(data, exog_cols, horizon=6):
    """Train SARIMAX model with exogenous variables."""
    y = data["ae_attendances"]
    exog = data[exog_cols]
    
    # Auto-ARIMA to find best order (seasonal period = 12)
    auto_model = pm.auto_arima(
        y, exogenous=exog, seasonal=True, m=12,
        start_p=1, start_q=1, max_p=3, max_q=3,
        start_P=0, start_Q=0, max_P=2, max_Q=2,
        trace=False, error_action='ignore', suppress_warnings=True,
        stepwise=True, n_jobs=1
    )
    order = auto_model.order
    seasonal_order = auto_model.seasonal_order
    
    # Fit final SARIMAX
    model = SARIMAX(y, exog=exog, order=order, seasonal_order=seasonal_order)
    fitted = model.fit(disp=False)
    
    # Forecast (need future exogenous values – use last observed or simple projection)
    last_exog = exog.iloc[-1].values.reshape(1, -1)
    future_exog = np.repeat(last_exog, horizon, axis=0)
    forecast = fitted.get_forecast(steps=horizon, exog=future_exog)
    forecast_mean = forecast.predicted_mean
    conf_int = forecast.conf_int()
    
    result = pd.DataFrame({
        "forecasted_ae_attendances": forecast_mean,
        "lower_ci": conf_int.iloc[:, 0],
        "upper_ci": conf_int.iloc[:, 1]
    })
    result.index = pd.date_range(start=y.index[-1] + pd.DateOffset(months=1), periods=horizon, freq="MS")
    
    # Backtesting metrics on training data (in-sample)
    fitted_values = fitted.fittedvalues
    rmse = np.sqrt(mean_squared_error(y, fitted_values))
    mae = mean_absolute_error(y, fitted_values)
    mape = mean_absolute_percentage_error(y, fitted_values) * 100
    
    return {
        "model": fitted,
        "forecast_df": result,
        "order": order,
        "seasonal_order": seasonal_order,
        "metrics": {"RMSE": rmse, "MAE": mae, "MAPE": mape}
    }

def run_sarima_forecast(df):
    data = prepare_data_for_sarima(df)
    exog_cols = ["staff_sickness_rate", "bed_occupancy_rate"]
    result = train_sarimax(data, exog_cols, horizon=6)
    return result
