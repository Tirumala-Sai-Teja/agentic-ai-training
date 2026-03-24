import sqlite3

conn = sqlite3.connect("database/cease_requests.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS cease_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_received TEXT,
    document_name TEXT,
    details TEXT
)
""")

conn.commit()
conn.close()

print("Database initialized successfully")