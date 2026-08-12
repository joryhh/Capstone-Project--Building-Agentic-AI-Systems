"""Reliability policy shared by every LLM-backed task.

Imported before any agent module, because `@task` binds its retry policy at decoration
time: a policy created after the agents are defined would never attach to anything.
"""

from __future__ import annotations

from langchain_core.rate_limiters import InMemoryRateLimiter
from langgraph.types import RetryPolicy

from .schemas import Requirement, ReviewFinding

# Strategy 1 — throttle. Groq's free tier caps tokens per minute; fanning four reviewers
# out at once produced a real 429. One shared limiter spaces every call out.
groq_rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.2,
    check_every_n_seconds=0.1,
    max_bucket_size=2,
)


def is_transient_error(exc: BaseException) -> bool:
    """True only for errors a second attempt could plausibly survive."""
    # A daily-quota 429 cannot clear inside a retry window — fail fast and surface it.
    if "per day" in str(exc) or "TPD" in str(exc):
        return False
    if type(exc).__name__ in {
        "RateLimitError", "APITimeoutError", "APIConnectionError",
        "InternalServerError", "ServiceUnavailableError",
        "TimeoutError", "ConnectionError",
    }:
        return True
    return getattr(exc, "status_code", None) in (429, 500, 502, 503, 504)


# Strategy 2 — retry with exponential backoff, transient errors only.
REVIEWER_RETRY = RetryPolicy(
    max_attempts=5,
    initial_interval=3.0,
    backoff_factor=2.0,
    max_interval=45.0,   # 3s, 6s, 12s, 24s — enough to clear a per-minute window
    jitter=True,
    retry_on=is_transient_error,
)


def keep_known_requirement_ids(
    findings: list[ReviewFinding],
    requirements: list[Requirement],
    label: str,
) -> list[ReviewFinding]:
    """Drop findings citing a requirement id that is not under review.

    The knowledge base contains a sample SRS numbered REQ-101..REQ-110. Those ids reach the
    reviewer through the retrieved context, so a reviewer can return a well-formed finding
    about a requirement that exists only in the reference material — and the Editor would
    then be asked to rewrite a requirement that is not in the document.
    'missing' findings are exempt: they carry GAP-nnn ids by design.
    """
    valid = {r.id for r in requirements}
    kept, dropped = [], []
    for f in findings:
        target = kept if (f.issue_type == "missing" or f.requirement_id in valid) else dropped
        target.append(f)
    if dropped:
        print(f"  [{label}] dropped {len(dropped)} finding(s) citing ids not under review: "
              f"{sorted({f.requirement_id for f in dropped})}")
    return kept


def with_fallback(reviewer_task, label: str):
    """Wrap a reviewer so a permanent failure degrades to a structured finding.

    Returns list[ReviewFinding] exactly as a real reviewer does, so the synthesizer needs
    no special case for a dead reviewer.
    """
    def safe(*args, **kwargs) -> list[ReviewFinding]:
        try:
            return reviewer_task(*args, **kwargs).result()
        except Exception as exc:
            return [
                ReviewFinding(
                    requirement_id="REVIEWER-ERROR",
                    issue_type="untestable",
                    severity="low",
                    reason=f"{label} failed after all retries: {type(exc).__name__}: {exc}",
                    suggested_change="Manual review required — the automated reviewer was unavailable.",
                )
            ]
    return safe
