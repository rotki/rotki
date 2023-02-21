from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind

WORLD_TO_BITPANDA = COMMON_ASSETS_MAPPINGS | {
    'IOTA': 'MIOTA',
    strethaddress_to_identifier('0x536381a8628dBcC8C70aC9A30A7258442eAb4c92'): 'PAN',  # Pantos
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',  # ANT v2
    'eip155:56/erc20:0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82': 'CAKE',
    'SOL-2': 'SOL',  # Solana
    'LUNA-2': 'LUNA',  # Luna Terra
    evm_address_to_identifier('0x221657776846890989a759BA2973e427DfF5C9bB', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'REP',  # noqa: E501
}
