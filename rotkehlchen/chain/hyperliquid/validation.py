def is_valid_hyperliquid_token_address(address: object) -> bool:
    """Return whether address is a 0x-prefixed 16-byte Hyperliquid Core token id."""
    if not isinstance(address, str) or len(address) != 34 or address.startswith('0x') is False:
        return False

    try:
        return len(bytes.fromhex(address[2:])) == 16
    except ValueError:
        return False
