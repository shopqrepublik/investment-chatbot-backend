import pandas as pd, requests, json, os, zipfile
from bs4 import BeautifulSoup
from textwrap import dedent

# === 1. Load tickers ===
def get_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
    table = BeautifulSoup(html, "html.parser").find("table", {"id": "constituents"})
    df = pd.read_html(str(table))[0]
    return df["Symbol"].str.replace(".", "-", regex=False).tolist()

def get_nasdaq():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
    tables = BeautifulSoup(html, "html.parser").find_all("table")
    for t in tables:
        df_tmp = pd.read_html(str(t))[0]
        if any(c in df_tmp.columns for c in ["Ticker", "Symbol"]):
            df = df_tmp
            break
    df.columns = [c.strip() for c in df.columns]
    if "Ticker" in df.columns:
        df.rename(columns={"Ticker": "Symbol"}, inplace=True)
    return df["Symbol"].str.replace(".", "-", regex=False).tolist()

sp = get_sp500()
nas = get_nasdaq()
tickers = sorted(list(set(sp + nas)))
print(f"✅ Loaded {len(tickers)} unique tickers")

# === 2. Split into 25 batches ===
os.makedirs("batches", exist_ok=True)
batches = [tickers[i:i+20] for i in range(0, len(tickers), 20)]

# === 3. Create .bat chain ===
for i, group in enumerate(batches, start=1):
    next_file = f"batch{i+1}.bat" if i < len(batches) else ""
    cmd = dedent(f"""
    @echo off
    echo === Batch {i} started ===
    python fetch_alpha_vantage_v2.py --tickers {' '.join(group)}
    echo === Sleeping 120 seconds before next batch... ===
    timeout /t 120 >nul
    """)
    if next_file:
        cmd += f"python {next_file}\n"
    else:
        cmd += "echo === All batches completed successfully ===\n pause\n"

    with open(f"batches/batch{i}.bat", "w", encoding="utf-8") as f:
        f.write(cmd.strip())

print("✅ 25 batch files created in /batches")
