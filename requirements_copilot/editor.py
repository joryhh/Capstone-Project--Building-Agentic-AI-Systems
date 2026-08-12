"""Requirements Editor.

Applies approved changes and nothing else. It makes no judgement about whether a suggestion
was correct — that decision was the Product Owner's, one step earlier.
"""

from __future__ import annotations

from langgraph.func import task

from .schemas import ApprovedChange, Requirement


class EditorError(Exception):
    """Raised when an ApprovedChange cannot be applied."""


def _apply_one(by_id: dict, change: ApprovedChange, next_new_id: int) -> int:
    if change.action == "leave_unchanged":
        return next_new_id

    if change.action in ("replace", "apply_po_edit"):
        if change.requirement_id not in by_id:
            raise EditorError(
                f"Cannot {change.action} unknown requirement_id={change.requirement_id!r}")
        if not change.edited_text:
            raise EditorError(
                f"{change.action} on {change.requirement_id!r} missing edited_text")
        by_id[change.requirement_id].text = change.edited_text
        return next_new_id

    if change.action == "add":
        if not change.edited_text:
            raise EditorError("add action missing edited_text")
        new_id = change.requirement_id
        # A completeness finding arrives as GAP-nnn, which is a finding id, not a
        # requirement id. Anything missing, taken, or not REQ-shaped gets a fresh id.
        if not new_id or new_id in by_id or not new_id.startswith("REQ-"):
            new_id = f"REQ-NEW-{next_new_id:03d}"
            next_new_id += 1
        by_id[new_id] = Requirement(id=new_id, text=change.edited_text)
        return next_new_id

    raise EditorError(f"Unknown action: {change.action!r}")


def apply_changes(
    requirements: list[Requirement], decisions: list[ApprovedChange]
) -> list[Requirement]:
    """Apply a batch of approved changes and return the updated requirements list."""
    by_id = {r.id: r for r in requirements}
    next_new_id = 1
    for change in decisions:
        next_new_id = _apply_one(by_id, change, next_new_id)
    return list(by_id.values())


apply_approved_changes = task(apply_changes)
