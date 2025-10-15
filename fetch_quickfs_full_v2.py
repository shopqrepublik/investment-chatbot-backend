import aiohttp
import asyncio
import pandas as pd
import sqlite3
import time
from bs4 import BeautifulSoup
import requests
import json
import os
from tqdm.asyncio import tqdm_asyncio

API_KEY = "c6fc36020c3d904fde9589b44a1d614497969f77"
BASE_URL = "https://public-api.quickfs.net/v1/data/all/"
OUTPUT_CSV = "quickfs_fundamentals.csv"
OUTPUT_DB = "quickfs_data.db"
REPORT_FILE = "sector_report.csv"
PROGRESS_FILE = "quickfs_progress.json"
CONCURRENT_LIMIT = 5

# === Какие метрики сохраняем ===
SELECTED_METRICS = [
    "revenue",
    "net_income",
    "eps_diluted",
    "pe_ratio",
    "roic",
    "roe"
]

# ======================================================
# 🧩 1. Получаем тикеры S&P500 и NASDAQ100
# ======================================================
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    html = requests.get(url).text
    df = pd.read_html(html)[0]
    df["Symbol"] = df["Symbol"].str.replace(".", "-", regex=False)
    return df[["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]]

def get_nasdaq_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    html = requests.get(url).text
    df = pd.read_html(html)[3]
    df.rename(columns={"Ticker": "Symbol", "Company": "Security"}, inplace=True)
    df["GICS Sector"] = "Technology (assumed)"
    df["GICS Sub-Industry"] = "N/A"
    return df[["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]]

# ======================================================
# ⚙️ 2. Асинхронная загрузка данных из QuickFS
# ======================================================
async def fetch_ticker(session, ticker):
    url = f"{BASE_URL}{ticker}.US?api_key={API_KEY}"
    try:
        async with session.get(url, timeout=25) as response:
            if response.status == 200:
                data = await response.json()
                return ticker, data.get("data", {})
            else:
                return ticker, None
    except Exception as e:
        print(f"⚠️ Error fetching {ticker}: {e}")
        return ticker, None

# ======================================================
# 🧮 3. Преобразуем JSON в плоскую таблицу
# ======================================================
def normalize_data(ticker, sector, sub_industry, company, data):
    records = []
    for metric, values in data.items():
        if metric not in SELECTED_METRICS:
            continue
        for year, val in values.items():
            records.append({
                "ticker": ticker,
                "company": company,
                "sector": sector,
                "sub_industry": sub_industry,
                "year": int(year),
                "metric": metric,
                "value": val
            })
    return records

# ======================================================
# 💾 4. Сохранение данных
# ======================================================
def save_data(df):
    df.to_csv(OUTPUT_CSV, index=False)
    conn = sqlite3.connect(OUTPUT_DB)
    df.to_sql("fundamentals", conn, if_exists="replace", index=False)
    conn.close()

# ======================================================
# 📊 5. Отчёт по секторам
# ======================================================
def generate_sector_report(df):
    pivot = df.pivot_table(
        index=["sector", "year"],
        columns="metric",
        values="value",
        aggfunc="mean"
    ).reset_index()

    pivot.to_csv(REPORT_FILE, index=False)
    print(f"📈 Sector report saved to {REPORT_FILE}")

# ======================================================
# 🚀 6. Основная логика
# ======================================================
async def main():
    sp500 = get_sp500_tickers()
    nasdaq = get_nasdaq_tickers()

    all_tickers_df = pd.concat([sp500, nasdaq]).drop_duplicates(subset=["Symbol"])
    all_tickers = all_tickers_df["Symbol"].tolist()
    print(f"📊 Total tickers to fetch: {len(all_tickers)}")

    # Resume
    fetched = set()
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            fetched = set(json.load(f))

    all_records = []
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    total = len(all_tickers)

    async with aiohttp.ClientSession() as session:
        async def fetch_with_limit(row):
            async with semaphore:
                ticker = row["Symbol"]
                sector = row["GICS Sector"]
                sub_industry = row["GICS Sub-Industry"]
                company = row["Security"]

                ticker, data = await fetch_ticker(session, ticker)
                if data:
                    return normalize_data(ticker, sector, sub_industry, company, data)
                else:
                    return []

        remaining = [r for _, r in all_tickers_df.iterrows() if r["Symbol"] not in fetched]
        print(f"▶️ Starting {len(remaining)} remaining tickers...")

        results = []
        for chunk_start in range(0, len(remaining), CONCURRENT_LIMIT * 2):
            chunk = remaining[chunk_start:chunk_start + CONCURRENT_LIMIT * 2]
            results_chunk = await tqdm_asyncio.gather(*[fetch_with_limit(r) for r in chunk])
            for res in results_chunk:
                all_records.extend(res)
            fetched.update([r["Symbol"] for r in chunk])
            progress = len(fetched) / total * 100
            print(f"💾 Progress saved: {len(fetched)}/{total} ({progress:.1f}%)")
            df = pd.DataFrame(all_records)
            df.to_csv(OUTPUT_CSV, index=False)
            with open(PROGRESS_FILE, "w") as f:
                json.dump(list(fetched), f)
            await asyncio.sleep(1.0)

    df = pd.DataFrame(all_records)
    save_data(df)
    generate_sector_report(df)
    print(f"\n✅ All data saved to {OUTPUT_DB} and {OUTPUT_CSV}")
    print(f"📈 Total records: {len(df)}")

# ======================================================
# 🏁 Запуск
# ======================================================
if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())
    print(f"⏱️ Finished in {(time.time() - start_time) / 60:.1f} minutes.")
