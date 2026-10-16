"""Per transaction record of token queries that failed because the nodes could not be reached.

A failed token query raises TokenQueryFailed, which is a subclass of the non conformant token
errors that many decoders catch, so it can't be used to stop the decoding of a transaction.
Instead the failure is recorded here and the decoder checks it before writing the events.

Outside of decoding no tracker is active and nothing is recorded. Threads spawned while a
transaction is decoded inherit a copy of the context in free-threaded python 3.14
(sys.flags.thread_inherit_context), so they record into the tracker of that transaction.
A fresh tracker is used per transaction, so a thread that outlives it can't affect another.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rotkehlchen.types import ChecksumEvmAddress


@dataclass
class TokenQueryFailures:
    # when forced, the failures do not stop the transaction from being decoded
    forced: bool
    addresses: set[ChecksumEvmAddress] = field(default_factory=set)


_token_query_failures: ContextVar[TokenQueryFailures | None] = ContextVar(
    'token_query_failures',
    default=None,
)


@contextmanager
def track_token_query_failures(forced: bool) -> Iterator[TokenQueryFailures]:
    """Record the token queries that fail to reach the nodes while in the context"""
    reset_token = _token_query_failures.set(failures := TokenQueryFailures(forced=forced))
    try:
        yield failures
    finally:
        _token_query_failures.reset(reset_token)


def record_token_query_failure(address: ChecksumEvmAddress) -> None:
    if (failures := _token_query_failures.get()) is not None:
        failures.addresses.add(address)


def is_token_query_forced() -> bool:
    """Whether the transaction being decoded is decoded even if token queries fail"""
    return (failures := _token_query_failures.get()) is not None and failures.forced
