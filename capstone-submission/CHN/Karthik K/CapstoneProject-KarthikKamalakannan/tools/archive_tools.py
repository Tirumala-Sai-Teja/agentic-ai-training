import os
ARCHIVE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'irrelevant_documents.txt')

def archive_irrelevant_document(
    received_date: str, document_name: str, reason: str, confidence: int,
) -> str:
    """Archive an irrelevant document with the reason it was deemed irrelevant."""
    with open(ARCHIVE_FILE, "a") as f:
        f.write(
            f"{received_date} | {document_name} | "
            f"confidence: {confidence}% | reason: {reason}\n"
        )
    return f"Archived '{document_name}' as irrelevant (confidence: {confidence}%)."
