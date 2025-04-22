from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

SCROLL_MONERIUM_ADDRESSES: Final = {
    string_to_evm_address('0xd7BB130A48595fCDf9480E36C1aE97ff2938aC21'),  # EURe
    string_to_evm_address('0x484D0D40773fa021B3D30232B4CAac6c7db283Fb'),  # GBPe
    string_to_evm_address('0x673541D0d71Dc324a6c94aCDcd540BcA8C5eA289'),  # USDe
    string_to_evm_address('0x9B4e8238D3Efd628E64d8A75bB29B309DaD6080e'),  # ISKe
}
