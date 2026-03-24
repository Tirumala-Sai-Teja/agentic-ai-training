import sqlite3

def save_to_db(state):
    conn = sqlite3.connect("Databaseactivities/cease.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY,
        name TEXT,
        type TEXT,
        data TEXT
    )
    """)

    cur.execute(
        "INSERT INTO documents (name, type, data) VALUES (?, ?, ?)",
        (state.document_name, state.doc_type, str(state.extracted_data))
    )

    conn.commit()
    conn.close()

    return state