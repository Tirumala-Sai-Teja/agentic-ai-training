"""
Main entry point for the Cease & Desist Document Processing System.
Demonstrates how to use the system and provides CLI interface.
"""
import sys
import logging
import csv
import os
from pathlib import Path
from datetime import datetime

from config.settings import MOCK_MODE, API_ENABLE
from models.db_models import init_db
from graph.workflow import DocumentProcessingGraph
from utils.logger import get_logger, audit_logger
from agents.audit_agent import AuditAgent

logger = get_logger(__name__)


def initialize_system() -> None:
    """Initialize the system by creating database tables."""
    logger.info("Initializing system...")
    init_db()
    logger.info("Database initialized successfully")


def print_banner() -> None:
    """Print system banner."""
    print("\n" + "="*80)
    print("CEASE & DESIST DOCUMENT PROCESSING SYSTEM")
    print("="*80)
    if MOCK_MODE:
        print("⚠️  RUNNING IN MOCK MODE (No OpenAI API calls)")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")


def print_menu() -> None:
    """Print main menu options."""
    print("\nMAIN MENU:")
    print("  1. Process a single document")
    print("  2. Process documents from a folder (batch)")
    print("  3. View processing results")
    print("  4. View audit logs")
    print("  5. View system statistics")
    print("  6. Database management (export/clear records)")
    print("  7. Exit")
    print()


def process_document_menu() -> None:
    """Menu for processing a document."""
    print("\nDOCUMENT PROCESSING")
    print("-" * 40)
    
    document_path = input("Enter path to PDF document: ").strip()
    
    if not Path(document_path).exists():
        print(f"❌ Error: File not found: {document_path}")
        return
    
    document_name = input("Enter document name (or press Enter for filename): ").strip()
    if not document_name:
        document_name = Path(document_path).name
    
    print(f"\n✓ Processing: {document_name}")
    print("This may take a moment...\n")
    
    try:
        # Initialize graph
        graph = DocumentProcessingGraph()
        
        # Process document
        final_state_dict = graph.process_document(document_path, document_name)
        
        # Convert dict to ProcessingState object if needed
        if isinstance(final_state_dict, dict):
            from models.schemas import ProcessingState
            final_state = ProcessingState(**final_state_dict)
        else:
            final_state = final_state_dict
        
        # Display results
        print("\n" + "="*80)
        print("PROCESSING RESULTS")
        print("="*80)
        print(f"Document: {final_state.document_name}")
        print(f"Status: {final_state.processing_status}")
        
        if final_state.classification_result:
            print(f"Classification: {final_state.classification_result.classification}")
            print(f"Confidence: {final_state.classification_result.confidence:.2%}")
            print(f"Reasoning: {final_state.classification_result.reasoning}")
        
        if final_state.extraction_result:
            print(f"\nExtracted Information:")
            print(f"  Sender: {final_state.extraction_result.sender_name or 'Unknown'}")
            print(f"  Date: {final_state.extraction_result.request_date or 'Unknown'}")
            print(f"  Claims: {len(final_state.extraction_result.key_claims)}")
            print(f"  Requested Actions: {len(final_state.extraction_result.requested_actions)}")
        
        if final_state.database_record_id:
            print(f"✓ Stored in database as record #{final_state.database_record_id}")
        
        if final_state.archive_record_id:
            print(f"✓ Archived as record #{final_state.archive_record_id}")
        
        if final_state.error_message:
            print(f"⚠️  Error: {final_state.error_message}")
        
        print("="*80)
    
    except Exception as e:
        print(f"❌ Error processing document: {str(e)}")
        logger.error(f"Document processing error: {str(e)}", exc_info=True)


