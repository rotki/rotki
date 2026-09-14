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
CCTP_SOLANA_DOMAIN: Final = 5

# V2 event topics (different parameter layout from V1)
DEPOSIT_FOR_BURN_V2: Final = b'\x0c\x8c\x1c\xbd\xc5\x19\x06\x13\xeb\xd4\x85Q\x1dN(\x12\xcf\xa4^\xec\xb7\x9d\x84X\x933\x1f\xed\xadQ0\xa5'  # noqa: E501
MESSAGE_RECEIVED_V2: Final = b'\xffH\xc1>\xda\x96\xb1\xcc\xea\xcck\x9e\xde\xed\xc9\xe9\xdb\x9db&\xaf\xbc0\x14kr\x0c\x19\xd3\xad\xdb\x1c'  # noqa: E501
MINT_AND_WITHDRAW_V2: Final = b'P\xc5^\x91Q4\xd4W\xde\xbf\xa5\x8e\xb6\xf44)V\xf8\xb0amQ\xa8\x9a6Y6\x01x\xe1\xabc'  # noqa: E501

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
