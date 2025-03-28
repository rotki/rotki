from typing import Final

from eth_typing import ABI

from rotkehlchen.chain.evm.types import string_to_evm_address

CRVUSD_MINTER: Final = string_to_evm_address('0xC9332fdCB1C491Dcc683bAe86Fe3cb70360738BC')
CRVUSD_MINTER_ABI: Final[ABI] = [{'stateMutability': 'view', 'type': 'function', 'name': 'controllers', 'inputs': [{'name': 'arg0', 'type': 'uint256'}], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'n_collaterals', 'inputs': [], 'outputs': [{'name': '', 'type': 'uint256'}]}]  # noqa: E501
CURVE_CRVUSD_CONTROLLER_ABI: Final[ABI] = [{'stateMutability': 'view', 'type': 'function', 'name': 'amm', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}, {'stateMutability': 'view', 'type': 'function', 'name': 'collateral_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}]  # noqa: E501
CRVUSD_PEG_KEEPERS: Final = {
    string_to_evm_address('0x9201da0D97CaAAff53f01B2fB56767C7072dE340'),  # USDC/crvUSD
    string_to_evm_address('0xFb726F57d251aB5C731E5C64eD4F5F94351eF9F3'),  # USDT/crvUSD
    string_to_evm_address('0x3fA20eAa107DE08B38a8734063D605d5842fe09C'),  # PYUSD/crvUSD
    string_to_evm_address('0x503E1Bf274e7a6c64152395aE8eB57ec391F91F8'),  # USDM/crvUSD
}
PEG_KEEPER_WITHDRAW_TOPIC: Final = b'[kC\x1dDv\xa2\x11\xbb}A\xc2\r\x1a\xab\x9a\xe22\x1d\xee\xe0\xd2\x0b\xe3\xd9\xfc\x9b\x10\x93\xfan='  # noqa: E501
