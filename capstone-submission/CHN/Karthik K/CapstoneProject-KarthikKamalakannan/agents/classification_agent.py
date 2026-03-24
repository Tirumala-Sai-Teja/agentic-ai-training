import json
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage

# ── Routing threshold ──────────────────────────────────────────────────────
# confidence > 95  → auto-route (cease → DB, irrelevant → archive)
# confidence <= 95 → HITL for human review
CONFIDENCE_THRESHOLD = 95

# ── Why threshold is hidden from the prompt ───────────────────────────────
# If LLM knows the cutoff it returns scores just above it to game routing.
# LLM scores honestly; Python routes based on that score.
# ──────────────────────────────────────────────────────────────────────────

CLASSIFY_PROMPT = """You are a strict legal document classifier specialising in
Cease & Desist (C&D) letters. Your job is to determine whether a document is a
valid C&D, something uncertain, or completely irrelevant.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Document may be in any language. Translate mentally, classify in English.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT MAKES A VALID CEASE & DESIST LETTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A genuine C&D letter MUST contain ALL of the following:

  [A] EXPLICIT DEMAND TO STOP
      The document must contain clear, direct language demanding
      the recipient STOP or CEASE a specific activity.
      Look for words/phrases like:
        - "cease and desist"
        - "immediately stop"
        - "cease all"
        - "demand that you stop"
        - "refrain from"
        - "discontinue"
        - "halt"
      ❌ Vague requests, suggestions, or complaints do NOT qualify.
      ❌ Settlement proposals, negotiation requests do NOT qualify.
      ❌ Complaints about past behaviour without a stop demand do NOT qualify.

  [B] IDENTIFIABLE SENDER
      The letter must identify who is making the demand — a person,
      company, or their legal representative (attorney/solicitor).
      ❌ Anonymous or completely unknown sender does NOT qualify.

  [C] SPECIFIC ACTIVITY TO STOP
      The demand must target a specific, identifiable activity.
      Examples: use of trademark, copyright infringement, harassment,
      breach of contract, defamation, stalking, unauthorised access.
      ❌ "stop everything" or vague demands do NOT qualify.

  ALL THREE must be present for classification as "cease".
  If ANY one is missing or unclear → classify as "uncertain".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT IS CLEARLY IRRELEVANT (never a C&D)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
These document types are NEVER cease & desist letters:
  - Invoice, receipt, payment request, billing statement
  - Letter of Authorisation (LOA)
  - NDA / Non-disclosure agreement
  - General complaint or grievance letter
  - Marketing or promotional letter
  - Court summons or subpoena
  - Settlement proposal or negotiation letter
  - Guardianship or custody request
  - Breach of contract claim without a stop demand
  - General legal correspondence without a stop demand
  - Employment termination letter
  - Policy violation warning (without cease demand)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIDENCE SCORING (0–100)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Score your confidence in the classification based on how clearly
the document meets (or fails) the criteria above.

  96–100 : Every criterion unambiguously met. Zero room for doubt.
  86–95  : All criteria present but one has minor ambiguity.
  71–85  : Most criteria present, one missing or unclear.
  51–70  : Partial match, significant elements missing or ambiguous.
  0–50   : Very weak match or clearly the wrong category.

Score independently for each classification:
  - For "cease": how clearly does the document satisfy [A]+[B]+[C]?
  - For "irrelevant": how clearly does it NOT satisfy [A]+[B]+[C]?
  - For "uncertain": how much genuine ambiguity exists?

Be conservative. The score represents real uncertainty.
A score above 90 means you would stake your professional reputation on it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLASSIFICATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  "cease"
    → ALL of [A], [B], [C] are clearly present
    → Document has unambiguous cease & desist intent

  "uncertain"
    → Document appears C&D-related BUT one or more of [A][B][C] is missing
    → OR: document has C&D-like language but overall intent is unclear
    → Use ONLY for documents that ARE in the C&D category but incomplete
    → Do NOT use for clearly irrelevant documents

  "irrelevant"
    → Document clearly does NOT contain all of [A][B][C]
    → Document type matches the irrelevant list above
    → Zero ambiguity about it not being a C&D

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXTRACTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Extract (use "unknown" if absent):
  sender_name       – Full legal name of sender or attorney
  sender_address    – Postal/mailing address
  cease_activity    – The specific activity demanded to stop
  irrelevant_reason – If irrelevant: document type + why not a C&D
                      (empty string if cease or uncertain)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reply ONLY with valid JSON — no markdown, no extra text.
confidence_score is your genuine assessment based on the criteria above.

{
  "classification":    "cease | uncertain | irrelevant",
  "confidence_score":  <integer 0-100>,
  "reason":            "<one sentence: which criteria [A][B][C] are met or missing>",
  "sender_name":       "",
  "sender_address":    "",
  "cease_activity":    "",
  "irrelevant_reason": ""
}
"""


