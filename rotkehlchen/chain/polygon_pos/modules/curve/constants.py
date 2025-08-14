from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

AAVE_POOLS: Final = {
    string_to_evm_address('0x445FE580eF8d70FF569aB36e80c647af338db351'),  # aDAI + aUSDC.e + aUSDT
    string_to_evm_address('0xb61Ecec987a9529dbA13a8Dd10ea24446ccBB6ae'),  # L3USD + DAI + USDC.e + USDT  # noqa: E501
}
