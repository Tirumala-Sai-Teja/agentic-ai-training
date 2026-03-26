"""
PDF to Markdown Converter
Supports both native (text-based) and scanned (image-based) PDFs.

Dependencies:
    pip install pdfplumber pypdf pytesseract Pillow pymupdf
    System: sudo apt install tesseract-ocr poppler-utils   (Linux)
            brew install tesseract poppler                  (macOS)
"""

import os
import re
import sys
import fitz          # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
from pypdf import PdfReader
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ─────────────────────────────────────────────
# 1.  Detect whether the PDF is native or scanned
# ─────────────────────────────────────────────

def is_scanned_pdf(pdf_path: str, sample_pages: int = 3) -> bool:
    """
    Returns True if the PDF is scanned (no extractable text).
    Checks up to `sample_pages` pages before deciding.
    """
    reader = PdfReader(pdf_path)
    pages_to_check = min(sample_pages, len(reader.pages))
    total_chars = sum(
        len(reader.pages[i].extract_text() or "")
        for i in range(pages_to_check)
    )
    return total_chars < 50  # fewer than 50 chars → almost certainly a scan


# ─────────────────────────────────────────────
# 2.  Extract text from a native PDF
# ─────────────────────────────────────────────

def extract_native_text(pdf_path: str) -> list[dict]:
    """
    Extracts text page-by-page from a native PDF using pdfplumber.
    Returns a list of dicts: {page_num, text, tables}
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            tables = page.extract_tables() or []
            pages.append({"page_num": i, "text": text, "tables": tables})
    return pages


# ─────────────────────────────────────────────
# 3.  OCR a scanned PDF with pytesseract
# ─────────────────────────────────────────────

def ocr_pdf(pdf_path: str, dpi: int = 200) -> list[dict]:
    """
    Rasterises each page with PyMuPDF and runs Tesseract OCR on it.
    Returns a list of dicts: {page_num, text, tables}
    """
    doc = fitz.open(pdf_path)
    pages = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)   # scale factor from 72-DPI base

    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(img, lang="eng")
        pages.append({"page_num": i, "text": text, "tables": []})

    doc.close()
    return pages


# ─────────────────────────────────────────────
# 4.  Convert a list of page dicts → Markdown
# ─────────────────────────────────────────────

def table_to_markdown(table: list[list]) -> str:
    """Converts a pdfplumber table (list of rows) to a Markdown table."""
    if not table:
        return ""

    # Normalise cells: replace None with empty string
    rows = [[str(cell or "").strip() for cell in row] for row in table]

    # Use the first row as the header
    header = rows[0]
    separator = ["---"] * len(header)
    body = rows[1:]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def clean_text(text: str) -> str:
    """Light cleanup: collapse multiple blank lines, strip trailing spaces."""
    text = re.sub(r"\n{3,}", "\n\n", text)      # max 2 consecutive newlines
    text = re.sub(r" +\n", "\n", text)           # trailing spaces
    return text.strip()


def heuristic_headings(text: str) -> str:
    """
    Simple heuristic: lines that are SHORT, ALL-CAPS or Title-Cased,
    and not ending with punctuation are treated as headings.
    Adjust the regex to match your document's style.
    """
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        # Heading candidate: ≤80 chars, title-cased or ALL-CAPS, no trailing period
        if (
            stripped
            and len(stripped) <= 80
            and not stripped.endswith((".", ",", ";", ":"))
            and (stripped.isupper() or stripped.istitle())
        ):
            result.append(f"## {stripped}")
        else:
            result.append(line)
    return "\n".join(result)


def pages_to_markdown(pages: list[dict], add_page_dividers: bool = True) -> str:
    """
    Combines page dicts into a single Markdown string.
    Optionally inserts `---` dividers between pages.
    """
    md_parts = []

    for page in pages:
        page_md = []

        if add_page_dividers and page["page_num"] > 1:
            page_md.append(f"\n---\n*Page {page['page_num']}*\n")

        # Apply heading heuristics to the raw text
        text = heuristic_headings(clean_text(page["text"]))
        if text:
            page_md.append(text)

        # Append any tables found on this page
        for table in page.get("tables", []):
            table_md = table_to_markdown(table)
            if table_md:
                page_md.append("\n" + table_md + "\n")

        md_parts.append("\n".join(page_md))

    return "\n".join(md_parts)


# ─────────────────────────────────────────────
# 5.  Main entry point
# ─────────────────────────────────────────────

def pdf_to_markdown(
    pdf_path: str,
    output_path: str | None = None,
    force_ocr: bool = False,
    dpi: int = 200,
    add_page_dividers: bool = True,
) -> dict:
    """
    Convert a PDF (native or scanned) to Markdown.

    Args:
        pdf_path:          Path to the input PDF.
        output_path:       Optional path to write the .md file.
        force_ocr:         Set True to always use OCR (even for native PDFs).
        dpi:               DPI for rasterisation when OCR is used (higher = better but slower).
        add_page_dividers: Insert `---` dividers between pages.

    Returns:
        A dictionary with 'pages' (list of page dicts) and 'markdown' (str).
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    scanned = force_ocr or is_scanned_pdf(pdf_path)
    mode = "OCR (scanned)" if scanned else "native text"
    print(f"[pdf_to_markdown] Detected mode: {mode}")
    print(f"[pdf_to_markdown] Processing: {pdf_path}")

    pages = ocr_pdf(pdf_path, dpi=dpi) if scanned else extract_native_text(pdf_path)

    print(f"[pdf_to_markdown] Extracted {len(pages)} page(s)")

    markdown = pages_to_markdown(pages, add_page_dividers=add_page_dividers)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"[pdf_to_markdown] Saved to: {output_path}")

    return {'pages': pages, 'markdown': markdown, 'mode': mode, 'extracted_pages': len(pages), 'input_pdf': pdf_path}


# ─────────────────────────────────────────────
# 6.  CLI usage
# ─────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_markdown.py <input.pdf> [output.md] [--force-ocr]")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_md = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    force_ocr = "--force-ocr" in sys.argv

    # Default output path: same name as PDF but with .md extension
    if output_md is None:
        output_md = os.path.splitext(input_pdf)[0] + ".md"

    result = pdf_to_markdown(
        pdf_path=input_pdf,
        output_path=output_md,
        force_ocr=force_ocr,
    )

    print("\n── Preview (first 500 chars) ──────────────────")
    print(result[:500])
