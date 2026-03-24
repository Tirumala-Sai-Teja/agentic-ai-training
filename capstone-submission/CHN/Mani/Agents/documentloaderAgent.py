import os
from langchain_community.document_loaders import PyPDFLoader, UnstructuredFileLoader

def load_document_text(file_path: str) -> str:
    """
    Detects file type and extracts all text into a single string.
    Supports PDF, DOCX, TXT, and common images.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No file found at {file_path}")

    file_extension = os.path.splitext(file_path)[1].lower()

    try:
        if file_extension == ".pdf":
            # Best for text-based PDFs
            loader = PyPDFLoader(file_path)
        else:
            # Catch-all for .docx, .txt, .jpg, .png (requires 'unstructured')
            loader = UnstructuredFileLoader(file_path)

        docs = loader.load()
        # Join all pages/elements into one continuous string
        full_text = "\n\n".join([doc.page_content for doc in docs])
        return full_text

    except Exception as e:
        return f"Error loading document: {str(e)}"