import os
from pathlib import Path
from src.graph import create_graph
import uuid

app=create_graph()
document_folder_path = "docs"

def process_pdfs_individually(folder_dir):
    pdf_files = list(Path(folder_dir).glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {folder_dir}")
        return

    for path in pdf_files:
        print(f"\n--- Processing: {path.name} ---")
        thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        
        with open(path, 'rb') as file:
            pdf_content = file.read()
        
        input_data = {"document_bytes": pdf_content,"document_name":path.name}
        
        for event in app.stream(input_data, config=thread_config):
            for value in event.values():
                print("------------------------")
                print(f"Response for {path.name}:", value)

if __name__ == "__main__":
    process_pdfs_individually(document_folder_path)

