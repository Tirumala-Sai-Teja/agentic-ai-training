from tools.loader_tool import load_document_text
from langgraph.graph import StateGraph, END
from Models.state import DocumentState
from tools.loader_tool import load_document_text
from tools.ocr_tool import ocr_tool
from Agents.classifier_agent import classify 
from Agents.extraction_agent import extract
from Agents.validation_agent import validate
from Agents.hitl_agent import human_review
from Agents.audit_agent import audit
from Databaseactivities.db import save_to_db
from Agents.archive_agent import archive_document

def load_node(state: DocumentState) -> DocumentState:
    print("[Loader] Loading document...")

    result = load_document_text(state.file_path)

    state.text = result["text"]
    state.metadata = result["metadata"]

    return state

def route_review(state):
    return "hitl" if state.needs_review else "save"

def build_graph():
    # 1. Initialize FIRST
    print("Building state graph...")
    builder = StateGraph(DocumentState)
    # 2. Define Nodes
    builder.add_node("load", load_node) # Use your wrapper function, not the tool directly
    builder.add_node("ocr", ocr_tool)
    builder.add_node("classify", classify)
    builder.add_node("extract", extract)
    builder.add_node("validate", validate)
    builder.add_node("hitl", human_review)
    builder.add_node("save", save_to_db)
    builder.add_node("audit", audit)
    builder.add_node("archive", archive_document)

    # 3. Define Edges & Flow
    builder.set_entry_point("load")
    builder.add_edge("load", "ocr")
    builder.add_edge("ocr", "classify")
    builder.add_edge("classify", "extract")
    builder.add_edge("extract", "validate")
    
    builder.add_conditional_edges(
        "validate",
        route_review,
        {
            "hitl": "hitl",
            "save": "save"
        }
    )
    builder.add_edge("hitl", "save")
    builder.add_edge("save", "audit")
    builder.add_edge("audit", "archive") # Added this so archive actually runs!
    builder.add_edge("archive", END)

    # 4. Compile
    return builder.compile()
    