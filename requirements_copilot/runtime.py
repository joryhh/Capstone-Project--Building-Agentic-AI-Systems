"""Shared LLM client and paths.

One place to change the model, so the four agent modules stay consistent.
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver

from .reliability import groq_rate_limiter

MODEL = os.environ.get("COPILOT_MODEL", "llama-3.3-70b-versatile")

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
DATA_DIR = Path(os.environ.get("COPILOT_DATA_DIR", REPO_ROOT / "data"))
KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"


def make_llm(temperature: float = 0) -> ChatGroq:
    """A Groq client sharing the global rate limiter."""
    return ChatGroq(model=MODEL, temperature=temperature, rate_limiter=groq_rate_limiter)


# Short-term memory: per-thread state, and what makes an interrupted run resumable.
checkpointer = InMemorySaver()
