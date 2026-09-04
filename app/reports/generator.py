import os
from datetime import datetime
from groq import Groq

def generate_executive_summary(eda_results, sarima_metrics, latest_values):
    """Generate an AI-written executive summary using Groq."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "AI summary unavailable – GROQ_API_KEY not set."
    client = Groq(api_key=api_key)
    
    prompt = f"""
You are a senior NHS analyst. Write a concise executive summary (150-200 words) based on these findings:

- Latest A&E attendances: {latest_values.get('ae_attendances', 'N/A'):,.0f}
- Total waiting list: {latest_values.get('waiting_list_total', 'N/A'):,.0f}
- Bed occupancy rate: {latest_values.get('bed_occupancy_rate', 'N/A'):.1f}%
- Staff sickness rate: {latest_values.get('staff_sickness_rate', 'N/A'):.1f}%
- SARIMA forecast RMSE: {sarima_metrics.get('RMSE', 'N/A'):,.0f}
- Forecast MAPE: {sarima_metrics.get('MAPE', 'N/A'):.2f}%

Write this in the style of a board-level briefing. Include:
1. A one-sentence overview.
2. Two key risks.
3. One recommendation.

Return only the summary text.
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"AI summary failed: {e}"
