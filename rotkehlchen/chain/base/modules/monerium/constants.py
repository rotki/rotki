from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

BASE_MONERIUM_ADDRESSES: Final = {
    string_to_evm_address('0xbf6e2966A9C3D99C9E4D069E04f7Bdb9C8aa762C'),  # EURe
    string_to_evm_address('0xc4759Ed641DA77CbDc9fA2f37E9260a29BF7cC52'),  # GBPe
    string_to_evm_address('0x1a3237Ae46886E416Ae25499eC9cD7Bf437f25Da'),  # ISKe
}
