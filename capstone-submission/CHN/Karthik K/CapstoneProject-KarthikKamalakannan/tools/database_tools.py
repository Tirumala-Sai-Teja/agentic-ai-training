import sqlite3
from datetime import datetime
DB_PATH = "cease_desist.db"

def store_cease_request(
    received_date: str, document_name: str, sender_name: str,
    sender_address: str, cease_activity: str, confidence: int, raw_text: str,
) -> str:
    """Store a valid cease & desist request in the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS cease_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            received_date TEXT,
            document_name TEXT,
            sender_name TEXT,
            sender_address TEXT,
            cease_activity TEXT,
            confidence INTEGER,
            raw_text TEXT,
            created_at TEXT
        )"""
    )
    conn.execute(
        """INSERT INTO cease_requests
           (received_date, document_name, sender_name, sender_address,
            cease_activity, confidence, raw_text, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (received_date, document_name, sender_name, sender_address,
         cease_activity, confidence, raw_text[:2000], datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return f"Stored cease request for '{document_name}' (confidence: {confidence}%)."
