"""The four specialist reviewer agents.

Each returns typed ReviewFinding records via `with_structured_output`, never free text
parsed by code. The two RAG-grounded reviewers retrieve first, then make a single grounded
generation call (2-Step RAG).
"""

from __future__ import annotations

from typing import Literal, Optional

from langgraph.func import task
from pydantic import BaseModel, Field

from .rag import retrieve_standards
from .reliability import REVIEWER_RETRY, keep_known_requirement_ids
from .runtime import make_llm
from .schemas import Requirement, ReviewFinding

reviewer_llm = make_llm()


# --------------------------------------------------------------- Completeness

class MissingRequirementDraft(BaseModel):
    """One capability described in the project but not covered by any requirement."""

    reason: str = Field(description="Why this is missing, referencing the project description")
    suggested_change: str = Field(description="The requirement to add, as 'The system shall ...'")
    severity: Literal["low", "medium", "high", "critical"]


class CompletenessFindings(BaseModel):
    gaps: list[MissingRequirementDraft] = Field(
        description="One per described capability with no matching requirement; "
                    "empty if fully covered"
    )


completeness_llm = reviewer_llm.with_structured_output(CompletenessFindings)


@task(retry_policy=REVIEWER_RETRY)
def completeness_reviewer(
    project_description: Optional[str], requirements: list[Requirement]
) -> list[ReviewFinding]:
    """Finds capabilities the project description promises but no requirement covers."""
    if not project_description:
        return []

    existing = "\n".join(f"- {r.id}: {r.text}" for r in requirements) or "(none provided)"
    prompt = f"""You are reviewing a requirements document for completeness against its project description.

PROJECT DESCRIPTION:
{project_description}

EXISTING REQUIREMENTS:
{existing}

Find every capability mentioned or clearly implied in the project description that has
NO corresponding requirement above. Do not flag anything already covered, even if worded
differently. If everything is covered, return an empty list.
"""
    result = completeness_llm.invoke(prompt)
    findings = [
        ReviewFinding(
            requirement_id=f"GAP-{i + 1:03d}",
            issue_type="missing",
            severity=g.severity,
            reason=g.reason,
            suggested_change=g.suggested_change,
        )
        for i, g in enumerate(result.gaps)
    ]
    print(f"  [completeness] found {len(findings)} gap(s)")
    return findings


# ------------------------------------------------------------------ Ambiguity

class AmbiguityFindingDraft(BaseModel):
    """One requirement flagged for vague or subjective wording."""

    requirement_id: str = Field(description="ID of the flagged requirement, copied exactly")
    reason: str = Field(description="Which terms are vague and why they can't be verified")
    suggested_change: str = Field(description="Rewritten with a measurable threshold")
    severity: Literal["low", "medium", "high", "critical"]


class AmbiguityFindings(BaseModel):
    findings: list[AmbiguityFindingDraft] = Field(
        description="One per requirement with vague wording; empty list if none"
    )


ambiguity_llm = reviewer_llm.with_structured_output(AmbiguityFindings)


@task(retry_policy=REVIEWER_RETRY)
def ambiguity_reviewer(requirements: list[Requirement]) -> list[ReviewFinding]:
    """Flags vague or subjective terms and proposes a measurable rewrite."""
    if not requirements:
        return []

    listed = "\n".join(f"- {r.id}: {r.text}" for r in requirements)
    prompt = f"""Review these requirements for vague or subjective wording that cannot be
objectively tested (e.g. "quickly", "user-friendly", "fast", "easy", "robust", "efficient").

REQUIREMENTS:
{listed}

For each requirement containing such wording, explain what is vague and rewrite it with a
concrete, measurable threshold. If a requirement is already specific and testable, do NOT
include it. An empty findings list is a valid and expected answer.
"""
    result = ambiguity_llm.invoke(prompt)
    findings = [
        ReviewFinding(
            requirement_id=f.requirement_id,
            issue_type="ambiguous",
            severity=f.severity,
            reason=f.reason,
            suggested_change=f.suggested_change,
        )
        for f in result.findings
    ]
    findings = keep_known_requirement_ids(findings, requirements, "ambiguity")
    print(f"  [ambiguity] found {len(findings)} vague requirement(s)")
    return findings


# ------------------------------------------------------- Conflict (RAG-grounded)

class ConflictDraft(BaseModel):
    """One contradiction found between two requirements."""

    requirement_id: str = Field(description="ID of the FIRST requirement in the pair, copied exactly")
    conflicting_with_id: str = Field(description="ID of the SECOND requirement in the pair, copied exactly")
    pattern: str = Field(description="Which conflict pattern from the retrieved reference this matches")
    reason: str = Field(description="Why both cannot be satisfied at once, naming both IDs")
    suggested_change: str = Field(description="A rewrite that removes the contradiction")
    severity: Literal["low", "medium", "high", "critical"]


