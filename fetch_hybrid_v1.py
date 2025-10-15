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
import yfinance as yf

# === CONFIG ===
FMP_API_KEY = "eaw6TrrNBdlOxUCqoRZlnnMqRZr7vmBB"
BASE_FMP = "https://financialmodelingprep.com/api/v3"
OUTPUT_CSV = "hybrid_fundamentals.csv"
OUTPUT_DB = "hybrid_data.db"
REPORT_FILE = "sector_report.csv"
TICKERS_CACHE = "tickers_cache.json"
CONCURRENT_LIMIT = 5

SELECTED_METRICS = ["revenue", "net_income", "eps", "pe_ratio", "roe", "roic"]

# ======================================================
# 1️⃣ Загрузка тикеров
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
    for t in tables:
        df_tmp = pd.read_html(str(t))[0]
        if any(c in df_tmp.columns for c in ["Ticker", "Symbol", "Company", "Company name"]):
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
    all_df = pd.concat([sp500, nasdaq]).drop_duplicates(subset=["Symbol"])
    with open(TICKERS_CACHE, "w") as f:
        json.dump(all_df.to_dict(orient="records"), f, indent=2)
    print(f"💾 Cached {len(all_df)} tickers to {TICKERS_CACHE}")
    return all_df

# ======================================================
# 2️⃣ Получение данных из Yahoo Finance
# ======================================================
async def fetch_yf(ticker):
    try:
        t = await asyncio.to_thread(yf.Ticker, ticker)
        fin = t.get_income_stmt(freq="yearly")
        bal = t.get_balance_sheet(freq="yearly")
        if fin is None or fin.empty:
            return []
        records = []
        for year, row in fin.T.iterrows():
            y = int(str(year)[:4])
            revenue = row.get("TotalRevenue")
            net_income = row.get("NetIncome")
            eps = row.get("BasicEPS") or row.get("DilutedEPS")
            pe = t.info.get("trailingPE")
            roe = t.info.get("returnOnEquity")
            ebit = row.get("EBIT")
            assets = bal.T.loc[year].get("TotalAssets") if not bal.empty and year in bal.T.index else None
            liab = bal.T.loc[year].get("TotalLiabilitiesNetMinorityInterest") if not bal.empty and year in bal.T.index else None
            roic = (ebit / (assets - liab)) if ebit and assets and liab and (assets - liab) != 0 else None
            records.append({
                "year": y, "revenue": revenue, "net_income": net_income,
                "eps": eps, "pe_ratio": pe, "roe": roe, "roic": roic
            })
        return records
    except Exception:
        return []

# ======================================================
# 3️⃣ Получение fallback-данных из FMP (free endpoints)
# ======================================================
async def fetch_fmp_growth(session, ticker):
    url = f"{BASE_FMP}/financial-growth/{ticker}?apikey={FMP_API_KEY}"
    async with session.get(url) as r:
        if r.status != 200:
            return []
        js = await r.json()
        records = []
        for item in js[:7]:
            year = int(item["date"][:4])
            records.append({
                "year": year,
                "revenue": item.get("revenueGrowth"),
                "net_income": item.get("netIncomeGrowth"),
                "eps": item.get("epsgrowth"),
                "pe_ratio": item.get("priceEarningsRatio"),
                "roe": item.get("returnOnEquity"),
                "roic": item.get("returnOnInvestedCapital")
            })
        return records

# ======================================================
# 4️⃣ Комбинирование и сохранение
# ======================================================
def normalize(ticker, company, sector, sub_industry, records):
    rows = []
    for r in records:
        for m in SELECTED_METRICS:
            rows.append({
                "ticker": ticker, "company": company, "sector": sector,
                "sub_industry": sub_industry, "year": r["year"],
                "metric": m, "value": r.get(m)
            })
    return rows


def save_data(df):
    if df.empty:
        print("⚠️ No data to save.")
        return
    df.to_csv(OUTPUT_CSV, index=False)
    with sqlite3.connect(OUTPUT_DB) as conn:
        df.to_sql("fundamentals", conn, if_exists="replace", index=False)
    print(f"💾 Saved {len(df)} rows to {OUTPUT_DB}")


def generate_sector_report(df):
    if df.empty:
        print("⚠️ No data for report.")
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

        async def process(row):
            async with sem:
                ticker = row["Symbol"]
                company, sector, sub = row["Security"], row["GICS Sector"], row["GICS Sub-Industry"]
                data = await fetch_yf(ticker)
                if not data:
                    data = await fetch_fmp_growth(session, ticker)
                return normalize(ticker, company, sector, sub, data)

        for chunk_start in range(0, len(tickers_df), CONCURRENT_LIMIT):
            chunk = tickers_df.iloc[chunk_start:chunk_start + CONCURRENT_LIMIT]
            res = await tqdm_asyncio.gather(*[process(r) for _, r in chunk.iterrows()])
            for r in res:
                all_records.extend(r)
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
