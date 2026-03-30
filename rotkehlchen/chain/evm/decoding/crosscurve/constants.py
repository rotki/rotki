from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_CROSSCURVE: Final = 'crosscurve'
CROSSCURVE_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_CROSSCURVE,
    label='CrossCurve',
    image='crosscurve.svg',
)

# UnifiedRouterV2 — deployed on Ethereum, BSC, Polygon, Avalanche, Optimism, Arbitrum, Fantom
UNIFIED_ROUTER_V2: Final = string_to_evm_address('0xfa43DE785dd3Cd0ef3dAE0dD2b8bE3F1B5112d1a')
# UnifiedRouterV2 — deployed on Base, Gnosis, Linea, Sonic and other newer chains
UNIFIED_ROUTER_V2_NEW: Final = string_to_evm_address('0xA2A786ff9148f7C88EE93372Db8CBe9e94585c74')

# CrossCurve cross-chain messaging contract, same address on all chains
CROSSCURVE_RELAYER: Final = string_to_evm_address('0xEce9CF6A8F2768A3b8b65060925B646AfEAa5167')

# Emitted by UnifiedRouterV2 when a cross-chain swap is initiated.
# topic[1] = indexed sender address
CROSSCHAIN_SWAP_INITIATED: Final = b'\xbfj\xfb\xaf\xfb;\x95[\xeb\xbfCC\x0b\xbf\x8e\xec\xb8\xd3O\xf8o)?Y"\x03\xab^\xd7\x9cRh'  # noqa: E501
# Emitted by CROSSCURVE_RELAYER on the destination chain when a bridge swap is completed.
CROSSCHAIN_SWAP_COMPLETED: Final = b'K[/\xd6\xaa&s\x9a-\xeaR\xc4\x1dR\xe1\xbf\xd7J2\x88\xc6\x04\xa27\xc5\x1b\xdf\xbd\xd3y\x90\x06'  # noqa: E501
