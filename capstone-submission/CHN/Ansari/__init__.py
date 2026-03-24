"""
Cease & Desist Document Processing System - Main Package

A production-ready system using LangChain and LangGraph for automated
classification, extraction, and processing of Cease & Desist documents.

Version: 1.0.0
Author: Enterprise AI Systems
License: Proprietary
"""

__version__ = "1.0.0"
__author__ = "Enterprise AI Systems"

from config.settings import MOCK_MODE, LLM_PROVIDER

__all__ = [
    "MOCK_MODE",
    "LLM_PROVIDER",
]
