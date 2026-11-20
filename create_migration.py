import sqlite3
from pathlib import Path

db = Path("data/bestiary_ru.db")
out = Path("migrations/001_initial_schema.sql")

con = sqlite3.connect(db)
rows = con.execute("""
    SELECT sql
    FROM sqlite_master
    WHERE sql IS NOT NULL
      AND name NOT LIKE 'sqlite_%'
    ORDER BY
      CASE type
        WHEN 'table' THEN 1
        WHEN 'index' THEN 2
        WHEN 'trigger' THEN 3
        WHEN 'view' THEN 4
        ELSE 5
      END
""").fetchall()

with out.open("w", encoding="utf-8") as f:
    f.write("-- Initial database schema migration\n\n")
    for (sql,) in rows:
        f.write(sql.rstrip(";") + ";\n\n")

con.close()
print(f"Migration created: {out}")
print(f"SQL objects: {len(rows)}")
