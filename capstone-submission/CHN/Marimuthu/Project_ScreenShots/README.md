
# Intelligent Document Processor for Cease Requests

This project implements an intelligent document processing workflow using LangChain, LangGraph, and Google Colab. The system automates the classification and extraction of information from PDF documents, specifically focusing on 'Cease and Desist' requests. It incorporates Human-in-the-Loop (HITL) review for uncertain cases and handles both text-based and scanned PDFs using OCR.

## Table of Contents
1. [Features](#features)
2. [Architecture](#architecture)
3. [Setup and Installation](#setup-and-installation)
4. [Usage](#usage)
5. [Components](#components)
6. [Data Storage](#data-storage)

## Features
- **Document Ingestion**: Uploads PDF documents for processing.
- **Text Extraction**: Extracts text from PDFs, supporting both native text and scanned documents via OCR (Tesseract).
- **AI-powered Classification**: Classifies documents into 'Cease', 'Uncertain', or 'Irrelevant' using a Groq LLM.
- **Information Extraction**: Extracts key details like sender name, account number, and request summary from relevant documents.
- **Human-in-the-Loop (HITL)**: Provides a Streamlit UI for human review and correction of 'Uncertain' classifications or extracted data.
- **Automated Archiving**: Archives 'Irrelevant' documents.
- **Database Storage**: Stores 'Cease' requests and their extracted details in an SQLite database.
- **Audit Logging**: Maintains a detailed audit trail of all processing steps.

## Architecture
The workflow is orchestrated using LangGraph, defining a state machine that guides documents through various processing stages:

1.  **`loader_agent`**: Extracts text from the PDF. If no text is found, it routes to the `vision_extraction_agent`.
2.  **`vision_extraction_agent`**: Performs OCR on scanned PDFs to extract text.
3.  **`classification_agent`**: Classifies the document and extracts initial details. Routes to `database_agent` for 'Cease', `archiving_agent` for 'Irrelevant', or `hitl_agent` for 'Uncertain'.
4.  **`hitl_agent`**: Triggers a Human-in-the-Loop review using a Streamlit UI or console. Based on human decision, routes to `database_agent` or `archiving_agent`.
5.  **`database_agent`**: Stores 'Cease' requests and their details in an SQLite database.
6.  **`archiving_agent`**: Archives 'Irrelevant' documents to a CSV file.
7.  **`audit_agent`**: Logs the completion of the workflow for each document.

## Setup and Installation

### 1. Colab Environment Setup
Ensure you are running this project in Google Colab.

### 2. Install Dependencies
The `Install Dependencies` cell installs all necessary Python packages. This includes `langchain`, `langchain-groq`, `pymupdf`, `python-dotenv`, `ipywidgets`, `pandas`, `requests`, `pydantic`, `ipython`, `streamlit`, `pdf2image`, and `pytesseract`.

### 3. Set Up API Keys
Edit the `Setup API Keys` cell to configure your `GROQ_API_KEY` and `LANGSMITH_API_KEY` in Colab's user data secrets. LangSmith is used for tracing and observability.

### 4. Install OCR Tools
The cells `Installing Packages for Scanned Docs` and `pytesseract setup` install `poppler-utils` (required by `pdf2image`) and `tesseract-ocr` along with the `pytesseract` Python library for local OCR capabilities.

### 5. Upload Documents
Use the `Upload documents to be processed` cell to upload your PDF files into the `input_docs` directory for processing.

### 6. Initialize Storage
The `Initialize database and files` cell creates the necessary directories (`input_docs`, `archive`, `audit`, `db`), sets up the SQLite database (`cease_requests.db`), an archive CSV (`irrelevant_documents.csv`), and an audit log (`audit_log.jsonl`).

## Usage

1.  **Run all setup cells**:
    Execute cells from `Install Dependencies` down to `Initialize database and files` to prepare the environment.

2.  **Upload PDF Documents**:
    Use the `Upload documents to be processed` cell to upload your PDF files. These will be moved to the `input_docs` directory.

3.  **Configure and Compile Workflow**:
    Ensure the `Pydantic Class for Result Schema`, `Initialize Groq model`, `Agent nodes`, `Utility - Extract text from PDF`, `vision_extraction_agent`, `Routing`, and `Build LangGraph` cells are run. These define the processing logic and compile the LangGraph workflow.

4.  **Start Human-in-the-Loop (HITL) UI (Optional but Recommended)**:
    If you want to use the Streamlit UI for human review:
    - Run the `Create the Streamlit UI script` cell to create the `human_review_ui.py` file.
    - Run the `Start Streamlit UI` cell to launch the Streamlit application. A link to the UI will be provided, and it will also be embedded in an iframe. When documents are routed to HITL, you will need to interact with this UI to provide a decision.
    
    Alternatively, for a simpler console-based HITL, ensure the `HITL Section - Input Console` cell is defined.

5.  **Process Documents**:
    Execute the `Process Documents` cell. This cell iterates through all PDFs in the `input_docs` directory, invokes the LangGraph workflow for each, and prints the final state.

6.  **Review Results**:
    - **`View DB records`**: See documents classified as 'Cease' (or reclassified by human as 'Cease') stored in the SQLite database.
    - **`View archive CSV`**: See documents classified as 'Irrelevant' (or reclassified by human as 'Irrelevant') archived in the CSV file.
    - **`View audit trail`**: Examine the `audit_df` DataFrame for a detailed log of each document's journey through the workflow.

## Components

### Python Libraries
-   **LangChain**: For building LLM applications.
-   **LangGraph**: For orchestrating the multi-agent workflow.
-   **LangChain Groq**: Integration with Groq LLMs.
-   **PyMuPDF (fitz)**: For efficient PDF text extraction.
-   **PyPDF2**: Alternative for PDF text extraction.
-   **pdf2image**: Converts PDF pages to images for OCR.
-   **pytesseract**: Python wrapper for Google's Tesseract-OCR Engine.
-   **Pydantic**: For data validation and schema definition.
-   **Pandas**: For data manipulation and analysis.
-   **Streamlit**: For creating the interactive Human-in-the-Loop UI.

### LLM
-   **Groq (qwen/qwen3-32b)**: Used for document classification and information extraction due to its speed and performance.

### Storage
-   **SQLite**: For structured storage of 'Cease' requests.
-   **CSV Files**: For archiving 'Irrelevant' documents.
-   **JSONL Files**: For audit logging.

## Data Storage
All persistent data is stored within the `/content/U855316_CapstoneProject` directory:
-   `input_docs/`: Original uploaded PDF documents.
-   `db/cease_requests.db`: SQLite database for 'Cease' requests.
-   `archive/irrelevant_documents.csv`: CSV for archived 'Irrelevant' documents.
-   `audit/audit_log.jsonl`: JSON Lines file containing the audit trail.
-   `human_review_payload.json`: Temporary file for passing data to the HITL UI.
-   `human_review_result.json`: Temporary file for receiving human decisions from the HITL UI.
