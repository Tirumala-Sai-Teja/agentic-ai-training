# 🏗️ Capstone Project: Cease & Desist Document Processing Agent

I used below tech stack to complete this project.

- LangGraph
- LECL [Just used inside document classification  & extraction nodes]
- SQLite DB [For persistance]
- Streamlit [Web UI used to show the extraction results & submit HITL reviews with 'document preview' feature]

## ⚙️Environment Setup

Below mentioned 2 API keys you need to update in the .env file.

- GROQ_API_KEY (Paste your GROQ api key here)
- LANGSMITH_API_KEY (Paste your LANGSMITH api key here for observability)

- Create the virtual environment and activate it (python -m venv .venv, .venv\Scripts\activate)
- install all the requirements (pip install -r requirements.txt)

All the input documents are already available inside (docs) folder.

For 'Irrelevant' document types, the archival log details will be written inside the 'Result.txt' flat file.

## 🏃‍♀️‍➡️Run the Project

1. Execute the 'main.py' file from the root folder
    - python main.py
    - It will read all the input docs from 'docs' folder and process all of them
    - If any document's classification confidence is low (or) 'Uncertain' HITL interruption will be created
2. Run the streamlit page 'ui.py' from the root folder
    - streamlit run ui.py
    - The small UI that will show all the extraction results [saved in DB] and HITL pending actions
        * 'See all extraction result' - Page will dispaly all the extracted results
        * 'HITL Pending Reviews' - Page will show all the pending reviews where user can submi their reviews [Document viewer is also presented to help human to classify]
    - Based on the HITL actions provided, the agent proceeds to next actions

## Additional Info

- Adjust the 'CLASSIFICATION_CONFIDENCE_THRESHOLD_HITL' value in .env file to set the threshold for HITL
- 'Document Loader' node will extract document content and send raw text using below 2 approach
    * Normal PDF Reader: When the input document is a digital PDF file
    * LLM Multi-Model: When the input document is a scanned PDF file
- Included 'ClassificationResult' model validator to check for below key fields. if not present in the document then it will force to classify it as 'Uncertain' to have a human review. [NOTE: Please update this list if we need to specify any other fields as mandatory fields.]
    * reference_no, 
    * infringing_url, 
    * deadline, 
    * monetary_demand
- I did not include 'Audit Agent' in this graph since i already integrated LangSmith that will do all the logging for observability




        



