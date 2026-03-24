import os
from typing import Dict, Any
from langchain_community.document_loaders import PyPDFLoader, UnstructuredFileLoader


def load_document_text(file_path: str) -> Dict[str, Any]:
    """
    Loads document and returns structured output:
    - text
    - metadata
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No file found at {file_path}")

    file_extension = os.path.splitext(file_path)[1].lower()
    file_name = os.path.basename(file_path)

    try:
        if file_extension == ".pdf":
            loader = PyPDFLoader(file_path)
        else:
            loader = UnstructuredFileLoader(file_path)

        docs = loader.load()

        full_text = "\n\n".join([doc.page_content for doc in docs])

        metadata = {
            "file_name": file_name,
            "file_type": file_extension,
            "num_pages": len(docs)
        }

        return {
            "text": full_text,
            "metadata": metadata
        }

    except Exception as e:
        raise RuntimeError(f"Document loading failed: {str(e)}")