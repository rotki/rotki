from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.oneinch.constants import ONEINCH_ICON

CPT_ONEINCH_LIQUIDITY: Final = '1inch-liquidity'
ONEINCH_LIQUIDITY_LABEL: Final = '1inch Liquidity Protocol'
ONEINCH_LIQUIDITY_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_ONEINCH_LIQUIDITY,
    label=ONEINCH_LIQUIDITY_LABEL,
    image=ONEINCH_ICON,
)

# Events emitted by the pools of both the Mooniswap and the 1inch Liquidity Protocol factories
# topic of the Deposited(address,address,uint256,uint256,uint256) event
DEPOSITED: Final = b'\x8b\xabj\xedZP\x897\x05\x1a\x14Na\xd6\xe6\x136\x83Jf\xaa\xee%\n\x00a:\xe6\xf7D\xc4"'  # noqa: E501
# topic of the Withdrawn(address,address,uint256,uint256,uint256) event
WITHDRAWN: Final = b'<\xae\x99#\xfd</F\x8a\xa2Z\x8e\xf6\x87\x92>7\xf9WE\x95W\xc08\x0f\xd0e&\xc0\xb8\xcd\xbc'  # noqa: E501
