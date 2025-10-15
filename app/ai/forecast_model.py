import numpy as np
import pandas as pd
import sqlite3
from sklearn.linear_model import LinearRegression
from prophet import Prophet
import warnings
import os
from datetime import datetime

warnings.filterwarnings("ignore", category=RuntimeWarning)


class GrowthForecaster:
    """
    GrowthForecaster — AI-модуль прогнозирования роста акций.
    Использует Prophet (временные ряды) или Linear Regression (fallback).
    """

    def __init__(self, db_path: str = "investment_bot.db"):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        self.conn = sqlite3.connect(self.db_path)

    def update_prices(self):
        """Заглушка для обновления данных — можно подключить EOD API или QuickFS."""
        print("⚙️ update_prices() not implemented — future feature")

    # ------------------------------------------------------------------
    def predict_growth(self, ticker: str, horizon_days: int = 90):
        """
        Прогнозирует рост для заданного тикера на основе временного ряда.
        Сначала пытается Prophet, если не удаётся — Linear Regression.
        """

        base = ticker.upper().replace(".US", "")
        possible_names = [base, f"{base}.US", f"{base}.NYSE", f"{base}.NASDAQ"]

        df = None
        for name in possible_names:
            try:
                q = f"SELECT date, close FROM prices WHERE ticker='{name}' ORDER BY date ASC"
                temp = pd.read_sql(q, self.conn)
                if len(temp) > 50:
                    df = temp
                    ticker = name
                    break
            except Exception as e:
                print(f"⚠️ Ошибка при чтении {name}: {e}")
                continue

        if df is None or len(df) < 50:
            return {
                "ticker": ticker,
                "predicted_growth_%": None,
                "confidence": 0,
                "note": "Not enough data"
            }

        # === Prophet try ===
        try:
            df_prophet = df.rename(columns={"date": "ds", "close": "y"})
            df_prophet["ds"] = pd.to_datetime(df_prophet["ds"])

            model = Prophet(
                yearly_seasonality=False,
                weekly_seasonality=False,
                daily_seasonality=False,
                changepoint_prior_scale=0.1
            )
            model.fit(df_prophet)

            future = model.make_future_dataframe(periods=horizon_days)
            forecast = model.predict(future)

            last_real = df_prophet["y"].iloc[-1]
            last_pred = forecast["yhat"].iloc[-1]

            if last_real == 0 or not np.isfinite(last_real):
                growth = 0.0
            else:
                growth = (last_pred - last_real) / last_real * 100

            if not np.isfinite(growth):
                growth = 0.0

            confidence = float(np.clip(model.params["delta"].std(), 0, 1))
            print(f"🔮 {ticker}: Prophet forecast +{growth:.2f}%")

            return {
                "ticker": ticker,
                "predicted_growth_%": round(float(growth), 2),
                "confidence": round(confidence, 2),
                "note": "Prophet forecast (time-series model)"
            }

        except Exception as e:
            print(f"⚠️ Prophet failed for {ticker}: {e}")
            # fallback на линейную регрессию
            return self._predict_linear(df, ticker, horizon_days)

    # ------------------------------------------------------------------
    def _predict_linear(self, df: pd.DataFrame, ticker: str, horizon_days: int = 90):
        """Fallback: простая линейная регрессия."""

        df["t"] = np.arange(len(df))
        X, y = df[["t"]], df["close"]

        try:
            model = LinearRegression().fit(X, y)
            future_days = np.arange(len(df), len(df) + horizon_days).reshape(-1, 1)
            preds = model.predict(future_days)

            if y.iloc[-1] == 0 or not np.isfinite(y.iloc[-1]):
                growth = 0.0
            else:
                growth = (preds[-1] - y.iloc[-1]) / y.iloc[-1] * 100

            if not np.isfinite(growth):
                growth = 0.0

            confidence = min(1.0, abs(model.coef_[0]) / (np.mean(df["close"]) * 0.01))
            print(f"✅ {ticker}: {len(df)} rows, {df['date'].iloc[-1]}, LR forecast +{growth:.2f}%")

            return {
                "ticker": ticker,
                "predicted_growth_%": round(float(growth), 2),
                "confidence": round(float(confidence), 2),
                "note": "Linear regression forecast (fallback)"
            }

        except Exception as e:
            with open("forecast_errors.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] {ticker} — LinearRegression ERROR: {e}\n")

            print(f"❌ Ошибка при Linear Regression {ticker}: {e}")
            return {
                "ticker": ticker,
                "predicted_growth_%": None,
                "confidence": 0,
                "note": f"Linear regression error: {e}"
            }
