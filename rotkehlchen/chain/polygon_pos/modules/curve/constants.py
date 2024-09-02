from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

AAVE_POOLS: Final = {
    string_to_evm_address('0x445fe580ef8d70ff569ab36e80c647af338db351'),  # aDAI + aUSDC.e + aUSDT
    string_to_evm_address('0xb61ecec987a9529dba13a8dd10ea24446ccbb6ae'),  # L3USD + DAI + USDC.e + USDT  # noqa: E501
}
