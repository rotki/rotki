def is_valid_starknet_address(address: str) -> bool:
    """Check if a string is a valid Starknet address.
    
    Starknet addresses are hexadecimal strings starting with '0x' and are 66 characters long
    (including the '0x' prefix), representing a 32-byte value.
    """
    # Remove '0x' prefix if present
    addr = address.lower()
    if addr.startswith('0x'):
        addr = addr[2:]
    
    # Check if it's a valid hexadecimal string
    if not all(c in '0123456789abcdef' for c in addr):
        return False
    
    # Starknet addresses can be up to 64 hex characters (32 bytes)
    # They are often padded to 64 characters, but can be shorter
    return 0 < len(addr) <= 64
