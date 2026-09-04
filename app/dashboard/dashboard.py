import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime

from app.analysis.eda import run_eda
from app.forecast.forecast import forecast_ae_next_6_months
from app.forecast.sarima_model import run_sarima_forecast
from app.forecast.monte_carlo import monte_carlo_ae
from app.analysis.advanced import decompose_series, test_stationarity
from app.analysis.causal import test_granger_causality
from app.reports.generator import generate_executive_summary

st.set_page_config(page_title="NHS FlowSight", layout="wide")
st.markdown("""
<style>
    .reportview-container {background: #0e1117}
    .sidebar .sidebar-content {background: #262730}
    .stMetric {background: #1f2937; border-radius: 10px; padding: 15px; color: white}
    .stPlotlyChart {border-radius: 10px; overflow: hidden}
</style>
""", unsafe_allow_html=True)

st.title("🏥 NHS FlowSight – System Demand & Capacity Analytics")

@st.cache_data(ttl=1800)
def load_all():
    eda = run_eda()
    forecast_linear = forecast_ae_next_6_months()
    monte = monte_carlo_ae(eda["data"], n_simulations=500, periods=12, seed=42)
    sarima = run_sarima_forecast(eda["data"])
    return eda, forecast_linear, monte, sarima

eda, forecast_linear, monte, sarima = load_all()
if not eda or "data" not in eda:
    st.error("Could not load NHS data.")
    st.stop()

df = eda["data"]
summary = eda["summary"]
corr = eda["correlation"]
seasonality = eda["ae_seasonality"]

st.sidebar.title("📊 Controls")
refresh = st.sidebar.button("🔄 Refresh Data")
if refresh:
    st.cache_data.clear()
    st.rerun()

st.subheader("Current State of the NHS")
col1, col2, col3, col4 = st.columns(4)
latest = df.iloc[-1]
col1.metric("Latest A&E Attendances", f"{latest['ae_attendances']:,.0f}")
col2.metric("Waiting List (Total)", f"{latest['waiting_list_total']:,.0f}")
col3.metric("Bed Occupancy (mean)", f"{latest['bed_occupancy_rate']:.1f}%")
col4.metric("Staff Sickness", f"{latest['staff_sickness_rate']:.1f}%")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Trends", "🔍 Analysis", "🔮 Forecast", "🧪 Scenario Simulator",
    "🧠 Advanced Analytics", "📄 Executive Report"
])

