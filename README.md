# Requirements Engineering Copilot

**Requirements Engineering Copilot** is a **multi-agent requirements review system** that turns a software requirements document into a reviewed, corrected, human-approved specification. It is built with the LangGraph Functional API, Groq (Llama 3.3 70B), a retrieval-augmented knowledge base of requirements-engineering standards, long-term cross-session memory, a human-in-the-loop approval gate, structured error handling, and LangSmith observability.

> **Students:** Dalia Alosaimi, Ghala Alawad, Jory Alhassan, Salma Alfehaid, Shahad Alahmari
>
> **Training program:** Building Agentic AI Systems
>
> **Delivered by:** SDAIA Academy
>
> **Trainer:** Mohammed Albeladi
>
> **Cohort/session dates:** **August 9 - August 13 2026**
>
> **SDAIA Academy on GitHub:** https://github.com/SDAIAAcademy

---

## Project Description

**Requirements Engineering Copilot** performs the review that normally happens in a requirements walkthrough meeting: reading a specification closely, finding what is vague, what contradicts, what cannot be tested, and what the project promised but the document never captured.

Requirements defects are the most expensive defects in software, because they propagate. A requirement that says the system should respond *quickly* survives review, becomes a design, becomes code, and is only discovered to be untestable when someone tries to write the acceptance test. A pair of requirements that quietly contradict each other are not noticed until an implementer has to satisfy both. These are the errors that manual review misses precisely because reading a long document attentively is difficult, and because no single reviewer holds every requirement in mind at once.

The obvious approach — one large prompt asking a model to "review these requirements" — fails in a predictable way. The model produces a plausible list of comments that mixes categories, misses contradictions between distant requirements, applies its own unstated notion of quality, and offers no way to accept some suggestions and reject others.

Requirements Engineering Copilot addresses this by dividing the review among specialists and keeping a human in control of the outcome. A **Requirements Supervisor** examines the input and decides, through a constrained LLM call, which reviewers the input actually needs. The selected reviewers run as concurrent workers: a **Completeness Reviewer** compares the requirements against the project description to find capabilities that were described but never specified; an **Ambiguity Reviewer** flags subjective wording and proposes measurable replacements; a **Conflict Reviewer** searches for pairs of requirements that cannot both be satisfied; and a **Testability & Standards Reviewer** judges whether each requirement has an objective pass/fail criterion.

The last two reviewers do not rely on the model's own taste. Both retrieve from a knowledge base of requirements-engineering standards before they judge, so a finding cites the specific rule it rests on — the prohibited-terms list, the required sentence form, the catalogued conflict pattern — rather than asserting that something feels wrong.

The Supervisor then merges every reviewer's output, removes duplicates, and orders findings by severity. Before a single word of the document changes, the workflow **pauses at a genuine interrupt** and presents each finding to the Product Owner, who may approve it, edit the wording, or reject it. Only after that decision does a separate **Requirements Editor** apply the approved changes. The Editor exercises no judgement of its own; that separation is deliberate, and it is what makes the system safe to point at a real specification.

Every Product Owner decision is written to a **long-term store keyed by project**, not by conversation. A decision made in one session is readable in a later session on a different thread, so the system accumulates a record of what this team has already agreed rather than starting from zero each time.

For evidence, the repository contains an executed Colab notebook with a demo section covering parsing, retrieval verification, routing selectivity, a full review, the approval pause and resume, cross-thread memory recall, error handling, and observability — alongside the same code organized as an importable Python package.

---

## Problem Statement

Reviewing a requirements document manually is slow, inconsistent, and dependent on which reviewer happens to read which page.

Handled that way, or by a single undivided model call, this commonly leads to:

- Vague terms that survive review and cannot be turned into an acceptance test
- Contradictory requirements that are only discovered during implementation
- Capabilities promised in the project brief but never written as requirements
- Review comments that reflect a reviewer's personal taste rather than a documented standard
- No record of which suggestions were accepted, edited, or rejected, and why
- Decisions from earlier reviews forgotten by the next session
- Automated tools that rewrite the document without asking

