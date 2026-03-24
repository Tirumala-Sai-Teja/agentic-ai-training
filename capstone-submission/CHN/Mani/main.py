import os
import json
import warnings
from typing import Dict, Any
from dotenv import load_dotenv

# Import the graph builder from your stateGraph file
from stateGraph import build_graph

# Ignore specific Pydantic/LangChain deprecation warnings for cleaner logs
warnings.filterwarnings("ignore")
load_dotenv()

def run_document_pipeline():
    """
    Main entry point to trigger the Agentic Graph for all documents 
    in the 'documents' folder.
    """
    
    # 1. Compile the Graph
    # This calls your build_graph() in stateGraph.py which connects 
    # load -> ocr -> classify -> extract -> validate -> etc.
    app = build_graph()
    print("Agentic Graph Compiled. Starting Processing...\n")

    folder_path = "documents"
    
    # Ensure the directory exists
    if not os.path.exists(folder_path):
        print(f" Error: The folder '{folder_path}' was not found.")
        return

    # List all supported files
    files = [
        f for f in os.listdir(folder_path)
        if f.endswith((".pdf", ".txt", ".docx"))
    ]

    if not files:
        print("No documents found in the folder.")
        return

    final_results = []

    # 2. Iterate through files and invoke the Graph for EACH one
    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        print(f"\n--- 📄 Processing: {file_name} ---")

        # Define the Initial State for the Graph
        # This matches the schema in your DocumentState
        initial_state = {
            "file_path": file_path,
            "text": "",
            "metadata": {},
            "doc_type": "UNKNOWN",
            "extraction": {},
            "needs_review": False,
            "confidence_score": 0.0
        }

        try:
            # 3. INVOKE THE GRAPH
            # This is where 'load_node', 'ocr_tool', etc., are actually called in order.
            final_state = app.invoke(initial_state)
            
            # Store the final state for reporting
            final_results.append({
                "file": file_name,
                "doc_type": final_state.get("doc_type"),
                "confidence": final_state.get("confidence_score"),
                "status": "REVIEW_REQUIRED" if final_state.get("needs_review") else "COMPLETED"
            })
            
            print(f"Success: {file_name} processed as {final_state.get('doc_type')}")

        except Exception as e:
            print(f"Error processing {file_name}: {str(e)}")
            final_results.append({"file": file_name, "status": "ERROR", "error": str(e)})

    # 4. Final Summary Report
    print("\n" + "="*50)
    print("FINAL BATCH REPORT")
    print("="*50)
    print(json.dumps(final_results, indent=2))

if __name__ == "__main__":
    run_document_pipeline()