"""DB-only accrued-interest projection for index-accruing wallet buckets.

Index-accruing tokens (such as Aave v3 and Spark Lend aTokens and variable debt tokens) grow in
nominal ``balanceOf(user)`` every block while only emitting events when the user interacts with
the protocol. Reconciliation keeps ``history_events`` and ``event_metrics`` untouched in nominal
units and projects only the remaining unrecorded interest between the latest accounted-for event's
reserve index (``I_last``, read from local ``evmtx_receipt_logs``) and the same-block reserve index
captured alongside ``balanceOf`` (``I_obs``, stored on ``wallet_balance_observations``).

Nothing in this module performs network or RPC calls.
"""
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from eth_utils import to_canonical_address

from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V3, MINT
from rotkehlchen.chain.evm.decoding.aave.v3.constants import BURN
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.resolver import identifier_to_evm_address, identifier_to_evm_chain
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.bucket_checks import (
    BucketReason,
    DerivedSnapshot,
    balances_match,
)
from rotkehlchen.locations.chains import location_to_chain
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

AAVE_V3_LIKE_PROTOCOLS: Final = frozenset((CPT_AAVE_V3, CPT_SPARK))
_MIN_SCALED_TOKEN_LOG_DATA_BYTES: Final = 96  # value (32) + balanceIncrease (32) + index (32)


@dataclass(frozen=True)
class AccruedInterestResolution:
    """Outcome of projecting unrecorded accrued interest for an index-accruing bucket."""
    accrued_interest: FVal | None
    pending_reason: BucketReason | None = None


def _resolve_last_index(
        cursor: DBCursor,
        location: str,
        user_address: str,
        asset: str,
        protocol: str | None,
        latest_event_identifier: int | None,
) -> int | None:
    """Read ``I_last`` for ``latest_event_identifier`` from local Aave v3 / Spark receipt logs.

    Both ``AToken`` and ``VariableDebtToken`` inherit ``IScaledBalanceToken`` /
    ``ScaledBalanceTokenBase`` and emit:
    - ``Mint(address indexed caller, address indexed onBehalfOf, uint256 value, uint256 balanceIncrease, uint256 index)``
      with user in ``topics[2]`` and ray index (1e27) in ``data[64:96]``.
    - ``Burn(address indexed from, address indexed target, uint256 value, uint256 balanceIncrease, uint256 index)``
      with user in ``topics[1]`` and ray index (1e27) in ``data[64:96]``.

    Plain ERC-20 aToken ``BalanceTransfer`` logs are intentionally not matched because pre-transfer
    accrued interest is not yet booked by the decoder; those buckets remain pending with
    ``interest_anchor_unavailable`` instead of silently hiding unbooked interest.
    """  # noqa: E501
    if protocol not in AAVE_V3_LIKE_PROTOCOLS or latest_event_identifier is None:
        return None

    token_address = identifier_to_evm_address(asset)
    token_chain = identifier_to_evm_chain(asset)
    bucket_chain = location_to_chain(location).to_chain_id()
    if token_address is None or token_chain != bucket_chain:
        return None

    try:
        user_topic = b'\x00' * 12 + to_canonical_address(user_address)
    except ValueError:
        log.debug('Cannot build Aave/Spark topic for non-EVM address %s', user_address)
        return None

    row = cursor.execute(
        'SELECT L.data '
        'FROM chain_events_info AS C '
        'INNER JOIN evm_transactions AS E '
        '    ON E.tx_hash = C.tx_ref AND E.chain_id = ? '
        'INNER JOIN evmtx_receipt_logs AS L '
        '    ON L.tx_id = E.identifier AND L.address = ? '
        'INNER JOIN evmtx_receipt_log_topics AS T0 '
        '    ON T0.log = L.identifier AND T0.topic_index = 0 AND T0.topic IN (?, ?) '
        'INNER JOIN evmtx_receipt_log_topics AS TU '
        '    ON TU.log = L.identifier '
        '    AND TU.topic_index = CASE WHEN T0.topic = ? THEN 2 ELSE 1 END '
        '    AND TU.topic = ? '
        'WHERE C.identifier = ? '
        'ORDER BY L.log_index DESC '
        'LIMIT 1',
        (
            bucket_chain.serialize_for_db(),
            token_address,
            MINT,
            BURN,
            MINT,
            user_topic,
            latest_event_identifier,
        ),
    ).fetchone()
    if row is None:
        return None

    data = row[0]
    if (
        not isinstance(data, (bytes, bytearray)) or
        len(data) < _MIN_SCALED_TOKEN_LOG_DATA_BYTES
    ):
        log.warning(
            'Malformed Aave/Spark Mint/Burn log data for event %s on token %s (length=%s)',
            latest_event_identifier,
            token_address,
            len(data) if isinstance(data, (bytes, bytearray)) else type(data).__name__,
        )
        return None

    if (index := int.from_bytes(data[64:96])) <= 0:
        log.warning(
            'Non-positive Aave/Spark reserve index %s for event %s on token %s',
            index,
            latest_event_identifier,
            token_address,
        )
        return None

    return index


