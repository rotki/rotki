"""The bank connector error taxonomy.

Every connector maps bank responses onto these so that callers (the exchange manager, the
API, the UI) can react uniformly without knowing the bank. They subclass RemoteError so
that all the existing exchange error handling keeps working unchanged.
"""
from dataclasses import dataclass
from typing import Any

from rotkehlchen.banks.manifest import AuthPrimitive  # noqa: TC001  # serialized at runtime
from rotkehlchen.errors.misc import RemoteError


class BankError(RemoteError):
    """Base class of every bank connector error"""


class BankAuthExpired(BankError):
    """The stored credentials or session no longer authenticate. The user has to re-run the
    connector's auth flow (for a static secret: enter a new key)."""


@dataclass(frozen=True)
class BankAuthChallenge:
    """A connector-independent interactive authentication prompt."""
    primitive: AuthPrimitive
    prompt: str
    challenge: str | None = None
    challenge_html: str | None = None
    challenge_data: str | None = None
    challenge_mime_type: str | None = None

    def serialize(self) -> dict[str, Any]:
        return {
            'primitive': self.primitive.serialize(),
            'prompt': self.prompt,
            'challenge': self.challenge,
            'challenge_html': self.challenge_html,
            'challenge_data': self.challenge_data,
            'challenge_mime_type': self.challenge_mime_type,
        }


class BankMFARequired(BankError):
    """The bank demands a second factor before it serves data. The connector's auth flow
    says which primitive (otp input, app approval, challenge) satisfies it."""

    def __init__(self, challenge: BankAuthChallenge) -> None:
        super().__init__(challenge.prompt)
        self.challenge = challenge


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
