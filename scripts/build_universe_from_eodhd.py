import sqlite3
import pandas as pd
import os

DB_PATH = "investment_bot.db"

# ✅ Актуальные и стабильные источники
SP500_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
NASDAQ_URL = "https://datahub.io/core/nasdaq-listings/r/nasdaq-listed.csv"  # официальный источник

def normalize_sp500(df: pd.DataFrame) -> pd.DataFrame:
    print("🧩 Normalizing S&P500 dataframe ...")
    rename_map = {}
    for col in df.columns:
        c = col.lower()
        if "symbol" in c:
            rename_map[col] = "symbol"
        elif "security" in c or "name" in c:
            rename_map[col] = "name"
        elif "sector" in c:
            rename_map[col] = "sector"
        elif "industry" in c:
            rename_map[col] = "industry"
    df = df.rename(columns=rename_map)

    for col in ["symbol", "name", "sector", "industry"]:
        if col not in df.columns:
            df[col] = None

    df["exchange"] = "NYSE/NASDAQ"
    df["currency"] = "USD"
    df["symbol"] = df["symbol"].astype(str).str.strip().str.replace(".", "-", regex=False) + ".US"
    return df[["symbol", "name", "exchange", "sector", "industry", "currency"]]

def normalize_nasdaq(df: pd.DataFrame) -> pd.DataFrame:
    print("🧩 Normalizing NASDAQ dataframe ...")
    rename_map = {}
    for col in df.columns:
        c = col.lower()
        if "symbol" in c or "ticker" in c:
            rename_map[col] = "symbol"
        elif "name" in c or "company" in c:
            rename_map[col] = "name"
    df = df.rename(columns=rename_map)

    for col in ["symbol", "name"]:
        if col not in df.columns:
            df[col] = None

    df["exchange"] = "NASDAQ"
    df["sector"] = None
    df["industry"] = None
    df["currency"] = "USD"
    df["symbol"] = df["symbol"].astype(str).str.strip() + ".US"
    return df[["symbol", "name", "exchange", "sector", "industry", "currency"]]

def fetch_sp500():
    print("📥 Fetching S&P500 from GitHub ...")
    df = pd.read_csv(SP500_URL)
    print(f"✅ Raw S&P500 rows: {len(df)}")
    return normalize_sp500(df)

def fetch_nasdaq():
    print("📥 Fetching NASDAQ listings from DataHub ...")
    df = pd.read_csv(NASDAQ_URL)
    print(f"✅ Raw NASDAQ rows: {len(df)}")
    return normalize_nasdaq(df)

def save_to_db(df):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # создаём таблицу, если не существует
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickers (
        id INTEGER PRIMARY KEY,
        symbol TEXT UNIQUE NOT NULL,
        name TEXT,
        exchange TEXT,
        sector TEXT,
        industry TEXT,
        currency TEXT DEFAULT 'USD',
        is_active INTEGER DEFAULT 1
    );
    """)

    query = """
    INSERT INTO tickers(symbol, name, exchange, sector, industry, currency, is_active)
    VALUES(?, ?, ?, ?, ?, ?, 1)
    ON CONFLICT(symbol) DO UPDATE SET
        name=excluded.name,
        exchange=excluded.exchange,
        sector=excluded.sector,
        industry=excluded.industry,
        currency=excluded.currency,
        is_active=1;
    """

    conn.executemany(query, df.itertuples(index=False, name=None))
    conn.commit()
    conn.close()
    print(f"💾 Saved {len(df)} tickers into database")

def main():
    sp500 = fetch_sp500()
    nasdaq = fetch_nasdaq()
    combined = pd.concat([sp500, nasdaq]).drop_duplicates(subset=["symbol"])
    os.makedirs("data", exist_ok=True)
    combined.to_csv("data/universe_spy_qqq.csv", index=False)
    save_to_db(combined)
    print(f"📁 Universe saved to data/universe_spy_qqq.csv ({len(combined)} tickers)")

if __name__ == "__main__":
    main()
