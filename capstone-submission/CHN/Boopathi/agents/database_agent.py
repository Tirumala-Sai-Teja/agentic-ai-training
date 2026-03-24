import sqlite3
from datetime import datetime

def store_cease(document_name, text):

    conn = sqlite3.connect("database/cease_requests.db")

    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO cease_requests
    (date_received, document_name, details)
    VALUES (?, ?, ?)
    """, (datetime.now(), document_name, text))

    conn.commit()

    conn.close()

    return "Stored in database"