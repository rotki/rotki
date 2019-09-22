from rotkehlchen.crypto import sha3
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.typing import Location, Timestamp, TradeID, TradeType


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
    if trade.location == Location.EXTERNAL:
        string = hashable_string_for_external_trade(
            trade.timestamp,
            trade.trade_type,
            trade.pair,
        )
    else:
        string = str(trade.location) + trade.link

    return TradeID(hash_id(string))


def formulate_margin_id(action: MarginPosition) -> str:
    string = str(action.location) + action.link
    return hash_id(string)


def formulate_asset_movement_id(action: AssetMovement) -> str:
    string = str(action.location) + str(action.category) + action.link
    return hash_id(string)
