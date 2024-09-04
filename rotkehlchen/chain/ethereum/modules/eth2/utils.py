import logging
from collections.abc import Sequence

from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.chain.ethereum.modules.eth2.constants import DEFAULT_VALIDATOR_CHUNK_SIZE
from rotkehlchen.db.filtering import (
    EthStakingEventFilterQuery,
    EthWithdrawalFilterQuery,
    WithdrawalTypesFilter,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, Timestamp
from rotkehlchen.utils.misc import get_chunks

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

INITIAL_ETH_DEPOSIT = FVal(32)
EPOCH_DURATION_SECS = 384

ETH2_GENESIS_TIMESTAMP = 1606824023


def epoch_to_timestamp(epoch: int) -> Timestamp:
    """Turn a beaconchain epoch to a unix timestamp"""
    return Timestamp(ETH2_GENESIS_TIMESTAMP + epoch * EPOCH_DURATION_SECS)


def form_withdrawal_notes(is_exit: bool, validator_index: int, amount: FVal) -> str:
    """Forms the ethereum withdrawal notes depending on is_exit and other attributes"""
    if is_exit is True:
        notes = f'Exited validator {validator_index} with {amount} ETH'
    else:
        notes = f'Withdrew {amount} ETH from validator {validator_index}'
    return notes


def calculate_query_chunks(
        indices_or_pubkeys: Sequence[int | Eth2PubKey],
        chunk_size: int = DEFAULT_VALIDATOR_CHUNK_SIZE,
) -> list[Sequence[int | Eth2PubKey]]:
    """Create chunks of queries.

    Beaconcha.in allows up to 100 validator or public keys in one query for most calls.
    Also has a URI length limit of ~8190, so seems no more than 80 public keys can be per call.

    Beacon nodes API has as similar limit
    https://ethereum.github.io/beacon-APIs/#/Beacon/getStateValidators
    If you cross it they will return 414 status error.

    They are creating a POST endpoint to get rid of this limit.
    """
    if len(indices_or_pubkeys) == 0:
        return []

    return list(get_chunks(indices_or_pubkeys, n=chunk_size))


def create_profit_filter_queries(
        from_ts: Timestamp,
        to_ts: Timestamp,
        validator_indices: list[int] | None,
        tracked_addresses: Sequence[ChecksumEvmAddress],
) -> tuple[EthWithdrawalFilterQuery, EthWithdrawalFilterQuery, EthStakingEventFilterQuery]:
    """Create the Filter queries for withdrawal events and execution layer reward events"""
    withdrawals_filter_query = EthWithdrawalFilterQuery.make(
        from_ts=from_ts,
        to_ts=to_ts,
        validator_indices=validator_indices,
        event_types=[HistoryEventType.STAKING],
        event_subtypes=[HistoryEventSubType.REMOVE_ASSET],
        entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT]),
        withdrawal_types_filter=WithdrawalTypesFilter.ONLY_PARTIAL,
    )
    exits_filter_query = EthWithdrawalFilterQuery.make(
        from_ts=from_ts,
        to_ts=to_ts,
        validator_indices=validator_indices,
        event_types=[HistoryEventType.STAKING],
        event_subtypes=[HistoryEventSubType.REMOVE_ASSET],
        entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT]),
        withdrawal_types_filter=WithdrawalTypesFilter.ONLY_EXITS,
    )
    execution_filter_query = EthStakingEventFilterQuery.make(
        from_ts=from_ts,
        to_ts=to_ts,
        validator_indices=validator_indices,
        event_types=[HistoryEventType.STAKING],
        event_subtypes=[HistoryEventSubType.BLOCK_PRODUCTION, HistoryEventSubType.MEV_REWARD],
        entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.ETH_BLOCK_EVENT]),
        location_labels=tracked_addresses,  # type: ignore  # addresses are strings
    )
    return withdrawals_filter_query, exits_filter_query, execution_filter_query
