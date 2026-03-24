from datetime import datetime
from tools.database_tools import store_cease_request

def database_agent(state):
    """Stores valid cease requests in SQLite."""
    d = state.get("extracted_details", {})
    document_name = state.get("document_name", "unknown")
    result = store_cease_request(
        received_date=datetime.now().strftime("%Y-%m-%d"),
        document_name=document_name,
        sender_name=d.get("sender_name", "unknown"),
        sender_address=d.get("sender_address", "unknown"),
        cease_activity=d.get("cease_activity", "unknown"),
        confidence=state.get("confidence_score", 0),
        raw_text=state.get("document_text", ""),
    )
    print(f"   → {result}")
    state["action_taken"] = result
    state.setdefault("audit_log", []).append({"agent": "DatabaseAgent", "action": result,
                       "timestamp": datetime.now().isoformat()})
    return state
