from rotkehlchen.crypto import sha3
from rotkehlchen.exchanges.data_structures import MarginPosition, Trade
from rotkehlchen.typing import Timestamp, TradeID, TradeType


def hashable_string_for_external_trade(
        timestamp: Timestamp,
        trade_type: TradeType,
        pair: str,
) -> str:
    return 'external' + str(timestamp) + str(trade_type) + pair


def hash_id(hashable: str) -> TradeID:
    id_bytes = sha3(hashable.encode())
    return TradeID(id_bytes.hex())


def formulate_trade_id(trade: Trade) -> TradeID:
    """Formulates a unique identifier for the trade to become the DB primary key"""
    if trade.location == 'external':
        string = hashable_string_for_external_trade(
            trade.timestamp,
            trade.trade_type,
            trade.pair,
        )
    else:
        string = (trade.location + trade.link)

    return TradeID(hash_id(string))


def formulate_margin_id(margin: MarginPosition) -> str:
    open_time = '' if margin.open_time is None else str(margin.open_time)
    string = margin.location + open_time + str(margin.close_time) + margin.pl_currency.identifier
    return hash_id(string)
