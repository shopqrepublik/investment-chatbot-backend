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

# === CONFIG ===
API_KEY = "c6fc36020c3d904fde9589b44a1d614497969f77"
BASE_URL = "https://public-api.quickfs.net/v1/data"
OUTPUT_CSV = "quickfs_fundamentals.csv"
OUTPUT_DB = "quickfs_data.db"
REPORT_FILE = "sector_report.csv"
PROGRESS_FILE = "quickfs_progress.json"
TICKERS_CACHE = "tickers_cache.json"
CONCURRENT_LIMIT = 5

# === Метрики, которые будем собирать ===
SELECTED_METRICS = [
    "revenue",
    "net_income",
    "eps_diluted",
    "pe_ratio",
    "roe",
    "roic"
]

# ======================================================
# 1️⃣ Получаем тикеры S&P500 и NASDAQ100 (с кешем)
# ======================================================
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers).text
    df = pd.read_html(str(BeautifulSoup(html, "html.parser").find("table", {"id": "constituents"})))[0]
    df["Symbol"] = df["Symbol"].str.replace(".", "-", regex=False)
    print(f"✅ S&P 500 tickers loaded: {len(df)}")
    return df[["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]]


def get_nasdaq_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(url, headers=headers).text
    tables = BeautifulSoup(html, "html.parser").find_all("table")
    for table in tables:
        df_tmp = pd.read_html(str(table))[0]
        if any(col in df_tmp.columns for col in ["Ticker", "Symbol", "Company", "Company name"]):
            df = df_tmp.copy()
            break
    df.columns = [c.strip() for c in df.columns]
    if "Ticker" in df.columns:
        df.rename(columns={"Ticker": "Symbol"}, inplace=True)
    name_col = next((c for c in ["Company", "Company name", "Security"] if c in df.columns), df.columns[1])
    df.rename(columns={name_col: "Security"}, inplace=True)
    df["GICS Sector"] = "Technology (assumed)"
    df["GICS Sub-Industry"] = "N/A"
    print(f"✅ NASDAQ 100 tickers loaded: {len(df)}")
    return df[["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]]


def load_tickers_with_cache():
    if os.path.exists(TICKERS_CACHE):
        with open(TICKERS_CACHE, "r") as f:
            tickers = json.load(f)
        print(f"📦 Loaded {len(tickers)} tickers from cache")
        return pd.DataFrame(tickers)
    sp500 = get_sp500_tickers()
    nasdaq = get_nasdaq_tickers()
    all_tickers_df = pd.concat([sp500, nasdaq]).drop_duplicates(subset=["Symbol"])
    tickers_list = all_tickers_df.to_dict(orient="records")
    with open(TICKERS_CACHE, "w") as f:
        json.dump(tickers_list, f, indent=2)
    print(f"💾 Cached {len(tickers_list)} tickers to {TICKERS_CACHE}")
    return all_tickers_df

# ======================================================
# 2️⃣ Асинхронная загрузка по каждой метрике
# ======================================================
async def fetch_metric(session, ticker, metric):
    url = f"{BASE_URL}/{ticker}.US/{metric}?api_key={API_KEY}"
    try:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                js = await response.json()
                if "data" in js and isinstance(js["data"], dict):
                    return metric, js["data"]
                else:
                    return metric, {}
            elif response.status == 429:
                print(f"⏳ Rate limit for {ticker}/{metric}, waiting 10s...")
                await asyncio.sleep(10)
                return await fetch_metric(session, ticker, metric)
            else:
                print(f"⚠️ {ticker}/{metric} returned HTTP {response.status}")
                return metric, {}
    except Exception as e:
        print(f"⚠️ Error fetching {ticker}/{metric}: {e}")
        return metric, {}

async def fetch_ticker(session, ticker):
    """Собирает все SELECTED_METRICS для одного тикера"""
    results = {}
    for metric in SELECTED_METRICS:
        m, data = await fetch_metric(session, ticker, metric)
        results[m] = data
    return results

# ======================================================
# 3️⃣ Преобразуем JSON в таблицу
# ======================================================
def normalize_data(ticker, sector, sub_industry, company, data):
    records = []
    for metric, values in data.items():
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
# 4️⃣ Сохранение данных
# ======================================================
def save_data(df):
    if df.empty:
        print("⚠️ Warning: DataFrame is empty, nothing to save.")
        return
    df.columns = [
        str(c).strip().replace(" ", "_").replace("(", "").replace(")", "").replace("%", "pct")
        if c not in (None, "") else f"col_{i}"
        for i, c in enumerate(df.columns)
    ]
    df.to_csv(OUTPUT_CSV, index=False)
    conn = sqlite3.connect(OUTPUT_DB)
    df.to_sql("fundamentals", conn, if_exists="replace", index=False)
    conn.close()
    print(f"💾 Saved {len(df)} rows to {OUTPUT_DB}")

# ======================================================
# 5️⃣ Отчёт по секторам
# ======================================================
def generate_sector_report(df):
    if df.empty:
        print("⚠️ Sector report skipped (empty DataFrame).")
        return
    pivot = df.pivot_table(index=["sector", "year"], columns="metric", values="value", aggfunc="mean").reset_index()
    pivot.to_csv(REPORT_FILE, index=False)
    print(f"📈 Sector report saved to {REPORT_FILE}")

# ======================================================
# 6️⃣ Основной процесс
# ======================================================
async def main():
    all_tickers_df = load_tickers_with_cache()
    all_tickers = all_tickers_df["Symbol"].tolist()
    print(f"📊 Total tickers to fetch: {len(all_tickers)}")

    all_records = []
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)

    async with aiohttp.ClientSession() as session:
        async def fetch_with_limit(row):
            async with semaphore:
                ticker = row["Symbol"]
                sector = row["GICS Sector"]
                sub_industry = row["GICS Sub-Industry"]
                company = row["Security"]
                data = await fetch_ticker(session, ticker)
                return normalize_data(ticker, sector, sub_industry, company, data)

        for chunk_start in range(0, len(all_tickers), CONCURRENT_LIMIT):
            chunk = all_tickers_df.iloc[chunk_start:chunk_start + CONCURRENT_LIMIT]
            results_chunk = await tqdm_asyncio.gather(*[fetch_with_limit(r) for _, r in chunk.iterrows()])
            for res in results_chunk:
                all_records.extend(res)
            print(f"💾 Progress saved: {len(all_records)} total records so far...")

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
