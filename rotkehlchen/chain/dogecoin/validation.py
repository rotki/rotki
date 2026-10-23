from typing import Final

from rotkehlchen.chain.bitcoin.validation import is_valid_base58_address

# Version bytes of the dogecoin mainnet P2PKH ("D...") and P2SH ("9..." or "A...") addresses
DOGECOIN_BASE58_VERSIONS: Final = frozenset({0x1e, 0x16})


def is_valid_dogecoin_address(value: str) -> bool:
    """Validates a dogecoin mainnet P2PKH or P2SH address"""
    return is_valid_base58_address(value=value, versions=DOGECOIN_BASE58_VERSIONS)
