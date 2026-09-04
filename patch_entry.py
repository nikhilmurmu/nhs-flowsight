# patch_entry.py
path = 'entry.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('from pydantic import BaseModel', 'from pydantic import BaseModel\nfrom functools import lru_cache')

old_summary = '''@app.get("/api/summary")
def get_summary():
    eda = run_eda()
    if not eda or "summary" not in eda:
        return {"error": "Data unavailable"}
    return eda["summary"].to_dict()'''

new_summary = '''@lru_cache(maxsize=1)
def get_eda_cached():
    return run_eda()

@app.get("/api/summary")
def get_summary():
    try:
        eda = get_eda_cached()
        if not eda or "summary" not in eda:
            return {"error": "Data unavailable"}
        return eda["summary"].to_dict()
    except Exception as e:
        return {"error": str(e)}'''

content = content.replace(old_summary, new_summary)

old_sarima = '''@app.get("/api/sarima-forecast")
def get_sarima_forecast():
    eda = run_eda()
    if not eda or "data" not in eda:
        return {"error": "Data unavailable"}
    result = run_sarima_forecast(eda["data"])'''

new_sarima = '''@app.get("/api/sarima-forecast")
def get_sarima_forecast():
    try:
        eda = get_eda_cached()
        if not eda or "data" not in eda:
            return {"error": "Data unavailable"}
        result = run_sarima_forecast(eda["data"])'''

content = content.replace(old_sarima, new_sarima)

old_monte = '''@app.get("/api/monte-carlo")
def get_monte_carlo():
    eda = run_eda()
    if not eda or "data" not in eda:
        return {"error": "Data unavailable"}
    mc = monte_carlo_ae(eda["data"], n_simulations=500, periods=12)'''

new_monte = '''@app.get("/api/monte-carlo")
def get_monte_carlo():
    try:
        eda = get_eda_cached()
        if not eda or "data" not in eda:
            return {"error": "Data unavailable"}
        mc = monte_carlo_ae(eda["data"], n_simulations=500, periods=12)'''

content = content.replace(old_monte, new_monte)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('entry.py patched with caching and error handling.')
