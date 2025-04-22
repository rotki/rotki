from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

ARBITRUM_MONERIUM_ADDRESSES: Final = {
    string_to_evm_address('0x0c06cCF38114ddfc35e07427B9424adcca9F44F8'),  # EURe
    string_to_evm_address('0x2D80dBf04D0802abD7A342DaFA5d7cB42bfbb52f'),  # GBPe
    string_to_evm_address('0x0Fc041a4B6a3F634445804daAFD03f202337C125'),  # USDe
    string_to_evm_address('0x845a96969e8d84FF32B8939934d9771005178920'),  # ISKe
}
