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
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
}