Requirements Engineering Copilot provides one orchestrated workflow that performs these checks while grounding its judgements in documented standards, keeping a human in control of every change, and remembering what was decided.

---

## System Objectives

The system is designed to:

1. Parse a raw requirements document into individually addressable, structured requirements.
2. Decide, through a constrained LLM call, which reviewers a given input needs.
3. Detect capabilities described in the project brief that no requirement covers.
4. Flag vague or subjective wording and propose measurable replacements.
5. Detect pairs of requirements that cannot both be satisfied.
6. Judge testability against retrieved requirements-engineering standards rather than model intuition.
7. Ground reviewer findings in a documented rule, cited in the finding itself.
8. Merge, deduplicate, and severity-order every reviewer's output into one report.
9. Pause for a real Product Owner decision before any requirement is modified.
10. Apply only approved changes, through an editor that makes no judgement of its own.
11. Persist Product Owner decisions across sessions and threads, keyed by project.
12. Survive transient API failures through throttling and bounded retry, and degrade safely when a reviewer cannot be reached.
13. Trace every agent, tool call, and retry to LangSmith for inspection.

---

## Multi-Agent Architecture

The system uses an **Orchestrator–Worker pattern built on the LangGraph Functional API**.

A single `@entrypoint` defines the workflow and each agent is an `@task` within it. The Supervisor is the orchestrator: it makes the routing decision, dispatches the selected reviewers as concurrent workers, and merges what they return. No reviewer calls another reviewer; each is an independent specialist over the same input, and their results meet only at the synthesizer.

This pattern fits the problem because the four reviewers are genuinely independent — a conflict check tells you nothing about testability — and because which reviewers are needed varies by input. A document with one requirement cannot have internal conflicts; a document submitted without a project description cannot be checked for completeness.

### Coordination Strategy

Coordination is **centralized through the Supervisor, with results merged in a single synthesis step**. The orchestrator collects reviewer futures before resolving any of them, so the selected reviewers execute concurrently rather than as a serial chain. Each reviewer returns a list of typed `ReviewFinding` records, and the synthesizer flattens them, deduplicates by `(requirement_id, issue_type)` keeping the highest severity, and sorts the result.

### Agents and Responsibilities

#### 1. Requirements Supervisor

Fills two roles. As **router**, it makes an LLM call with `with_structured_output` returning a typed `RouterDecision` — four booleans and a justification — deciding which reviewers this input needs. This is a constrained-output decision, not keyword matching. A deterministic guardrail sits *under* the LLM's choice and blocks only what is structurally impossible: completeness review with no description to compare against, conflict review with fewer than two requirements. As **synthesizer**, it merges the reviewers' findings, removes duplicates, and orders them by severity.

#### 2. Completeness Reviewer

Compares the project description against the parsed requirements to find capabilities that were described or clearly implied but never turned into a requirement, and drafts the requirement that would close each gap. Its findings carry `GAP-nnn` identifiers, since they refer to requirements that do not yet exist.

#### 3. Ambiguity Reviewer

Flags subjective or unmeasurable wording — *quickly*, *user-friendly*, *robust*, *efficient* — and rewrites each flagged requirement with a concrete threshold.

#### 4. Conflict Reviewer (RAG-grounded)

Retrieves the catalogued conflict patterns, then searches requirement pairs for contradictions that match them, naming the pattern in each finding. The retrieved reference also states what is *not* a conflict, which suppresses false positives on general rules paired with an explicitly-scoped exception.

#### 5. Testability & Standards Reviewer (RAG-grounded)

Retrieves the quality criteria and the house writing template, then judges whether each requirement has an objective pass/fail criterion and follows the documented sentence form. Findings cite the specific rule breached rather than asserting a general dissatisfaction.

#### 6. Requirements Editor

Applies approved changes and nothing else — replacing a requirement, adding a new one, applying the Product Owner's own wording, or leaving a rejected finding untouched. It performs no evaluation; every decision it acts on was made by a human one step earlier.

---

## Workflow

