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
BASE_URL = "https://public-api.quickfs.net/v1/data/all/"
OUTPUT_CSV = "quickfs_fundamentals.csv"
OUTPUT_DB = "quickfs_data.db"
REPORT_FILE = "sector_report.csv"
PROGRESS_FILE = "quickfs_progress.json"
TICKERS_CACHE = "tickers_cache.json"
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
# 🧩 1. Получаем тикеры S&P500 и NASDAQ100 (с кешем)
# ======================================================
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; QuickFSDataBot/1.0)"}
    html = requests.get(url, headers=headers).text

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "constituents"})
    if table is None:
        raise RuntimeError("❌ Не найдена таблица S&P 500 на странице Wikipedia")

    df = pd.read_html(str(table))[0]
    df["Symbol"] = df["Symbol"].str.replace(".", "-", regex=False)
    print(f"✅ S&P 500 tickers loaded: {len(df)}")
    return df[["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]]


def get_nasdaq_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; QuickFSDataBot/1.0)"}
    html = requests.get(url, headers=headers).text

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")

    target_table = None
    for table in tables:
        df_tmp = pd.read_html(str(table))[0]
        if any(col in df_tmp.columns for col in ["Ticker", "Symbol", "Company", "Company name"]):
            target_table = df_tmp
            break

    if target_table is None:
        raise RuntimeError("❌ Не найдена таблица Nasdaq-100")

    df = target_table.copy()
    df.columns = [c.strip() for c in df.columns]

    if "Ticker" in df.columns:
        df.rename(columns={"Ticker": "Symbol"}, inplace=True)
    elif "Symbol" not in df.columns:
        raise RuntimeError("❌ Не найдена колонка с тикерами в таблице NASDAQ-100")

    if "Company" in df.columns:
        name_col = "Company"
    elif "Company name" in df.columns:
        name_col = "Company name"
    elif "Security" in df.columns:
        name_col = "Security"
    else:
        name_col = df.columns[1]

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
    else:
        sp500 = get_sp500_tickers()
        nasdaq = get_nasdaq_tickers()
        all_tickers_df = pd.concat([sp500, nasdaq]).drop_duplicates(subset=["Symbol"])
        tickers_list = all_tickers_df.to_dict(orient="records")
        with open(TICKERS_CACHE, "w") as f:
            json.dump(tickers_list, f, indent=2)
        print(f"💾 Cached {len(tickers_list)} tickers to {TICKERS_CACHE}")
        return all_tickers_df

# ======================================================
# ⚙️ 2. Асинхронная загрузка данных из QuickFS
# ======================================================
async def fetch_ticker(session, ticker, retries=3):
    url = f"{BASE_URL}{ticker}.US?api_key={API_KEY}"
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return ticker, data.get("data", {})
                elif response.status == 429:
                    print(f"⏳ Rate limit hit for {ticker}, waiting 10s...")
                    await asyncio.sleep(10)
                else:
                    print(f"⚠️ {ticker} returned HTTP {response.status}")
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"⚠️ Error fetching {ticker} (attempt {attempt+1}): {e}")
            await asyncio.sleep(2)
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
    if df.empty:
        print("⚠️ Warning: DataFrame is empty, nothing to save.")
        return

    # Очистим имена колонок для SQLite
    df.columns = [
        str(c).strip().replace(" ", "_").replace("(", "").replace(")", "").replace("%", "pct")
        if c not in (None, "") else f"col_{i}"
        for i, c in enumerate(df.columns)
    ]

    df.to_csv(OUTPUT_CSV, index=False)
    conn = sqlite3.connect(OUTPUT_DB)
    try:
        df.to_sql("fundamentals", conn, if_exists="replace", index=False)
    except Exception as e:
        print(f"❌ Error saving to SQL: {e}")
        print("Columns:", df.columns.tolist())
    finally:
        conn.close()

# ======================================================
# 📊 5. Отчёт по секторам
# ======================================================
def generate_sector_report(df):
    if df.empty:
        print("⚠️ Sector report skipped (empty DataFrame).")
        return

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
    all_tickers_df = load_tickers_with_cache()
    all_tickers = all_tickers_df["Symbol"].tolist()
    print(f"📊 Total tickers to fetch: {len(all_tickers)}")

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

