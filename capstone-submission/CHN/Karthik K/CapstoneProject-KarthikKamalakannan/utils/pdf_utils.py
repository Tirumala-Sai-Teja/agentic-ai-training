import base64
from langchain_core.messages import HumanMessage

def page_to_base64_png(page) -> str:
    """Render a PyMuPDF page to a base64-encoded PNG string."""
    pix = page.get_pixmap(dpi=150)
    png_bytes = pix.tobytes("png")
    return base64.standard_b64encode(png_bytes).decode("utf-8")


def extract_pdf_text_with_vision(pdf_path, vision_llm):
    """
    Extract text from a PDF using Groq's vision model.
    1. Open PDF with PyMuPDF
    2. Render each page as a PNG image
    3. Send all page images to Groq vision model as base64 image_url messages
    4. Collect and concatenate the extracted text per page
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF is required for PDF→image conversion. Install it with: pip install pymupdf"
        )
    doc = fitz.open(pdf_path)
    num_pages = len(doc)
    all_text = []
    print(f"   → {num_pages} page(s) detected — sending to Groq vision model...")
    for page_num, page in enumerate(doc, start=1):
        print(f"   → Extracting page {page_num}/{num_pages}...")
        b64_image = page_to_base64_png(page)
        # Correct message format for Groq vision model
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}},
                    {"type": "text", "text": (
                        f"This is page {page_num} of {num_pages} of a document. "
                        "Extract and return ALL text exactly as it appears. "
                        "Preserve dates, names, addresses, headings, and paragraph structure. "
                        "Do not summarise — return the complete text verbatim."
                    )}
                ]
            }
        ]
        response = vision_llm.invoke(messages)
        page_text = response.content.strip()
        all_text.append(f"--- Page {page_num} ---\n{page_text}")
    doc.close()
    return "\n\n".join(all_text)
