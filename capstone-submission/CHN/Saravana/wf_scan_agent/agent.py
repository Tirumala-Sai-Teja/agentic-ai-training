import os
import shutil
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
import pdfplumber
import litellm
import sqlite3
import uuid
from datetime import datetime

high_confidence_path = r"\wf_scan_agent\high_confidence_folder"
low_confidence_path = r"\wf_scan_agent\low_confidence_folder"
tool_content = "Use the extracted text from the PDF to find if the content is a cease and desist letter or cease & desist. Based on your confidence in the answer, respond to the Manager agent with score from 0 to 100. If you have no confidence give 0. If confidence is very high give 100. Always provide a score. If you have some confidence, give a score between 0 and 100. Always provide an answer to the user's question based on the extracted text, even if the confidence is low." 

# Database functions for session management
def init_db():
    """Initialize the SQLite database and create sessions table if it doesn't exist."""
    conn = sqlite3.connect('sessions.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        user_input TEXT NOT NULL,
        agent_response TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()

def save_session(session_id, user_input, agent_response):
    """Save a session interaction to the database."""
    conn = sqlite3.connect('sessions.db')
    c = conn.cursor()
    c.execute('INSERT INTO sessions (session_id, user_input, agent_response, timestamp) VALUES (?, ?, ?, ?)',
              (session_id, user_input, agent_response, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# Read the PDF and extract text using pdfplumber
def pdf_reader_tool(file_path: str=None) -> dict:
        """Parse PDF and read the full content as text."""
        text = ""
        print(f"Inside PDF reader tool, file path is ****************: {file_path}")
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return { 
             "file_path": file_path,
             "extracted_text": text
               }

def get_list_of_files_tools(folder_path: str=None) -> dict:
    """Get the list of pdf files inside the folder."""
    files = []
    for file in os.listdir(folder_path):
        if file.endswith(".pdf"):
            files.append(os.path.join(folder_path, file))
    return {
         "folder_path": folder_path,
         "files": files
         }

#Moves file to high confidence folder if confidence score is > 90 or if user validates the file as cease and desist file.
def high_confidence_tool(file_path: str=None) -> dict:
    """Move the file to high confidence folder."""
    if high_confidence_path and not os.path.exists(high_confidence_path):
            os.makedirs(high_confidence_path, exist_ok=True)
    shutil.move(file_path, high_confidence_path)
    return {
         "file_path": high_confidence_path,
         "status": "Moved to high confidence folder"
         }

#Moves file to low confidence folder If user says its not cease and desist file then move to low_confidence_path.
def low_confidence_tool(file_path: str=None) -> dict:
    """Move the file to low confidence folder."""
    if low_confidence_path and not os.path.exists(low_confidence_path):
            os.makedirs(low_confidence_path, exist_ok=True)
    shutil.move(file_path, low_confidence_path)
    return {
         "file_path": low_confidence_path,
         "status": "Moved to low confidence folder"
         }

def groq_llm_tool(prompt: str) -> dict:
    response = litellm.completion(
        model="groq/llama-3.1-8b-instant",   
        api_key=os.getenv("GROQ_API_KEY"),
        messages=[
             {"role": "system", "content": tool_content},
             {"role": "user", "content": prompt}
             ],
        max_tokens=256,
        temperature=1.2,
    )
    print(f"Inside Groq LLM prompt ****************: {prompt}")
    response = response["choices"][0]["message"]["content"]
    print(f"Inside Groq LLM response ****************: {response}")
    return {"role": "tool", "content": response}
# Session management tools
current_session_id = None

def init_session_tool() -> dict:
    """Initialize a new session for the conversation."""
    global current_session_id
    current_session_id = str(uuid.uuid4())
    init_db()
    return {
        "session_id": current_session_id,
        "status": "Session initialized"
    }

def save_session_tool(user_input: str, agent_response: str) -> dict:
    """Save the current interaction to the database."""
    global current_session_id
    if current_session_id:
        save_session(current_session_id, user_input, agent_response)
        return {"status": "Interaction saved to database"}
    return {"status": "No active session"}
# Register the tool with ADK
root_agent = Agent(
    name="wf_scan_agent",
    model="gemini-2.5-flash",  
    description="Manager agent who delegates tasks to other agents and responds to the user with answers provided by other agent.",
    instruction="""
    You are a Manager agent that greets the user.
    For users you are called Wells Fargo assistant.
    You should start your conversation by saying 'Greeting from Wells Fargo!'.
    If user asks to classify pdf from folder, ask user to provide the folder path where all the files are located.
    To get the list of files in the folder, call get_list_of_files_tool.
    With the list of files provided from get_list_of_files_tool, loop through each file and do below functions.
    Functions:
    1. Call pdf_reader_tool and pass the filepath to extract text from the PDF.
    2. To classify the PDF content, use groq_llm_tool.
    3. Pass the extracted text and the user"'"s question to groq_llm_tool to classify.
    4. Based on the confidence score from the groq_llm_tool, follow below conditions for each file.
        Conditions:
            1. If confince score is > 90, call tool high_confidence_tool to move the file.
            2. if confidence score is < 90 ask the user to validate the file and provide feedback.
                2.1 If user says its cease and desist file, ca;; high_confidence_tool to move the file.
                2.2 If user says its not cease and desist file, call low_confidence_tool to move the file.
    Always call init_session_tool at the start of a new conversation if not already done.
    After responding to the user, call save_session_tool with the user's input and your response.
    """,
    tools=[get_list_of_files_tools,pdf_reader_tool, groq_llm_tool, high_confidence_tool, low_confidence_tool, init_session_tool, save_session_tool],
)