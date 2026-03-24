from pdf2image import convert_from_path
import pytesseract
import os

def ocr_tool(state):
    print("[OCR] Checking if OCR is needed...")

    # Skip if text exists
    if getattr(state, "text", None) and len(state.text.strip()) > 50:
        print("[OCR] Text already present, skipping OCR")
        return state

    #UPDATE THIS PATH to your actual Poppler bin folder
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    tesseract_path = os.path.join(BASE_DIR, "..", "Tesseract-OCR", "tesseract.exe")
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    POPPLER_PATH = poppler_path = os.path.join(BASE_DIR, "..", "poppler", "Library", "bin")

    try:
        ext = os.path.splitext(state.file_path)[1].lower()
        
        if ext == ".pdf":
            print("[OCR] Converting PDF to images using Poppler...")
            # Pass poppler_path directly here
            pages = convert_from_path(state.file_path, 300, poppler_path=POPPLER_PATH)
            
            extracted_text = ""
            for page in pages:
                extracted_text += pytesseract.image_to_string(page) + "\n"
            
            state.text = extracted_text
            print(f"[OCR] Success! Extracted {len(extracted_text)} characters.")
            
        elif ext in [".png", ".jpg", ".jpeg"]:
            from PIL import Image
            state.text = pytesseract.image_to_string(Image.open(state.file_path))

    except Exception as e:
        print(f"[OCR] Failed: {str(e)}")
        # If OCR fails, we MUST ensure text isn't None for the next node
        if not getattr(state, "text", None):
            state.text = "ERROR: OCR Failed to extract text."

    return state