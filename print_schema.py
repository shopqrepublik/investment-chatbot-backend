import sqlite3, sys
db = sys.argv[1] if len(sys.argv) > 1 else "investment_bot.db"
con = sqlite3.connect(db)
cur = con.cursor()
print(f"\n=== {db} ===")
# Таблицы и вьюхи
cur.execute("SELECT name, type FROM sqlite_master WHERE type in ('table','view') ORDER BY type, name;")
for name, typ in cur.fetchall():
    print(f"\n-- {typ.upper()} {name}")
    # DDL
    cur2 = con.execute("SELECT sql FROM sqlite_master WHERE name=?",(name,))
    print(cur2.fetchone()[0])
    # Колонки
    cur3 = con.execute(f"PRAGMA table_info('{name}')")
    cols = cur3.fetchall()
    print("-- columns:", ", ".join([f"{c[1]} {c[2]}" for c in cols]))
con.close()
