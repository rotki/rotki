from rotkehlchen.fval import FVal


def strk_to_wei(amount: int | FVal) -> FVal:
    """Convert STRK amount to wei (smallest unit)
    1 STRK = 10^18 wei
    """
    return FVal(amount) * FVal(10**18)


def wei_to_strk(amount: int | FVal) -> FVal:
    """Convert wei to STRK
    1 STRK = 10^18 wei
    """
    return FVal(amount) / FVal(10**18)


def normalize_starknet_address(address: str) -> str:
    """Normalize a Starknet address to a standard format.
    
    Ensures the address has a '0x' prefix and is padded to 66 characters (64 hex digits + '0x').
    """
    addr = address.lower()
    if not addr.startswith('0x'):
        addr = '0x' + addr
    
    # Pad to 66 characters (64 hex digits + '0x' prefix)
    if len(addr) < 66:
        addr = '0x' + addr[2:].zfill(64)
    
    return addr