def classification_agent(state: dict, llm, confidence_threshold: int = CONFIDENCE_THRESHOLD) -> dict:
    """
    Classify document using the LLM.

    Threshold = 95. Routing:
      confidence > 95  → auto-route (cease→DB, irrelevant→archive)
      confidence <= 95 → HITL regardless of classification
      confidence None  → HITL (safest fallback)
    """
    print(f"\n🔍 [Classification Agent] Classifying via LLM (threshold={confidence_threshold}%)...")

    messages = [
        SystemMessage(content=CLASSIFY_PROMPT),
        HumanMessage(content=f"Document content:\n\n{state['document_text'][:5000]}"),
    ]

    raw = llm.invoke(messages).content.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "classification":    "uncertain",
            "confidence_score":  None,
            "reason":            "Could not parse LLM response — routing to HITL.",
            "irrelevant_reason": "Parse error — requires manual review.",
            "sender_name":       "unknown",
            "sender_address":    "unknown",
            "cease_activity":    "unknown",
        }

    raw_class = result.get("classification", "uncertain")

    # ── Confidence: pure LLM value, no caps, no defaults ─────────────
    raw_confidence = result.get("confidence_score")
    confidence = None
    if raw_confidence is not None:
        try:
            confidence = int(float(str(raw_confidence)))
            if not (0 <= confidence <= 100):
                print(f"   ⚠️  Out-of-range confidence ({confidence}) → treating as None → HITL")
                confidence = None
        except (TypeError, ValueError):
            print(f"   ⚠️  Unparseable confidence ({raw_confidence!r}) → treating as None → HITL")
            confidence = None

    reason = result.get("reason", "")

    # ── Routing: confidence > threshold → auto, else → HITL ──────────
    if confidence is not None and confidence > confidence_threshold:
        routed_class = raw_class
        routing_note = f"confidence {confidence}% > {confidence_threshold}% → auto '{raw_class}'"
        auto_routed  = True
    else:
        routed_class = "hitl_needed"
        routing_note = (
            f"confidence {confidence}% <= {confidence_threshold}% → HITL"
            if confidence is not None
            else "LLM did not return confidence → HITL"
        )
        auto_routed = False

    conf_display = f"{confidence}%" if confidence is not None else "not provided"
    print(f"   → LLM class  : {raw_class.upper()}")
    print(f"   → Confidence : {conf_display}")
    print(f"   → Threshold  : {confidence_threshold}%")
    print(f"   → Route      : {'✅ AUTO' if auto_routed else '⚠️  HITL'} — {routing_note}")

    # ── Update state ──────────────────────────────────────────────────
    state["classification"]        = routed_class
    state["classification_reason"] = reason
    state["confidence_score"]      = confidence
    state["irrelevant_reason"]     = result.get("irrelevant_reason", "")
    state["extracted_details"]     = {
        "sender_name":    result.get("sender_name",    "unknown"),
        "sender_address": result.get("sender_address", "unknown"),
        "cease_activity": result.get("cease_activity", "unknown"),
        "raw_class":      raw_class,
    }
    state["audit_log"] = state.get("audit_log", []) + [{
        "agent":     "ClassificationAgent",
        "action":    (
            f"LLM='{raw_class}' confidence={conf_display} "
            f"threshold={confidence_threshold}% → routed='{routed_class}'"
        ),
        "reason":    reason,
        "timestamp": datetime.now().isoformat(),
    }]

    return state