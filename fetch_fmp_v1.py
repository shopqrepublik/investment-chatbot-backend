import aiohttp
import asyncio
import pandas as pd
import sqlite3
import time
import requests
import json
import os
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm_asyncio

# === CONFIG ===
FMP_API_KEY = "eaw6TrrNBdlOxUCqoRZlnnMqRZr7vmBB"
BASE_URL = "https://financialmodelingprep.com/api/v3"
OUTPUT_CSV = "fmp_fundamentals.csv"
OUTPUT_DB = "fmp_data.db"
REPORT_FILE = "sector_report.csv"
TICKERS_CACHE = "tickers_cache.json"
CONCURRENT_LIMIT = 5

# === Метрики ===
SELECTED_METRICS = [
    "revenue",
    "net_income",
    "eps",
    "pe_ratio",
    "roe",
    "roic"
]

# ======================================================
# 1️⃣ Получение тикеров S&P500 и NASDAQ100 (с кешем)
# ======================================================
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
    table = BeautifulSoup(html, "html.parser").find("table", {"id": "constituents"})
    df = pd.read_html(str(table))[0]
    df["Symbol"] = df["Symbol"].str.replace(".", "-", regex=False)
    print(f"✅ S&P 500 tickers loaded: {len(df)}")
    return df[["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]]


def get_nasdaq_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
    tables = BeautifulSoup(html, "html.parser").find_all("table")
    target = None
    for t in tables:
        df_tmp = pd.read_html(str(t))[0]
        if any(c in df_tmp.columns for c in ["Ticker", "Symbol", "Company", "Company name"]):
            target = df_tmp
            break
    df = target.copy()
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
    all_df = pd.concat([sp500, nasdaq]).drop_duplicates(subset=["Symbol"])
    with open(TICKERS_CACHE, "w") as f:
        json.dump(all_df.to_dict(orient="records"), f, indent=2)
    print(f"💾 Cached {len(all_df)} tickers to {TICKERS_CACHE}")
    return all_df

# ======================================================
# 2️⃣ Асинхронная загрузка данных из FMP
# ======================================================
async def fetch_json(session, url):
    try:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"⚠️ HTTP {response.status} → {url}")
                return None
    except Exception as e:
        print(f"⚠️ Error fetching {url}: {e}")
        return None


async def fetch_fmp_data(session, ticker):
    """Загружает income statement и ratios для одного тикера"""
    data = {}

    income_url = f"{BASE_URL}/income-statement/{ticker}?period=annual&limit=10&apikey={FMP_API_KEY}"
    ratios_url = f"{BASE_URL}/ratios/{ticker}?limit=10&apikey={FMP_API_KEY}"

    income_json, ratios_json = await asyncio.gather(
        fetch_json(session, income_url),
        fetch_json(session, ratios_url)
    )

    if not income_json or not isinstance(income_json, list):
        return []

    for item in income_json:
        year = int(item["date"][:4])
        data[year] = {
            "revenue": item.get("revenue"),
            "net_income": item.get("netIncome"),
            "eps": item.get("eps")
        }

    if ratios_json and isinstance(ratios_json, list):
        for item in ratios_json:
            year = int(item["date"][:4])
            if year in data:
                data[year]["pe_ratio"] = item.get("priceEarningsRatio")
                data[year]["roe"] = item.get("returnOnEquity")
                data[year]["roic"] = item.get("returnOnInvestedCapital")

    records = []
    for year, vals in data.items():
        for metric, value in vals.items():
            records.append({"year": year, "metric": metric, "value": value})
    return records

# ======================================================
# 3️⃣ Преобразуем данные в таблицу
# ======================================================
def normalize(ticker, company, sector, sub_industry, records):
    rows = []
    for r in records:
        rows.append({
            "ticker": ticker,
            "company": company,
            "sector": sector,
            "sub_industry": sub_industry,
            "year": r["year"],
            "metric": r["metric"],
            "value": r["value"]
        })
    return rows

# ======================================================
# 4️⃣ Сохранение и отчёты
# ======================================================
def save_data(df):
    if df.empty:
        print("⚠️ Warning: DataFrame is empty.")
        return
    df.to_csv(OUTPUT_CSV, index=False)
    with sqlite3.connect(OUTPUT_DB) as conn:
        df.to_sql("fundamentals", conn, if_exists="replace", index=False)
    print(f"💾 Saved {len(df)} rows to {OUTPUT_DB}")


def generate_sector_report(df):
    if df.empty:
        print("⚠️ No data for sector report.")
        return
    pivot = df.pivot_table(index=["sector", "year"], columns="metric", values="value", aggfunc="mean").reset_index()
    pivot.to_csv(REPORT_FILE, index=False)
    print(f"📈 Sector report saved to {REPORT_FILE}")

# ======================================================
# 5️⃣ Основной процесс
# ======================================================
async def main():
    tickers_df = load_tickers_with_cache()
    all_records = []

    sem = asyncio.Semaphore(CONCURRENT_LIMIT)

    async with aiohttp.ClientSession() as session:
        async def with_limit(row):
            async with sem:
                ticker, company, sector, sub = row["Symbol"], row["Security"], row["GICS Sector"], row["GICS Sub-Industry"]
                data = await fetch_fmp_data(session, ticker)
                return normalize(ticker, company, sector, sub, data)

        for chunk_start in range(0, len(tickers_df), CONCURRENT_LIMIT):
            chunk = tickers_df.iloc[chunk_start:chunk_start + CONCURRENT_LIMIT]
            res_chunk = await tqdm_asyncio.gather(*[with_limit(r) for _, r in chunk.iterrows()])
            for res in res_chunk:
                all_records.extend(res)
            print(f"💾 Progress: {len(all_records)} records collected...")

    df = pd.DataFrame(all_records)
    save_data(df)
    generate_sector_report(df)
    print(f"\n✅ Completed. Total records: {len(df)}")

# ======================================================
# 🏁 Запуск
# ======================================================
if __name__ == "__main__":
    start = time.time()
    asyncio.run(main())
    print(f"⏱️ Finished in {(time.time() - start)/60:.1f} min")
