from typing import TYPE_CHECKING

from rotkehlchen.chain.bitcoin.constants import BLOCKSTREAM_BASE_URL
from rotkehlchen.chain.bitcoin.types import BitcoinTx
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.utils.network import request_get_dict

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.manager import BitcoinManager


def get_decoded_events_of_bitcoin_tx(
        bitcoin_manager: 'BitcoinManager',
        tx_id: str,
) -> list[HistoryEvent]:
    """Convenience function to query a bitcoin tx by its id and decode it."""
    bitcoin_manager.refresh_tracked_accounts()
    return bitcoin_manager.decode_transaction(
        tx=BitcoinTx.deserialize(request_get_dict(f'{BLOCKSTREAM_BASE_URL}/tx/{tx_id}')),
    )
