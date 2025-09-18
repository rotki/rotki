from contextlib import suppress

from base58 import b58decode


def is_valid_solana_address(address: str) -> bool:
    """Check if a string is a valid solana address."""
    with suppress(ValueError, TypeError):
        return len(b58decode(address)) == 32

    return False
