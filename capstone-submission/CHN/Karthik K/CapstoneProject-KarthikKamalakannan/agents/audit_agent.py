from datetime import datetime
from tools.audit_tools import write_audit_entry

def audit_agent(state):
    """Writes the final compliance audit entry."""
    reviewed_by = "human_operator" if state.get("human_decision") else "system"
    final_class = (
        state.get("human_decision")
        or state.get("extracted_details", {}).get("raw_class")
        or state.get("classification", "unknown")
    )
    document_name = state.get("document_name", "unknown")
    result = write_audit_entry(
        document_name=document_name,
        classification=final_class,
        reason=state.get("classification_reason", ""),
        confidence=state.get("confidence_score", 0),
        action=state.get("action_taken", "none"),
        reviewed_by=reviewed_by,
    )
    print(f"   → {result}")
    state.setdefault("audit_log", []).append({"agent": "AuditAgent", "action": result,
                       "timestamp": datetime.now().isoformat()})
    return state