```text
Requirements Document + Project Description
   |
   v
Requirements Parser Tool  (structured extraction, stable IDs)
   |
   v
Requirements Supervisor  — ROUTER
   |   constrained LLM decision: which reviewers does this input need?
   |
   +---> Completeness Reviewer          (if a project description exists)
   +---> Ambiguity Reviewer             (if any requirement exists)
   +---> Conflict Reviewer         RAG  (if two or more requirements exist)
   +---> Testability & Standards   RAG  (if any requirement exists)
   |         selected workers run concurrently
   v
Requirements Supervisor  — SYNTHESIZER
   |   merge, deduplicate, order by severity
   v
Human-in-the-Loop Interrupt
   |   per finding: approve / edit / reject
   |   nothing below this line runs until the Product Owner responds
   v
Persist decisions to long-term project memory
   |
   v
Requirements Editor  (applies approved changes only)
   |
   v
Updated Requirements Document
```

---

## Workflow Pattern

The system implements the **Orchestrator–Worker** pattern. The Supervisor is the orchestrator and the four reviewers are the workers.

It was chosen over the alternatives because the reviewers are independent specialists over one shared input, with no data flowing between them — which rules out Prompt Chaining — and because the set of reviewers is decided per input rather than fixed, which is more than plain Parallelization provides. The orchestrator's decision is a real one: a single-requirement document with no description runs two reviewers, while a full document runs all four.

---

## RAG Pipeline

The knowledge base holds four reference documents: requirements quality criteria, the organisation's requirement-writing template and its prohibited-terms list, a sample SRS exemplar, and a catalogue of conflict patterns. They are the team's own summaries of established requirements-engineering guidance, so the repository carries no licensing problem.

The pipeline has five explicit stages: documents are **loaded** from disk, **split** with a recursive character splitter that prefers Markdown heading boundaries so a chunk rarely straddles two rules, **embedded** with a local MiniLM model requiring no API key, **stored** in an in-process vector store, and **retrieved** by semantic similarity.

### RAG Strategy: Hybrid

The system uses **Hybrid RAG**, and both halves are implemented.

The **2-Step half** lives inside the two grounded reviewers: retrieval is unconditional and deterministic, followed by a single structured generation call with the retrieved passages in the prompt. The **Agentic half** is `search_requirements_standards`, a real tool an agent can invoke on demand for a one-off check without running a full review pass.

Pure Agentic RAG was rejected because a reviewer that decides for itself whether to retrieve will sometimes skip it, and then falls back on its own notion of a good requirement — which is exactly the subjective judgement the Standards Reviewer exists to replace. Pure 2-Step was rejected because ad-hoc lookups during synthesis are unpredictable in topic and number, and forcing a fixed retrieval for those would be wasteful. The cost of Hybrid is one guaranteed retrieval per reviewer pass even on a clean document, which against an in-process store is a few milliseconds in exchange for guaranteed grounding.

---

## Context and Memory

**Short-term memory** is a LangGraph checkpointer keyed by `thread_id`. It carries state across a single review session and is what allows a run paused at the approval gate to be resumed with the same thread identifier.

**Long-term memory** is a separate store keyed by `project_id`. Product Owner decisions — what was approved, what was edited and to what wording, what was rejected and why — are written there and read back by later sessions running on entirely different threads. That independence from `thread_id` is what distinguishes it from short-term state: a growing list of conversation messages would disappear the moment the thread changed.

Each run begins by retrieving prior decisions for the project and surfacing them in the approval payload, so the Product Owner sees what the team has already agreed before deciding again.

---

## Human-in-the-Loop

Before any requirement text changes, the workflow pauses at a real `interrupt()` and surfaces every finding, the prior decisions on file, and the allowed responses.

For each finding, the Product Owner can:

- **Approve** — the reviewer's suggested wording is applied
- **Edit** — the Product Owner's own wording is applied instead
- **Reject** — the requirement is left exactly as it was

Execution resumes through `Command(resume=...)` carrying the decisions. Every decision is persisted to long-term memory, then passed to the Editor. No requirement is added or modified without an explicit approval.

