import dataclasses
import logging
from typing import Final

import requests

from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now

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

    def note_failure_or_penalize(self) -> None:
        """
        This function determines whether an oracle should be punished or not.

        It is called when an oracle fails, if the failure count reaches a threshold,
        it is punished for a duration i.e. skipped. Otherwise, the failure count is incremented.
        """
        if self.query_failures_count >= CachedSettings().oracle_penalty_threshold_count:
            self.penalize()
        else:
            self.query_failures_count += 1

    def note_request_failure(self, error: requests.RequestException) -> None:
        """Record a failed request to the oracle.

        A timeout means the host accepted the connection and then went silent for the whole
        read timeout. Waiting for that to happen threshold-many times would stall every
        price query in the meantime, so the oracle is penalized at once. Any other failure
        counts toward the threshold as before.
        """
        if isinstance(error, requests.exceptions.Timeout):
            self.penalize()
        else:
            self.note_failure_or_penalize()


class PenalizablePriceOracleMixin:
    """
    This class represents oracle that can be penalized due to failures.
    """
    def __init__(self) -> None:
        self.penalty_info = PenaltyInfo(last_penalized_ts=Timestamp(0), query_failures_count=0)

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
        if self.penalty_info.query_failures_count == penalty_threshold_count:
            self.penalty_info.note_failure_or_penalize()
        if ts_now() - self.penalty_info.last_penalized_ts <= penalty_duration:
            return True

        if self.penalty_info.probe_pending:
            if self.probe_availability() is False:
                log.debug(f'{self.__class__.__name__} still does not answer after its penalty expired. Penalizing it again')  # noqa: E501
                self.penalty_info.penalize()
                return True
            self.penalty_info.probe_pending = False

        return False
