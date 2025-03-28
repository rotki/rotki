from typing import Final

from eth_typing import ABI

from rotkehlchen.chain.evm.types import string_to_evm_address

CRVUSD_MINTER: Final = string_to_evm_address('0xC9332fdCB1C491Dcc683bAe86Fe3cb70360738BC')
CRVUSD_MINTER_ABI: Final[ABI] = [{'stateMutability': 'view', 'type': 'function', 'name': 'controllers', 'inputs': [{'name': 'arg0', 'type': 'uint256'}], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'n_collaterals', 'inputs': [], 'outputs': [{'name': '', 'type': 'uint256'}]}]  # noqa: E501
CURVE_CRVUSD_CONTROLLER_ABI: Final[ABI] = [{'stateMutability': 'view', 'type': 'function', 'name': 'amm', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'collateral_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}]  # noqa: E501
CRVUSD_PEG_KEEPERS_AND_POOLS: Final = {
    string_to_evm_address('0x9201da0D97CaAAff53f01B2fB56767C7072dE340'): string_to_evm_address('0x4DEcE678ceceb27446b35C672dC7d61F30bAD69E'),  # USDC/crvUSD  # noqa: E501
    string_to_evm_address('0xFb726F57d251aB5C731E5C64eD4F5F94351eF9F3'): string_to_evm_address('0x390f3595bCa2Df7d23783dFd126427CCeb997BF4'),  # USDT/crvUSD  # noqa: E501
    string_to_evm_address('0x3fA20eAa107DE08B38a8734063D605d5842fe09C'): string_to_evm_address('0x625E92624Bc2D88619ACCc1788365A69767f6200'),  # PYUSD/crvUSD  # noqa: E501
    string_to_evm_address('0x503E1Bf274e7a6c64152395aE8eB57ec391F91F8'): string_to_evm_address('0x30cE6E5A75586F0E83bCAc77C9135E980e6bc7A8'),  # USDM/crvUSD  # noqa: E501
}
PEG_KEEPER_PROVIDE_TOPIC: Final = b'\x8dh[\xd3\xf4]\x86\x1cu\x9e\xd7\xa4n\xa3\xd3\x0e\xb5\xccl\xe9\xfe\x06\xc5&\x93\x1f\x94\xc9c\xbc\xa7\xd2'  # noqa: E501
PEG_KEEPER_WITHDRAW_TOPIC: Final = b'[kC\x1dDv\xa2\x11\xbb}A\xc2\r\x1a\xab\x9a\xe22\x1d\xee\xe0\xd2\x0b\xe3\xd9\xfc\x9b\x10\x93\xfan='  # noqa: E501
