from datetime import datetime
import os

def archive_document(state):
    os.makedirs("logs", exist_ok=True)

    with open("logs/archive.txt", "a") as f:
        f.write(f"{datetime.now()} - {state.document_name}\n")

    return {
        "status": "archived"
    }