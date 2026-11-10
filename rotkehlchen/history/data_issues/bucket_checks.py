from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from collections.abc import Collection

    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.types import TimestampMS

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
    observation_id: int | None = None
    """The identity of the observation the comparison used. Two observations of the same asset
    can share an observed_at second, so the saved identity is what detects that one replaced
    the other. None is a check written before identities were stored, where only observed_at
    can decide."""

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
            observation_id=observation_id,
        ) for (
            location, label, asset, derived_balance, observed_balance,
            latest_event_identifier, observed_at, compared_at, observation_id,
        ) in cursor.execute(
            'SELECT location, location_label, asset, derived_balance, observed_balance, '
            'latest_event_identifier, observed_at, compared_at, observation_id '
            'FROM bucket_balance_checks',
        )
    }


def save_balance_check(write_cursor: DBCursor, check: BucketBalanceCheck) -> None:
    """Save the check, replacing the previous one of its bucket."""
    write_cursor.execute(
        'INSERT OR REPLACE INTO bucket_balance_checks(location, location_label, asset, '
        'derived_balance, observed_balance, latest_event_identifier, observed_at, compared_at, '
        'observation_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            *check.key,
            str(check.derived_balance),
            str(check.observed_balance),
            check.latest_event_identifier,
            check.observed_at,
            check.compared_at,
            check.observation_id,
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
    UNSUPPORTED_LOCATION = 'unsupported_location'
    # why there is no usable observation
    ASSET_COVERAGE_MISSING = 'asset_coverage_missing'
    OBSERVATION_MISSING = 'observation_missing'
    OBSERVATION_STALE = 'observation_stale'
    # why the history side is not ready
    HISTORY_NOT_SYNCED = 'history_not_synced'
    HISTORY_PENDING_DECODING = 'history_pending_decoding'
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
    """The latest derived balance of a wallet bucket, None when it has no balance metric.

    latest_ts is the timestamp of the last event the derived balance covers, in milliseconds,
    used to tell whether the observation is older than the history.

    is_history_free marks the synthetic zero of a bucket whose history was proven to have no
    events at all (see eligibility.WalletEvidence). It is not a metric read from the database;
    it only survives read-side classification because the same verification runs again before
    every read.
    """
    balance: FVal
    latest_event_identifier: int | None
    latest_ts: TimestampMS | None = None
    is_history_free: bool = False


def classify_bucket(
        is_blocked: bool,
        unsupported: Collection[BucketReason],
        check: BucketBalanceCheck | None,
        derived: DerivedSnapshot | None,
        is_derived_history_stale: bool,
        latest_observed_at: Timestamp | None,
        now: Timestamp,
        tolerance: FVal,
        latest_observation_id: int | None = None,
        pending_reasons: Collection[BucketReason] = (),
) -> BucketClassification:
    """Classify a bucket that is in scope. Ignored assets and untracked accounts are left out
    before this, and the first rule that matches decides the status:

    1. processing is stopped for the bucket: blocked, whatever any issue says
    2. the comparison is unsupported or disabled for it: not_compared
    3. it has no saved check, or its evidence is not usable: pending
    4. the derived history or the observation is stale, or the check superseded or expired:
       pending
    5. otherwise reconciled or mismatch

    pending_reasons are the facts of the shared eligibility reader (missing coverage, unsynced
    history, pending decoding). They make a bucket pending even when a saved check exists, so
    a bucket that became ineligible can't keep showing an old match.

    A bucket without balance metrics has no derived balance, which is never replaced by zero.
    The one exception is the synthetic zero of a verified history-free bucket, which the
    caller gets from the eligibility reader rather than building itself.

    Every applicable reason is returned, whichever status wins.
    """
    reasons: list[BucketReason] = list(unsupported)
    reasons.extend(pending_reasons)
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
        if (
            (latest_observed_at is not None and latest_observed_at > check.observed_at) or
            (
                latest_observation_id is not None and
                latest_observation_id != check.observation_id
            )
        ):
            # The identity catches a replacement within the same second, which the timestamp
            # alone can't see.
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
