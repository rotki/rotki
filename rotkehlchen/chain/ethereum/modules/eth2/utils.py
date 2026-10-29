import json
import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.chain.ethereum.modules.eth2.constants import (
    DEFAULT_BEACONCHAIN_API_VALIDATOR_CHUNK_SIZE,
    UNRECORDED_MEV_RETRY_WINDOW,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.filtering import EthStakingEventFilterQuery, HistoryEventFilterQuery
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, Timestamp
from rotkehlchen.utils.misc import get_chunks

if TYPE_CHECKING:
    from collections.abc import Sequence


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

EPOCH_DURATION_SECS: Final = 384
SECONDS_PER_SLOT: Final = 12

ETH2_GENESIS_TIMESTAMP: Final = 1606824023
ETH2_MERGE_TIMESTAMP: Final = 1663224162


NestRange = tuple[ChecksumEvmAddress, int, int, Timestamp]


def nest_ranges(raw: str | None) -> list[NestRange]:
    """The produced-block ranges a nuthatch nest served and rotki has yet to ask about once more
    after the nest stopped asking the relays for their records: (withdrawal address, first block,
    last block, when it served them), from their JSON."""
    return [
        (string_to_evm_address(address), from_block, to_block, Timestamp(served_at))
        for address, from_block, to_block, served_at in json.loads(raw or '[]')
    ]


def nest_range_settled(served_at: Timestamp, asked_at: Timestamp) -> bool:
    """Whether an answer at `asked_at` for a range the nest served at `served_at` is the last
    there is to ask for: the nest asks the relays for UNRECORDED_MEV_RETRY_WINDOW after serving
    it, given a day's margin."""
    return asked_at >= served_at + UNRECORDED_MEV_RETRY_WINDOW + DAY_IN_SECONDS


def merge_nest_ranges(ranges: list[NestRange]) -> list[NestRange]:
    """Join an address's overlapping or adjacent ranges, each joined one kept as long as its most
    recently served part needs."""
    merged: list[NestRange] = []
    for address, from_block, to_block, served_at in sorted(ranges):
        if len(merged) != 0 and (last := merged[-1])[0] == address and from_block <= last[2] + 1:
            merged[-1] = (address, last[1], max(last[2], to_block), max(last[3], served_at))
        else:
            merged.append((address, from_block, to_block, served_at))
    return merged


def timestamp_to_slot(timestamp: Timestamp) -> int:
    """Turn a post-merge unix timestamp to a beacon chain slot."""
    if timestamp < ETH2_MERGE_TIMESTAMP:
        raise ValueError(
            f'Can not query a beacon block proposer for pre-merge timestamp {timestamp}',
        )

    return (timestamp - ETH2_GENESIS_TIMESTAMP) // SECONDS_PER_SLOT


def epoch_to_timestamp(epoch: int) -> Timestamp:
    """Turn a beaconchain epoch to a unix timestamp"""
    return Timestamp(ETH2_GENESIS_TIMESTAMP + epoch * EPOCH_DURATION_SECS)


def calculate_query_chunks(
        indices_or_pubkeys: Sequence[int | Eth2PubKey],
        chunk_size: int = DEFAULT_BEACONCHAIN_API_VALIDATOR_CHUNK_SIZE,
) -> list[Sequence[int | Eth2PubKey]]:
    """Split validator queries into chunks to respect API limits.

    For POST endpoints: up to 100 validators per request
    For GET endpoints: up to 80 validators per request (due to URL length limit of ~8190)
    """
    if len(indices_or_pubkeys) == 0:
        return []

    return list(get_chunks(indices_or_pubkeys, n=chunk_size))


def create_profit_filter_queries(
        from_ts: Timestamp,
        to_ts: Timestamp,
        validator_indices: list[int] | None,
        tracked_addresses: Sequence[ChecksumEvmAddress],
) -> tuple[EthStakingEventFilterQuery, HistoryEventFilterQuery]:
    """Create the Filter queries for execution layer reward events"""
    blocks_execution_filter_query = EthStakingEventFilterQuery.make(
        from_ts=from_ts,
        to_ts=to_ts,
        validator_indices=validator_indices,
        event_types=[HistoryEventType.STAKING],
        event_subtypes=[HistoryEventSubType.BLOCK_PRODUCTION],
        entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.ETH_BLOCK_EVENT]),
        location_labels=tracked_addresses,  # type: ignore  # addresses are strings
    )
    # Unfortunately here at the moment we can't filter by validator index. But since it's
    # in the extra data we do it where this filter is used
    mev_execution_filter_query = HistoryEventFilterQuery.make(
        from_ts=from_ts,
        to_ts=to_ts,
        event_types=[HistoryEventType.STAKING],
        event_subtypes=[HistoryEventSubType.MEV_REWARD],
        location_labels=tracked_addresses,  # type: ignore  # addresses are strings
    )
    return blocks_execution_filter_query, mev_execution_filter_query
