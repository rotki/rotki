from rotkehlchen.chain.bitcoin.bch.cashaddr import cashaddr_decode
from rotkehlchen.chain.bitcoin.bch.constants import CASHADDR_PREFIX


def is_valid_bitcoin_cash_address(address: str) -> bool:
    """Validates a Bitcoin Cash's CashAddr format
    e.g bitcoincash:qpmmlusvvrjj9ha2xdgv8xcrpfwsqn5rngt3k26ve2
    """
    if address.upper() != address and address.lower() != address:
        return False

    if (colon_count := (address := address.lower()).count(':')) == 0:
        address = CASHADDR_PREFIX + ':' + address
    elif colon_count > 1:
        return False

    try:
        cashaddr_decode(prefix=CASHADDR_PREFIX, address=address)
    except ValueError:
        return False

    return True
