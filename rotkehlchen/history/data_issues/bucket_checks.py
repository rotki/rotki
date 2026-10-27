from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from collections.abc import Collection

    from rotkehlchen.db.drivers.sqlite import DBCursor

BALANCE_CHECK_MAX_AGE: Final = 2 * DAY_IN_SECONDS
"""How old, in seconds, the observation or the comparison of a saved check can get before the
check stops counting as current. It is twice the daily cadence of the full comparison, so a
single missed run is tolerated and two are not."""

type CheckKey = tuple[str, str, str]
"""Location, address and asset of the wallet bucket a check belongs to."""


@dataclass(frozen=True)
class BucketBalanceCheck:
    """The last comparison of a wallet bucket's derived balance with its observed balance.

    observed_at and compared_at are different clocks and must not be confused:
    - observed_at is when the observed balance was queried from the chain, in seconds. It is
      the age of the source data. It is taken from the observation used by the comparison and
      is never replaced by the time the comparison ran.
    - compared_at is when the comparison was executed and saved, in seconds. It is the age of
      the verdict.

    Comparing now against a balance cache that was filled yesterday gives a compared_at of now
    and an observed_at of yesterday. Making that observation look fresh is exactly the mistake
    two timestamps avoid, so a check is current only while both are within BALANCE_CHECK_MAX_AGE
    and no newer observation than observed_at exists. A run that skips a bucket, fails or
    runs out of time writes nothing, so neither timestamp ever advances without a comparison.

    Whether the two balances match is not stored. It is derived from them and the tolerance when
    the check is read.
    """
    location: str
    location_label: str
    asset: str
    derived_balance: FVal
    observed_balance: FVal
    latest_event_identifier: int | None
    observed_at: Timestamp
    compared_at: Timestamp

    @property
    def key(self) -> CheckKey:
        return self.location, self.location_label, self.asset


def get_balance_checks(cursor: DBCursor) -> dict[CheckKey, BucketBalanceCheck]:
    """All the saved checks."""
    return {
        (location, label, asset): BucketBalanceCheck(
            location=location,
            location_label=label,
            asset=asset,
            derived_balance=FVal(derived_balance),
            observed_balance=FVal(observed_balance),
            latest_event_identifier=latest_event_identifier,
            observed_at=Timestamp(observed_at),
            compared_at=Timestamp(compared_at),
        ) for (
            location, label, asset, derived_balance, observed_balance,
            latest_event_identifier, observed_at, compared_at,
        ) in cursor.execute(
            'SELECT location, location_label, asset, derived_balance, observed_balance, '
            'latest_event_identifier, observed_at, compared_at FROM bucket_balance_checks',
        )
    }


def save_balance_check(write_cursor: DBCursor, check: BucketBalanceCheck) -> None:
    """Save the check, replacing the previous one of its bucket."""
    write_cursor.execute(
        'INSERT OR REPLACE INTO bucket_balance_checks(location, location_label, asset, '
        'derived_balance, observed_balance, latest_event_identifier, observed_at, compared_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (
            *check.key,
            str(check.derived_balance),
            str(check.observed_balance),
            check.latest_event_identifier,
            check.observed_at,
            check.compared_at,
        ),
    )


def balances_match(derived: FVal, observed: FVal, tolerance: FVal) -> bool:
    """Whether the balances differ by at most the tolerance, a fraction of the larger one."""
    return abs(observed - derived) <= tolerance * max(abs(observed), abs(derived))


class BucketStatus(StrEnum):
    BLOCKED = 'blocked'
    NOT_COMPARED = 'not_compared'
    PENDING = 'pending'
    RECONCILED = 'reconciled'
    MISMATCH = 'mismatch'


class BucketReason(StrEnum):
    # why a comparison is not supported
    EXCHANGE = 'exchange'
    NON_EVM_CHAIN = 'non_evm_chain'
    PROTOCOL_BUCKET = 'protocol_bucket'
    QUERIES_DISABLED = 'queries_disabled'
    REBASING = 'rebasing'
    # why a saved comparison is not current
    DERIVED_HISTORY_STALE = 'derived_history_stale'
    DERIVED_SNAPSHOT_CHANGED = 'derived_snapshot_changed'
    NEVER_COMPARED = 'never_compared'
    OBSERVATION_SUPERSEDED = 'observation_superseded'
    RESULT_EXPIRED = 'result_expired'


@dataclass(frozen=True)
class BucketClassification:
    """The status of a bucket and every reason that applies, also those a higher priority
    status hides, such as the stale history of a blocked bucket."""
    status: BucketStatus
    reasons: tuple[BucketReason, ...]


@dataclass(frozen=True)
class DerivedSnapshot:
    """The latest derived balance of a wallet bucket, None when it has no balance metric."""
    balance: FVal
    latest_event_identifier: int | None


def classify_bucket(
        is_blocked: bool,
        unsupported: Collection[BucketReason],
        check: BucketBalanceCheck | None,
        derived: DerivedSnapshot | None,
        is_derived_history_stale: bool,
        latest_observed_at: Timestamp | None,
        now: Timestamp,
        tolerance: FVal,
) -> BucketClassification:
    """Classify a bucket that is in scope. Ignored assets and untracked accounts are left out
    before this, and the first rule that matches decides the status:

    1. processing is stopped for the bucket: blocked, whatever any issue says
    2. the comparison is unsupported or disabled for it: not_compared
    3. it has no saved check: pending
    4. the derived history or the observation is stale, or the check superseded or expired:
       pending
    5. otherwise reconciled or mismatch

    A bucket without balance metrics has no derived balance, which is never replaced by zero.
    Every applicable reason is returned, whichever status wins.
    """
    reasons: list[BucketReason] = list(unsupported)
    if is_derived_history_stale:  # a property of the bucket, whether or not it was ever compared
        reasons.append(BucketReason.DERIVED_HISTORY_STALE)
    if check is None:
        reasons.append(BucketReason.NEVER_COMPARED)
    else:
        if derived is None or (
            derived.balance != check.derived_balance or
            derived.latest_event_identifier != check.latest_event_identifier
        ):
            reasons.append(BucketReason.DERIVED_SNAPSHOT_CHANGED)
        if latest_observed_at is not None and latest_observed_at > check.observed_at:
            reasons.append(BucketReason.OBSERVATION_SUPERSEDED)
        if (
            now - check.observed_at > BALANCE_CHECK_MAX_AGE or
            now - check.compared_at > BALANCE_CHECK_MAX_AGE
        ):
            reasons.append(BucketReason.RESULT_EXPIRED)

    if is_blocked:
        return BucketClassification(status=BucketStatus.BLOCKED, reasons=tuple(reasons))
    if len(unsupported) != 0:
        return BucketClassification(status=BucketStatus.NOT_COMPARED, reasons=tuple(reasons))
    if check is None or len(reasons) != 0:
        return BucketClassification(status=BucketStatus.PENDING, reasons=tuple(reasons))

    return BucketClassification(
        status=(
            BucketStatus.RECONCILED
            if balances_match(check.derived_balance, check.observed_balance, tolerance)
            else BucketStatus.MISMATCH
        ),
        reasons=(),
    )
