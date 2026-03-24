from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
import json
from dotenv import load_dotenv


load_dotenv()
llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0.0
)

def extract(state):
    print(f"[Extractor] Extracting data for type: {state.doc_type}...")

    # ✅ Ensure memory exists
    memory = getattr(state, "memory", {})

    # ✅ Normalize doc_type
    doc_type = state.doc_type.upper()

    schema = {
        "LETTER OF AUTHORIZATION": {
            "authorizing_party": "",
            "authorized_party": "",
            "authorization_scope": "",
            "effective_dates": "",
            "signatures": ""
        },
        "NOTICE": {
            "notice_type": "",
            "recipient": "",
            "subject": "",
            "important_dates": "",
            "action_required": ""
        },
        "BUSINESS DOCUMENT": {
            "document_type": "",
            "parties_involved": "",
            "key_terms": "",
            "dates": "",
            "amounts": ""
        }
    }

    target_schema = schema.get(doc_type, {"data": "unknown"})

    # ✅ Use memory context (previous documents)
    past_context = ""
    if memory.get("documents"):
        past_context = json.dumps(memory["documents"][-3:], indent=2)  # last 3 docs

    prompt = f"""
You are a strict JSON generator.

Return ONLY valid JSON. No explanation.

Schema:
{json.dumps(target_schema, indent=2)}

Previous similar documents (context):
{past_context}

Rules:
- Fill values from the document
- If missing, use ""
- Do NOT add extra fields

Document:
{state.text[:4000]}
"""

    messages = [
        SystemMessage(content="You extract structured data from documents."),
        HumanMessage(content=prompt)
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    print("----- RAW LLM OUTPUT -----")
    print(content)
    print("--------------------------")

    try:
        if "```" in content:
            content = content.split("```")[1]
            content = content.replace("json", "").strip()

        extraction_data = json.loads(content)

    except Exception as e:
        print(f"Extraction parsing failed: {e}")

        extraction_data = {"error": "Extraction failed"}

    # ✅ UPDATE MEMORY (store extracted data)
    memory.setdefault("documents", []).append({
        "doc": getattr(state, "document_name", "unknown"),
        "type": doc_type,
        "data": extraction_data
    })

    # ✅ Return BOTH extracted data + memory
    return {
        "extracted_data": extraction_data,
        "memory": memory
    }