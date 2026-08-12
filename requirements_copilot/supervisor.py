"""The Supervisor: router and synthesizer.

As **router** it makes an LLM call with constrained output to decide which reviewers an
input needs — not a keyword rule. As **synthesizer** it merges the selected reviewers'
findings, removes duplicates, and orders by severity.
"""

from __future__ import annotations

from typing import Optional

from langgraph.func import task
from pydantic import BaseModel, Field

from .display import wrap
from .reliability import REVIEWER_RETRY
from .runtime import make_llm
from .schemas import Requirement, ReviewFinding

llm = make_llm()


class RouterDecision(BaseModel):
    """Which reviewers should run on this input."""

    run_completeness: bool = Field(description="True only if a project description exists")
    run_ambiguity: bool = Field(description="True if at least one requirement exists")
    run_conflict: bool = Field(description="True only if at least two requirements exist")
    run_testability: bool = Field(description="True if at least one requirement exists")
    reason: str = Field(description="One sentence justifying the selection")


router_llm = llm.with_structured_output(RouterDecision)


def _enforce_hard_guardrails(
    decision: RouterDecision,
    project_description: Optional[str],
    requirements: list[Requirement],
) -> RouterDecision:
    """A deterministic floor under the LLM's choice.

    This does not replace routing — it only blocks work that is structurally impossible
    rather than a judgement call: completeness needs a description to compare against,
    conflict needs at least two requirements.
    """
    if not project_description:
        decision.run_completeness = False
    if len(requirements) < 2:
        decision.run_conflict = False
    if not requirements:
        decision.run_ambiguity = False
        decision.run_testability = False
    return decision


@task(retry_policy=REVIEWER_RETRY)
def supervisor_route(
    project_description: Optional[str], requirements: list[Requirement]
) -> RouterDecision:
    """Supervisor-as-router: the LLM decides who runs, via constrained structured output."""
    listed = ("\n".join(f"- [{r.id}] {r.text}" for r in requirements)) if requirements else "(none)"
    prompt = f"""You are the Supervisor for a requirements-review pipeline.
Decide which reviewers should run on this input. Do not run a reviewer whose job is
logically impossible given the input (e.g. completeness with no project description).

Output strict JSON booleans (true/false) for the routing fields, not strings.

Project description: {project_description if project_description else "(none provided)"}
Number of requirements: {len(requirements)}
Requirements:
{listed}
"""
    decision = router_llm.invoke(prompt)
    return _enforce_hard_guardrails(decision, project_description, requirements)


SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@task
def supervisor_synthesize(finding_lists: list[list[ReviewFinding]]) -> list[ReviewFinding]:
    """Flatten, dedupe by (requirement_id, issue_type) keeping the worst, sort by severity."""
    flattened = [f for group in finding_lists for f in group]
    deduped: dict = {}
    for f in flattened:
        key = (f.requirement_id, f.issue_type)
        current = deduped.get(key)
        if current is None or SEVERITY_RANK[f.severity] < SEVERITY_RANK[current.severity]:
            deduped[key] = f
    return sorted(deduped.values(), key=lambda f: SEVERITY_RANK[f.severity])


def render_report(findings: list[ReviewFinding]) -> str:
    """Severity-ordered report with a per-severity summary line."""
    if not findings:
        return ("REQUIREMENTS REVIEW REPORT\n\n"
                "No findings — the document passed every check that ran.")

    counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITY_RANK}
    summary = "  ".join(f"{s}:{counts[s]}" for s in ("critical", "high", "medium", "low"))

    lines = ["REQUIREMENTS REVIEW REPORT", "", f"{len(findings)} finding(s)    {summary}", ""]
    for f in findings:
        lines.append(f"[{f.severity.upper()}] {f.issue_type.upper()} — {f.requirement_id}")
        lines.append(f"   why : {wrap(f.reason, 9)}")
        lines.append(f"   fix : {wrap(f.suggested_change, 9)}")
        lines.append("")
    return "\n".join(lines)
