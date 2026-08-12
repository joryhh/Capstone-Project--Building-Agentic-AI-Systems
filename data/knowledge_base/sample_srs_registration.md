# Sample SRS Extract — University Course Registration (reference exemplar)

This extract is provided as a model of correctly written requirements for a course
registration domain. Reviewers may compare submitted requirements against these.

REQ-101 The system shall allow an authenticated student to register for a course section
when the section has at least one available seat and the student has no outstanding
registration hold.
Acceptance: Given a section with 1 seat free and a student with no hold, when the student
submits a registration request, then the seat count decreases by 1 and the student appears
on the section roster.

REQ-102 The system shall prevent registration for a course section whose enrolled count
equals its seat capacity, and shall return an explanatory message naming the full section.

REQ-103 The system shall allow a student to drop a course section up to and including the
published add/drop deadline for the current term.

REQ-104 The system shall reject any drop request submitted after the published add/drop
deadline and shall return an explanatory message stating the deadline date.

REQ-105 The system shall notify a waitlisted student within 5 minutes of a seat becoming
available in the section for which they are waitlisted.

REQ-106 The system shall allow an academic advisor to view the complete registration
history of any student assigned to that advisor.

REQ-107 The system shall allow an academic advisor to override a registration hold, and
shall record the advisor identity, timestamp, and stated reason for every override.

REQ-108 The system shall generate a weekly enrollment report listing current enrolled
count and seat capacity for every course section, and shall make it available to
department administrators each Monday by 06:00 local time.

REQ-109 The system shall complete a registration transaction within 3 seconds under a load
of 500 concurrent registration requests.

REQ-110 The system shall record an audit entry for every registration, drop, and override
action, containing actor identity, action type, target section, and timestamp.
