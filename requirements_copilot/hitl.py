"""Human-in-the-loop approval.

The pipeline pauses with `interrupt()` before anything is written, presents every finding
to the Product Owner, and resumes on `Command(resume=...)`. Each finding gets approve,
edit, or reject; decisions are translated into ApprovedChange records and persisted to
long-term memory.
"""

from __future__ import annotations

from typing import Literal, Optional

from langgraph.func import task
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from .memory import save_project_memory
from .schemas import ApprovedChange, ReviewFinding


class POFindingDecision(BaseModel):
    finding_index: int = Field(ge=0)
    decision: Literal["approve", "edit", "reject"]
    edited_text: Optional[str] = None
    notes: Optional[str] = None


class POReviewResponse(BaseModel):
    decisions: list[POFindingDecision]


@task
def requirements_approval_hitl(
    project_id: str,
    findings: list[ReviewFinding],
    previous_project_decisions: list[dict],
) -> dict:
    """Pause the run and hand every finding to the Product Owner."""
    return interrupt({
        "type": "requirements_review_approval",
        "project_id": project_id,
        "message": "Review every finding and choose approve, edit, or reject.",
        "previous_project_decisions": previous_project_decisions,
        "findings": [
            {"finding_index": i, **f.model_dump(),
             "allowed_decisions": ["approve", "edit", "reject"]}
            for i, f in enumerate(findings)
        ],
    })


@task
def build_approved_changes(
    findings: list[ReviewFinding], po_response: dict
) -> list[ApprovedChange]:
    """Translate PO decisions into Editor instructions. Every finding needs exactly one."""
    response = POReviewResponse(**po_response)

    by_index: dict[int, POFindingDecision] = {}
    for d in response.decisions:
        if d.finding_index in by_index:
            raise ValueError(f"Duplicate decision for finding {d.finding_index}.")
        by_index[d.finding_index] = d
    if set(by_index) != set(range(len(findings))):
        raise ValueError("Every finding must have exactly one Product Owner decision.")

    changes: list[ApprovedChange] = []
    for index, finding in enumerate(findings):
        d = by_index[index]

        if d.decision == "approve":
            action = "add" if finding.issue_type == "missing" else "replace"
            changes.append(ApprovedChange(
                requirement_id=finding.requirement_id, action=action,
                edited_text=finding.suggested_change, notes=d.notes))

        elif d.decision == "edit":
            if not d.edited_text or not d.edited_text.strip():
                raise ValueError(f"Finding {index} requires edited_text.")
            # A 'missing' finding has no existing requirement to edit in place — the PO
            # editing it still means ADD. Emitting apply_po_edit would hand the Editor a
            # GAP-nnn id that does not exist.
            action = "add" if finding.issue_type == "missing" else "apply_po_edit"
            changes.append(ApprovedChange(
                requirement_id=finding.requirement_id, action=action,
                edited_text=d.edited_text.strip(), notes=d.notes))

        else:
            changes.append(ApprovedChange(
                requirement_id=finding.requirement_id, action="leave_unchanged",
                edited_text=None, notes=d.notes))

    return changes


@task
def persist_po_decisions(
    project_id: str,
    findings: list[ReviewFinding],
    approved_changes: list[ApprovedChange],
) -> list[str]:
    """Write each decision to long-term memory so later sessions can see it."""
    if len(findings) != len(approved_changes):
        raise ValueError("findings and approved_changes must be the same length.")

    decision_for = {"leave_unchanged": "reject", "apply_po_edit": "edit"}
    memory_ids = []
    for finding, change in zip(findings, approved_changes):
        memory_ids.append(save_project_memory.invoke({
            "project_id": project_id,
            "requirement_id": finding.requirement_id,
            "decision": decision_for.get(change.action, "approve"),
            "final_text": change.edited_text or "",
            "notes": change.notes or "",
        }))
    return memory_ids


def scripted_po_decision(item: dict) -> dict:
    """Default Product Owner answers, rotating approve / edit / reject.

    Lets the system run unattended: `input()` would block a non-interactive run and leave
    no captured output. The pause and the resume are real either way — only the source of
    the answers changes.
    """
    index = item["finding_index"]
    if index % 3 == 0:
        return {"finding_index": index, "decision": "approve", "edited_text": None,
                "notes": "Accepted the reviewer's suggested wording."}
    if index % 3 == 1:
        return {"finding_index": index, "decision": "edit",
                "edited_text": f"{item['suggested_change']} Verified against the team glossary.",
                "notes": "Approved with a Product Owner wording change."}
    return {"finding_index": index, "decision": "reject", "edited_text": None,
            "notes": "Deferred — out of scope for this release."}


def interactive_po_decision(item: dict) -> dict:
    """Prompt the Product Owner at the console."""
    while True:
        choice = input(
            f"\nFinding {item['finding_index']} — approve / edit / reject: "
        ).strip().lower()
        if choice in {"approve", "edit", "reject"}:
            break
        print("Please enter approve, edit, or reject.")

    edited_text = None
    if choice == "edit":
        edited_text = input("Enter the edited requirement: ").strip()
        while not edited_text:
            edited_text = input("Cannot be empty. Enter the edited requirement: ").strip()

    notes = input("Optional notes (Enter to skip): ").strip()
    return {"finding_index": item["finding_index"], "decision": choice,
            "edited_text": edited_text, "notes": notes or None}
