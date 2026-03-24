from langchain_groq import ChatGroq
import re
from dotenv import load_dotenv

load_dotenv()
llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0.0
)

def classify(state):
    print("[Classifier] Running LLM classification...")

    # ✅ Ensure memory exists
    memory = getattr(state, "memory", {})

    # ✅ Get past examples (last 3)
    past_examples = ""
    if memory.get("classifications"):
        past_examples = "\n".join([
            f"- {item['text'][:100]} → {item['category']}"
            for item in memory["classifications"][-3:]
        ])

    prompt = f"""
Act as a strict document classifier.

Learn from previous examples:

{past_examples}

Classify the document into EXACTLY ONE category:

Cease → Explicit demand to stop an action  
Uncertain → Complaint or unclear intent  
Irrelevant → Not related  

Rules:
- "cease and desist", "stop", "do not contact" → Cease
- Complaint without direct stop → Uncertain
- Otherwise → Irrelevant

Return ONLY:

Category: <Cease | Uncertain | Irrelevant>
Confidence: <0 to 1>

Document:
{state.text[:3000]}
"""

    response = llm.invoke(prompt)
    output = response.content.strip()

    print("----- CLASSIFIER OUTPUT -----")
    print(output)
    print("-----------------------------")

    # ✅ Parse
    category_match = re.search(r"Category:\s*(\w+)", output)
    confidence_match = re.search(r"Confidence:\s*([0-9.]+)", output)

    category = category_match.group(1) if category_match else "Uncertain"
    confidence = float(confidence_match.group(1)) if confidence_match else 0.5

    # ✅ Update memory
    memory.setdefault("classifications", []).append({
        "text": state.text[:200],
        "category": category,
        "confidence": confidence
    })

    # ✅ Map to doc_type
    if category.lower() == "cease":
        doc_type = "NOTICE"
    elif category.lower() == "uncertain":
        doc_type = "BUSINESS DOCUMENT"
    else:
        doc_type = "IRRELEVANT"

    return {
        "classification": category,
        "confidence": confidence,
        "doc_type": doc_type,
        "memory": memory
    }