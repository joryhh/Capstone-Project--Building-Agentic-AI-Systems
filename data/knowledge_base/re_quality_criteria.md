# Requirements Quality Criteria (study extract)

A well-written requirement is expected to satisfy several quality characteristics.
These characteristics are drawn from established requirements-engineering guidance
and restated here in our own words for use as a review reference.

## Unambiguous
A requirement is unambiguous when it has exactly one possible interpretation.
Words such as "quickly", "fast", "user-friendly", "efficient", "robust", "flexible",
"as appropriate", "if necessary", "etc." and "and/or" introduce ambiguity because two
readers can reasonably disagree about what satisfies them. Replace these with a stated
value, a stated condition, or a named standard.

## Verifiable (testable)
A requirement is verifiable when a finite, cost-effective process exists to check that
the delivered system meets it. In practice this means the requirement must have an
objective pass/fail criterion. A requirement that cannot be verified by inspection,
analysis, demonstration, or test is not verifiable and should be rewritten.
Non-verifiable phrasing includes "the system shall be easy to use", "the system shall
work well", and "the system shall be secure" with no stated threshold or standard.

## Measurable performance
Performance requirements must state a numeric target, the unit of measurement, and the
conditions under which the target applies. The recommended form is:
"The system shall <action> within <number> <unit> under <stated load or condition>."
For example, a response-time requirement should state both the time limit and the
concurrent-user load at which that limit must hold.

## Complete
A requirement is complete when it states the triggering condition, the actor, the system
response, and the outcome, with no "to be determined" content remaining. A requirements
set is complete when it covers every capability described in the project scope, including
error handling and exception behaviour for each described capability.

## Consistent
A requirements set is consistent when no requirement contradicts another. Conflicts
commonly appear as a general permission paired with a narrower prohibition covering the
same actor and action, as two different values specified for the same quantity, or as two
requirements that impose incompatible ordering on the same operation.

## Singular
A requirement should state exactly one need. A sentence joining two behaviours with "and"
usually should be split into two requirements so that each can be verified separately.

## Feasible and traceable
A requirement must be achievable within known constraints, and must be traceable back to a
stated stakeholder need or scope item and forward to its verification method.
