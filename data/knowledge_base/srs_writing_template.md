# Requirement Statement Template and House Style

## Mandatory sentence form
Every functional requirement in this organisation is written as:

  The system shall <observable behaviour> [when <trigger>] [within <measurable limit>].

The auxiliary verb "shall" denotes a binding requirement. "Should" denotes a
recommendation and must not be used for contractual requirements. "Will" denotes a
statement of fact about the environment, not a requirement on the system.

## Identifier convention
Each requirement carries a unique, stable identifier of the form REQ-NNN. Identifiers are
never reused after a requirement is deleted.

## Acceptance criteria
Every requirement is accompanied by at least one acceptance criterion stated in
Given / When / Then form, so that a tester can determine pass or fail without consulting
the author.

## Prohibited vague terms
The following terms are rejected in review unless immediately followed by a numeric
threshold or a named external standard: quickly, fast, slow, user-friendly, intuitive,
easy, simple, seamless, efficient, optimised, robust, reliable, scalable, secure,
appropriate, adequate, sufficient, minimal, maximal, state-of-the-art, modern.

## Performance requirement examples
Acceptable: The system shall return search results within 2 seconds for result sets of up
to 500 records, with 200 concurrent users.
Rejected: The system shall return search results quickly.

## Availability requirements
Availability is expressed as a percentage measured over a stated period, together with the
maximum permitted duration of a single unplanned outage.
Acceptable: The system shall maintain 99.5% availability measured monthly, with no single
unplanned outage exceeding 30 minutes.
Rejected: The system shall be highly available.
