from datetime import datetime

def hitl_agent(state):
    """Human-in-the-loop for low-confidence or uncertain documents."""
    raw_class  = state.get("extracted_details", {}).get("raw_class", "unknown")
    confidence = state.get("confidence_score", 0)
    print("\n" + "─" * 64)
    print("👤  HUMAN REVIEW REQUIRED")
    print(f"   Document       : {state.get('document_name', '?')}")
    print(f"   LLM suggested  : {raw_class.upper()}")
    print(f"   Confidence     : {confidence}%  (threshold: 85%)")
    print(f"   Reason         : {state.get('classification_reason', '')}")
    if state.get("irrelevant_reason"):
        print(f"   Irrelevant note: {state['irrelevant_reason']}")
    print(f"\n   Document preview:")
    for line in state.get("document_text", "")[:500].splitlines():
        print(f"     {line}")
    print("   ...")
    print("─" * 64)
    print("\n   [1] cease      – Valid cease & desist request")
    print("   [2] irrelevant – Not a cease & desist request")
    while True:
        c = input("\n   Enter 1 or 2: ").strip()
        if c == "1":
            decision    = "cease"
            hitl_reason = ""
            break
        elif c == "2":
            decision    = "irrelevant"
            hitl_reason = input("   Brief reason it is irrelevant: ").strip()
            break
        else:
            print("   Please enter 1 or 2.")
    print(f"\n   → Human decided: {decision.upper()}")
    # Update state in-place to preserve all keys
    state["human_decision"] = decision
    state["classification"] = decision
    state["irrelevant_reason"] = hitl_reason or state.get("irrelevant_reason", "")
    state.setdefault("audit_log", []).append({
        "agent":       "HITLAgent",
        "action":      f"Human overrode '{raw_class}' ({confidence}%) → '{decision}'",
        "timestamp":   datetime.now().isoformat(),
        "reviewed_by": "human_operator",
    })
    return state
