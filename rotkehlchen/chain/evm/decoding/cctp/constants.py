from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.types import ChainID

CPT_CCTP: Final = 'cctp'
CCTP_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_CCTP,
    label='Circle CCTP',
    image='cctp.svg',
)
DEPOSIT_FOR_BURN: Final = b'/\xa9\xca\x89I\x82\x93\x01\x90r~uP\n\x97\xd8\xdcP\x023\xa5\x06^\x0f1&\xc4\x8f\xbe\x03C\xc0'  # noqa: E501
MESSAGE_RECEIVED: Final = b'X \x0bL4\xae\x05\xee\x81mq\x00S\xff\xf3\xfbu\xafC\x95\x91]=*w\x1b$\xaa\x10\xe3\xcc]'  # noqa: E501
MINT_AND_WITHDRAW: Final = b'\x1b*\x7f\xf0\x80\xb8\xcbo\xf46\xce\x03r\xe3\x99i+\xbf\xb6\xd4\xaeWf\xfd\x8dX\xa7\xb8\xccaB\xe6'  # noqa: E501
USDC_DECIMALS: Final = 6  # all Circle issued USDC has 6 decimals

# V2 event topics (different parameter layout from V1)
DEPOSIT_FOR_BURN_V2: Final = b'\x0c\x8c\x1c\xbd_\x93\x9bG\xea\xd8\x0e\x82\x07@}\xd4K\x96\x16<4\x9e\xc5r\xa2\x89\xee\xb2\xba\x8a~\x8d'  # noqa: E501
MESSAGE_RECEIVED_V2: Final = b'\xff\x48\xc1\x3e\xfc\xd1_\xb2\xf2\x82Dc\xd0\xb8\xd9\x1e\xce\x11R\x01\x01\xa2\xe1|\x1aH\xa5\x03\xe3\xdf~\x9c'  # noqa: E501
MINT_AND_WITHDRAW_V2: Final = b'P\xc5^\x91\x8aF\xa7\xc6\x80p\x16\xb7L\xb5\xab\x99\x93\xc0]\x9a\\\x12\x9e\xbc\xb0\x1b\xec\xd7\xd4,\xd0'  # noqa: E501

CCTP_DOMAIN_MAPPING: Final = {
    0: ChainID.ETHEREUM,
    1: ChainID.AVALANCHE,
    2: ChainID.OPTIMISM,
    3: ChainID.ARBITRUM_ONE,
    6: ChainID.BASE,
    7: ChainID.POLYGON_POS,
    15: ChainID.MONAD,
    19: ChainID.HYPERLIQUID,
}
