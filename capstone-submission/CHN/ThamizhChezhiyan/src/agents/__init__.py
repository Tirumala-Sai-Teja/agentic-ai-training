"""
EDPS - Enterprise Document Processing System Agents Package
"""

from src.agents.classification_agent import ClassificationAgent
from src.agents.database_agent import DatabaseAgent
from src.agents.archiving_agent import ArchivingAgent
from src.agents.audit_agent import AuditAgent
from src.agents.hitl_agent import HITLAgent
from src.agents.manager_agent import ManagerAgent

__all__ = [
    "ClassificationAgent",
    "DatabaseAgent",
    "ArchivingAgent",
    "AuditAgent",
    "HITLAgent",
    "ManagerAgent",
]
