import PyPDF2
from pdf2image import convert_from_path
from easyocr import Reader

from pathlib import Path
from typing import List, Tuple
import logging
from PIL import Image
import os
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

logger = logging.getLogger(__name__)

def load_documents(folder_path, supported_formats: set = None) -> List[Tuple[str, str]]:
    folder_path = Path(folder_path)
    if not folder_path.exists():
        raise ValueError(f"Folder path {folder_path} does not exist")

    if supported_formats is None:
        supported_formats = {".pdf", ".png", ".jpg", ".jpeg"}

    documents = []
    logger.info(f"Loading documents from {folder_path}")
    logger.info(f"Supported file formats: {supported_formats}")

    try:
        for file_path in folder_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                documents.append((str(file_path), file_path.name))
                logger.info(f"Loaded document: {file_path.name}")
    except Exception as e:
        logger.error(f"Error loading documents: {e}")
        raise

    logger.info(f"Total documents loaded: {len(documents)}")
    return documents

def _preprocess_image(image):
    """Preprocess image for better OCR results."""
    try:
        import cv2
        import numpy as np

        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        img = cv2.bilateralFilter(img, 9, 75, 75)
        img = cv2.adaptiveThreshold(
            img,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            21,
            10,
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
        return Image.fromarray(img)
    except Exception as e:
        logger.warning(f"Image preprocessing failed ({e}), using raw image")
        return image

def extract_text(file_path: str) -> str:
    """
    Extract text from a given file and fall back to OCR when needed.

    Args:
        file_path: Path to the document file

    Returns:
        Extracted text
    """

    from src.config.config import OCR_DPI, OCR_LANG, OCR_USE_GPU

    path = Path(file_path)
    suffix = path.suffix.lower()
    extracted_text = ""

    if not path.exists():
        logger.error(f"File does not exist: {file_path}")
        return ""

    try:
        # First pass: direct extraction for machine-readable files.
        if suffix == ".pdf":
            import PyPDF2
            with open(file_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                parts = []
                for page in pdf_reader.pages:
                    parts.append(page.extract_text() or "")
                extracted_text = "\n".join(parts).strip()

        elif suffix == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                extracted_text = file.read().strip()

        elif suffix in {".png", ".jpg", ".jpeg"}:
            # For images, OCR is the primary extraction path.
            extracted_text = ""

        else:
            logger.error(f"Unsupported file format: {suffix}")
            return ""
    except Exception as e:
        logger.warning(f"Primary text extraction failed for {file_path}: {e}")
        extracted_text = ""

    # Fallback: OCR if nothing useful was extracted.
    if not extracted_text:
        try:
            from src.config.config import OCR_DPI, OCR_LANG, OCR_USE_GPU

            ocr_lang = "en" if OCR_LANG.lower() in {"eng", "english"} else OCR_LANG
            import numpy as np
            reader = Reader([ocr_lang], gpu=OCR_USE_GPU)
            ocr_parts = []

            if suffix == ".pdf":
                images = convert_from_path(file_path, dpi=OCR_DPI)
                for image in images:
                    image = _preprocess_image(image)
                    ocr_result = reader.readtext(
                        np.array(image),
                        detail=0,
                        paragraph=True,
                    )
                    ocr_parts.append(" ".join(ocr_result).strip())

            elif suffix in {".png", ".jpg", ".jpeg"}:
                image = Image.open(file_path)
                image = _preprocess_image(image)
                ocr_result = reader.readtext(
                    np.array(image),
                    detail=0,
                    paragraph=True,
                )
                ocr_parts.append(" ".join(ocr_result).strip())

            extracted_text = "\n".join([p for p in ocr_parts if p]).strip()

        except ImportError:
            logger.warning(
                "EasyOCR dependencies missing. Install with: pip install easyocr pdf2image pillow"
            )
            return ""
        except Exception as e:
            logger.error(f"OCR extraction failed for {file_path}: {e}")
            return ""

    if not extracted_text:
        logger.warning(f"No text extracted from file: {file_path}")
        return ""

    return extracted_text


class DocumentProcesser:
    @staticmethod
    def _preprocess_image(image):
        return _preprocess_image(image)

    @staticmethod
    def extract_text(file_path: str) -> str:
        return extract_text(file_path)
