# 📄 Intelligent Document Processing Pipeline (Capstone Project)

---

## 🚀 Overview

This project is an **AI-powered document processing system** that automates the entire lifecycle of handling PDF documents.

It combines:
- OCR (for scanned PDFs)
- LLM reasoning (for classification & extraction)
- Workflow orchestration using **LangGraph**
- Human-in-the-loop decision making

👉 Goal: Build a **production-style pipeline** similar to enterprise document processing systems.

---

## 🧠 Features (Explained)

### 📥 1. Document Ingestion
- Accepts PDF files from `sample_docs/`
- Supports both:
  - Text PDFs
  - Scanned/image-based PDFs

👉 Makes the system usable in real-world messy data scenarios

---

### 🔍 2. OCR + Text Extraction
- Uses **PyMuPDF** for structured text extraction
- Falls back to **Tesseract OCR** for scanned PDFs

👉 Ensures **no document is skipped**, even if it's image-based

---

### 🧪 3. Text Validation Layer
- Checks if extracted text is meaningful
- Filters out:
  - Empty text
  - Garbage OCR outputs

👉 Prevents bad data from entering LLM stage

---

### 🤖 4. LLM-Based Classification
- Uses Groq/OpenAI model
- Classifies document into:
  - **Cease** → Relevant document
  - **Irrelevant** → Not useful
  - **Uncertain** → Needs human review

👉 Core intelligence layer of the pipeline

---

### 🧑‍⚖️ 5. Human-in-the-Loop (HITL)
- Triggered when confidence is low
- Allows manual decision:
  - Cease / Irrelevant

👉 Mimics real enterprise approval workflows

---

### 📊 6. Data Extraction
- Extracts structured fields from relevant documents
- Output stored as JSON

👉 Converts unstructured → structured data

---

### 🗄️ 7. Database Storage
- Stores processed results in **SQLite (`documents.db`)**

Includes:
- Document name
- Classification
- Extracted data
- Timestamp

👉 Enables analytics and tracking

---

### 📦 8. Archiving
- Irrelevant documents are logged into:
  ```
  archive.txt
  ```

👉 Keeps audit trail of discarded documents

---

### 🧾 9. Audit Logging
- Every step is logged into:
  ```
  audit_log.txt
  ```

Includes:
- Classification result
- HITL decisions
- Processing steps

👉 Critical for debugging & compliance

---

### 🔁 10. Batch Processing
- Processes all files in:
  ```
  sample_docs/
  ```
- Moves processed files to:
  ```
  completed_docs/
  ```

👉 Enables automation at scale

---

## 🧩 LangGraph Workflow (Mermaid Diagram)

```mermaid
graph TD

A[Start: Load PDF] --> B[Extract Text (OCR/PDF)]
B --> C[Validate Text]

C -->|Valid| D[Classify (LLM)]
C -->|Invalid| Z[Archive]

D -->|Cease| E[Extract Data]
D -->|Irrelevant| Z[Archive]
D -->|Uncertain| F[HITL]

F -->|Cease| E
F -->|Irrelevant| Z

E --> G[Store in DB]

Z --> H[Write Archive]

G --> I[Audit Log]
H --> I

I --> J[Move to completed_docs]

J --> K[End]
```

👉 This represents your **LangGraph state machine**

---

## 📁 Project Structure

```
project/
│
├── sample_docs/        # Input PDFs
├── completed_docs/     # Processed PDFs
├── archive.txt         # Archived logs
├── audit_log.txt       # Execution logs
├── documents.db        # SQLite DB
│
├── main.ipynb          # Core pipeline
└── README.md
```

---

## ⚙️ Setup Instructions

### 1️⃣ Install dependencies

```bash
pip install langgraph langchain langchain-core pymupdf pytesseract pillow
```

---

### 2️⃣ Install Tesseract OCR

👉 Required for scanned PDFs

- Windows:
  - Install from official Tesseract repo
  - Add to PATH

- Mac:
```bash
brew install tesseract
```

- Linux:
```bash
sudo apt install tesseract-ocr
```

---

### 3️⃣ Set API Key (if using LLM)

```bash
export GROQ_API_KEY=your_key
```

or

```bash
export OPENAI_API_KEY=your_key
```

---

## ▶️ How to Run

### Step 1: Add documents
Place PDFs inside:
```
sample_docs/
```

---

### Step 2: Run single document

```python
run_pipeline("sample_docs/file.pdf", "file.pdf")
```

---

### Step 3: Run batch processing

```python
process_all_documents("sample_docs")
```

---

### Step 4: Check outputs

- ✅ Database → `documents.db`
- 📦 Archive → `archive.txt`
- 🧾 Logs → `audit_log.txt`
- 📁 Files moved → `completed_docs/`

---

## ⚠️ Limitations

- HITL uses `input()` (not UI-based)
- No retry mechanism for LLM failures
- SQLite not scalable for production
- No async processing

---

## 🔥 Future Improvements

- Streamlit UI for HITL  
- FastAPI deployment  
- Async parallel processing  
- Cloud storage (S3)  
- Vector DB + RAG  
- Advanced validation rules  

---

## 🏁 Conclusion

This project demonstrates a **real-world AI workflow system** combining:

- OCR  
- LLM reasoning  
- Workflow orchestration (LangGraph)  
- Human decision loops  

👉 It is a strong foundation for:
- Enterprise automation
- AI agents
- Process mining pipelines

---

## 👨‍💻 Author

Thiru Gnanam
