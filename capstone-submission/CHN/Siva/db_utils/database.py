import sqlite3
from dotenv import load_dotenv
import os
import logging
import pandas as pd
import json

load_dotenv()
logger = logging.getLogger(__name__)
def init_db():
    conn = None
    try:
        conn = sqlite3.connect(os.getenv("SQLITE_DB_NAME"))
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS extraction_result (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT,
                doc_name TEXT,
                doc_type TEXT, 
                doc_file BLOB,
                extracted_data TEXT, 
                confidence REAL,
                reason TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error in initializing SQLite DB table: {str(e)}")
        raise e
    finally:
        if conn:
            conn.close()

def save_extraction_result(thread_id, doc_name, doc_type,confidence,reason, doc_bytes, pydantic_data):
    conn = None
    try:
        json_payload = pydantic_data.model_dump_json()
        #confidence = getattr(pydantic_data, 'confidence', 0.0)

        conn = sqlite3.connect(os.getenv("SQLITE_DB_NAME"), timeout=10)  
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO extraction_result 
            (thread_id, doc_name, doc_type, doc_file, extracted_data, confidence, status,reason) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (thread_id, doc_name, doc_type, doc_bytes, json_payload, confidence, "Completed",reason)
        )
        
        conn.commit()
        logger.info(f"Successfully saved extraction for {doc_name}")

    except Exception as e:
        logger.error(f"Unexpected error saving extraction result to database: {e}")
        raise e

    finally:
        if conn:
            conn.close()

def get_all_extractions():
    conn = None
    try:
        logger.info("Getting all extraction details")
        conn = sqlite3.connect(os.getenv("SQLITE_DB_NAME"))
        
        query = "SELECT id, thread_id, doc_name, doc_type, extracted_data, confidence,reason, status FROM extraction_result"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['extracted_data'] = df['extracted_data'].apply(json.loads)
        return df
    except Exception as e:
        logger.error(f"Error while getting extraction details: {str(e)}")
        raise e
    finally:
        if conn:
            conn.close()