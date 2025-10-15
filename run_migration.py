import sqlite3
import pathlib

# Определяем пути
root_dir = pathlib.Path(__file__).parent
db_path = root_dir / "investment_bot.db"
sql_path = root_dir / "migrations" / "migration_market.sql"

# Читаем SQL
with open(sql_path, "r", encoding="utf-8") as f:
    sql_script = f.read()

# Подключаемся к базе
conn = sqlite3.connect(db_path)
conn.executescript(sql_script)
conn.commit()
conn.close()

print("✅ Миграция успешно выполнена!")