class ConflictFindings(BaseModel):
    conflicts: list[ConflictDraft] = Field(
        description="One per genuinely contradictory pair; empty if mutually consistent"
    )


conflict_llm = reviewer_llm.with_structured_output(ConflictFindings)


@task(retry_policy=REVIEWER_RETRY)
def conflict_reviewer(requirements: list[Requirement]) -> list[ReviewFinding]:
    """Detects contradictions between requirements, grounded in retrieved conflict patterns."""
    if len(requirements) < 2:
        return []

    # Step 1 — retrieve
    context = retrieve_standards(
        "requirement conflict patterns contradiction permission prohibition "
        "incompatible ordering mutually exclusive what is not a conflict",
        k=3,
    )

    # Step 2 — generate, grounded
    listed = "\n".join(f"- {r.id}: {r.text}" for r in requirements)
    prompt = f"""You are the Conflict Reviewer. Find pairs of requirements that contradict
each other, using the reference material below to decide what does and does not count.

REFERENCE MATERIAL:
{context}

REQUIREMENTS UNDER REVIEW:
{listed}

Report a conflict only when two requirements cannot both be satisfied by any single
implementation. Requirements about different actors, different entities, or mutually
exclusive preconditions are NOT conflicts. A general rule with an exception that explicitly
states its precedence is NOT a conflict.

Copy requirement IDs exactly. Report ONLY on requirements listed under REQUIREMENTS UNDER
REVIEW — the reference material has its own example IDs, which are illustrations only.
If nothing genuinely contradicts, return an empty list.
"""
    result = conflict_llm.invoke(prompt)
    findings = [
        ReviewFinding(
            requirement_id=c.requirement_id,
            issue_type="conflicting",
            severity=c.severity,
            # ReviewFinding carries one id, so the partner is named in the reason rather
            # than changing the shared schema.
            reason=f"Conflicts with {c.conflicting_with_id} [{c.pattern}]. {c.reason}",
            suggested_change=c.suggested_change,
        )
        for c in result.conflicts
    ]
    findings = keep_known_requirement_ids(findings, requirements, "conflict")
    print(f"  [conflict] found {len(findings)} contradiction(s)")
    return findings


# ------------------------------------- Testability & Standards (RAG-grounded)

class TestabilityDraft(BaseModel):
    """One requirement that cannot be objectively verified, or breaches house style."""

    requirement_id: str = Field(description="ID of the flagged requirement, copied exactly")
    reason: str = Field(description="Why it has no pass/fail criterion, or which rule it breaches")
    suggested_change: str = Field(description="Rewritten so a tester can determine pass/fail")
    severity: Literal["low", "medium", "high", "critical"]


class TestabilityFindings(BaseModel):
    findings: list[TestabilityDraft] = Field(
        description="One per unverifiable or non-compliant requirement; empty if all are fine"
    )


testability_llm = reviewer_llm.with_structured_output(TestabilityFindings)


@task(retry_policy=REVIEWER_RETRY)
def testability_standards_reviewer(requirements: list[Requirement]) -> list[ReviewFinding]:
    """Flags requirements with no objective pass/fail criterion, grounded in the standards."""
    if not requirements:
        return []

    # Step 1 — retrieve, querying with the requirement text so passages match THIS document
    query = (
        "verifiable testable acceptance criteria measurable threshold pass fail "
        "prohibited vague terms requirement sentence form "
        + " ".join(r.text for r in requirements)
    )
    context = retrieve_standards(query, k=4)

    # Step 2 — generate, grounded
    listed = "\n".join(f"- {r.id}: {r.text}" for r in requirements)
    prompt = f"""You are the Testability & Standards Reviewer. Judge each requirement against
the retrieved standards below, not against your own preferences.

RETRIEVED STANDARDS:
{context}

REQUIREMENTS UNDER REVIEW:
{listed}

Flag a requirement when EITHER:
(a) it has no objective pass/fail criterion, or
(b) it breaches a rule in the retrieved standards, such as a prohibited vague term with no
    numeric threshold.

Cite the specific rule in your reason and rewrite it following the retrieved template.
Do not flag a requirement that is already specific and verifiable, and do not flag one
solely for missing acceptance criteria when its behaviour is already objectively observable.

Report ONLY on requirements listed under REQUIREMENTS UNDER REVIEW — the retrieved standards
contain their own example IDs (REQ-1nn), which are illustrations only.
An empty findings list is a valid and expected answer.
"""
    result = testability_llm.invoke(prompt)
    findings = [
        ReviewFinding(
            requirement_id=f.requirement_id,
            issue_type="untestable",
            severity=f.severity,
            reason=f.reason,
            suggested_change=f.suggested_change,
        )
        for f in result.findings
    ]
    findings = keep_known_requirement_ids(findings, requirements, "testability")
    print(f"  [testability] found {len(findings)} unverifiable requirement(s)")
    return findings
