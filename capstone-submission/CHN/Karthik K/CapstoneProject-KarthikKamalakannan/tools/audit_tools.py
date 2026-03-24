import json
from datetime import datetime
AUDIT_FILE = "audit_log.jsonl"

def write_audit_entry(
    document_name: str, classification: str, reason: str,
    confidence: int, action: str, reviewed_by: str = "system",
) -> str:
    """Write a compliance audit log entry."""
    entry = {
        "timestamp":      datetime.now().isoformat(),
        "document_name":  document_name,
        "classification": classification,
        "confidence":     confidence,
        "reason":         reason,
        "action":         action,
        "reviewed_by":    reviewed_by,
    }
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return f"Audit entry written for '{document_name}' (confidence: {confidence}%)."
