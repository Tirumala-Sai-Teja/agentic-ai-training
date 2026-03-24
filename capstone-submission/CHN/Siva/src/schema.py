from typing import TypedDict, Optional, List, Annotated,Literal
from pydantic import BaseModel,Field,model_validator
import operator

DocCategory=Literal["Cease","Uncertain","Irrelevant"]

class ClassificationResult(BaseModel):
    sender_name: str = Field(description="Name of the sender; use 'Not Specified' if unknown")
    sender_org: Optional[str] = Field(description="Sender organization; use 'Not Specified' if unknown")
    recipient_name: str = Field(description="Full name of the recipient; use 'Not Specified' if unknown")
    infringement_type: str = Field(description="Type of claim, e.g., Copyright, Trademark, Patent; use 'Not Specified' if unknown")
    subject_matter: str = Field(description="The specific work or asset in question; use 'Not Specified' if unknown")
    reference_no: Optional[str] = Field(description="Internal case or reference number; use 'Not Specified' if unknown")
    demands: List[str] = Field(default_factory=list, description="List of specific actions requested (e.g., 'Remove image', 'Pay fee')")
    monetary_demand: Optional[str] = Field(description="Amount requested, including currency symbol (e.g., '$1,500'); use 'Not Specified' if unknown")
    deadline: Optional[str] = Field(description="Stated deadline in YYYY-MM-DD format if possible; use 'Not Specified' if unknown")
    infringing_url: Optional[str] = Field(description="The specific URL where the infringement occurs; use 'Not Specified' if unknown")

    category: DocCategory = Field(description="Categorize as 'Cease' if the intent is clear, 'Uncertain' if critical identification info is missing, or 'Irrelevant' if not a legal notice.")
    confidence: float = Field(ge=0, le=1, description="Model's confidence in this extraction. A float between 0 and 1, Do NOT use quotes")
    reason: str = Field(description="Brief justification for the chosen category")
    is_human_reviewed: bool = Field(default=False, description="Internal use only. Do not modify.Do NOT use quotes")

    # @model_validator(mode='after')
    # def force_uncertain_category(self) -> 'ClassificationResult':
    #     print(f"At validator check:{self.is_human_reviewed}")
    #     if self.is_human_reviewed:
    #         return self
    #     required_fields = [
    #         self.reference_no, 
    #         self.infringing_url, 
    #         self.deadline, 
    #         self.monetary_demand
    #     ]
        
    #     has_missing_data = any(
    #         val is None or "not specified" in str(val).lower() 
    #         for val in required_fields
    #     )

    #     if has_missing_data and self.category == "Cease":
    #         # Force the change
    #         print("Setting the state value to Uncertain")
    #         self.category = "Uncertain"
    #         self.reason = "Category forced to Uncertain because critical fields (Reference No or URL) are 'Not Specified'."
    #         self.confidence = 1.0
            
    #     return self

    @model_validator(mode='after')
    def force_uncertain_category(self) -> 'ClassificationResult':
        if self.is_human_reviewed or self.category != "Cease":
            return self

        check_fields = {
            "Reference No": self.reference_no,
            "Infringing URL": self.infringing_url,
            "Deadline": self.deadline,
            "Monetary Demand": self.monetary_demand
        }

        missing_names = [
            label for label, val in check_fields.items()
            if val is None or "not specified" in str(val).lower()
        ]

        if missing_names:
            missing_str = ", ".join(missing_names)
            
            self.category = "Uncertain"
            self.reason = f"Category forced to Uncertain because critical fields ({missing_str}) are 'Not Specified'."
            self.confidence = 1.0
            print(f"Forced Uncertain due to: {missing_str}")
            
        return self

class ExtractionResult(BaseModel):
    sender_name: str
    sender_org: Optional[str]
    recipient_name: str
    infringement_type: str = Field(description="e.g., Copyright, Trademark")
    subject_matter: str = Field(description="The specific work, e.g., 'Urban Textures' photos")
    reference_no: Optional[str]
    demands: List[str] = Field(description="List of specific actions requested")
    monetary_demand: Optional[str] = Field(description="Total dollar amount requested, if any")
    deadline: Optional[str]
    infringing_url: Optional[str]

class AgentState(TypedDict):
    document_name: str
    document_bytes: bytes
    document_raw_text: str
    classification: Optional[ClassificationResult]
    extraction: Optional[ExtractionResult]
    human_decision:Optional[str]
    logs: Annotated[List[str],operator.add]
    