Decisions are scripted by default so the system runs unattended and captures output; an interactive console mode is available with `--interactive`.

---

## Error Handling

Two strategies, both wired into the live pipeline rather than declared and left unused.

**Throttling.** Groq's free tier caps tokens per minute, and dispatching four reviewers concurrently produced a real `429 RateLimitError`. A single rate limiter shared by every LLM client spaces calls out so the ceiling is not reached in the first place.

**Retry with exponential backoff.** A `RetryPolicy` is attached to every LLM-backed task at decoration time, retrying up to five attempts with a growing interval. Its predicate is selective: rate limits, timeouts, dropped connections and 5xx responses are retried, while authentication failures and malformed requests are not, because they fail identically on every attempt. Daily-quota errors are also excluded, since they cannot clear inside any retry window.

**Graceful degradation.** A reviewer that still fails after every retry returns a structured "manual review required" finding instead of aborting the run, so one dead reviewer cannot destroy an otherwise complete review.

A fourth guard filters reviewer output: the knowledge base contains a sample SRS with its own requirement identifiers, and a reviewer can occasionally return a well-formed finding about a requirement that exists only in the reference material. Those findings are dropped before they reach the Editor.

---

## Observability

Tracing is enabled through LangSmith, capturing every agent, tool call, retry, and token count.

The trace surfaced three things the printed output did not. Retrieval is effectively free — spans complete in hundredths of a second while a full pipeline run takes fifteen to twenty-five seconds — so the latency is entirely in the LLM calls and the lever for speed is fewer or smaller calls, not a faster vector store. The retry policy is visibly firing: rate-limited traces show durations of one to two minutes, which is the backoff itself rather than a slow request. And the gap between P50 and P99 latency, roughly 1 second against 105 seconds, quantifies how much of the tail is external quota rather than the graph.

The rate limiter was added in direct response to those traces, and the retry predicate was narrowed to fail fast on daily-quota errors after the trace showed nearly two minutes spent retrying a limit that could not clear.

---

## Technologies

- Python
- Google Colab
- LangGraph (Functional API: `@task` / `@entrypoint`)
- LangChain
- Groq (Llama 3.3 70B)
- HuggingFace `sentence-transformers/all-MiniLM-L6-v2` (local embeddings)
- LangChain `InMemoryVectorStore`
- LangGraph `InMemorySaver` (short-term) and `InMemoryStore` (long-term)
- Pydantic (structured output)
- LangSmith (tracing)

---

## Repository Structure

```text
Capstone-Project--Building-Agentic-AI-Systems/
├── Capstone_Main_Workflow.ipynb     # integrated system and executed evidence
├── requirements_copilot/            # the same final code, as an importable package
│   ├── __init__.py                  # public API
│   ├── schemas.py                   # Requirement, ReviewFinding, ApprovedChange
│   ├── reliability.py               # rate limiter, retry policy, fallback, output filter
│   ├── runtime.py                   # shared LLM factory, checkpointer, paths
│   ├── display.py                   # console formatting helpers
│   ├── tools.py                     # Requirements Parser tool + document loader
│   ├── rag.py                       # load → split → embed → store → retrieve
│   ├── reviewers.py                 # the four specialist reviewer agents
│   ├── supervisor.py                # router, synthesizer, report renderer
│   ├── memory.py                    # long-term project memory store and tools
│   ├── hitl.py                      # interrupt, decision translation, persistence
│   ├── editor.py                    # applies approved changes only
│   └── pipelines.py                 # review_pipeline and requirements_copilot
├── data/
│   ├── demo_requirements_flawed.txt      # sample input document
│   ├── demo_project_description.txt      # sample project brief
│   └── knowledge_base/                   # RAG corpus
│       ├── re_quality_criteria.md
│       ├── srs_writing_template.md
│       ├── sample_srs_registration.md
│       └── conflict_patterns.md
├── docs/
│   └── ARCHITECTURE.md              # technical write-up
├── run_demo.py                      # end-to-end command-line demonstration
├── requirements.txt
├── .gitignore
└── README.md
```

