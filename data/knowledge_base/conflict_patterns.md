# Common Requirement Conflict Patterns (review reference)

A conflict exists when two requirements cannot both be satisfied by any single
implementation. Reviewers should test each candidate pair against these patterns.

## Pattern 1 — Permission versus prohibition
One requirement grants an actor an unrestricted ability while another forbids the same
actor the same ability under a condition that can occur. Signal words: "at any time",
"always", "never", "under no circumstances".
Example: "Users may edit their profile at any time" conflicts with "Users cannot edit
their profile after account verification", because a verified user falls under both.

## Pattern 2 — Contradictory quantitative limits
Two requirements state different values for the same measurable property under the same
conditions, such as two different response-time ceilings or two different retention
periods for the same record type.

## Pattern 3 — Incompatible ordering
Two requirements each demand that a different step occur first in the same workflow, for
example requiring payment before confirmation while also requiring confirmation before
payment.

## Pattern 4 — Mutually exclusive states
Two requirements demand that the same entity be in two states that cannot hold at once,
such as requiring that a record be permanently immutable while also requiring that it be
editable by an administrator.

## Pattern 5 — Deadline versus exception without precedence
A general deadline rule and a narrower exception rule both apply to the same action, and
neither states which takes precedence. This is a genuine conflict until an explicit
precedence rule is added.

## What is NOT a conflict
Two requirements that address different actors, different entities, or mutually exclusive
preconditions are not in conflict. A general rule followed by an exception that explicitly
names its precedence is not a conflict. Requirements at different levels of detail, where
one refines the other, are not in conflict.
