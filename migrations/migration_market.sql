-- 1) Справочник тикеров
CREATE TABLE IF NOT EXISTS tickers (
    id INTEGER PRIMARY KEY,
    symbol TEXT UNIQUE NOT NULL,     -- 'AAPL.US'
    name TEXT,
    exchange TEXT,                   -- NASDAQ / NYSE
    sector TEXT,
    industry TEXT,
    currency TEXT DEFAULT 'USD',
    is_active INTEGER DEFAULT 1
);

-- 2) Индексы на prices (защита от дублей)
CREATE UNIQUE INDEX IF NOT EXISTS idx_prices_ticker_date
ON prices(ticker, date);

CREATE INDEX IF NOT EXISTS idx_prices_ticker ON prices(ticker);
CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);

-- 3) Дивиденды и сплиты (на будущее)
CREATE TABLE IF NOT EXISTS dividends (
    id INTEGER PRIMARY KEY,
    ticker TEXT NOT NULL,           -- оставляем строкой для совместимости
    ex_date DATE NOT NULL,
    pay_date DATE,
    amount REAL,
    currency TEXT DEFAULT 'USD',
    UNIQUE(ticker, ex_date)
);

CREATE TABLE IF NOT EXISTS splits (
    id INTEGER PRIMARY KEY,
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    numerator REAL,
    denominator REAL,
    UNIQUE(ticker, date)
);

-- 4) Прогнозы (под МЛ/LLM)
CREATE TABLE IF NOT EXISTS model_runs (
    id INTEGER PRIMARY KEY,
    model_name TEXT,
    params_json TEXT,
    run_ts DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY,
    model_run_id INTEGER REFERENCES model_runs(id),
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    predicted_close REAL,
    actual_close REAL,
    UNIQUE(model_run_id, ticker, date)
);