def _compute_accrued_interest(
        derived_balance: FVal,
        last_index: int,
        observation_index: int,
) -> FVal:
    """Compute ``B_derived * (I_obs - I_last) / I_last`` using exact integer difference.

    Mathematically identical to ``B_derived * (I_obs / I_last) - B_derived`` while avoiding
    cancellation when ``I_obs`` and ``I_last`` are close 28-digit rays.
    """
    if observation_index == last_index or derived_balance == ZERO:
        return ZERO

    return derived_balance * FVal(observation_index - last_index) / FVal(last_index)


def resolve_accrued_interest(
        cursor: DBCursor,
        location: str,
        user_address: str,
        asset: str,
        protocol: str | None,
        derived: DerivedSnapshot,
        observed_amount: FVal | None,
        observation_index: int | None,
        tolerance: FVal,
) -> AccruedInterestResolution:
    """Resolve unrecorded accrued interest for an index-accruing wallet bucket.

    Invariants:
    - Zero-balance shortcut: when ``derived.balance == 0``, accrued interest is ``0`` without
      requiring ``observation_index`` or ``I_last``.
    - Zeroed on-chain shortcut: when ``derived.balance > 0``, ``observed_amount == 0``, and
      either ``observation_index`` or ``I_last`` (or the protocol / tx anchor) is
      unavailable, if ``derived`` does not match ``0`` within ``tolerance``, return no pending
      reason and ``accrued_interest=None`` so the bucket reports ``MISMATCH`` immediately (since
      ``I_obs >= I_last > 0`` implies ``B_expected >= derived > 0`` and a zeroed token is dropped
      from subsequent token queries).
    - Independent of ``observed_amount``: positive accrued interest is computed strictly from
      ``(derived.balance, I_last, I_obs)``.
    """
    if derived.balance == ZERO:
        return AccruedInterestResolution(accrued_interest=ZERO)

    if observed_amount is None:
        return AccruedInterestResolution(accrued_interest=None)

    is_zeroed_onchain_mismatch = (
        derived.balance > ZERO and
        observed_amount == ZERO and
        not balances_match(derived.balance, ZERO, tolerance)
    )

    def _unavailable(reason: BucketReason) -> AccruedInterestResolution:
        return AccruedInterestResolution(
            accrued_interest=None,
            pending_reason=None if is_zeroed_onchain_mismatch else reason,
        )

    if observation_index is None or observation_index <= 0:
        return _unavailable(BucketReason.INTEREST_INDEX_MISSING)

    last_index = _resolve_last_index(
        cursor=cursor,
        location=location,
        user_address=user_address,
        asset=asset,
        protocol=protocol,
        latest_event_identifier=derived.latest_event_identifier,
    )
    if last_index is None:
        return _unavailable(BucketReason.INTEREST_ANCHOR_UNAVAILABLE)

    if observation_index < last_index:
        return AccruedInterestResolution(
            accrued_interest=None,
            pending_reason=BucketReason.OBSERVATION_STALE,
        )

    return AccruedInterestResolution(
        accrued_interest=_compute_accrued_interest(
            derived_balance=derived.balance,
            last_index=last_index,
            observation_index=observation_index,
        ),
    )
