"""The two entrypoints.

**Workflow pattern: Orchestrator–Worker.** The Supervisor is the orchestrator; the four
reviewers are workers. It fits because the reviewers are independent specialists over the
same input, and which of them are needed is decided per input rather than fixed in advance.
Futures are collected before any `.result()` so selected reviewers run concurrently.

`review_pipeline` reviews and reports. `requirements_copilot` is the full system, adding
long-term memory, the approval pause, and the Editor.
"""

from __future__ import annotations

from langgraph.func import entrypoint

from .editor import apply_approved_changes
from .hitl import build_approved_changes, persist_po_decisions, requirements_approval_hitl
from .memory import retrieve_project_memory
from .reviewers import (
    ambiguity_reviewer,
    completeness_reviewer,
    conflict_reviewer,
    testability_standards_reviewer,
)
from .runtime import checkpointer
from .schemas import Requirement
from .supervisor import render_report, supervisor_route, supervisor_synthesize


def _run_selected_reviewers(decision, project_description, requirements):
    """Dispatch only the reviewers the orchestrator selected, concurrently."""
    futures = []
    if decision.run_completeness:
        futures.append(completeness_reviewer(project_description, requirements))
    if decision.run_ambiguity:
        futures.append(ambiguity_reviewer(requirements))
    if decision.run_conflict:
        futures.append(conflict_reviewer(requirements))
    if decision.run_testability:
        futures.append(testability_standards_reviewer(requirements))
    return [f.result() for f in futures]


@entrypoint(checkpointer=checkpointer)
def review_pipeline(inputs: dict) -> dict:
    """Review only: route -> selected reviewers -> merged report."""
    project_description = inputs.get("project_description")
    requirements = [Requirement(**r) for r in inputs.get("requirements", [])]

    decision = supervisor_route(project_description, requirements).result()
    print(f"  [router] {decision.reason}")

    finding_lists = _run_selected_reviewers(decision, project_description, requirements)
    findings = supervisor_synthesize(finding_lists).result()

    return {
        "routing_decision": decision.model_dump(),
        "findings": [f.model_dump() for f in findings],
        "report": render_report(findings),
    }


@entrypoint(checkpointer=checkpointer)
def requirements_copilot(inputs: dict) -> dict:
    """Full system: memory -> route -> review -> approval pause -> Editor -> updated document."""
    project_id = inputs["project_id"]
    project_description = inputs.get("project_description")
    requirements = [Requirement(**r) for r in inputs.get("requirements", [])]

    previous_decisions = retrieve_project_memory.invoke({"project_id": project_id})

    decision = supervisor_route(project_description, requirements).result()
    print(f"  [router] {decision.reason}")

    finding_lists = _run_selected_reviewers(decision, project_description, requirements)
    findings = supervisor_synthesize(finding_lists).result()

    # Pause here — nothing below this line runs until the Product Owner responds.
    po_response = requirements_approval_hitl(project_id, findings, previous_decisions).result()

    approved_changes = build_approved_changes(findings, po_response).result()
    memory_ids = persist_po_decisions(project_id, findings, approved_changes).result()
    updated = apply_approved_changes(requirements, approved_changes).result()

    return {
        "project_id": project_id,
        "routing_decision": decision.model_dump(),
        "previous_project_decisions": previous_decisions,
        "findings": [f.model_dump() for f in findings],
        "report": render_report(findings),
        "approved_changes": [c.model_dump() for c in approved_changes],
        "saved_memory_ids": memory_ids,
        "updated_requirements": [r.model_dump() for r in updated],
    }
