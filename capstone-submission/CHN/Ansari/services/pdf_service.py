"""
PDF service for document text extraction.
Provides methods to extract text from PDF files using multiple methods with intelligent fallback.
"""
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional
import pdfplumber
import PyPDF2
from config.settings import PDF_EXTRACTION_METHOD, MAX_PDF_SIZE_MB
import logging

logger = logging.getLogger(__name__)

# Optional OCR support - EasyOCR and PaddleOCR (no system dependencies)
TESseRACT_AVAILABLE = False
EASYOCR_AVAILABLE = False
PADDLEOCR_AVAILABLE = False
FITZ_AVAILABLE = False

try:
    import fitz  # PyMuPDF - pure Python, no system dependencies
    FITZ_AVAILABLE = True
except ImportError:
    logger.warning("PyMuPDF not available. Install with: pip install PyMuPDF")

try:
    from pdf2image import convert_from_path
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    pass

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    pass

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    pass

if not TESSERACT_AVAILABLE and not EASYOCR_AVAILABLE and not PADDLEOCR_AVAILABLE:
    logger.warning("OCR not available. For image-based PDFs, install: pip install easyocr or pip install paddleocr")


def find_poppler_path() -> Optional[str]:
    """
    Try to find poppler installation on system.
    Returns the path to poppler bin directory, or None if not found.
    """
    # Check common Windows installation paths
    if platform.system() == "Windows":
        common_paths = [
            "C:\\Program Files\\poppler\\Library\\bin",
            "C:\\Program Files (x86)\\poppler\\Library\\bin",
            "C:\\poppler\\Library\\bin",
            str(Path.home() / "AppData" / "Local" / "poppler" / "Library" / "bin"),
        ]
        
        for path in common_paths:
            if Path(path).exists():
                logger.info(f"Found poppler at {path}")
                return path
    
    # Try to find pdfinfo in PATH
    try:
        result = subprocess.run(["where" if platform.system() == "Windows" else "which", "pdfinfo"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            poppler_bin = str(Path(result.stdout.strip()).parent)
            logger.info(f"Found pdfinfo in PATH: {poppler_bin}")
            return poppler_bin
    except Exception as e:
        logger.debug(f"Could not find pdfinfo in PATH: {e}")
    
    return None


POPPLER_PATH = find_poppler_path()


class PDFExtractionError(Exception):
    """Raised when PDF extraction fails."""
    pass


class PDFService:
    """
    Service for PDF text extraction.
    
    Supports multiple extraction methods and handles various PDF formats.
    """
    
    @staticmethod
    def validate_pdf(file_path: str) -> None:
        """
        Validate that file exists and is within size limits.
        
        Args:
            file_path: Path to the PDF file
            
        Raises:
            PDFExtractionError: If file doesn't exist or is too large
        """
        path = Path(file_path)
        
        if not path.exists():
            raise PDFExtractionError(f"PDF file not found: {file_path}")
        
        if not path.suffix.lower() == ".pdf":
            raise PDFExtractionError(f"File is not a PDF: {file_path}")
        
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_PDF_SIZE_MB:
            raise PDFExtractionError(
                f"PDF file too large: {file_size_mb:.2f}MB (max: {MAX_PDF_SIZE_MB}MB)"
            )
    
    
    @staticmethod
    def extract_text_pdfplumber(file_path: str) -> tuple[str, int]:
        """
        Extract text from PDF using pdfplumber.
        Fast method for searchable/text-based PDFs.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted_text, page_count)
            
        Raises:
            PDFExtractionError: If extraction fails
        """
        try:
            text_content = []
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    try:
                        text = page.extract_text()
                        if text:
                            text_content.append(text)
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page: {e}")
                        continue
            
            combined_text = "\n".join(text_content)
            if not combined_text.strip():
                raise PDFExtractionError("No text could be extracted from PDF")
            
            return combined_text, page_count
        
        except PDFExtractionError:
            raise
        except Exception as e:
            raise PDFExtractionError(f"pdfplumber extraction failed: {str(e)}")
    
    @staticmethod
    def extract_text_pypdf(file_path: str) -> tuple[str, int]:
        """
        Extract text from PDF using PyPDF2.
        Fallback method if pdfplumber fails.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted_text, page_count)
            
        Raises:
            PDFExtractionError: If extraction fails
        """
        try:
            text_content = []
            with open(file_path, "rb") as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                page_count = len(pdf_reader.pages)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text = page.extract_text()
                        if text:
                            text_content.append(text)
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {e}")
                        continue
            
            combined_text = "\n".join(text_content)
            if not combined_text.strip():
                raise PDFExtractionError("No text could be extracted from PDF")
            
            return combined_text, page_count
        
        except PDFExtractionError:
            raise
        except Exception as e:
            raise PDFExtractionError(f"PyPDF2 extraction failed: {str(e)}")
    
    @staticmethod
    def extract_text_ocr_tesseract(file_path: str) -> tuple[str, int]:
        """
        Extract text from PDF using Tesseract OCR.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted_text, page_count)
            
        Raises:
            PDFExtractionError: If Tesseract not available or extraction fails
        """
        if not TESSERACT_AVAILABLE:
            raise PDFExtractionError(
                "Tesseract OCR not installed. Install with: pip install pdf2image pytesseract. "
                "Also requires Tesseract: https://github.com/UB-Mannheim/tesseract/wiki"
            )
        
        try:
            logger.info(f"Using Tesseract OCR to extract text from {file_path}")
            
            # Convert PDF to images
            images = convert_from_path(file_path, dpi=200, poppler_path=POPPLER_PATH)
            
            if not images:
                raise PDFExtractionError("Could not convert PDF to images for OCR")
            
            text_content = []
            for page_num, image in enumerate(images, 1):
                try:
                    text = pytesseract.image_to_string(image)
                    if text.strip():
                        text_content.append(text)
                    else:
                        logger.warning(f"No text extracted from page {page_num} via Tesseract")
                except Exception as e:
                    logger.warning(f"Tesseract failed for page {page_num}: {e}")
                    continue
            
            combined_text = "\n".join(text_content)
            if not combined_text.strip():
                raise PDFExtractionError("No text could be extracted via Tesseract OCR")
            
            return combined_text, len(images)
        
        except PDFExtractionError:
            raise
        except Exception as e:
            raise PDFExtractionError(f"Tesseract OCR extraction failed: {str(e)}")
    
    @staticmethod
    def extract_text_ocr_easyocr(file_path: str) -> tuple[str, int]:
        """
        Extract text from PDF using EasyOCR (pure Python, no system installation needed).
        Final fallback for image-based PDFs.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted_text, page_count)
            
        Raises:
            PDFExtractionError: If EasyOCR not available or extraction fails
        """
        if not EASYOCR_AVAILABLE:
            raise PDFExtractionError(
                "EasyOCR not installed. Install with: pip install easyocr"
            )
        
        try:
            logger.info(f"Using EasyOCR to extract text from {file_path}")
            
            # Convert PDF to images
            images = convert_from_path(file_path, dpi=200, poppler_path=POPPLER_PATH)
            
            if not images:
                raise PDFExtractionError("Could not convert PDF to images for OCR")
            
            # Initialize EasyOCR reader
            reader = easyocr.Reader(['en'], gpu=False)
            
            text_content = []
            for page_num, image in enumerate(images, 1):
                try:
                    logger.debug(f"Processing page {page_num} with EasyOCR")
                    results = reader.readtext(image, detail=0)  # detail=0 returns text only
                    text = "\n".join(results)
                    if text.strip():
                        text_content.append(text)
                    else:
                        logger.warning(f"No text extracted from page {page_num} via EasyOCR")
                except Exception as e:
                    logger.warning(f"EasyOCR failed for page {page_num}: {e}")
                    continue
            
            combined_text = "\n".join(text_content)
            if not combined_text.strip():
                raise PDFExtractionError("No text could be extracted via EasyOCR")
            
            return combined_text, len(images)
        
        except PDFExtractionError:
            raise
        except Exception as e:
            raise PDFExtractionError(f"EasyOCR extraction failed: {str(e)}")
    
    @staticmethod
    def pdf_to_images_fitz(file_path: str, dpi: int = 200) -> list:
        """
        Convert PDF to images using PyMuPDF (pure Python, no system dependencies).
        
        Args:
            file_path: Path to the PDF file
            dpi: Resolution in DPI (default 200)
            
        Returns:
            List of PIL Image objects
            
        Raises:
            PDFExtractionError: If conversion fails
        """
        if not FITZ_AVAILABLE:
            raise PDFExtractionError(
                "PyMuPDF not installed. Install with: pip install PyMuPDF"
            )
        
        try:
            from PIL import Image
            import io
            
            logger.debug(f"Converting PDF to images using PyMuPDF at {dpi} DPI")
            pdf_document = fitz.open(file_path)
            images = []
            
            # Convert DPI to zoom level (default is 72 DPI)
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            
            for page_num, page in enumerate(pdf_document, 1):
                try:
                    pix = page.get_pixmap(matrix=mat)
                    # Convert to PIL Image
                    img_data = pix.tobytes("ppm")
                    img = Image.open(io.BytesIO(img_data))
                    images.append(img)
                    logger.debug(f"Converted page {page_num} to image")
                except Exception as e:
                    logger.warning(f"Failed to convert page {page_num}: {e}")
                    continue
            
            pdf_document.close()
            
            if not images:
                raise PDFExtractionError("Could not convert any PDF pages to images")
            
            return images
        
        except PDFExtractionError:
            raise
        except Exception as e:
            raise PDFExtractionError(f"PyMuPDF conversion failed: {str(e)}")
    
    @staticmethod
    def extract_text_ocr_paddle(file_path: str) -> tuple[str, int]:
        """
        Extract text from PDF using PaddleOCR (pure Python, no system dependencies).
        Excellent for image-based PDFs with no Poppler/Tesseract dependency.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted_text, page_count)
            
        Raises:
            PDFExtractionError: If PaddleOCR not available or extraction fails
        """
        if not PADDLEOCR_AVAILABLE:
            raise PDFExtractionError(
                "PaddleOCR not installed. Install with: pip install paddleocr paddlepaddle"
            )
        
        try:
            logger.info(f"Using PaddleOCR to extract text from {file_path}")
            
            # Convert PDF to images using PyMuPDF (pure Python)
            if FITZ_AVAILABLE:
                images = PDFService.pdf_to_images_fitz(file_path, dpi=200)
            else:
                raise PDFExtractionError(
                    "PyMuPDF required for image extraction. Install with: pip install PyMuPDF"
                )
            
            if not images:
                raise PDFExtractionError("Could not convert PDF to images")
            
            # Initialize PaddleOCR
            ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False)
            
            text_content = []
            for page_num, image in enumerate(images, 1):
                try:
                    logger.debug(f"Processing page {page_num} with PaddleOCR")
                    # Convert PIL Image to numpy array
                    import numpy as np
                    img_array = np.array(image)
                    
                    # Run OCR
                    results = ocr.ocr(img_array, cls=True)
                    
                    # Extract text from results
                    if results:
                        page_text = []
                        for line in results:
                            if line:
                                for detection in line:
                                    text = detection[1][0]
                                    if text.strip():
                                        page_text.append(text)
                        
                        if page_text:
                            text_content.append("\n".join(page_text))
                            logger.debug(f"Extracted {len(page_text)} text items from page {page_num}")
                        else:
                            logger.warning(f"No text extracted from page {page_num} via PaddleOCR")
                except Exception as e:
                    logger.warning(f"PaddleOCR failed for page {page_num}: {e}")
                    continue
            
            combined_text = "\n".join(text_content)
            if not combined_text.strip():
                raise PDFExtractionError("No text could be extracted via PaddleOCR")
            
            return combined_text, len(images)
        
        except PDFExtractionError:
            raise
        except Exception as e:
            raise PDFExtractionError(f"PaddleOCR extraction failed: {str(e)}")
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean extracted text by removing extra whitespace and normalizing.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        lines = text.split("\n")
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        cleaned_text = "\n".join(cleaned_lines)
        
        # Normalize quotes
        cleaned_text = cleaned_text.replace(""", '"').replace(""", '"')
        cleaned_text = cleaned_text.replace("'", "'").replace("'", "'")
        
        return cleaned_text
    
    @staticmethod
    def extract_text(
        file_path: str,
        method: Optional[str] = None,
        fallback: bool = True
    ) -> tuple[str, int]:
        """
        Extract text from PDF file with intelligent fallback chain.
        
        Tries extraction methods in order:
        1. pdfplumber (fast, for text-based PDFs)
        2. PyPDF2 (fallback)
        3. PaddleOCR (for image-based PDFs, pure Python - no system dependencies)
        4. EasyOCR (alternative OCR)
        5. Tesseract OCR (if available with system dependencies)
        
        Args:
            file_path: Path to the PDF file
            method: Extraction method ('pdfplumber', 'pypdf', or 'ocr'). Uses config default if None.
            fallback: If True, falls back to alternate method on failure
            
        Returns:
            Tuple of (extracted_text, page_count)
            
        Raises:
            PDFExtractionError: If all extraction methods fail
        """
        logger.info(f"Extracting text from PDF: {file_path}")
        
        # Validate PDF
        PDFService.validate_pdf(file_path)
        
        # Determine method
        extraction_method = method or PDF_EXTRACTION_METHOD
        
        try:
            if extraction_method == "pdfplumber":
                text, page_count = PDFService.extract_text_pdfplumber(file_path)
            elif extraction_method == "pypdf":
                text, page_count = PDFService.extract_text_pypdf(file_path)
            elif extraction_method == "ocr":
                # Try PaddleOCR first (pure Python, no system dependencies)
                if PADDLEOCR_AVAILABLE:
                    try:
                        logger.debug("Attempting OCR with PaddleOCR (pure Python)")
                        text, page_count = PDFService.extract_text_ocr_paddle(file_path)
                    except PDFExtractionError as e:
                        logger.warning(f"PaddleOCR failed: {str(e)}")
                        # Try Tesseract next
                        if TESSERACT_AVAILABLE:
                            try:
                                logger.info("Falling back to Tesseract OCR")
                                text, page_count = PDFService.extract_text_ocr_tesseract(file_path)
                            except PDFExtractionError:
                                # Try EasyOCR last
                                if EASYOCR_AVAILABLE:
                                    logger.info("Falling back to EasyOCR")
                                    text, page_count = PDFService.extract_text_ocr_easyocr(file_path)
                                else:
                                    raise
                        elif EASYOCR_AVAILABLE:
                            logger.info("Falling back to EasyOCR")
                            text, page_count = PDFService.extract_text_ocr_easyocr(file_path)
                        else:
                            raise
                # Try Tesseract if PaddleOCR not available
                elif TESSERACT_AVAILABLE:
                    try:
                        logger.debug("Attempting OCR with Tesseract")
                        text, page_count = PDFService.extract_text_ocr_tesseract(file_path)
                    except PDFExtractionError as e:
                        logger.warning(f"Tesseract failed: {str(e)}")
                        if EASYOCR_AVAILABLE:
                            logger.info("Falling back to EasyOCR")
                            text, page_count = PDFService.extract_text_ocr_easyocr(file_path)
                        else:
                            raise
                # Try EasyOCR if neither PaddleOCR nor Tesseract available
                elif EASYOCR_AVAILABLE:
                    logger.debug("Attempting OCR with EasyOCR")
                    text, page_count = PDFService.extract_text_ocr_easyocr(file_path)
                else:
                    raise PDFExtractionError(
                        "No OCR engine available. Install: pip install paddleocr paddepaddle (recommended - pure Python) "
                        "or pip install easyocr (requires PyMuPDF for image conversion)"
                    )
            else:
                raise PDFExtractionError(f"Unknown extraction method: {extraction_method}")
            
            # Clean text
            cleaned_text = PDFService.clean_text(text)
            logger.info(f"Successfully extracted {page_count} pages, {len(cleaned_text)} characters")
            
            return cleaned_text, page_count
        
        except PDFExtractionError as e:
            logger.warning(f"PDF extraction failed with {extraction_method}: {str(e)}")
            
            if fallback and extraction_method == "pdfplumber":
                logger.info("Falling back to PyPDF2 extraction")
                return PDFService.extract_text(file_path, method="pypdf", fallback=True)
            elif fallback and extraction_method == "pypdf":
                logger.info("Falling back to OCR extraction (for image-based PDFs)")
                return PDFService.extract_text(file_path, method="ocr", fallback=False)
            else:
                raise PDFExtractionError(f"All PDF extraction methods failed: {str(e)}")
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """
        Get metadata about PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with file metadata
        """
        path = Path(file_path)
        return {
            "file_path": str(path),
            "file_name": path.name,
            "file_size_bytes": path.stat().st_size,
            "file_size_mb": path.stat().st_size / (1024 * 1024),
            "created_at": path.stat().st_ctime,
            "modified_at": path.stat().st_mtime,
        }
