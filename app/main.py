# app/main.py
import os
import sqlite3
import math
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import List, Dict, Any

import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────────────
# Конфиг
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()
DB_PATH = os.getenv("DB_PATH", "investment_bot.db")

WEIGHTS = {
    "trend_slope": 0.25,
    "momentum_20": 0.20,
    "rsi_quality": 0.15,
    "macd_quality": 0.15,
    "low_volatility": 0.10,
    "low_drawdown": 0.10,
    "recent_strength": 0.05,
}

UNIVERSE_LIMIT = int(os.getenv("UNIVERSE_LIMIT", "300"))
MIN_BARS = int(os.getenv("MIN_BARS", "120"))
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "400"))

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Investment Chatbot API", version="3.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────────
# Модели
# ──────────────────────────────────────────────────────────────────────────────
class PortfolioQuizAnswers(BaseModel):
    horizon: str
    risk_level: str
    investment_priority: str
    amount: str
    diversification: str

class AlpacaOrder(BaseModel):
    ticker: str
    amount: float

# ──────────────────────────────────────────────────────────────────────────────
# DB helpers
# ──────────────────────────────────────────────────────────────────────────────
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def fetch_universe(limit=UNIVERSE_LIMIT) -> List[str]:
    with get_db() as c:
        q = "SELECT DISTINCT ticker FROM prices ORDER BY ticker LIMIT ?"
        return [r[0] for r in c.execute(q, (limit,)).fetchall()]

