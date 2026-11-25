from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Final, TypeVar

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable, Iterator

    from rotkehlchen.types import HistoryEventQueryType
    from rotkehlchen.user_messages import MessagesAggregator

T = TypeVar('T')

# Called with the seconds beaconcha.in makes the current thread wait out a rate limit. Set only
# while a staking events query runs, so that other beaconcha.in callers report nothing.
BEACONCHAIN_RATE_LIMIT_LISTENER: Final[ContextVar[Callable[[int], None] | None]] = ContextVar(
    'beaconchain_rate_limit_listener',
    default=None,
)


class StakingEventsProgress:
    """Reports a staking events query's progress to the frontend.

    `total` counts what the query goes through: validators for block productions and
    withdrawal addresses for withdrawals.
    """

    def __init__(
            self,
            msg_aggregator: MessagesAggregator,
            query_type: HistoryEventQueryType,
            total: int,
    ) -> None:
        self.msg_aggregator = msg_aggregator
        self.query_type = query_type
        self.total = total
        self.processed = 0

    def _send(self, waiting_seconds: int | None = None) -> None:
        self.msg_aggregator.add_message(
            message_type=WSMessageType.PROGRESS_UPDATES,
            data={
                'subtype': str(ProgressUpdateSubType.STAKING_EVENTS_QUERY),
                'query_type': self.query_type.name.lower(),  # as the query API takes it
                'processed': self.processed,
                'total': self.total,
                'waiting_seconds': waiting_seconds,
            },
        )

    def start(self) -> None:
        self._send()

    def advance(self, count: int = 1) -> None:
        if count == 0:
            return

        self.processed = min(self.processed + count, self.total)
        self._send()

    def tracking(
            self,
            items: Iterable[T],
            weight: Callable[[T], int] = lambda _: 1,
    ) -> Iterator[T]:
        """Yield the items, counting each as processed once the loop moves past it.

        A `continue` in the loop body still counts the item, since it was handled.
        """
        for item in items:
            yield item
            self.advance(weight(item))

    def report_wait(self, seconds: int) -> None:
        self._send(waiting_seconds=seconds)

    @contextmanager
    def reporting_rate_limit_waits(self) -> Generator[None]:
        """Report beaconcha.in rate limit waits of this thread as waits of this query."""
        token = BEACONCHAIN_RATE_LIMIT_LISTENER.set(self.report_wait)
        try:
            yield
        finally:
            BEACONCHAIN_RATE_LIMIT_LISTENER.reset(token)