def process_folder_menu() -> None:
    """Menu for batch processing documents from a folder."""
    print("\nBATCH DOCUMENT PROCESSING")
    print("-" * 40)
    
    folder_path = input("Enter path to folder containing PDF documents: ").strip()
    
    folder = Path(folder_path)
    if not folder.exists():
        print(f"❌ Error: Folder not found: {folder_path}")
        return
    
    if not folder.is_dir():
        print(f"❌ Error: Path is not a directory: {folder_path}")
        return
    
    # Find all PDF files in the folder
    pdf_files = list(folder.glob("*.pdf")) + list(folder.glob("**/*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in: {folder_path}")
        return
    
    # Remove duplicates (from ** pattern matching)
    pdf_files = list(set(pdf_files))
    pdf_files.sort()
    
    print(f"\n✓ Found {len(pdf_files)} PDF file(s)")
    print("Starting batch processing...\n")
    
    # Statistics tracking
    successful = 0
    failed = 0
    results = []
    
    # Initialize graph once for all documents
    graph = DocumentProcessingGraph()
    
    # Process each document
    for idx, pdf_path in enumerate(pdf_files, 1):
        document_name = pdf_path.name
        
        print(f"\n[{idx}/{len(pdf_files)}] Processing: {document_name}")
        print("-" * 60)
        
        try:
            # Process document
            final_state_dict = graph.process_document(str(pdf_path), document_name)
            
            # Convert dict to ProcessingState object if needed
            if isinstance(final_state_dict, dict):
                from models.schemas import ProcessingState
                final_state = ProcessingState(**final_state_dict)
            else:
                final_state = final_state_dict
            
            # Display results
            print(f"Status: {final_state.processing_status}")
            
            if final_state.classification_result:
                classification = final_state.classification_result.classification
                confidence = final_state.classification_result.confidence
                print(f"Classification: {classification} ({confidence:.2%})")
            
            if final_state.extraction_result and final_state.classification_result.classification == "CEASE":
                sender = final_state.extraction_result.sender_name or "Unknown"
                print(f"Sender: {sender}")
            
            if final_state.database_record_id:
                print(f"✓ Stored in database as record #{final_state.database_record_id}")
            
            if final_state.archive_record_id:
                print(f"✓ Archived as record #{final_state.archive_record_id}")
            
            if final_state.error_message:
                print(f"⚠️  Error: {final_state.error_message}")
                result_status = "Failed"
                failed += 1
            else:
                result_status = "Success"
                successful += 1
            
            results.append({
                "document": document_name,
                "status": result_status,
                "classification": final_state.classification_result.classification if final_state.classification_result else "N/A",
                "confidence": final_state.classification_result.confidence if final_state.classification_result else 0,
            })
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results.append({
                "document": document_name,
                "status": "Failed",
                "classification": "N/A",
                "confidence": 0,
            })
            failed += 1
            logger.error(f"Batch processing error for {document_name}: {str(e)}", exc_info=True)
    
    # Display summary
    print("\n" + "="*80)
    print("BATCH PROCESSING SUMMARY")
    print("="*80)
    print(f"Total Documents: {len(pdf_files)}")
    print(f"✓ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(successful/len(pdf_files)*100):.1f}%")
    
    print("\nDetailed Results:")
    print("-" * 80)
    print(f"{'Document':<40} {'Status':<15} {'Classification':<15} {'Confidence':<10}")
    print("-" * 80)
    for result in results:
        doc_name = result['document'][:37] + "..." if len(result['document']) > 40 else result['document']
        print(f"{doc_name:<40} {result['status']:<15} {result['classification']:<15} {result['confidence']:>8.1%}")
    
    print("="*80)
def view_results_menu() -> None:
    """Menu for viewing processing results."""
    print("\nVIEW RESULTS")
    print("-" * 40)
    
    from agents.database_agent import DatabaseAgent
    from agents.archival_agent import ArchivalAgent
    
    db_agent = DatabaseAgent()
    archive_agent = ArchivalAgent()
    
    print("\n1. CEASE RECORDS")
    cease_records = db_agent.get_all_cease_records(limit=10)
    
    if cease_records:
        print(f"Total CEASE records: {len(cease_records)}")
        for record in cease_records:
            print(f"\n  [{record.id}] {record.document_name}")
            print(f"      Classification: {record.classification}")
            print(f"      Confidence: {record.confidence:.2%}")
            print(f"      Received: {record.received_date.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("No CEASE records found")
    
    print("\n\n2. ARCHIVED RECORDS")
    archive_records = archive_agent.get_archived_documents(limit=10)
    
    if archive_records:
        print(f"Total archived records: {len(archive_records)}")
        for record in archive_records:
            print(f"\n  [{record['id']}] {record['document_name']}")
            print(f"      Classification: {record['classification']}")
            print(f"      Archived: {record['archive_date'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("No archived records found")


def view_audit_logs_menu() -> None:
    """Menu for viewing audit logs."""
    print("\nAUDIT LOGS")
    print("-" * 40)
    
    audit_agent = AuditAgent()
    
    # Display system summary
    summary = audit_agent.get_system_summary()
    
    print(f"\nSystem Summary:")
    print(f"  Total Log Entries: {summary.get('total_logs', 0)}")
    print(f"  Successful: {summary.get('successful_logs', 0)}")
    print(f"  Failed: {summary.get('failed_logs', 0)}")
    print(f"  Pending: {summary.get('pending_logs', 0)}")
    print(f"  Event Types: {', '.join(summary.get('event_types', []))}")
    
    # Get recent logs
    logs = audit_agent.get_audit_logs(limit=20)
    if logs:
        print(f"\nRecent Audit Logs (last 20):")
        for log in logs[:5]:  # Show first 5
            print(f"\n  [{log['id']}] {log['timestamp']}")
            print(f"      Agent: {log['agent']}")
            print(f"      Event: {log['event_type']}")
            print(f"      Status: {log['status']}")
            if log['error_message']:
                print(f"      Error: {log['error_message']}")


def view_system_stats() -> None:
    """View system statistics."""
    print("\nSYSTEM STATISTICS")
    print("-" * 40)
    
    audit_agent = AuditAgent()
    from agents.database_agent import DatabaseAgent
    from agents.archival_agent import ArchivalAgent
    
    # Get counts
    db_agent = DatabaseAgent()
    archive_agent = ArchivalAgent()
    
    cease_records = db_agent.get_all_cease_records(limit=10000)
    archived_records = archive_agent.get_archived_documents(limit=10000)
    
    summary = audit_agent.get_system_summary()
    
    print(f"\nDocument Counts:")
    print(f"  CEASE Records: {len(cease_records)}")
    print(f"  Archived Documents: {len(archived_records)}")
    print(f"  Total Processed: {len(cease_records) + len(archived_records)}")
    
    print(f"\nAudit Trail:")
    print(f"  Total Events: {summary.get('total_logs', 0)}")
    print(f"  Successful: {summary.get('successful_logs', 0)}")
    print(f"  Failed: {summary.get('failed_logs', 0)}")
    
    print(f"\nSystem Status:")
    print(f"  LLM Mode: {'Mock' if MOCK_MODE else 'OpenAI'}")
    print(f"  API Enabled: {API_ENABLE}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def export_database_to_csv() -> None:
    """Export CEASE records to CSV file."""
    from agents.database_agent import DatabaseAgent
    
    print("\n📥 EXPORTING DATABASE TO CSV")
    print("-" * 60)
    
    db_agent = DatabaseAgent()
    cease_records = db_agent.get_all_cease_records(limit=10000)
    
    if not cease_records:
        print("No CEASE records to export")
        return
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_file = f"storage/cease_records_export_{timestamp}.csv"
    
    try:
        with open(export_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                "ID",
                "Document Name",
                "Classification",
                "Confidence",
                "Received Date",
                "Sender Name",
                "Key Claims",
                "Requested Actions",
                "Deadline",
                "Created At",
                "Updated At"
            ])
            
            # Write records
            for record in cease_records:
                extraction = record.extracted_details or {}
                sender = extraction.get("sender_name", "")
                claims = ", ".join(extraction.get("key_claims", []))
                actions = ", ".join(extraction.get("requested_actions", []))
                deadline = extraction.get("deadline", "")
                
                writer.writerow([
                    record.id,
                    record.document_name,
                    record.classification,
                    f"{record.confidence:.2%}",
                    record.received_date.strftime("%Y-%m-%d %H:%M:%S"),
                    sender,
                    claims,
                    actions,
                    deadline,
                    record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else "",
                    record.updated_at.strftime("%Y-%m-%d %H:%M:%S") if record.updated_at else "",
                ])
        
        print(f"✅ Successfully exported {len(cease_records)} records to: {export_file}")
        print(f"📊 File size: {os.path.getsize(export_file) / 1024:.2f} KB")
    
    except Exception as e:
        print(f"❌ Export failed: {str(e)}")
        logger.error(f"CSV export error: {str(e)}", exc_info=True)


def display_database_table() -> None:
    """Display CEASE records in a formatted table."""
    from agents.database_agent import DatabaseAgent
    
    print("\n📋 CEASE RECORDS TABLE")
    print("=" * 130)
    
    db_agent = DatabaseAgent()
    cease_records = db_agent.get_all_cease_records(limit=1000)
    
    if not cease_records:
        print("No CEASE records found")
        print("=" * 130)
        return
    
    # Header
    print(f"{'ID':<5} {'Document Name':<50} {'Classification':<15} {'Confidence':<12} {'Received Date':<20}")
    print("-" * 130)
    
    # Rows
    for record in cease_records:
        doc_name = record.document_name[:47] + "..." if len(record.document_name) > 50 else record.document_name
        date_str = record.received_date.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{record.id:<5} {doc_name:<50} {record.classification:<15} {record.confidence:>10.1%}  {date_str:<20}")
    
    print("=" * 130)
    print(f"Total CEASE Records: {len(cease_records)}")


def clear_database_records() -> None:
    """Clear all CEASE and archive records from database."""
    from agents.database_agent import DatabaseAgent
    from agents.archival_agent import ArchivalAgent
    
    print("\n🗑️  CLEAR DATABASE RECORDS")
    print("-" * 60)
    print("⚠️  WARNING: This will delete ALL records from the database!")
    print("   This action CANNOT be undone!")
    print()
    
    # Get current counts
    db_agent = DatabaseAgent()
    archive_agent = ArchivalAgent()
    
    cease_count = db_agent.count_cease_records()
    archive_count = len(archive_agent.get_archived_documents(limit=10000))
    
    print(f"Records to be deleted:")
    print(f"  - CEASE Records: {cease_count}")
    print(f"  - Archived Records: {archive_count}")
    print(f"  - Total: {cease_count + archive_count}")
    print()
    
    # Ask for confirmation
    confirm = input("Do you want to export to CSV before clearing? (y/n): ").strip().lower()
    if confirm == "y":
        export_database_to_csv()
        print()
    
    # Final confirmation
    final_confirm = input("Type 'DELETE' to confirm and clear all records: ").strip()
    
    if final_confirm != "DELETE":
        print("❌ Cancelled - Database NOT cleared")
        return
    
    try:
        # Delete CEASE records
        if cease_count > 0:
            db_agent.delete_all_cease_records()
            print(f"✅ Deleted {cease_count} CEASE records")
        
        # Delete archived records (manual query since we need a delete method in archival agent)
        if archive_count > 0:
            from models.db_models import SessionLocal, ArchiveRecord
            session = SessionLocal()
            try:
                deleted = session.query(ArchiveRecord).delete()
                session.commit()
                print(f"✅ Deleted {deleted} archived records")
            finally:
                session.close()
        
        print("\n✅ Database cleared successfully!")
        logger.info("Database cleared by user")
    
    except Exception as e:
        print(f"❌ Error clearing database: {str(e)}")
        logger.error(f"Database clear error: {str(e)}", exc_info=True)


def database_management_menu() -> None:
    """Database management submenu."""
    from agents.database_agent import DatabaseAgent
    
    while True:
        print("\n📊 DATABASE MANAGEMENT")
        print("-" * 40)
        print("  1. View records in table format")
        print("  2. Export records to CSV")
        print("  3. Clear all records")
        print("  4. Back to main menu")
        print()
        
        choice = input("Select option (1-4): ").strip()
        
        if choice == "1":
            display_database_table()
        elif choice == "2":
            export_database_to_csv()
        elif choice == "3":
            clear_database_records()
        elif choice == "4":
            break
        else:
            print("❌ Invalid option. Please select 1-4.")


def main_menu() -> None:
    """Main menu loop."""
    print_banner()
    
    while True:
        print_menu()
        choice = input("Select option (1-7): ").strip()
        
        if choice == "1":
            process_document_menu()
        elif choice == "2":
            process_folder_menu()
        elif choice == "3":
            view_results_menu()
        elif choice == "4":
            view_audit_logs_menu()
        elif choice == "5":
            view_system_stats()
        elif choice == "6":
            database_management_menu()
        elif choice == "7":
            print("👋 Exiting system. Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid option. Please select 1-7.")


def main() -> None:
    """Main entry point."""
    try:
        # Initialize system
        initialize_system()
        
        # Start main menu
        main_menu()
    
    except KeyboardInterrupt:
        print("\n\n👋 System interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
