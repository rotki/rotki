from rotkehlchen.crypto import sha3
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.typing import Timestamp, TradeType


def hashable_string_for_external_trade(
        timestamp: Timestamp,
        trade_type: TradeType,
        pair: str,
) -> str:
    return 'external' + str(timestamp) + str(trade_type) + pair


def hash_trade_id(hashable: str) -> str:
    id_bytes = sha3(hashable.encode())
    return id_bytes.hex()


def formulate_trade_id(trade: Trade) -> str:
    """Formulates a unique identifier for the trade to become the DB primary key"""
    if trade.location == 'external':
        string = hashable_string_for_external_trade(
            trade.timestamp,
            trade.trade_type,
            trade.pair,
        )
    else:
        string = (trade.location + trade.link)

    return hash_trade_id(string)
