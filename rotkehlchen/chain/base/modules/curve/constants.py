from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CURVE_SWAP_ROUTERS_NG: Final = {
    string_to_evm_address('0xd6681e74eEA20d196c15038C580f721EF2aB6320'),  # CurveRouterSidechain v1.0  # noqa: E501
    string_to_evm_address('0x4f37A9d177470499A2dD084621020b023fcffc1F'),  # CurveRouterSidechain v1.1  # noqa: E501
}
DEPOSIT_AND_STAKE_ZAP: Final = string_to_evm_address('0x69522fb5337663d3B4dFB0030b881c1A750Adb4f')
