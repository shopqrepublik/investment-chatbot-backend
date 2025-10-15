# app/analysis/regime_detector.py
import pandas as pd
import numpy as np
from typing import Dict

def detect_market_regime(spy_series: pd.Series) -> Dict[str, any]:
    """Enhanced market regime detection"""
    s = spy_series.dropna()
    
    if len(s) < 220:
        return {"regime": "neutral", "confidence": 0.4, "trend": "insufficient_data"}
    
    # Moving averages
    ma_50 = s.rolling(50).mean().iloc[-1]
    ma_200 = s.rolling(200).mean().iloc[-1]
    
    # Volatility
    returns = s.pct_change().dropna()
    vol_30d = returns.tail(30).std() * np.sqrt(252)
    vol_252d = returns.std() * np.sqrt(252)
    
    # Trend strength
    trend_strength = (ma_50 / ma_200 - 1) * 100
    
    # Regime determination
    if trend_strength > 2 and vol_30d < 0.18:
        return {"regime": "bull_calm", "confidence": 0.8, "trend_strength": trend_strength}
    elif trend_strength > 2 and vol_30d >= 0.18:
        return {"regime": "bull_volatile", "confidence": 0.7, "trend_strength": trend_strength}
    elif trend_strength < -2 and vol_30d > 0.22:
        return {"regime": "bear_volatile", "confidence": 0.75, "trend_strength": trend_strength}
    elif trend_strength < -2:
        return {"regime": "bear_calm", "confidence": 0.65, "trend_strength": trend_strength}
    else:
        return {"regime": "sideways", "confidence": 0.6, "trend_strength": trend_strength}