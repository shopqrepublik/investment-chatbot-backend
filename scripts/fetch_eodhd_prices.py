import os
import time
import sqlite3
import requests
import argparse
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

# === Настройки ===
load_dotenv()
API_TOKEN = os.getenv("EODHD_TOKEN")
BASE_URL = "https://eodhd.com/api"
DB_PATH = "investment_bot.db"

END = date.today().isoformat()
START = (date.today() - timedelta(days=365 * 10)).isoformat()


# === Вспомогательные функции ===

def get_tickers(conn):
    """Забираем все активные тикеры из БД."""
    cur = conn.cursor()
    q = "SELECT symbol FROM tickers WHERE is_active=1 ORDER BY symbol"
    return [r[0] for r in cur.execute(q).fetchall()]


def get_last_date(conn, ticker):
    """Получаем последнюю дату для тикера."""
    cur = conn.execute("SELECT MAX(date) FROM prices WHERE ticker=?", (ticker,))
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def fetch_eod(ticker, start=START, end=END, retries=3):
    """Загружаем котировки через EODHD API."""
    url = f"{BASE_URL}/eod/{ticker}?api_token={API_TOKEN}&fmt=json&period=d&from={start}&to={end}"
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 403:
                raise RuntimeError(f"403 Forbidden for {ticker}")
            if r.status_code != 200:
                print(f"⚠️ {ticker}: HTTP {r.status_code}")
                return []
            return r.json()
        except requests.exceptions.RequestException as e:
            wait = 5 * (2 ** attempt)
            print(f"⚠️ {ticker}: network error ({e}), retrying in {wait}s...")
            time.sleep(wait)
    print(f"❌ {ticker}: failed after {retries} retries")
    return []


def save_prices(conn, ticker, rows):
    """Сохраняем котировки в таблицу prices с upsert."""
    if not rows:
        return 0
    data = []
    for x in rows:
        data.append((
            ticker,
            x.get("date"),
            x.get("open"),
            x.get("high"),
            x.get("low"),
            x.get("close"),
            x.get("adjusted_close", x.get("close")),
            x.get("volume")
        ))
    q = """
    INSERT INTO prices(ticker, date, open, high, low, close, adj_close, volume)
    VALUES(?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(ticker, date) DO UPDATE SET
        open=excluded.open,
        high=excluded.high,
        low=excluded.low,
        close=excluded.close,
        adj_close=excluded.adj_close,
        volume=excluded.volume;
    """
    conn.executemany(q, data)
    conn.commit()
    return len(data)


# === Основной процесс ===

def main():
    parser = argparse.ArgumentParser(description="Fetch EODHD prices in batches")
    parser.add_argument("--start", type=int, default=0, help="Start index")
    parser.add_argument("--end", type=int, default=500, help="End index (exclusive)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    tickers = get_tickers(conn)[args.start:args.end]
    total = len(tickers)

    print(f"📈 Starting download for {total} tickers from index {args.start} to {args.end} ({START}→{END})")

    start_time = time.time()

    for i, ticker in enumerate(tickers, 1):
        try:
            last = get_last_date(conn, ticker)

            if last:
                start_date = (datetime.strptime(last, "%Y-%m-%d") + timedelta(days=1)).date().isoformat()
            else:
                start_date = START

            # если всё уже актуально — пропускаем
            if start_date >= END:
                print(f"[{i}/{total}] {ticker}: already up to date (latest {last})")
                continue

            rows = fetch_eod(ticker, start=start_date, end=END)
            n = save_prices(conn, ticker, rows)
            print(f"[{i}/{total}] {ticker}: +{n} rows (since {start_date})")

            # защита от rate-limit
            time.sleep(2.5)

        except Exception as e:
            print(f"⚠️ Error {ticker}: {e}")
            time.sleep(5)

    conn.close()

    elapsed = time.time() - start_time
    print(f"\n✅ All tickers processed. Time elapsed: {elapsed/60:.1f} min ({total} tickers)")


if __name__ == "__main__":
    main()
