from langgraph.graph import StateGraph,START,END
from src.schema import AgentState
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from dotenv import load_dotenv
import os
from src.nodes import document_loader,document_classifier,save_result_to_db,document_archive,route_classification,route_human_decision
from db_utils.database import init_db

load_dotenv()
init_db()

def create_graph():
    graph=StateGraph(AgentState)

    graph.add_node("document_loader",document_loader)
    graph.add_node("document_classifier",document_classifier)
    graph.add_node("save_result_to_db",save_result_to_db)
    graph.add_node("document_archive",document_archive)
    graph.add_node("human_review", lambda state: state) 

    graph.add_edge(START,"document_loader")
    graph.add_edge("document_loader","document_classifier")
    graph.add_conditional_edges(
        "document_classifier",
        route_classification,
        {
            "save_result_to_db":"save_result_to_db",
            "document_archive":"document_archive",
            "human_review":"human_review"
        })
    graph.add_conditional_edges(
        "human_review",
        route_human_decision,
        {
            "save_result_to_db":"save_result_to_db",
            "document_archive":"document_archive"
        }
    )

    graph.add_edge("save_result_to_db",END)
    graph.add_edge("document_archive",END)

    con=sqlite3.connect(os.getenv("SQLITE_DB_NAME"),check_same_thread=False)
    memory=SqliteSaver(con)

    return graph.compile(checkpointer=memory,interrupt_before=["human_review"])