def fetch_prices(tickers: List[str]) -> pd.DataFrame:
    since = (datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    with get_db() as c:
        q = f"""
            SELECT ticker, date, close
            FROM prices
            WHERE ticker IN ({','.join('?' * len(tickers))}) AND date >= ?
            ORDER BY ticker, date
        """
        rows = c.execute(q, (*tickers, since)).fetchall()
    df = pd.DataFrame(rows, columns=["ticker", "date", "close"])
    df["date"] = pd.to_datetime(df["date"])
    return df

# ──────────────────────────────────────────────────────────────────────────────
# Индикаторы
# ──────────────────────────────────────────────────────────────────────────────
def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(up, index=series.index).rolling(period).mean()
    roll_down = pd.Series(down, index=series.index).rolling(period).mean()
    rs = roll_up / (roll_down + 1e-9)
    return 100.0 - (100.0 / (1.0 + rs))

def macd(series: pd.Series, fast=12, slow=26, signal=9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    return macd_line, signal_line, macd_line - signal_line

def annualized_vol(close: pd.Series, window=30) -> float:
    returns = close.pct_change()
    vol = returns.rolling(window).std().iloc[-1]
    return float(vol * np.sqrt(252)) if not pd.isna(vol) else np.nan

def max_drawdown(close: pd.Series, window=90) -> float:
    roll_max = close.rolling(window).max()
    dd = (close / roll_max) - 1.0
    return float(dd.min())

def trend_slope(close: pd.Series, window=90) -> float:
    s = close.tail(window)
    if len(s) < 10:
        return np.nan
    y = np.log(s.values)
    x = np.arange(len(s))
    slope, _ = np.polyfit(x, y, 1)
    return float(slope * 252)

def recent_strength(close: pd.Series) -> float:
    r = close.pct_change().tail(5)
    return float((r > 0).sum() / len(r)) if not r.empty else np.nan

def momentum(close: pd.Series, window=20) -> float:
    if len(close) < window + 1:
        return np.nan
    return float((close.iloc[-1] / close.iloc[-window]) - 1.0)

# ──────────────────────────────────────────────────────────────────────────────
# Скоуринг
# ──────────────────────────────────────────────────────────────────────────────
def zscore(series: pd.Series) -> pd.Series:
    return (series - series.mean()) / (series.std() + 1e-9)

def build_scores(ind_df: pd.DataFrame) -> pd.DataFrame:
    df = ind_df.copy()
    df["z_trend"] = zscore(df["trend_slope"])
    df["z_mom20"] = zscore(df["mom20"])
    df["z_rsiQ"] = zscore(1.0 - (np.abs(df["rsi"] - 55.0) / 55.0))
    df["z_macdQ"] = zscore((df["macd_above_sig"].astype(float) + df["macd_above_zero"].astype(float)) / 2.0)
    df["z_lowVol"] = -zscore(df["vol30"])
    df["z_lowDD"] = -zscore(-df["dd90"])
    df["z_rstrength"] = zscore(df["recent_strength"])
    df["score"] = (
        WEIGHTS["trend_slope"] * df["z_trend"]
        + WEIGHTS["momentum_20"] * df["z_mom20"]
        + WEIGHTS["rsi_quality"] * df["z_rsiQ"]
        + WEIGHTS["macd_quality"] * df["z_macdQ"]
        + WEIGHTS["low_volatility"] * df["z_lowVol"]
        + WEIGHTS["low_drawdown"] * df["z_lowDD"]
        + WEIGHTS["recent_strength"] * df["z_rstrength"]
    )
    return df

# ──────────────────────────────────────────────────────────────────────────────
# Портфель
# ──────────────────────────────────────────────────────────────────────────────
LATEST_PORTFOLIO: Dict[str, Any] = {}

def picks_by_preferences(risk: str, diversification: str, pool: pd.DataFrame) -> int:
    base = {"concentrated": 3, "balanced": 5, "full": 8}.get(diversification, 5)
    if risk == "low":
        base = max(4, base + 1)
    elif risk == "high":
        base = max(3, base - 1)
    return int(base)

def risk_filters(risk: str, df: pd.DataFrame) -> pd.DataFrame:
    res = df.copy()
    if risk == "low":
        res = res[(res["vol30"] < res["vol30"].median()) & (res["dd90"] > -0.25)]
    elif risk == "high":
        res = res[(res["dd90"] > -0.6)]
    return res

# ──────────────────────────────────────────────────────────────────────────────
# API endpoints
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/api/v1/portfolio/generate")
def generate_portfolio(req: PortfolioQuizAnswers):
    print("🧩 Generating portfolio:", req.dict())
    universe = fetch_universe(limit=UNIVERSE_LIMIT)
    if not universe:
        raise HTTPException(404, "В базе нет доступных тикеров")

    prices = fetch_prices(universe)
    if prices.empty:
        raise HTTPException(404, "Нет цен в БД")

    ind_rows = []
    for t, g in prices.groupby("ticker"):
        close = g.sort_values("date")["close"].astype(float)
        if len(close) < MIN_BARS:
            continue
        rsi14 = rsi(close, 14).iloc[-1]
        macd_line, macd_sig, _ = macd(close)
        vol30 = annualized_vol(close, 30)
        dd90 = max_drawdown(close, 90)
        mom20 = momentum(close, 20)
        slope = trend_slope(close, 90)
        rstrength = recent_strength(close)
        ind_rows.append({
            "ticker": t,
            "price": float(close.iloc[-1]),
            "rsi": float(rsi14),
            "macd": float(macd_line.iloc[-1]),
            "macd_signal": float(macd_sig.iloc[-1]),
            "macd_above_sig": macd_line.iloc[-1] > macd_sig.iloc[-1],
            "macd_above_zero": macd_line.iloc[-1] > 0,
            "vol30": float(vol30),
            "dd90": float(dd90),
            "mom20": float(mom20),
            "trend_slope": float(slope),
            "recent_strength": float(rstrength),
        })

    if not ind_rows:
        raise HTTPException(500, "Недостаточно данных для индикаторов")

    scored = build_scores(pd.DataFrame(ind_rows)).dropna()
    scored = risk_filters(req.risk_level.lower(), scored)
    top_n = picks_by_preferences(req.risk_level.lower(), req.diversification.lower(), scored)
    top = scored.sort_values("score", ascending=False).head(top_n).reset_index(drop=True)

    eps = 1e-6
    weights = np.clip(top["score"] - top["score"].min() + eps, eps, None)
    weights = weights / weights.sum()

    recommended_assets = []
    for i, row in top.iterrows():
        recommended_assets.append({
            "ticker": row["ticker"],
            "allocation_pct": round(float(weights.iloc[i] * 100.0), 2),
            "ai_score": round(float(row["score"]), 3),
        })

    summary = {
        "assets_analyzed": int(len(scored)),
        "recommended": int(len(recommended_assets)),
        "avg_score": round(float(top["score"].mean()), 3),
    }

    result = {
        "recommended_assets": recommended_assets,
        "summary": summary,
        "timestamp": datetime.utcnow().isoformat()
    }

    LATEST_PORTFOLIO["last"] = result
    print(f"✅ Portfolio generated. Picked {len(recommended_assets)} / analyzed {len(scored)}")
    return result

@app.get("/api/v1/portfolio/latest")
def get_latest_portfolio():
    if "last" not in LATEST_PORTFOLIO:
        raise HTTPException(404, "Портфель ещё не создан")
    return LATEST_PORTFOLIO["last"]

@app.get("/api/v1/health")
def health():
    try:
        with get_db() as c:
            t = c.execute("SELECT COUNT(DISTINCT ticker) FROM prices").fetchone()[0]
            rows = c.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
        return {"status": "ok", "tickers": int(t), "rows": int(rows)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# ──────────────────────────────────────────────────────────────────────────────
# Middleware: гарантируем JSON на /api/*
# ──────────────────────────────────────────────────────────────────────────────
@app.middleware("http")
async def ensure_json_for_api(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        try:
            response = await call_next(request)
            if response.media_type and "html" in response.media_type.lower():
                return JSONResponse(
                    {"error": "Invalid response type", "message": "Expected JSON, got HTML"},
                    status_code=500
                )
            return response
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    return await call_next(request)

# ──────────────────────────────────────────────────────────────────────────────
# Frontend fallback (если билд фронта лежит рядом)
# ──────────────────────────────────────────────────────────────────────────────
if os.path.exists("frontend/dist"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        index_path = os.path.join("frontend", "dist", "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return JSONResponse({"error": "Frontend not found"}, status_code=404)
