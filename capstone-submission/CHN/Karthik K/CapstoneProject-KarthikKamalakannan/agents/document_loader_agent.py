from datetime import datetime
from pathlib import Path
from utils.pdf_utils import extract_pdf_text_with_vision

def document_loader_agent(state, vision_llm):
    """Converts PDF pages to images and extracts text via Groq vision."""
    name = Path(state["pdf_path"]).name
    print(f"\n📄 [Document Loader] Converting '{name}' → images → Groq vision...")
    text = extract_pdf_text_with_vision(state["pdf_path"], vision_llm)
    print(f"   → Extraction complete ({len(text)} chars)")
    # Ensure document_name and document_text are set in the state for downstream agents
    state["document_name"] = name
    state["document_text"] = text
    return state
