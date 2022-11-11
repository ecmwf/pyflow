from ecflow import DState

#: Defines a complete state.
complete = DState.complete

#: Defines an unknown state.
unknown = DState.unknown

#: Defines an aborted state.
aborted = DState.aborted

#: Defines a submitted state.
submitted = DState.submitted

#: Defines a suspended state.
suspended = DState.suspended

#: Defines an active state.
active = DState.active

#: Defines a queued state.
queued = DState.queued

MAP = {
    "complete": complete,
    "unknown": unknown,
    "aborted": aborted,
    "submitted": submitted,
    "suspended": suspended,
    "active": active,
    "queued": queued,
}
