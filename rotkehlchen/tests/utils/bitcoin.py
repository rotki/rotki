from typing import TYPE_CHECKING

from rotkehlchen.chain.bitcoin.btc.constants import (
    BLOCKCHAIN_INFO_BASE_URL,
    BLOCKCYPHER_BASE_URL,
    BLOCKCYPHER_TX_IO_LIMIT,
)
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.utils.network import request_get_dict

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.btc.manager import BitcoinManager
    from rotkehlchen.chain.bitcoin.types import BitcoinTx


def get_decoded_events_of_bitcoin_tx(
        bitcoin_manager: 'BitcoinManager',
        tx_id: str,
        use_blockcypher: bool = False,
) -> list[HistoryEvent]:
    """Convenience function to query a bitcoin tx by its id and decode it."""
    bitcoin_manager.refresh_tracked_accounts()
    tx: BitcoinTx | None
    if use_blockcypher:
        tx = bitcoin_manager._process_raw_tx_from_blockcypher(
            data=request_get_dict(f'{BLOCKCYPHER_BASE_URL}/txs/{tx_id}?limit={BLOCKCYPHER_TX_IO_LIMIT}'),
        )
    else:
        tx = bitcoin_manager.deserialize_tx_from_blockchain_info(
            data=request_get_dict(f'{BLOCKCHAIN_INFO_BASE_URL}/rawtx/{tx_id}'),
        )

    assert tx is not None, 'tx result should not be None. Perhaps the tx is unconfirmed?'
    return bitcoin_manager.decode_transaction(tx=tx)
