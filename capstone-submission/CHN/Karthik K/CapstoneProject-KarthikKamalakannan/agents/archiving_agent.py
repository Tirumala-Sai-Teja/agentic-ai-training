from datetime import datetime
from tools.archive_tools import archive_irrelevant_document

def archiving_agent(state):
    """Archives irrelevant documents with reason."""
    reason = (
        state.get("irrelevant_reason")
        or state.get("classification_reason")
        or "Not a cease & desist document"
    )
    document_name = state.get("document_name", "unknown")
    result = archive_irrelevant_document(
        received_date=datetime.now().strftime("%Y-%m-%d"),
        document_name=document_name,
        reason=reason,
        confidence=state.get("confidence_score", 0),
    )
    print(f"   → {result}")
    state["action_taken"] = result
    state.setdefault("audit_log", []).append({"agent": "ArchivingAgent", "action": result,
                       "timestamp": datetime.now().isoformat()})
    return state
