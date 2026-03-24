import os
def audit(state):
    print("[Audit] Logging...")

    log = {
        "doc": os.path.basename(state.file_path),
        "type": state.doc_type,
        "confidence": state.confidence,
        "final_output": state.final_output,
        "review_required": state.needs_review
    }

    print("AUDIT:", log)
    return state