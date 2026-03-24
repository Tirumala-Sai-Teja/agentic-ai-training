from langgraph.graph import StateGraph,START,END
from langgraph.types import Send,Command
from typing import TypedDict, Annotated,Literal
import operator
import csv
from pathlib import Path
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.messages import HumanMessage,SystemMessage
import base64
import io
import fitz
import base64
import json
import sqlite3
from datetime import datetime
# from iPython.display import Image,display

class AgentState(TypedDict):
    # message: Annotated[list[str], operator.add] 
    message :str
    status:str
    directory_path:str
    files:list[Path]
    fileContent :dict
    fileTypes :dict
    currentFile:     dict 
    humanReview:   dict
    auditLog:      Annotated[list[dict], operator.add]

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
llm = ChatGroq(
    api_key = os.getenv("GROQ_API_KEY"),
    temperature=0,
    model= "meta-llama/llama-4-scout-17b-16e-instruct"
)

DB_PATH      = "cease_desist.db"
ARCHIVE_PATH = "irrelevant_archive.json"
AUDIT_PATH   = "auditLog.json"

## Creating the DB if not exists
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cease_documents (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            filename         TEXT NOT NULL,
            content          TEXT,
            label            TEXT,
            confidence_score REAL,
            created_at       TEXT
        )
    """)
    conn.commit()
    conn.close()

    
def routerNode(state:AgentState) -> AgentState:
    if state['status'] == "FAIL":
        return "errorOperation"
    elif state['status'] == "SUCCESS":
        return "successOperation"
    
  
# NODES
def checkFolderNode(state:AgentState) -> dict:
    file_path = state['directory_path']
    status = "FAIL"
    message = ""
    try:
        files = [entry for entry in Path(file_path).iterdir() if entry.is_file()]
        if len(files) ==0:
            status = "FAIL"
            message="File not found"
        else:
            status = "SUCCESS"
            message="Loaded files successfully"
        return {                        
        "files": files,
        "status":    status,
        "message":   message,
        "auditLog": [{              
            "agent":"checkFolderNode",
            "status": status,
            "message": message,
            "actionOutput": {"files": ",".join(map(str, state['files'] or []))},
            "timestamp":    datetime.now().isoformat()
        }]
    }
    except Exception as e:
        return {                        
        "files": {},
        "status":    status,
        "message":   str(e),
        "auditLog": [{              
            "agent":"checkFolderNode",
            "status": status,
            "message": message,
            "actionOutput": {},
            "timestamp":    datetime.now().isoformat()
        }]
    }

def extractFileContentNode(state:AgentState) -> dict:
    """
    Loop through the files in directory, pass to llm to extarct the data.
    """
    status = "SUCCESS"
    message = ""
    extracted = {}
    for file in state['files']:
        try:
            if file.suffix.lower() == '.pdf':
                content = read_pdf(file)
            else:
                content = file.read_text(encoding='utf-8')

            if not content:               
                content = extract_with_vision(file)

            extracted[file.name] = content
        except Exception as e:
            status = "FAIL"
            message = str(e)
            extracted[file.name] = f"Exception Error extracting content: {str(e)}"
            break
                
    if status == "SUCCESS":
        message=f"Successfully extracted {len(extracted)} files"
    return {                          # ← return ONLY changed keys
        "fileContent": extracted,
        "status":    status,
        "message":   message,
        "auditLog": [{              
            "agent":"extractFileContentNode",
            "status": status,
            "message": message,
            "actionOutput": extracted,
            "timestamp":    datetime.now().isoformat()
        }]
    }

def classifyDocumentsNode(state: AgentState) -> dict:
    filetypes = {}
    status = "SUCCESS"
    message = ""
    RUBRIC = """
    Calculate a 'confidence score' and classify based on it:
    - 'Cease'      : confidence score >= 90%  → Valid cease & desist request
    - 'Uncertain'  : confidence score >= 65% and < 90% → Cannot clearly classify
    - 'Irrelevant' : confidence score < 65%   → Not a valid cease & desist request
    """

    SYSTEM_MESSAGE = f"""
    You are an expert AI content classifier and evaluator.
    Your task is to classify the provided document content into one of these categories:
    - Cease
    - Uncertain
    - Irrelevant

    Use this rubric to classify:
    {RUBRIC}

    Always return a valid JSON object with this exact structure:
    {{
        "label": "Cease | Uncertain | Irrelevant",
        "confidence_score": <number between 0 and 100>,
        "reasoning": "Step-by-step analysis of why the document belongs to this category"
    }}
    Return ONLY the JSON object. No extra text, no markdown, no code blocks.
    """

    for filename, content in state['fileContent'].items():
        try:
            USER_MESSAGE = f"Classify the following document content:\n\n{content[:2000]}"

            response = llm.invoke([
                SystemMessage(content=SYSTEM_MESSAGE),
                HumanMessage(content=USER_MESSAGE)
            ])

            raw = response.content.strip()
            # Remove markdown code blocks
            if raw.startswith("```"):
                raw = raw.split("```")[1]          # get content between backticks
                if raw.startswith("json"):
                    raw = raw[4:]                  # remove "json" word after ```
                raw = raw.strip()

            parsed = json.loads(raw)
            filetypes[filename] = parsed
            print(f"  '{filename}' → label: {parsed['label']}, confidence: {parsed['confidence_score']}%")

        except Exception as e:
            status = "FAIL"
            message = str(e)
            filetypes[filename] = {
                "label": "Error",
                "confidence_score": 0,
                "reasoning": f"Error classifying: {str(e)}"
            }
            break
    
    if status == "SUCCESS":
        message=f"Successfully classified {len(filetypes)} files"
    
    return {                          # ← return ONLY changed keys
        "fileTypes": filetypes,
        "status":    status,
        "message":   message,
        "auditLog": [{              
            "agent":"classifyDocumentsNode",
            "status": status,
            "message": message,
            "actionOutput": filetypes,
            "timestamp":    datetime.now().isoformat()
        }]
    }

def routingDeciderNode(state: AgentState) -> Command[Literal['sqlAgentNode', 'fileArchivingAgentNode', 'humanInTheLoopAgentNode', 'auditAgentNode']]:
    """
    Iterates through fileTypes one file at a time.
    Sets currentFile in state and routes to the correct agent.
    Removes the processed file from fileTypes so next call gets the next file.
    """
    remaining = state.get('fileTypes', {})

    # All files processed — go to audit
    if not remaining:
        return Command(
            update={
                "auditLog": [{
                    "agent":        "routingDeciderNode",
                    "status":       "SUCCESS",
                    "message":      "All files routed and processed",
                    "actionOutput": {},
                    "timestamp":    datetime.now().isoformat()
                }]
            },
            goto='auditAgentNode'
        )

    # Pick the next file
    filename, info = next(iter(remaining.items()))
    label = info.get('label')

    # Remove this file from remaining so next iteration moves forward
    updated_remaining = {k: v for k, v in remaining.items() if k != filename}

    update = {
        "currentFile": {"filename": filename, "info": info},
        "fileTypes":   updated_remaining,        # ← shrinks by one each call
        "auditLog": [{
            "agent":        "routingDeciderNode",
            "status":       "SUCCESS",
            "message":      f"Routing '{filename}' → {label}",
            "actionOutput": {"filename": filename, "label": label},
            "timestamp":    datetime.now().isoformat()
        }]
    }

    if label == 'Uncertain':
        return Command(update=update, goto='humanInTheLoopAgentNode')
    elif label == 'Cease':
        return Command(update=update, goto='sqlAgentNode')
    elif label == 'Irrelevant':
        return Command(update=update, goto='fileArchivingAgentNode')
    else:
        # Unknown label — skip to next file
        return Command(update=update, goto='routingDeciderNode')

def sqlAgentNode(state: AgentState) -> Command[Literal['routingDeciderNode']]:
    current   = state['currentFile']
    filename  = current['filename']
    info      = current['info']

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cease_documents (filename, content, label, confidence_score, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            filename,
            state['fileContent'].get(filename, ""),
            info.get('label', 'Cease'),
            info.get('confidence_score', 0),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        print(f" Saved to DB: '{filename}'")

        return Command(
            update={
                "auditLog": [{
                    "agent":        "sqlAgentNode",
                    "status":       "SUCCESS",
                    "message":      f"Saved '{filename}' to DB",
                    "actionOutput": {filename: info},
                    "timestamp":    datetime.now().isoformat()
                }]
            },
            goto='routingDeciderNode'        # ← loop back for next file
        )
    except Exception as e:
        return Command(
            update={
                "status": "FAIL",
                "auditLog": [{
                    "agent":        "sqlAgentNode",
                    "status":       "FAIL",
                    "message":      f"SQL Error on '{filename}': {str(e)}",
                    "actionOutput": {},
                    "timestamp":    datetime.now().isoformat()
                }]
            },
            goto='routingDeciderNode'        # ← still loop back even on error
        )


def fileArchivingAgentNode(state: AgentState) -> Command[Literal['routingDeciderNode']]:
    current  = state['currentFile']
    filename = current['filename']
    info     = current['info']

    try:
        existing = []
        if Path(ARCHIVE_PATH).exists():
            with open(ARCHIVE_PATH, 'r', encoding='utf-8') as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = []

        existing.append({
            "filename":         filename,
            "content":          state['fileContent'].get(filename, ""),
            "label":            info.get('label', 'Irrelevant'),
            "confidence_score": info.get('confidence_score', 0),
            "reasoning":        info.get('reasoning', ''),
            "archived_at":      datetime.now().isoformat()
        })
        print(f" Archived: '{filename}'")

        with open(ARCHIVE_PATH, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=4)

        return Command(
            update={
                "auditLog": [{
                    "agent":        "fileArchivingAgentNode",
                    "status":       "SUCCESS",
                    "message":      f"Archived '{filename}'",
                    "actionOutput": {filename: info},
                    "timestamp":    datetime.now().isoformat()
                }]
            },
            goto='routingDeciderNode'        # ← loop back for next file
        )
    except Exception as e:
        return Command(
            update={
                "status": "FAIL",
                "auditLog": [{
                    "agent":        "fileArchivingAgentNode",
                    "status":       "FAIL",
                    "message":      f"Archive Error on '{filename}': {str(e)}",
                    "actionOutput": {},
                    "timestamp":    datetime.now().isoformat()
                }]
            },
            goto='routingDeciderNode'
        )


def humanInTheLoopAgentNode(state: AgentState) -> Command[Literal['sqlAgentNode', 'fileArchivingAgentNode', 'routingDeciderNode']]:
    current  = state['currentFile']
    filename = current['filename']
    info     = current['info']

    try:
        print("\n" + "="*60)
        print("HUMAN REVIEW REQUIRED")
        print("="*60)
        print(f"\n File      : {filename}")
        print(f" Confidence: {info.get('confidence_score', 0)}%")
        print(f" Reasoning : {info.get('reasoning', 'N/A')}")
        print(f" Preview   :\n{state['fileContent'].get(filename, '')[:500]}...")
        print("-"*60)

        while True:
            decision = input("Enter 'cease' or 'irrelevant': ").strip().lower()
            if decision in ['cease', 'irrelevant']:
                human_label = 'Cease' if decision == 'cease' else 'Irrelevant'
                print(f"  Recorded: '{filename}' → {human_label}")
                break
            else:
                print("  Invalid. Please enter 'cease' or 'irrelevant'.")

        # Update humanReview and currentFile with the decided label
        updated_review = {**state.get('humanReview', {}), filename: human_label}
        updated_current = {"filename": filename, "info": {**info, "label": human_label}}

        update = {
            "humanReview": updated_review,
            "currentFile": updated_current,    # ← update label so next node uses correct one
            "auditLog": [{
                "agent":        "humanInTheLoopAgentNode",
                "status":       "SUCCESS",
                "message":      f"Human decided '{filename}' → {human_label}",
                "actionOutput": {filename: human_label},
                "timestamp":    datetime.now().isoformat()
            }]
        }

        # Route based on human decision
        if human_label == 'Cease':
            return Command(update=update, goto='sqlAgentNode')
        else:
            return Command(update=update, goto='fileArchivingAgentNode')

    except Exception as e:
        return Command(
            update={
                "status": "FAIL",
                "auditLog": [{
                    "agent":        "humanInTheLoopAgentNode",
                    "status":       "FAIL",
                    "message":      f"Human Review Error on '{filename}': {str(e)}",
                    "actionOutput": {},
                    "timestamp":    datetime.now().isoformat()
                }]
            },
            goto='routingDeciderNode'
        )
    
def auditAgentNode(state: AgentState) -> dict:
    """
    Audit Agent — always the final node.
    Runs whether pipeline succeeded or failed at any stage.
    """
    print("\n" + "="*60)
    print("AUDIT AGENT REPORT")
    print("="*60)

    audit_report = {
        "run_timestamp": datetime.now().isoformat(),
        "total_files":   len(state['fileContent']),
        "final_status":  state['status'],
        "agent_results": state['auditLog'],
        "summary": {
            "success": [e['agent'] for e in state['auditLog'] if e['status'] == 'SUCCESS'],
            "failed":  [e['agent'] for e in state['auditLog'] if e['status'] == 'FAIL'],
        }
    }

    for entry in state['auditLog']:
        icon = "✅" if entry['status'] == "SUCCESS" else "❌"
        print(f"  {icon} {entry['agent']:<30} → {entry['status']}")
        if entry.get('error'):
            print(f"     └─ Error  : {entry['error']}")
        if entry.get('files'):
            print(f"     └─ Files  : {entry['files']}")
        if entry.get('decisions'):
            print(f"     └─ Decisions: {entry['decisions']}")

    with open(AUDIT_PATH, 'w', encoding='utf-8') as f:
        json.dump(audit_report, f, indent=4)

    print(f"\n📄 Audit report saved: {AUDIT_PATH}")
    print("="*60)
    message = ("Audit Agent: report generated")
    return {
    "message": message
}

def pdf_page_to_base64(file: Path, page_num: int) -> str:
    """Convert a single PDF page to base64 image using PyMuPDF."""
    doc = fitz.open(str(file))
    page = doc[page_num]
    pix = page.get_pixmap(dpi=200)
    img_bytes = pix.tobytes("png")
    doc.close()
    return base64.b64encode(img_bytes).decode("utf-8")

def extract_with_vision(file: Path) -> str:
    """Use ChatGroq vision model to extract text from scanned/handwritten PDF."""
    print(f"  '{file.name}' sending to ChatGroq Vision...")
    doc = fitz.open(str(file))
    full_text = ""

    for i in range(len(doc)):
        print(f"    Processing page {i+1}/{len(doc)}...")
        image_base64 = pdf_page_to_base64(file, i)

        #LangChain HumanMessage format for vision
        message = HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                },
                {
                    "type": "text",
                    "text": "Extract all the text from this document image accurately. "
                            "Preserve structure and formatting. "
                            "If handwritten, transcribe exactly word by word."
                }
            ]
        )
        response = llm.invoke([message])
        full_text += response.content + "\n"

    doc.close()
    return full_text.strip()
 
def read_pdf(file: Path) -> str:
    """Read PDF using PyPDFLoader - handles both structured and unstructured PDFs."""
    loader = PyPDFLoader(str(file))
    pages = loader.load()                          # returns list of Document objects
    text = "\n".join([page.page_content for page in pages])
    return text.strip()



if __name__ == "__main__":
    init_db()
    graph = StateGraph(AgentState)

    graph.add_node('checkFolderNode',checkFolderNode)
    graph.add_node('routerNode',lambda state:state)
    graph.add_node('extractFileContentNode',extractFileContentNode)
    graph.add_node('classifyDocumentsNode',classifyDocumentsNode)
    graph.add_node("auditAgentNode",auditAgentNode)
    graph.add_node('sqlAgentNode',sqlAgentNode)
    graph.add_node('fileArchivingAgentNode',fileArchivingAgentNode)
    graph.add_node('humanInTheLoopAgentNode',humanInTheLoopAgentNode)
    graph.add_node('routingDeciderNode',routingDeciderNode)
    ### actual flow code
    graph.add_edge(START,'checkFolderNode')
    graph.add_conditional_edges(
        'checkFolderNode',
        routerNode,
        {
            "errorOperation":"auditAgentNode",
            "successOperation":"extractFileContentNode"  # success -> extract
        }
    )
    graph.add_conditional_edges(
    'extractFileContentNode',
    routerNode,
        {
            "errorOperation": "auditAgentNode",
            "successOperation": "classifyDocumentsNode"   # success → classify
        }
    )   
    graph.add_edge('classifyDocumentsNode',  'routingDeciderNode')
    graph.add_edge('auditAgentNode',          END)

    ##############
    
    # graph.add_edge(START, 'classifyDocumentsNode')
    # graph.add_edge('classifyDocumentsNode',  'routingDeciderNode')
    # graph.add_edge('auditAgentNode',          END)

    app = graph.compile()

    # ##### to Read the extracted content from the csv
    # file_content_map = {}
    # with open("extracted_content.csv", mode='r', encoding='utf-8') as csvfile:
    #     reader = csv.reader(csvfile)
    #     next(reader)                              # skip header row
    #     for row in reader:
    #         filename = row[0]
    #         content  = row[1]
    #         file_content_map[filename] = content

    # print(file_content_map)
    #output =app.invoke({"message":[],"directory_path":"Testfiles/","files":[],'fileContent':{}})
    output =app.invoke(
        {
        "message":"",
        "status":"",
        "directory_path":"Testfiles/",
        "files":[],
        'fileContent':{},
        "fileTypes":{},
        "currentFile" :{},
        "humanReview":{},
        "auditLog":[]
        })
    
    # print(output)
    # print(output['fileContent'])
    
    # to print the extracted content to a storage

    # output_path =  "extracted_content.csv"
    # with open(output_path, mode='w', newline='', encoding='utf-8') as csvfile:
    #     writer = csv.writer(csvfile)
    #     writer.writerow(["filename", "content"])              # header
    #     for filename, content in output['fileContent'].items():
    #         writer.writerow([filename, content])
    # print(f"CSV saved at: {output_path}")

    # display(Image(app.get_graph().draw_mermaid_png()))     

