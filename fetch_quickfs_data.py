import aiohttp
import asyncio
import pandas as pd
import sqlite3
import time
from bs4 import BeautifulSoup
import requests
import json
import os

API_KEY = "c6fc36020c3d904fde9589b44a1d614497969f77"
BASE_URL = "https://public-api.quickfs.net/v1/data/all/"
OUTPUT_CSV = "quickfs_fundamentals.csv"
OUTPUT_DB = "quickfs_data.db"
PROGRESS_FILE = "quickfs_progress.json"

# ======================================================
# 🧩 1. Получение тикеров S&P 500 и NASDAQ 100
# ======================================================
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    html = requests.get(url).text
    df = pd.read_html(html)[0]
    return sorted(df["Symbol"].unique().tolist())

def get_nasdaq_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    html = requests.get(url).text
    df = pd.read_html(html)[3]
    return sorted(df["Ticker"].unique().tolist())

# ======================================================
# ⚙️ 2. Асинхронная загрузка данных из QuickFS
# ======================================================
async def fetch_ticker(session, ticker):
    url = f"{BASE_URL}{ticker}.US?api_key={API_KEY}"
    try:
        async with session.get(url, timeout=20) as response:
            if response.status == 200:
                data = await response.json()
                return ticker, data.get("data", {})
            else:
                return ticker, None
    except Exception as e:
        print(f"⚠️ Error fetching {ticker}: {e}")
        return ticker, None

# ======================================================
# 🧮 3. Преобразование данных в плоскую структуру
# ======================================================
def normalize_data(ticker, data):
    records = []
    for metric, values in data.items():
        for year, val in values.items():
            records.append({
                "ticker": ticker,
                "year": int(year),
                "metric": metric,
                "value": val
            })
    return records

# ======================================================
# 💾 4. Сохранение данных в CSV и SQLite
# ======================================================
def save_data(df):
    df.to_csv(OUTPUT_CSV, index=False)
    conn = sqlite3.connect(OUTPUT_DB)
    df.to_sql("fundamentals", conn, if_exists="replace", index=False)
    conn.close()

# ======================================================
# 🚀 5. Основная логика
# ======================================================
async def main():
    sp500 = get_sp500_tickers()
    nasdaq = get_nasdaq_tickers()
    all_tickers = sorted(set(sp500 + nasdaq))
    print(f"📊 Total tickers to fetch: {len(all_tickers)}")

    # Resume support
    fetched = set()
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            fetched = set(json.load(f))

    all_records = []

    async with aiohttp.ClientSession() as session:
        for i, ticker in enumerate(all_tickers, 1):
            if ticker in fetched:
                print(f"⏭️ Skipping {ticker} (already fetched)")
                continue

            print(f"[{i}/{len(all_tickers)}] ⬇️ Downloading {ticker} ...")
            t0 = time.time()

            ticker, data = await fetch_ticker(session, ticker)
            if data:
                records = normalize_data(ticker, data)
                all_records.extend(records)
                print(f"✅ {ticker}: {len(records)} records ({time.time()-t0:.1f}s)")

                # Save progress every 10 tickers
                if i % 10 == 0:
                    pd.DataFrame(all_records).to_csv(OUTPUT_CSV, index=False)
                    with open(PROGRESS_FILE, "w") as f:
                        json.dump(list(fetched | {ticker}), f)
                    print("💾 Progress saved.")

            await asyncio.sleep(0.8)  # respect rate limit

    # Final save
    df = pd.DataFrame(all_records)
    save_data(df)
    print(f"✅ All data saved to {OUTPUT_DB} and {OUTPUT_CSV}")

if __name__ == "__main__":
    asyncio.run(main())
