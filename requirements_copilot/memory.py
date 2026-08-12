"""Long-term project memory.

Short-term memory is the checkpointer in `runtime`, keyed by `thread_id`. This module is
the long-term half: a separate store keyed by `project_id`, so Product Owner decisions
written in one thread are readable from a different thread in a later session. That
independence from `thread_id` is what makes it long-term rather than a growing message list.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from langchain_core.tools import tool
from langgraph.store.memory import InMemoryStore

project_memory_store = InMemoryStore()


def _namespace(project_id: str) -> tuple[str, str]:
    project_id = project_id.strip()
    if not project_id:
        raise ValueError("project_id must not be empty.")
    return (project_id, "po_decisions")


@tool
def save_project_memory(
    project_id: str,
    requirement_id: str,
    decision: str,
    final_text: str = "",
    notes: str = "",
) -> str:
    """Save a Product Owner decision to long-term project memory. Returns the memory id."""
    memory_id = str(uuid4())
    project_memory_store.put(
        _namespace(project_id),
        memory_id,
        {
            "project_id": project_id,
            "requirement_id": requirement_id,
            "decision": decision,
            "final_text": final_text or None,
            "notes": notes or None,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return memory_id


@tool
def retrieve_project_memory(project_id: str) -> list[dict]:
    """Retrieve every stored Product Owner decision for a project, from any thread."""
    items = project_memory_store.search(_namespace(project_id), limit=100)
    return [{"memory_id": item.key, **item.value} for item in items]
