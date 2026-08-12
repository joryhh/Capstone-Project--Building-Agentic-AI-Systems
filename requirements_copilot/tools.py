"""Requirements Parser tool.

A real tool: it reads `document_text` and extracts from it, returning structured
Requirement records with stable IDs.
"""

from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .runtime import make_llm
from .schemas import Requirement

parser_llm = make_llm()


class RequirementDraft(BaseModel):
    """One extracted requirement, before an ID is assigned."""

    text: str = Field(description="The requirement statement, lightly normalized")
    category: Optional[str] = Field(default=None, description="Optional grouping")


class ParsedRequirementsDraft(BaseModel):
    requirements: list[RequirementDraft] = Field(
        description="Every distinct requirement found, in the order they appear"
    )


structured_parser_llm = parser_llm.with_structured_output(ParsedRequirementsDraft)


@tool
def parse_requirements(document_text: str) -> list[dict]:
    """Parse a raw requirements document into structured Requirement items with stable IDs.

    Use this whenever you have unstructured requirements text and need it converted into
    individually addressable records for review.
    """
    if not document_text or not document_text.strip():
        return []

    prompt = f"""Extract every distinct requirement statement from the document below.
A requirement is a single sentence describing something the system shall/should/must do.
Split compound sentences into separate requirements if they describe separate behaviors.
Ignore headings, examples, and non-requirement prose.

DOCUMENT:
{document_text}
"""
    draft = structured_parser_llm.invoke(prompt)
    requirements = [
        Requirement(id=f"REQ-{i + 1:03d}", text=d.text.strip(), category=d.category)
        for i, d in enumerate(draft.requirements)
    ]
    print(f"  [parser] extracted {len(requirements)} requirement(s) "
          f"from {len(document_text)} chars")
    return [r.model_dump() for r in requirements]


def load_document_text(file_path: str) -> str:
    """Read raw text from a .txt or .docx file."""
    if str(file_path).endswith(".docx"):
        from docx import Document
        return "\n".join(p.text for p in Document(file_path).paragraphs)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
