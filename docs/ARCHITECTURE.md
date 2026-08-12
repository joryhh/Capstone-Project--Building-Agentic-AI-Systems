# Architecture

Technical write-up for the Requirements Engineering Copilot. One section per capstone
requirement, written from the executed notebook rather than from the plan.

---

## 1. Agent fundamentals

Every agent that returns data consumed by code returns a Pydantic model through
`with_structured_output`, never free text parsed afterwards. Seven structured-output
bindings exist: the parser, the four reviewers, the router, and the Product Owner decision
schema.

Three real tools are defined with `@tool`:

- **`parse_requirements`** reads `document_text` and extracts requirement statements from
  it, assigning stable `REQ-nnn` identifiers. It uses its argument; it is not a function
  returning a fixed string.
- **`search_requirements_standards`** queries the vector store and returns matching
  passages with their source filenames.
- **`save_project_memory` / `retrieve_project_memory`** write and read Product Owner
  decisions in the long-term store.

Reviewers return `list[ReviewFinding]`, a frozen schema shared across the whole system, so
the synthesizer can merge output from four different agents without special-casing any of
them.

---

## 2. Multi-agent routing architecture

**Track A — Supervisor + Workers.**

`supervisor_route` makes an LLM call bound to a typed `RouterDecision`: four booleans and a
one-sentence justification. The model sees the project description, the requirement count,
and the requirement text, and decides which reviewers the input warrants. There is no
keyword matching anywhere in the routing path.

A deterministic guardrail runs *after* the LLM decision and only removes options that are
structurally impossible rather than unwise: completeness review requires a description to
compare against, and conflict review requires at least two requirements to compare. It can
disable a reviewer the model selected; it can never enable one the model rejected.

Selectivity is demonstrated directly in the notebook by running two inputs through the same
pipeline and printing both decisions side by side. A full document runs all four reviewers;
a single requirement with no description runs two.

---

## 3. RAG pipeline

Four reference documents are loaded from `data/knowledge_base/`, split with a recursive
character splitter (chunk size 800, overlap 120) that prefers Markdown heading boundaries,
embedded with `sentence-transformers/all-MiniLM-L6-v2` running locally, stored in an
in-process `InMemoryVectorStore`, and retrieved by similarity search.

Chroma was deliberately removed: it pulled an OpenTelemetry dependency chain that conflicted
with the runtime, and at this corpus size an in-process store is sufficient.

**Retrieval is verified, not assumed.** The notebook asks a question whose answer appears
verbatim in the corpus — the maximum permitted duration of a single unplanned outage — and
asserts that the retrieved passages contain it. A retriever that silently returns nothing is
the most common failure in a RAG pipeline that otherwise looks correct, and this assertion
is what rules it out.

**Strategy: Hybrid.** Mandatory 2-Step retrieval inside the two grounded reviewers, plus an
agentic tool for on-demand lookups. The reasoning for rejecting pure Agentic and pure 2-Step
is given in the README under *RAG Strategy*.

---

## 4. Context and state management

**Short-term:** a LangGraph `InMemorySaver` checkpointer keyed by `thread_id`, shared by
both entrypoints. It carries state within a review session and is what makes a run paused at
the approval gate resumable.

**Long-term:** a separate `InMemoryStore` under the namespace `(project_id, "po_decisions")`.
Every Product Owner decision is written there with the requirement id, the decision, the
final text, notes, and a UTC timestamp.

**Cross-thread test.** The notebook writes decisions during a session on
`demo-copilot-session-1`, then reads them back from a brand-new thread,
`demo-copilot-session-2`, asserting both that the recalled set is non-empty and that its
requirement ids match the findings from the first session. Because the key is the project
and not the thread, the data survives; a growing message list would not.

---

## 5. Human-in-the-loop

`requirements_approval_hitl` calls `interrupt()` with a payload containing every finding,
its index, the allowed decisions, and the prior decisions on file for that project. The
interrupt sits immediately before the Editor, so nothing has been written when the run
pauses.

The run is completed with `Command(resume={"decisions": [...]})`. Both halves are executed
in the notebook with output captured: the pause prints the payload, and the resume prints
the resulting approved changes.

All three decision paths are exercised. Approve applies the reviewer's wording; edit applies
the Product Owner's own; reject leaves the requirement untouched. A completeness finding is
translated into an `add` rather than a `replace`, whether approved or edited, because a
`GAP-nnn` identifier refers to a requirement that does not yet exist.

---

## 6. LangGraph Functional API and error handling

The system is built with `@task` and `@entrypoint`. There is no `StateGraph` anywhere.

Two error-handling strategies are implemented and wired in, not merely declared:

**Retry.** A `RetryPolicy` object — five attempts, three-second initial interval, factor of
two, forty-five-second cap, jitter — is attached to all five LLM-backed tasks at decoration
time. The notebook asserts the attachment rather than claiming it. The predicate retries
rate limits, timeouts, connection failures and 5xx responses, and refuses authentication
errors, malformed requests, and daily-quota errors, none of which can succeed on a retry.

**Graceful degradation.** `with_fallback` wraps a reviewer so a permanent failure returns a
structured `REVIEWER-ERROR` finding instead of propagating. It is demonstrated with a
deliberately broken reviewer inside a real entrypoint.

**Throttling** is a third measure, added after a 429 in a live run: one `InMemoryRateLimiter`
shared by every Groq client, spacing requests so the token-per-minute ceiling is not reached.

---

## 7. Workflow pattern

**Orchestrator–Worker.** The Supervisor orchestrates; the four reviewers are workers.
Reviewer futures are collected before any `.result()` call, so the selected reviewers run
concurrently rather than in sequence.

The alternatives were considered and rejected. Prompt Chaining does not fit because no
reviewer consumes another's output. Plain Parallelization does not fit because the set of
workers is decided per input rather than fixed. Evaluator–Optimizer does not fit because
there is no iterative refinement loop; the human decides once and the Editor applies.

---

## 8. Observability

Tracing runs through LangSmith with `LANGCHAIN_TRACING_V2`, under the project
`capstone-requirements-reviewer`.

Three observations from the trace, each of which changed the implementation or the mental
model:

1. **Retrieval is not the bottleneck.** Retrieval spans complete in hundredths of a second
   against fifteen-to-twenty-five-second pipeline runs. The intuition that the RAG-grounded
   reviewers were slow *because of retrieval* was wrong; the cost is entirely in the LLM
   calls.
2. **The retry policy is visibly firing.** Rate-limited traces show one-to-two-minute
   durations. A failed API call takes under a second, so those durations are the backoff
   itself — the retry mechanism working, observed rather than assumed.
3. **P50 versus P99 quantifies the tail.** Roughly one second against one hundred and five.
   Two orders of magnitude apart is the clearest available signal that the bottleneck is
   external quota rather than the graph.

The rate limiter was added in response to observation 2, and the retry predicate was narrowed
to fail fast on daily-quota errors after the trace showed time spent retrying a limit that
could not clear within any backoff window.
