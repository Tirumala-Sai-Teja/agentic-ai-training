from datetime import datetime

def archive_document(document_name):

    with open("logs/archive.txt", "a") as f:

        f.write(f"{datetime.now()} - {document_name}\n")

    return "Archived"