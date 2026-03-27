"""
EDPS - Enterprise Document Processing System
Multi-agent system for Cease & Desist document processing with human-in-the-loop
"""

import sys
import logging
import subprocess
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from src.config.config import DATA_DIR, LOGS_DIR, ARCHIVE_DIR
from src.database.models import init_db
from src.agents.manager_agent import ManagerAgent
from src.tools.document_loader import load_documents
from src.agents.audit_agent import AuditAgent


def initialize_system():
    """Initialize directory structure and database"""
    logger.info("Initializing EDPS System...")
    
    DATA_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(exist_ok=True)
    
    try:
        init_db()
        logger.info("System initialized successfully")
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        raise


def process_documents(folder_path: str):
    """Process all documents from folder"""
    logger.info(f"Processing documents from: {folder_path}")
    
    try:
        documents = load_documents(folder_path)
        
        if not documents:
            print(f"❌ No documents found in {folder_path}\n")
            return
        
        print(f"\n📄 Found {len(documents)} document(s)\n")
        
        manager = ManagerAgent()
        results = manager.process_batch(documents)
        
        # Display results
        print("\n" + "="*60)
        print("PROCESSING RESULTS")
        print("="*60)
        
        cease_count = 0
        uncertain_count = 0
        irrelevant_count = 0
        error_count = 0
        
        for result in results:
            classification = result.get('classification', 'Unknown')
            doc_name = result.get('document_name', 'Unknown')
            status = result.get('processing_status', 'unknown')
            
            if 'error' in result:
                error_count += 1
                print(f"❌ {doc_name}: {status}")
            elif classification == "Cease":
                cease_count += 1
                print(f"✅ {doc_name}: Cease (stored in database)")
            elif classification == "Uncertain":
                uncertain_count += 1
                print(f"⚠️  {doc_name}: Uncertain (queued for review)")
            else:
                irrelevant_count += 1
                print(f"📁 {doc_name}: Irrelevant (archived)")
        
        print("\n" + "-"*60)
        print(f"Total: {len(results)} | Cease: {cease_count} | "
              f"Uncertain: {uncertain_count} | Irrelevant: {irrelevant_count} | "
              f"Errors: {error_count}")
        print("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"Processing error: {e}")
        print(f"❌ Error: {e}\n")


def view_pending_reviews():
    """Display and handle pending human review documents"""
    try:
        manager = ManagerAgent()
        pending = manager.hitl_agent.get_review_queue()
        
        if not pending:
            print("\n✅ No documents pending review\n")
            return
        
        print("\n" + "="*60)
        print("PENDING REVIEWS")
        print("="*60)
        
        for i, doc in enumerate(pending, 1):
            print(f"\n[{i}] {doc.get('document_name')}")
            print(f"    Classification: {doc.get('classification')}")
            print(f"    Confidence: {doc.get('confidence'):.0%}")
            print(f"    Indicators: {', '.join(doc.get('key_indicators', []))}")
            print(f"    Explanation: {doc.get('explanation')}")
            
            while True:
                decision = input(f"\n    Decision (Cease/Irrelevant/Skip) [s]: ").strip().lower() or 's'
                if decision in ['cease', 'irrelevant', 's']:
                    break
                print("    Invalid choice. Enter: Cease, Irrelevant, or Skip")
            
            if decision == 's':
                continue
                
            notes = input(f"    Notes (optional): ").strip()
            
            success = manager.hitl_agent.submit_review_decision(
                doc.get('document_name'),
                decision.capitalize(),
                notes,
                database_agent=manager.database_agent,
                archiving_agent=manager.archiving_agent
            )
            
            if success:
                print(f"    ✅ Decision recorded")
            else:
                print(f"    ❌ Failed to record decision")
        
        print("\n" + "="*60 + "\n")
        
    except Exception as e:
        logger.error(f"Review error: {e}")
        print(f"❌ Error: {e}\n")


def view_audit_trail():
    """Display audit trail report"""
    try:
        audit = AuditAgent()
        report = audit.generate_audit_report()
        
        print("\n" + "="*60)
        print("AUDIT TRAIL")
        print("="*60)
        print(f"Total Entries: {report.get('total_audit_entries', 0)}")
        
        print("\nActions by Agent:")
        for agent, count in report.get('agent_actions', {}).items():
            print(f"  • {agent}: {count}")
        
        print("\nClassifications:")
        for cls, count in report.get('classification_summary', {}).items():
            print(f"  • {cls}: {count}")
        
        print("\nStatus Summary:")
        for s, count in report.get('status_summary', {}).items():
            print(f"  • {s}: {count}")
        
        print("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"Audit error: {e}")
        print(f"❌ Error: {e}\n")


def view_system_status():
    """Display system status and statistics"""
    try:
        manager = ManagerAgent()
        status = manager.get_system_status()
        
        print("\n" + "="*60)
        print("SYSTEM STATUS")
        print("="*60)
        print(f"Status: {status.get('system_status')}")
        
        db_stats = status.get('database_stats', {})
        print("\n📊 DATABASE:")
        print(f"  Total: {db_stats.get('total_documents', 0)}")
        print(f"  Cease Requests: {db_stats.get('cease_requests', 0)}")
        print(f"  Uncertain: {db_stats.get('uncertain_documents', 0)}")
        
        archive_stats = status.get('archive_stats', {})
        print("\n📁 ARCHIVE:")
        print(f"  Total Archived: {archive_stats.get('total_archived', 0)}")
        
        hitl_stats = status.get('hitl_stats', {})
        print("\n👤 REVIEW QUEUE:")
        print(f"  Pending: {hitl_stats.get('pending_review', 0)}")
        print(f"  Total Decisions: {hitl_stats.get('total_decisions', 0)}")
        
        audit = status.get('audit_summary', {})
        print("\n📝 AUDIT:")
        print(f"  Total Entries: {audit.get('total_entries', 0)}")
        
        print("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"Status error: {e}")
        print(f"❌ Error: {e}\n")


def start_backend():
    """Start FastAPI backend server"""
    logger.info("Starting FastAPI backend...")
    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "src.api:app", 
             "--host", "0.0.0.0", "--port", "8000", "--reload"],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Backend failed to start: {e}")
        print("❌ Failed to start backend server\n")
    except KeyboardInterrupt:
        print("\n\n👋 Backend stopped\n")


def show_menu():
    """Display main menu and handle user selection"""
    while True:
        print("\n" + "="*60)
        print("EDPS - Enterprise Document Processing System")
        print("="*60)
        print("\n1. Process Documents from Folder")
        print("2. View Pending Reviews")
        print("3. View System Status")
        print("4. View Audit Trail")
        print("5. Start Backend Server (GUI on port 3008)")
        print("6. Exit")
        print("\n" + "-"*60)
        
        choice = input("Select option (1-6): ").strip()
        
        if choice == '1':
            folder = input("\nEnter folder path: ").strip()
            if folder:
                process_documents(folder)
            else:
                print("❌ Invalid path\n")
                
        elif choice == '2':
            view_pending_reviews()
            
        elif choice == '3':
            view_system_status()
            
        elif choice == '4':
            view_audit_trail()
            
        elif choice == '5':
            print("\n🚀 Starting backend server...")
            print("📱 Web UI will be available at: http://localhost:3008")
            print("🔌 API will be available at: http://localhost:8000")
            print("Press Ctrl+C to stop\n")
            start_backend()
            
        elif choice == '6':
            print("\n👋 Goodbye!\n")
            sys.exit(0)
        else:
            print("❌ Invalid choice\n")


def main():
    """Main entry point"""
    try:
        initialize_system()
        show_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted\n")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