with tab1:
    st.subheader("A&E Attendances Over Time")
    fig = px.line(df, x="month", y="ae_attendances", title="Monthly A&E Attendances (2010–2026)")
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Seasonality – Average A&E Attendances by Month")
    fig2 = px.bar(seasonality, x=seasonality.index, y=seasonality.values,
                  title="Average A&E Attendances by Month")
    fig2.update_layout(template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

with tab2:
    st.subheader("Correlation Between NHS Indicators")
    fig3 = px.imshow(corr, text_auto=True, aspect="auto",
                     title="Correlation Matrix", color_continuous_scale="RdBu_r")
    fig3.update_layout(template="plotly_dark")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Summary Statistics")
    st.dataframe(summary.style.format("{:.2f}"))

with tab3:
    st.subheader("SARIMA Forecast – Next 6 Months with Exogenous Variables")
    if sarima is not None:
        sarima_forecast = sarima["forecast_df"]
        actual = df[["month", "ae_attendances"]].rename(columns={"ae_attendances": "value"})
        actual["type"] = "Actual"
        sarima_df = sarima_forecast.reset_index().rename(columns={"index": "month", "forecasted_ae_attendances": "value"})
        sarima_df["type"] = "SARIMA Forecast"
        combined = pd.concat([actual, sarima_df[["month", "value", "type"]]], ignore_index=True)
        fig4 = px.line(combined, x="month", y="value", color="type",
                       title="A&E Attendances: Actual vs SARIMA Forecast")
        fig4.update_layout(template="plotly_dark")
        st.plotly_chart(fig4, use_container_width=True)
        st.subheader("SARIMA Model Metrics")
        st.json(sarima["metrics"])
        st.dataframe(sarima_forecast)
    else:
        st.warning("SARIMA forecast not available.")

    st.subheader("Monte Carlo Simulation – 12-Month Projection with Uncertainty")
    sim = monte["simulations"]
    mean_path = monte["mean_path"]
    lower_5 = monte["lower_5"]
    upper_95 = monte["upper_95"]
    fig_mc = go.Figure()
    fig_mc.add_trace(go.Scatter(x=df["month"], y=df["ae_attendances"], name="Historical", mode="lines"))
    fig_mc.add_trace(go.Scatter(x=mean_path.index, y=mean_path, name="Mean Projection", line=dict(dash="dash")))
    fig_mc.add_trace(go.Scatter(x=upper_95.index, y=upper_95, fill=None, mode="lines", line=dict(color="gray"), name="95th Percentile"))
    fig_mc.add_trace(go.Scatter(x=lower_5.index, y=lower_5, fill="tonexty", mode="lines", line=dict(color="gray"), name="5th Percentile"))
    fig_mc.update_layout(template="plotly_dark", title="Monte Carlo Simulation of A&E Attendances")
    st.plotly_chart(fig_mc, use_container_width=True)

with tab4:
    st.subheader("Scenario Simulator – Impact of Demand Growth")
    growth_rate = st.slider("Annual demand growth rate (%)", min_value=-5.0, max_value=10.0, value=2.0, step=0.5)
    latest_value = df["ae_attendances"].iloc[-1]
    months = 12
    future_months = pd.date_range(start=df["month"].max() + pd.DateOffset(months=1), periods=months, freq="ME")
    scenario_values = [latest_value * (1 + growth_rate / 100 / 12) ** i for i in range(1, months + 1)]
    scenario_df = pd.DataFrame({"month": future_months, "projected_ae_attendances": scenario_values})
    fig5 = px.line(scenario_df, x="month", y="projected_ae_attendances",
                   title=f"Scenario: {growth_rate:.1f}% Annual Growth")
    fig5.update_layout(template="plotly_dark")
    st.plotly_chart(fig5, use_container_width=True)
    peak = scenario_df["projected_ae_attendances"].max()
    st.info(f"Peak projected A&E attendances in next 12 months: **{peak:,.0f}**")

with tab5:
    st.subheader("Time Series Decomposition")
    decomp = decompose_series(df, "ae_attendances", period=12)
    fig_decomp = go.Figure()
    fig_decomp.add_trace(go.Scatter(x=decomp["original"].index, y=decomp["original"], name="Original"))
    fig_decomp.add_trace(go.Scatter(x=decomp["trend"].index, y=decomp["trend"], name="Trend"))
    fig_decomp.add_trace(go.Scatter(x=decomp["seasonal"].index, y=decomp["seasonal"], name="Seasonal"))
    fig_decomp.add_trace(go.Scatter(x=decomp["residual"].index, y=decomp["residual"], name="Residual"))
    fig_decomp.update_layout(template="plotly_dark", title="A&E Attendances Decomposition")
    st.plotly_chart(fig_decomp, use_container_width=True)

    st.subheader("Stationarity Tests")
    stat_results = test_stationarity(decomp["original"])
    st.json(stat_results)

    st.subheader("Granger Causality: Sickness → A&E Pressure")
    causal = test_granger_causality(df, "staff_sickness_rate", "ae_attendances", max_lag=4)
    st.json(causal)

with tab6:
    st.subheader("Executive Summary")
    if st.button("Generate AI Briefing"):
        with st.spinner("Generating AI briefing..."):
            latest_vals = {
                "ae_attendances": latest["ae_attendances"],
                "waiting_list_total": latest["waiting_list_total"],
                "bed_occupancy_rate": latest["bed_occupancy_rate"],
                "staff_sickness_rate": latest["staff_sickness_rate"]
            }
            ai_summary = generate_executive_summary(eda, sarima["metrics"], latest_vals)
            st.session_state["ai_summary"] = ai_summary
    if "ai_summary" in st.session_state:
        st.markdown(st.session_state["ai_summary"])

    st.markdown(f"""
    ### NHS FlowSight – Executive Briefing
    **Date:** {datetime.now().strftime('%d %B %Y')}

    #### Key Findings
    - **A&E Demand:** Average monthly A&E attendances are **{summary.loc['ae_attendances', 'mean']:,.0f}** (range: **{summary.loc['ae_attendances', 'min']:,.0f}** to **{summary.loc['ae_attendances', 'max']:,.0f}**).
    - **Waiting List:** Total waiting list currently stands at **{latest['waiting_list_total']:,.0f}** patients.
    - **Staff Sickness:** Average sickness rate is **{summary.loc['staff_sickness_rate', 'mean']:.1f}%**, with maximum **{summary.loc['staff_sickness_rate', 'max']:.1f}%**.
    - **Bed Occupancy:** Average occupancy is **{summary.loc['bed_occupancy_rate', 'mean']:.1f}%**, near the safe threshold of 85%.

    #### Forecast Outlook
    SARIMA forecast projects A&E attendances to reach **{sarima['forecast_df']['forecasted_ae_attendances'].iloc[-1]:,.0f}** in 6 months. Monte Carlo simulation suggests a 5th-95th percentile range of **{monte['lower_5'].iloc[-1]:,.0f} to {monte['upper_95'].iloc[-1]:,.0f}**.

    #### Methodology
    Data sourced from NHS England (A&E, ambulance, RTT) and ONS (employment). Time series decomposition, SARIMA forecasting, Granger causality, and Monte Carlo simulation were used.
    """)