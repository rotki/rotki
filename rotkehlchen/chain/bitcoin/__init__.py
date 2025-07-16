from rotkehlchen.chain.bitcoin.bch.utils import is_valid_bitcoin_cash_address
from rotkehlchen.chain.bitcoin.utils import is_valid_btc_address
from rotkehlchen.types import SupportedBlockchain


def is_valid_bitcoin_address(chain: SupportedBlockchain, value: str) -> bool:
    """Returns False only if it's a bitcoin chain with an invalid address."""
    return (
        not chain.is_bitcoin() or
        (is_valid_btc_address(value) or is_valid_bitcoin_cash_address(value))
    )
