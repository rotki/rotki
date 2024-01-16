import dataclasses

from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now


@dataclasses.dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=False)  # noqa: E501
class PenaltyInfo:
    last_penalized_ts: Timestamp
    query_failures_count: int

    def note_failure_or_penalize(self) -> None:
        """
        This function determines whether an oracle should be punished or not.

        It is called when an oracle fails, if the failure count reaches a threshold,
        it is punished for a duration i.e. skipped. Otherwise, the failure count is incremented.
        """
        if self.query_failures_count >= CachedSettings().oracle_penalty_threshold_count:
            self.last_penalized_ts = ts_now()
            self.query_failures_count = 0
        else:
            self.query_failures_count += 1


class PenalizablePriceOracleMixin:
    """
    This class represents oracle that can be penalized due to failures.
    """
    def __init__(self) -> None:
        self.penalty_info = PenaltyInfo(last_penalized_ts=Timestamp(0), query_failures_count=0)

    def is_penalized(self) -> bool:
        """This function checks if an oracle should be penalized or not."""
        # prevent making an additional query whenever the failure count has reached the threshold.
        penalty_threshold_count = CachedSettings().oracle_penalty_threshold_count
        penalty_duration = CachedSettings().oracle_penalty_duration
        if self.penalty_info.query_failures_count == penalty_threshold_count:
            self.penalty_info.note_failure_or_penalize()
        return ts_now() - self.penalty_info.last_penalized_ts <= penalty_duration
