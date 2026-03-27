"""
Audit Agent - Provides audit trail and compliance reporting
"""
import json
from pathlib import Path
from src.tools.audit_logger import get_audit_trail
from src.config.config import LOGS_DIR
import logging

logger = logging.getLogger(__name__)


class AuditAgent:
    """Agent responsible for audit trail management and reporting"""

    def __init__(self):
        """Initialize the audit agent"""
        self.audit_trail = get_audit_trail()
        self.name = "AuditAgent"

    def generate_audit_report(self) -> dict:
        """
        Generate comprehensive audit report
        
        Returns:
            Dictionary with audit statistics and details
        """
        try:
            audit_entries = self.audit_trail.get_audit_trail()

            # Ensure audit_entries is a list
            if not isinstance(audit_entries, list):
                logger.error(f"Expected list from audit trail, got {type(audit_entries)}")
                return {"error": f"Invalid audit trail format: expected list, got {type(audit_entries)}"}

            # Analyze entries
            agent_actions = {}
            classification_summary = {}
            status_summary = {}

            for entry in audit_entries:
                # Ensure entry is a dictionary
                if not isinstance(entry, dict):
                    logger.warning(f"Skipping invalid audit entry: {entry} (type: {type(entry)})")
                    continue
                    
                agent_name = entry.get("agent_name", "Unknown")
                classification = entry.get("classification")
                status = entry.get("status")

                # Count actions per agent
                if agent_name not in agent_actions:
                    agent_actions[agent_name] = 0
                agent_actions[agent_name] += 1

                # Count classifications
                if classification:
                    if classification not in classification_summary:
                        classification_summary[classification] = 0
                    classification_summary[classification] += 1

                # Count statuses
                if status:
                    if status not in status_summary:
                        status_summary[status] = 0
                    status_summary[status] += 1

            report = {
                "total_audit_entries": len(audit_entries),
                "agent_actions": agent_actions,
                "classification_summary": classification_summary,
                "status_summary": status_summary,
                "recent_entries": audit_entries[-10:] if audit_entries else []  # Last 10 entries
            }

            # Log this report generation
            self.audit_trail.log_action(
                agent_name=self.name,
                action="Generate Audit Report",
                explanation=f"Audit report generated with {len(audit_entries)} entries",
                status="success"
            )

            logger.info(f"Audit report generated: {len(audit_entries)} entries")
            return report

        except Exception as e:
            logger.error(f"Error generating audit report: {e}")
            return {"error": str(e)}

    def export_audit_trail(self, output_file: Path = None) -> bool:
        """
        Export audit trail to JSON file
        
        Args:
            output_file: Path to export file
        
        Returns:
            True if exported successfully, False otherwise
        """
        try:
            if output_file is None:
                output_file = LOGS_DIR / f"audit_export_{self.get_timestamp()}.json"

            audit_entries = self.audit_trail.get_audit_trail()

            with open(output_file, 'w') as f:
                json.dump(audit_entries, f, indent=2)

            self.audit_trail.log_action(
                agent_name=self.name,
                action="Export Audit Trail",
                explanation=f"Audit trail exported to {output_file}",
                status="success"
            )

            logger.info(f"Audit trail exported to {output_file}")
            return True

        except Exception as e:
            logger.error(f"Error exporting audit trail: {e}")
            return False

    def get_audit_trail_for_document(self, document_name: str) -> list:
        """
        Get audit trail for a specific document
        
        Args:
            document_name: Name of the document
        
        Returns:
            List of audit entries for the document
        """
        try:
            audit_entries = self.audit_trail.get_audit_trail(document_name=document_name)

            self.audit_trail.log_action(
                agent_name=self.name,
                action="Get Document Audit Trail",
                document_name=document_name,
                explanation=f"Retrieved {len(audit_entries)} audit entries for document",
                status="success"
            )

            logger.info(f"Retrieved {len(audit_entries)} audit entries for {document_name}")
            return audit_entries

        except Exception as e:
            logger.error(f"Error retrieving audit trail for document: {e}")
            return []

    def verify_compliance(self) -> dict:
        """
        Verify compliance by checking audit trail
        
        Returns:
            Dictionary with compliance status
        """
        try:
            audit_entries = self.audit_trail.get_audit_trail()

            compliance = {
                "total_documents_processed": len(set(e.get("document_name") for e in audit_entries)),
                "all_actions_logged": len(audit_entries) > 0,
                "classification_coverage": self._check_classification_coverage(audit_entries),
                "error_tracking": self._check_error_tracking(audit_entries),
                "status": "COMPLIANT" if len(audit_entries) > 0 else "NO_ACTIVITY"
            }

            self.audit_trail.log_action(
                agent_name=self.name,
                action="Verify Compliance",
                explanation=f"Compliance verification status: {compliance['status']}",
                status="success"
            )

            logger.info(f"Compliance verification completed: {compliance['status']}")
            return compliance

        except Exception as e:
            logger.error(f"Error during compliance verification: {e}")
            return {"error": str(e), "status": "ERROR"}

    def _check_classification_coverage(self, audit_entries: list) -> dict:
        """Check if all classification types are covered"""
        classifications = set()
        for entry in audit_entries:
            if entry.get("classification"):
                classifications.add(entry.get("classification"))

        return {
            "unique_classifications": list(classifications),
            "cease_processed": "Cease" in classifications,
            "uncertain_processed": "Uncertain" in classifications,
            "irrelevant_processed": "Irrelevant" in classifications
        }

    def _check_error_tracking(self, audit_entries: list) -> dict:
        """Check error tracking in audit trail"""
        total_entries = len(audit_entries)
        failed_entries = len([e for e in audit_entries if e.get("status") == "failed"])
        success_entries = len([e for e in audit_entries if e.get("status") == "success"])

        return {
            "total_operations": total_entries,
            "successful_operations": success_entries,
            "failed_operations": failed_entries,
            "success_rate": (success_entries / total_entries * 100) if total_entries > 0 else 0
        }

    @staticmethod
    def get_timestamp() -> str:
        """Get current timestamp for file naming"""
        from datetime import datetime
        return datetime.utcnow().strftime("%Y%m%d_%H%M%S")
