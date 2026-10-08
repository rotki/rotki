from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants import ONE
from rotkehlchen.types import SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.types import ChecksumEvmAddress, Timestamp

HYPERLIQUID_PUBLIC_RPC_NODES: Final = (WeightedNode(
    node_info=NodeName(
        name='hyperliquid',
        endpoint='https://rpc.hyperliquid.xyz/evm',
        owned=False,
        blockchain=SupportedBlockchain.HYPERLIQUID,
    ),
    active=True,
    weight=ONE,
),)


def query_history_events(
        api: HyperliquidAPI,
        address: ChecksumEvmAddress,
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> list[HistoryBaseEntry]:
    """Query Hyperliquid Core history and return all its events sorted by time."""
    return sorted(
        (event for batch in api.iter_history_event_batches(
            address=address,
            start_ts=start_ts,
            end_ts=end_ts,
        ) for event in batch),
        key=lambda event: (event.timestamp, event.group_identifier, event.sequence_index),
    )
