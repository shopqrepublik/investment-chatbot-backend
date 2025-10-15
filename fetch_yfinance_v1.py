import asyncio
import pandas as pd
import sqlite3
import time
import os
import json
from bs4 import BeautifulSoup
import requests
import yfinance as yf
from tqdm.asyncio import tqdm_asyncio

# === CONFIG ===
OUTPUT_CSV = "quickfs_fundamentals.csv"
OUTPUT_DB = "quickfs_data.db"
REPORT_FILE = "sector_report.csv"
TICKERS_CACHE = "tickers_cache.json"
CONCURRENT_LIMIT = 5

# === Метрики для сбора ===
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
# 2️⃣ Получение данных по тикеру (с yfinance)
# ======================================================
async def fetch_ticker_data(ticker):
    try:
        info = await asyncio.to_thread(yf.Ticker, ticker)
        t = info

        fin = t.financials.T if t.financials is not None else pd.DataFrame()
        bal = t.balance_sheet.T if t.balance_sheet is not None else pd.DataFrame()
        if fin.empty:
            return []

        records = []
        for year, row in fin.iterrows():
            y = pd.to_datetime(year).year
            revenue = row.get("Total Revenue", None)
            net_income = row.get("Net Income", None)
            eps = row.get("Basic EPS", None)
            pe = t.info.get("trailingPE", None)
            roe = t.info.get("returnOnEquity", None)
            ebit = row.get("Ebit", None)
            total_assets = bal.loc[year].get("Total Assets") if not bal.empty and year in bal.index else None
            total_liab = bal.loc[year].get("Total Liab") if not bal.empty and year in bal.index else None
            invested_capital = None
            if total_assets is not None and total_liab is not None:
                invested_capital = total_assets - total_liab
            roic = None
            if ebit and invested_capital and invested_capital != 0:
                roic = ebit / invested_capital

            records.append({
                "year": y,
                "revenue": revenue,
                "net_income": net_income,
                "eps": eps,
                "pe_ratio": pe,
                "roe": roe,
                "roic": roic
            })
        return records
    except Exception as e:
        print(f"⚠️ {ticker}: {e}")
        return []

# ======================================================
# 3️⃣ Преобразование в общую таблицу
# ======================================================
def normalize(ticker, company, sector, sub_industry, records):
    rows = []
    for r in records:
        for m in SELECTED_METRICS:
            rows.append({
                "ticker": ticker,
                "company": company,
                "sector": sector,
                "sub_industry": sub_industry,
                "year": r["year"],
                "metric": m,
                "value": r.get(m)
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

    async def process_row(row):
        ticker, company, sector, sub = row["Symbol"], row["Security"], row["GICS Sector"], row["GICS Sub-Industry"]
        recs = await fetch_ticker_data(ticker)
        return normalize(ticker, company, sector, sub, recs)

    sem = asyncio.Semaphore(CONCURRENT_LIMIT)
    async def with_limit(r):
        async with sem:
            return await process_row(r)

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
