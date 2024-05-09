from typing import Final

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.hop.structures import HopBridgeEventData
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH

BRIDGES: Final = {
    string_to_evm_address('0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a'): HopBridgeEventData(
        identifier=A_ETH.identifier,
        amm_wrapper=string_to_evm_address('0x10541b07d8Ad2647Dc6cD67abd4c03575dade261'),
        saddle_swap=string_to_evm_address('0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d'),
    ), string_to_evm_address('0x46ae9BaB8CEA96610807a275EBD36f8e916b5C61'): HopBridgeEventData(
        identifier='eip155:8453/erc20:0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA',
        amm_wrapper=string_to_evm_address('0x7D269D3E0d61A05a0bA976b7DBF8805bF844AF3F'),
        saddle_swap=string_to_evm_address('0x022C5cE6F1Add7423268D41e08Df521D5527C2A0'),
    ), string_to_evm_address('0xe22D2beDb3Eca35E6397e0C6D62857094aA26F52'): HopBridgeEventData(
        identifier='eip155:8453/erc20:0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC',
        amm_wrapper=ZERO_ADDRESS,
    ),
}
