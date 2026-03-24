from langgraph.graph import StateGraph, END

from agents.classifier_agent import classify_document
from agents.database_agent import store_cease
from agents.archive_agent import archive_document
from agents.human_agent import human_review
from utils.logger import log_event

from typing import TypedDict

class AgentState(TypedDict):
    text: str
    document_name: str
    label: str
    confidence: float

# CLASSIFIER NODE
# -------- CLASSIFIER NODE --------

def classifier_node(state: AgentState):

    # Handle LangGraph wrapped input
    if "text" not in state and "input" in state:
        state = state["input"]

    text = state["text"]
    document_name = state["document_name"]

    label, confidence = classify_document(text)

    print(f"Document {document_name} classified as: {label} (Confidence: {confidence})")

    log_event(f"{document_name} classified as {label} (Confidence: {confidence})")

    state["label"] = label
    state["confidence"] = confidence

    return state


# DATABASE NODE
def database_node(state: AgentState):

    text = state["text"]
    document_name = state["document_name"]

    store_cease(document_name, text)

    log_event(f"{document_name} stored in database")

    return state


# ARCHIVE NODE
def archive_node(state: AgentState):

    document_name = state["document_name"]

    archive_document(document_name)

    log_event(f"{document_name} archived")

    return state


# HUMAN REVIEW NODE
def human_review_node(state: AgentState):

    text = state["text"]
    document_name = state["document_name"]

    decision = human_review(text)

    log_event(f"{document_name} human decision: {decision}")

    if decision.lower() == "cease":
        store_cease(document_name, text)
    else:
        archive_document(document_name)

    return state


# ROUTING
def route_decision(state: AgentState):

    label = state["label"]

    if label == "Cease":
        return "database"

    elif label == "Irrelevant":
        return "archive"

    else:
        return "human_review"


workflow = StateGraph(AgentState)

workflow.add_node("classifier", classifier_node)
workflow.add_node("database", database_node)
workflow.add_node("archive", archive_node)
workflow.add_node("human_review", human_review_node)

workflow.set_entry_point("classifier")

workflow.add_conditional_edges(
    "classifier",
    route_decision,
    {
        "database": "database",
        "archive": "archive",
        "human_review": "human_review"
    }
)

workflow.add_edge("database", END)
workflow.add_edge("archive", END)
workflow.add_edge("human_review", END)

app = workflow.compile()