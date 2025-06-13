from rotkehlchen.chain.bitcoin.manager import BitcoinManager
from rotkehlchen.chain.bitcoin.types import BitcoinTx
from rotkehlchen.chain.bitcoin.utils import query_blockstream_or_mempool_api
from rotkehlchen.history.events.structures.base import HistoryEvent


def get_decoded_events_of_bitcoin_tx(
        bitcoin_manager: 'BitcoinManager',
        tx_id: str,
) -> list[HistoryEvent]:
    """Convenience function to query a bitcoin tx by its id and decode it."""
    bitcoin_manager.refresh_tracked_accounts()
    return bitcoin_manager.decode_transaction(
        tx=BitcoinTx.deserialize(query_blockstream_or_mempool_api(url_suffix=f'tx/{tx_id}')),
    )
