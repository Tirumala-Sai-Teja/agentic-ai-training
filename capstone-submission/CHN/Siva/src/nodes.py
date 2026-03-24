from src.schema import AgentState, ClassificationResult, ExtractionResult
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
import fitz
import base64
from langchain_core.messages import HumanMessage
import os
from db_utils.database import save_extraction_result

load_dotenv()
logger = logging.getLogger(__name__)

llm=ChatGroq(
    model=os.getenv("GROQ_MODEL"),
    temperature=0
)

def document_loader(state:AgentState)->AgentState:
    """
    Used to load the document by extracting the raw text details from the given document
    """
    try:
        logger.info("Document Loader Agent - started")
        doc_bytes = state.get("document_bytes")

        if not doc_bytes    :
            raise ValueError("No document data provided")
        
        with fitz.open(stream=doc_bytes, filetype="pdf") as doc:
            full_text = ""
            full_response = []
            if len(doc[0].get_text().strip()) <= 50:
                logger.info("Given PDF is a scanned file. OCR/multi model is need to extract the details")
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    base64_image = base64.b64encode(img_bytes).decode('utf-8')

                    content = [
                        {"type": "text", "text": f"Extract all text and tables from page {i+1} of this document."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                        }
                    ]
                    
                    print(f"Processing page {i+1}...")
                    message = HumanMessage(content=content)
                    page_response = llm.invoke([message])
                    full_response.append(page_response.content)
                full_text="\n\n--- Page Break ---\n\n".join(full_response)
                return {
                            "logs":["PDF document details are extracted as text content using LLM"],
                            "document_raw_text":full_text
                        }
            else:
                logger.info("Given PDF is a regular/digital file. No OCR is needed")
                for page in doc:
                    full_text += page.get_text()
                return {
                            "logs":["PDF document details are extracted as text content using normal PDF reader"],
                            "document_raw_text":full_text
                        }
        
        logger.info("Document Loader Agent - ended")

    except Exception as e:
        logger.error(f"Error in document_loader: {str(e)}")
        raise e

def document_classifier(state:AgentState)->AgentState:
    """
    Classify the given input document to correct type
    """
    try:
        logger.info("Classify document - started")
        structured_llm=llm.with_structured_output(ClassificationResult)

        CLASSIFICATION_PROMPT = """
                        You are an expert in document extraction. Extract all the details from the document. 
                        
                        CRITICAL RULE: 
                        Only set to 'Cease' if the document is a demand letter and NO fields are 'Not Specified'.
                        If the document text is minimal, generic (e.g., 'Test'), or does not contain legal/infringement details, classify the category as 'Irrelevant'.

                        Document Text: {document_text}
                        """
        prompt=ChatPromptTemplate.from_template(CLASSIFICATION_PROMPT)
        chain=prompt|structured_llm

        result=chain.invoke({"document_text":state.get("document_raw_text")})
        logger.info(f"Classified document as: {result.category}. with confidence: {result.confidence}")
        logger.info("Classify document - ended")
        print(f"At Classification node [is_human_reviewed] - {result.is_human_reviewed}")
        
        result.is_human_reviewed = False
        return {
            "classification":result,
            "extraction":result,
            "logs":["Document classification completed"]
        }
    except Exception as e:
        logger.error(f"Error in classify document: {str(e)}")
        raise e

def save_result_to_db(state:AgentState,config: RunnableConfig)->AgentState:
    """
    This step is used to save the extracted details to database
    """
    try:
        logger.info("Saving extracted result to database - started")
        thread_id = config["configurable"].get("thread_id")
        classification_result = state.get("classification")
        save_extraction_result(
            thread_id=thread_id,
            doc_name=state.get("document_name"),
            doc_type=classification_result.category,
            confidence=classification_result.confidence,
            reason=classification_result.reason,
            doc_bytes=state.get("document_bytes"),
            pydantic_data=state.get("classification")
        )
        return {
            "logs":["Saved extracted details to database"]
        }
    except Exception as e:
        logger.error(f"Error in saving extracted details to database: {str(e)}")
        raise e

def document_archive(state:AgentState)->AgentState:
    """
    Handles the irrelevant document by writing the file name in the flat file
    """
    try:
        logger.info("Writing unknown file details to flat file")
        from datetime import datetime
        with open("Result.txt", "a") as file:
            file.write(f"{state['document_name']} - classified as irrelevant document\n")
            file.write(f"Reason: {state['classification'].reason}\n")
            file.write(f'Classified On: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}\n')
            file.write("---------------------------------------------------\n")
        
        return {
            "logs":["Given document is irrelevant type - Status updated in Result.txt flat file and archived"]
        }
    except Exception as e:
        logger.error(f"Error in writing irrelevant document details to flat file: {str(e)}")
        raise e

def route_classification(state: AgentState):
    classification = state.get("classification")
    
    threshold = float(os.getenv("CLASSIFICATION_CONFIDENCE_THRESHOLD_HITL", 0.9))
    confidence = round(classification.confidence, 2)
    
    print(f"Classified Confidence: {confidence}")
    
    if (classification.is_human_reviewed or confidence >= threshold) and classification.category == "Cease":
        return "save_result_to_db"
    
    if classification.category == "Uncertain" or confidence < threshold:
        return "human_review"

    return "document_archive"

def route_human_decision(state: AgentState):
    #decision = state.get("human_decision")
    print(f"Routing Decision. Category is: {state['classification'].category}")
    logger.info(f"Routing Decision. Category is: {state['classification'].category}")
    category = state["classification"].category
    if category == "Cease":
        return "save_result_to_db"
    else:
        return "document_archive"