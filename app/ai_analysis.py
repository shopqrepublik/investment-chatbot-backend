import os
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import pearsonr
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class PortfolioAIAnalyzer:
    def __init__(self, portfolio: list[dict], total_value: float = 10000.0):
        self.portfolio = portfolio
        self.total_value = total_value

    async def calculate_metrics(self):
        tickers = [item["ticker"] for item in self.portfolio]
        prices = yf.download(tickers, period="6mo")["Adj Close"].dropna()
        returns = prices.pct_change().dropna()

        metrics = {
            "mean_return": float(returns.mean().mean() * 100),
            "volatility": float(returns.std().mean() * 100),
            "sharpe_ratio": float((returns.mean().mean() / returns.std().mean()) * np.sqrt(252)),
            "correlation": float(pearsonr(returns.iloc[:, 0], returns.mean(axis=1))[0])
        }
        return metrics

    async def generate_ai_report(self, metrics):
        prompt = f"""
        You are an investment analyst. Analyze the following portfolio metrics:
        Expected return: {metrics['mean_return']:.2f}%
        Volatility: {metrics['volatility']:.2f}%
        Sharpe Ratio: {metrics['sharpe_ratio']:.2f}
        Correlation Index: {metrics['correlation']:.2f}

        Provide:
        1. Risk assessment (short paragraph)
        2. Key strengths of the portfolio
        3. Potential weaknesses
        4. AI recommendation for optimization
        """

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    async def run_full_analysis(self):
        metrics = await self.calculate_metrics()
        ai_text = await self.generate_ai_report(metrics)
        return {"metrics": metrics, "ai_analysis": ai_text}
