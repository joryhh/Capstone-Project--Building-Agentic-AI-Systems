"""Requirements Engineering Copilot.

A multi-agent system that reviews a software requirements document and proposes
improvements, with a Product Owner approving every change before it is applied.

Built for the SDAIA Academy "Building Agentic AI Systems" programme.

Typical use:

    from requirements_copilot import requirements_copilot, parse_requirements
    from langgraph.types import Command

    parsed = parse_requirements.invoke({"document_text": open("doc.txt").read()})
    cfg = {"configurable": {"thread_id": "session-1"}}

    paused = requirements_copilot.invoke(
        {"project_id": "my-project", "project_description": desc, "requirements": parsed}, cfg)
    payload = paused["__interrupt__"][0].value

    decisions = [scripted_po_decision(f) for f in payload["findings"]]
    done = requirements_copilot.invoke(Command(resume={"decisions": decisions}), cfg)
"""

from .schemas import ApprovedChange, Requirement, ReviewFinding
from .reliability import REVIEWER_RETRY, groq_rate_limiter, is_transient_error, with_fallback
from .runtime import MODEL, checkpointer
from .tools import load_document_text, parse_requirements
from .rag import (
    pipeline_summary,
    retrieve_standards,
    search_requirements_standards,
    standards_store,
)
from .reviewers import (
    ambiguity_reviewer,
    completeness_reviewer,
    conflict_reviewer,
    testability_standards_reviewer,
)
from .supervisor import RouterDecision, render_report, supervisor_route, supervisor_synthesize
from .memory import retrieve_project_memory, save_project_memory
from .hitl import (
    build_approved_changes,
    interactive_po_decision,
    persist_po_decisions,
    requirements_approval_hitl,
    scripted_po_decision,
)
from .editor import EditorError, apply_approved_changes, apply_changes
from .pipelines import requirements_copilot, review_pipeline

__version__ = "1.0.0"

__all__ = [
    "Requirement", "ReviewFinding", "ApprovedChange",
    "REVIEWER_RETRY", "groq_rate_limiter", "is_transient_error", "with_fallback",
    "MODEL", "checkpointer",
    "parse_requirements", "load_document_text",
    "retrieve_standards", "search_requirements_standards", "standards_store",
    "pipeline_summary",
    "completeness_reviewer", "ambiguity_reviewer",
    "conflict_reviewer", "testability_standards_reviewer",
    "supervisor_route", "supervisor_synthesize", "render_report", "RouterDecision",
    "save_project_memory", "retrieve_project_memory",
    "requirements_approval_hitl", "build_approved_changes", "persist_po_decisions",
    "scripted_po_decision", "interactive_po_decision",
    "apply_changes", "apply_approved_changes", "EditorError",
    "review_pipeline", "requirements_copilot",
]
