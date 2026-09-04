import sys
from pathlib import Path

# Add the app folder to Python's search path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from fastapi import FastAPI, HTTPException, Header, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import Optional
import sqlite3
import hashlib
import secrets
import uuid

from jose import jwt, JWTError
from pydantic import BaseModel

from app.analysis.eda import run_eda
from app.forecast.sarima_model import run_sarima_forecast
from app.forecast.monte_carlo import monte_carlo_ae

app = FastAPI(title="NHS FlowSight API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "NhsFlowSight_9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

DB_PATH = "nhs_users.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            plan TEXT DEFAULT 'free',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return salt + ":" + hashlib.sha256((salt + password).encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    try:
        salt, stored_hash = hashed.split(":", 1)
        return hashlib.sha256((salt + plain).encode()).hexdigest() == stored_hash
    except:
        return False

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(row)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/summary")
def get_summary():
    eda = run_eda()
    if not eda or "summary" not in eda:
        return {"error": "Data unavailable"}
    return eda["summary"].to_dict()

@app.get("/api/sarima-forecast")
def get_sarima_forecast():
    eda = run_eda()
    if not eda or "data" not in eda:
        return {"error": "Data unavailable"}
    result = run_sarima_forecast(eda["data"])
    return {
        "forecast": result["forecast_df"].to_dict(orient="records"),
        "metrics": result["metrics"],
        "order": result["order"],
        "seasonal_order": result["seasonal_order"]
    }

@app.get("/api/monte-carlo")
def get_monte_carlo():
    eda = run_eda()
    if not eda or "data" not in eda:
        return {"error": "Data unavailable"}
    mc = monte_carlo_ae(eda["data"], n_simulations=500, periods=12)
    return {
        "mean_path": mc["mean_path"].to_dict(),
        "lower_5": mc["lower_5"].to_dict(),
        "upper_95": mc["upper_95"].to_dict()
    }

@app.post("/signup")
def signup(email: str = Form(...), password: str = Form(...)):
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    api_key = f"nhs-{uuid.uuid4().hex[:24]}"
    hashed_pw = hash_password(password)
    conn.execute("INSERT INTO users (email, hashed_password, api_key, plan, created_at) VALUES (?, ?, ?, 'free', ?)",
                 (email, hashed_pw, api_key, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return {"message": "Account created", "api_key": api_key}

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if not row or not verify_password(password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = dict(row)
    access_token = create_access_token(data={"sub": str(user["id"])})
    return {"access_token": access_token, "token_type": "bearer", "api_key": user["api_key"]}

@app.get("/api/me")
def me(user: dict = Depends(get_current_user)):
    return {"email": user["email"], "plan": user["plan"], "api_key": user["api_key"]}
