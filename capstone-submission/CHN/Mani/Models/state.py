from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class DocumentState:
    file_path: str
    document_name: Optional[str] = None
    text: Optional[str] = None
    metadata: Optional[Dict] = None
    doc_type: Optional[str] = None
    extracted_data: Optional[Dict] = None
    confidence: Optional[float] = None
    needs_review: Optional[bool] = False
    final_output: Optional[Dict] = None