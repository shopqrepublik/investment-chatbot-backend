import sqlite3

c = sqlite3.connect('investment_bot.db')
c.executescript("""
CREATE TABLE IF NOT EXISTS predictions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticker TEXT NOT NULL,
  model TEXT NOT NULL,
  horizon_days INTEGER NOT NULL,
  asof_date TEXT NOT NULL,
  predicted_growth REAL,
  confidence REAL,
  note TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_predictions_unique
  ON predictions(ticker, model, horizon_days, asof_date);
CREATE INDEX IF NOT EXISTS idx_predictions_created_at
  ON predictions(created_at);
""")
c.commit(); c.close()
print("✅ predictions table ready")
