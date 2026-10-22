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
    addresses: set[ChecksumEvmAddress] = field(default_factory=set)


_token_query_failures: ContextVar[TokenQueryFailures | None] = ContextVar(
    'token_query_failures',
    default=None,
)


@contextmanager
def track_token_query_failures() -> Iterator[TokenQueryFailures]:
    """Record the token queries that fail to reach the nodes while in the context"""
    reset_token = _token_query_failures.set(failures := TokenQueryFailures())
    try:
        yield failures
    finally:
        _token_query_failures.reset(reset_token)


def record_token_query_failure(address: ChecksumEvmAddress) -> None:
    if (failures := _token_query_failures.get()) is not None:
        failures.addresses.add(address)


def is_token_query_deferring() -> bool:
    """Whether a token query already failed in the transaction being decoded, which is then
    left undecoded anyway, so its other token queries don't need to reach the nodes"""
    return (failures := _token_query_failures.get()) is not None and len(failures.addresses) != 0
