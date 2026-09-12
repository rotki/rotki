"""The bank connector error taxonomy.

Every connector maps bank responses onto these so that callers (the exchange manager, the
API, the UI) can react uniformly without knowing the bank. They subclass RemoteError so
that all the existing exchange error handling keeps working unchanged.
"""
from typing import Any

from rotkehlchen.errors.misc import RemoteError


class BankError(RemoteError):
    """Base class of every bank connector error"""


class BankAuthExpired(BankError):
    """The stored credentials or session no longer authenticate. The user has to re-run the
    connector's auth flow (for a static secret: enter a new key)."""


class BankMFARequired(BankError):
    """The bank demands a second factor before it serves data. The connector's auth flow
    says which primitive (otp input, app approval, challenge) satisfies it."""


class BankRateLimited(BankError):
    """The bank throttled us. `retry_after` is the number of seconds the bank asked us to
    wait, when it said so."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class BankSchemaDrift(BankError):
    """The bank changed something in its API: a missing key, a value of an unexpected type
    or an unknown enum value. `context` carries what is needed to debug from a user report
    and never carries account data: endpoint, HTTP status, key names, enum values."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context if context is not None else {}

    def __str__(self) -> str:
        if len(self.context) == 0:
            return super().__str__()
        details = ', '.join(f'{key}={value!r}' for key, value in sorted(self.context.items()))
        return f'{super().__str__()} ({details})'
