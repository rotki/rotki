from rotkehlchen.crypto import sha3
from rotkehlchen.exchanges.data_structures import Trade


def formulate_trade_id(trade: Trade) -> str:
    """Formulates a unique identifier for the trade to become the DB primary key"""
    if trade.location == 'external':
        string = trade.location + str(trade.timestamp) + str(trade.trade_type) + trade.pair
    else:
        string = (trade.location + trade.link)

    id_bytes = sha3(string.encode())
    return id_bytes.decode()
