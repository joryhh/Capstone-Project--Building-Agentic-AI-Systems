"""Shared data contracts.

Every agent in the system speaks in these three types. `Requirement` and `ReviewFinding`
are the contract between the reviewers and the Supervisor; `ApprovedChange` is the contract
between the human-in-the-loop step and the Editor.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Requirement(BaseModel):
    """A single parsed requirement."""

    id: str = Field(description="Stable identifier, e.g. 'REQ-001'")
    text: str = Field(description="The requirement statement")
    category: Optional[str] = Field(default=None, description="Optional grouping")


class ReviewFinding(BaseModel):
    """One issue raised by any reviewer, against one requirement."""

    requirement_id: str = Field(description="ID of the requirement this refers to")
    issue_type: Literal["missing", "ambiguous", "conflicting", "untestable"] = Field(
        description="missing: should exist but doesn't; ambiguous: vague wording; "
                    "conflicting: contradicts another; untestable: no pass/fail criterion"
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        description="How much this would hurt the project if left unresolved"
    )
    reason: str = Field(description="One or two sentences explaining the issue")
    suggested_change: str = Field(description="A concrete, measurable rewrite or addition")


class ApprovedChange(BaseModel):
    """A Product Owner decision on one finding, consumed by the Editor."""

    requirement_id: str
    action: Literal["replace", "add", "apply_po_edit", "leave_unchanged"] = Field(
        description="replace: use suggested_change; add: insert a new requirement; "
                    "apply_po_edit: use the PO's own wording; leave_unchanged: rejected"
    )
    edited_text: Optional[str] = Field(
        default=None, description="Set for every action except leave_unchanged"
    )
    notes: Optional[str] = Field(default=None, description="PO rationale, optional")
