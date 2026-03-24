from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)

def classify_document(text):

    prompt = f"""
    Act as Document Classifier 
    
    Classify the document into EXACTLY ONE of the following categories:

    Cease → Explicit demand to stop an action immediately  
    Uncertain → Complaint or unclear intent  
    Irrelevant → Not related  

    Rules:
    - If the document contains "cease and desist", "stop communication", or "do not contact", classify as Cease
    - If the intent is unclear or indirect, classify as Uncertain
    - Even if the document is long or contains legal content, prioritize the presence of a stop instruction 
    Return STRICTLY in this format (no extra text):
    
    Category: Cease OR Uncertain OR Irrelevant
    Confidence: <0 to 1>
    

    Do not think aloud. Do not explain.

    Document:
    {text}
    """
    response = llm.invoke(prompt)

    response_text = response.content.strip()

    lines = response_text.split("\n")

    # Default values (fallback)
    label = "Uncertain"
    confidence = 0.5

    # Robust parsing
    for line in lines:
        if "category" in line.lower():
            try:
                label = line.split(":")[1].strip()
            except:
                label = "Uncertain"

        elif "confidence" in line.lower():
            try:
                confidence = float(line.split(":")[1].strip())
            except:
                confidence = 0.5

    return label, confidence