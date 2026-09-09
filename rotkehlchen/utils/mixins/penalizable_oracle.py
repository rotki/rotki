import dataclasses
import logging
from typing import TYPE_CHECKING, Final, Literal

import requests

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Seconds allowed for the availability probe that runs once a penalty expires. It is a single
# cheap request meant to detect that the host still stalls, so it must not wait the full
# user-configured read timeout.
ORACLE_PROBE_TIMEOUT: Final = 5


@dataclasses.dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=False)  # noqa: E501
class PenaltyInfo:
    last_penalized_ts: Timestamp
    query_failures_count: int
    # True from the moment an oracle is penalized until a probe confirms it answers again
    probe_pending: bool = False

    def penalize(self) -> None:
        """Skip the oracle for the penalty duration, starting now"""
        self.last_penalized_ts = ts_now()
        self.query_failures_count = 0
        self.probe_pending = True

    def note_failure_or_penalize(self) -> bool:
        """
        This function determines whether an oracle should be punished or not.

        It is called when an oracle fails, if the failure count reaches a threshold,
        it is punished for a duration i.e. skipped. Otherwise, the failure count is incremented.
        Returns True if the penalty started with this call.
        """
        if self.query_failures_count >= CachedSettings().oracle_penalty_threshold_count:
            self.penalize()
            return True

        self.query_failures_count += 1
        return False


class PenalizablePriceOracleMixin:
    """
    This class represents oracle that can be penalized due to failures.
    """
    name: str  # set by the oracle interface the concrete class also inherits from

    def __init__(self) -> None:
        self.penalty_info = PenaltyInfo(last_penalized_ts=Timestamp(0), query_failures_count=0)
        self.msg_aggregator: MessagesAggregator | None = None

    def set_msg_aggregator(self, msg_aggregator: MessagesAggregator) -> None:
        """Give the oracle a way to tell the user it got penalized"""
        self.msg_aggregator = msg_aggregator

    def _notify_penalized(self, reason: Literal['timeout', 'errors']) -> None:
        """Tell the frontend the oracle is set aside, so a slow price load is explained
        instead of looking like rotki hanging. `timeout` means the host stopped answering,
        `errors` that it failed threshold-many times in a row."""
        penalty_duration = CachedSettings().oracle_penalty_duration
        log.warning('Penalizing price oracle %s for %s seconds due to %s', self.name, penalty_duration, reason)  # noqa: E501
        if self.msg_aggregator is None:
            return

        self.msg_aggregator.add_message(
            message_type=WSMessageType.ORACLE_PENALIZED,
            data={
                'oracle': self.name,
                'reason': reason,
                'penalty_duration': penalty_duration,
            },
        )

    def note_request_failure(self, error: requests.RequestException) -> None:
        """Record a failed request to the oracle.

        A timeout means the host accepted the connection and then went silent for the whole
        read timeout. Waiting for that to happen threshold-many times would stall every
        price query in the meantime, so the oracle is penalized at once. Any other failure
        counts toward the threshold as before.
        """
        if isinstance(error, requests.exceptions.Timeout):
            self.penalty_info.penalize()
            self._notify_penalized(reason='timeout')
        elif self.penalty_info.note_failure_or_penalize():
            self._notify_penalized(reason='errors')

    def probe_availability(self) -> bool:
        """Cheap request checking whether the oracle answers again after a penalty expired.

        Oracles that can be probed override this. The default trusts the expiry.
        """
        return True

    def is_penalized(self) -> bool:
        """This function checks if an oracle should be penalized or not.

        Once the penalty expires the oracle is probed before real queries reach it again.
        If the probe fails the penalty restarts, so a host that is still down costs a
        single short probe per penalty duration instead of a full round of timeouts.
        """
        # prevent making an additional query whenever the failure count has reached the threshold.
        penalty_threshold_count = CachedSettings().oracle_penalty_threshold_count
        penalty_duration = CachedSettings().oracle_penalty_duration
        if (
                self.penalty_info.query_failures_count == penalty_threshold_count and
                self.penalty_info.note_failure_or_penalize()
        ):
            self._notify_penalized(reason='errors')
        if ts_now() - self.penalty_info.last_penalized_ts <= penalty_duration:
            return True

        if self.penalty_info.probe_pending:
            if self.probe_availability() is False:
                log.debug('%s still does not answer after its penalty expired. Penalizing it again', self.name)  # noqa: E501
                self.penalty_info.penalize()
                self._notify_penalized(reason='timeout')
                return True
            self.penalty_info.probe_pending = False

        return False
