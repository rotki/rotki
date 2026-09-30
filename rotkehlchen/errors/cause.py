from enum import StrEnum, auto


class FailureCause(StrEnum):
    """Why an API request or async task failed.

    The status code says how the request failed, not whether retrying can help: a 502 is
    both an unreachable remote and a rejected key, and a 409 covers most validation and
    state failures alike. The cause travels beside the message so the frontend can offer a
    retry for a transient failure and name the fix for a permanent one. Whether a failure is
    worth retrying is read from its cause alone, so no failure carries a separate flag.

    The members shared with the websocket UserMessageKey keep its spelling, so one
    frontend mapping reads both lanes.
    """
    NETWORK = auto()  # a remote could not be reached, or did not answer in time
    AUTH = auto()  # credentials missing, rejected or expired
    BAD_DATA = auto()  # a remote answered with something we could not read
    LOCAL_DB = auto()  # our own stored data is inconsistent or unwritable
    UNSUPPORTED = auto()  # rotki does not support this thing yet
    INTERNAL = auto()  # an invariant broke; the user can only file a report
    INVALID_INPUT = auto()  # the request was malformed or out of range
    NOT_FOUND = auto()  # the thing the request names does not exist
    CONFLICT = auto()  # the current state does not allow the request
    FORBIDDEN = auto()  # the request needs premium, exceeds its limits or is from a foreign origin
    RATE_LIMITED = auto()  # a remote asked us to slow down; retry after a wait
    REMOTE_REJECTED = auto()  # a remote was reached and refused the request
    CANCELLED = auto()  # the user or a logout stopped the task; not a failure to show
