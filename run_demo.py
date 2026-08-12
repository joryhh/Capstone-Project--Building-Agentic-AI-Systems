#!/usr/bin/env python3
"""End-to-end demonstration of the Requirements Engineering Copilot.

Reviews the sample BrightPath document, pauses for Product Owner approval, applies the
approved changes, and prints the updated requirements document.

    python run_demo.py                 # scripted Product Owner decisions
    python run_demo.py --interactive   # answer approve/edit/reject at the console

Requires GROQ_API_KEY. Set LANGCHAIN_API_KEY and LANGCHAIN_TRACING_V2=true for tracing.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from langgraph.types import Command

from requirements_copilot import (
    Requirement,
    ReviewFinding,
    render_report,
    interactive_po_decision,
    load_document_text,
    parse_requirements,
    pipeline_summary,
    requirements_copilot,
    retrieve_project_memory,
    scripted_po_decision,
)
from requirements_copilot.display import banner, kv, ok, step, wrap
from requirements_copilot.runtime import DATA_DIR, MODEL, checkpointer

PROJECT_ID = "brightpath-capstone"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interactive", action="store_true",
                        help="answer approve/edit/reject at the console")
    parser.add_argument("--requirements", default=str(DATA_DIR / "demo_requirements_flawed.txt"))
    parser.add_argument("--description", default=str(DATA_DIR / "demo_project_description.txt"))
    args = parser.parse_args()

    if not os.environ.get("GROQ_API_KEY"):
        print("GROQ_API_KEY is not set. Export it and try again.", file=sys.stderr)
        return 1

    for path in (args.requirements, args.description):
        if not Path(path).exists():
            print(f"Input file not found: {path}", file=sys.stderr)
            return 1

    banner("setup")
    kv("model", MODEL)
    for label, value in pipeline_summary().items():
        kv(label, value)

    # ---------------------------------------------------------------- parse
    banner("1  parse")
    description = load_document_text(args.description)
    document = load_document_text(args.requirements)
    parsed = parse_requirements.invoke({"document_text": document})
    for r in parsed:
        kv(r["id"], wrap(r["text"], 12), width=10)

    # ------------------------------------------------------- review + pause
    banner("2  review")
    config = {"configurable": {"thread_id": "run-demo-session-1"}}
    paused = requirements_copilot.invoke(
        {"project_id": PROJECT_ID, "project_description": description, "requirements": parsed},
        config,
    )
    if "__interrupt__" not in paused:
        print("Pipeline did not pause for approval.", file=sys.stderr)
        return 1

    payload = paused["__interrupt__"][0].value

    # The paused result carries no report yet, so render one from the interrupt payload.
    finding_fields = ReviewFinding.model_fields
    findings = [
        ReviewFinding(**{k: v for k, v in f.items() if k in finding_fields})
        for f in payload["findings"]
    ]
    print()
    print(render_report(findings))

    banner("3  product owner approval")
    kv("findings awaiting review", len(payload["findings"]), width=26)
    kv("prior decisions on file", len(payload["previous_project_decisions"]), width=26)

    decide = interactive_po_decision if args.interactive else scripted_po_decision
    decisions = []
    for item in payload["findings"]:
        record = decide(item)
        decisions.append(record)
        if not args.interactive:
            print(f"  {record['decision']:<8} {item['issue_type']:<12} {item['requirement_id']}")

    resumed = requirements_copilot.invoke(Command(resume={"decisions": decisions}), config)
    ok("interrupt() paused the run and Command(resume=...) completed it")

    # ------------------------------------------------------- updated output
    banner("4  updated requirements document")
    before = {r["id"]: r["text"] for r in parsed}
    updated = [Requirement(**r) for r in resumed["updated_requirements"]]

    for r in updated:
        if r.id not in before:
            marker = "ADDED  "
        elif before[r.id] != r.text:
            marker = "REVISED"
        else:
            marker = "       "
        print(f"{marker}  {r.id:<12}{wrap(r.text, 21)}")

    step("summary")
    kv("added", sum(1 for r in updated if r.id not in before))
    kv("revised", sum(1 for r in updated if r.id in before and before[r.id] != r.text))
    kv("unchanged", sum(1 for r in updated if r.id in before and before[r.id] == r.text))

    # ------------------------------------------------- cross-thread memory
    banner("5  long-term memory from a new thread")
    from langgraph.func import entrypoint

    @entrypoint(checkpointer=checkpointer)
    def read_memory(inputs: dict) -> dict:
        return {"memories": retrieve_project_memory.invoke({"project_id": inputs["project_id"]})}

    recalled = read_memory.invoke(
        {"project_id": PROJECT_ID},
        {"configurable": {"thread_id": "run-demo-session-2"}},
    )["memories"]

    kv("written in thread", "run-demo-session-1")
    kv("read from thread", "run-demo-session-2")
    kv("decisions recalled", len(recalled))
    for m in recalled:
        print(f"  {m['decision']:<8} {m['requirement_id']:<10} {(m['final_text'] or '—')[:44]}")

    if not recalled:
        print("Long-term memory did not survive the thread change.", file=sys.stderr)
        return 1
    ok("decisions written in one thread are readable from a different thread")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