The complete implementation is available inside `Capstone_Main_Workflow.ipynb` for reproducible evaluation in Google Colab. The `requirements_copilot` package is the same final code organized for import and reuse.

---

## Prerequisites

- Python 3.11 or later
- A **Groq** API key (LLM: Llama 3.3 70B)
- A **LangSmith** API key (tracing; optional but required for the observability section)

Embeddings run locally and need no API key. Requirements Engineering Copilot does **not** store API keys in the GitHub repository.

---

## Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/joryhh/Capstone-Project--Building-Agentic-AI-Systems.git
cd Capstone-Project--Building-Agentic-AI-Systems
pip install -r requirements.txt
```

Provide the API keys as environment variables (for the package) or in the Colab Secrets panel (for the notebook):

```bash
export GROQ_API_KEY=your_groq_key
export LANGCHAIN_API_KEY=your_langsmith_key
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_PROJECT=capstone-requirements-reviewer
```

---

## How to Run

### Option 1 - Google Colab (recommended for evaluation)

1. Open `Capstone_Main_Workflow.ipynb` in Google Colab.
2. Open the **Secrets** panel, add `GROQ_API_KEY` and `LANGCHAIN_API_KEY`, and enable notebook access to each.
3. From the menu select **Runtime -> Restart session and run all**.

The notebook installs its dependencies, defines the system in sections 1 to 11, and runs every demonstration in section 12. Allow roughly four minutes: LLM calls are deliberately throttled to stay inside the Groq free-tier token limit.

### Option 2 - Command line

```bash
python run_demo.py                 # scripted Product Owner decisions
python run_demo.py --interactive   # answer approve / edit / reject at the console
```

Point it at your own documents with `--requirements` and `--description`.

### Option 3 - As a library

```python
from langgraph.types import Command
from requirements_copilot import (
    parse_requirements, requirements_copilot, scripted_po_decision,
)

parsed = parse_requirements.invoke({"document_text": open("my_requirements.txt").read()})
config = {"configurable": {"thread_id": "session-1"}}

paused = requirements_copilot.invoke(
    {"project_id": "my-project",
     "project_description": open("my_brief.txt").read(),
     "requirements": parsed},
    config,
)

payload = paused["__interrupt__"][0].value
decisions = [scripted_po_decision(f) for f in payload["findings"]]

result = requirements_copilot.invoke(Command(resume={"decisions": decisions}), config)
print(result["report"])
for r in result["updated_requirements"]:
    print(r["id"], r["text"])
```

---

## Expected Output

Requirements Engineering Copilot produces:

- A structured list of parsed requirements with stable identifiers
- A routing decision naming which reviewers ran and why
- A severity-ordered review report, each finding carrying a reason and a concrete rewrite
- An approval payload listing every finding alongside prior decisions for the project
- A record of which findings were approved, edited, or rejected
- The updated requirements document, marking what was added and what was revised
- A per-project decision history readable from any later session

The executed notebook additionally demonstrates: a verified retrieval returning a verbatim answer from the knowledge base, routing that genuinely differs between two inputs, an approval pause followed by a resume, long-term memory recalled from a new thread, a retry policy attached to every LLM task with a fallback degrading safely, and per-stage latency measurements alongside the LangSmith trace.

---

## Capstone Concepts Demonstrated

Requirements Engineering Copilot demonstrates the key concepts covered in **Building Agentic AI Systems**, including:

- Agent fundamentals: real tool calls and Pydantic-typed structured output throughout
- Multi-agent routing: a Supervisor deciding through constrained LLM output, not keyword rules
- A complete RAG pipeline with a justified Hybrid strategy
- Context and state management: a per-thread checkpointer alongside a per-project long-term store, with cross-thread recall
- Human-in-the-loop: a genuine `interrupt()` and a `Command(resume=...)` that completes the run
- The LangGraph Functional API with `@task` and `@entrypoint`
- Error handling: proactive throttling, a selective retry policy, and graceful degradation
- The Orchestrator–Worker workflow pattern, chosen and named explicitly
- LangSmith observability, with findings that changed the implementation
