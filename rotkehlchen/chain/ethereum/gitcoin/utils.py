from typing import Any, Dict, Tuple

from typing_extensions import Literal

from rotkehlchen.accounting.ledger_actions import GitcoinEventTxType


def process_gitcoin_txid(
        key: Literal['txid', 'tx_hash'],
        entry: Dict[str, Any],
) -> Tuple[GitcoinEventTxType, str]:
    """May raise KeyError"""
    raw_txid = entry[key]
    tx_type = GitcoinEventTxType.ETHEREUM
    tx_id = raw_txid
    if raw_txid.startswith('sync-tx:'):
        tx_type = GitcoinEventTxType.ZKSYNC
        tx_id = raw_txid.split('sync-tx:')[1]  # can't fail due to the if condition

    return tx_type, tx_id
