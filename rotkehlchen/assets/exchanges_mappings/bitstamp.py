from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind

WORLD_TO_BITSTAMP = COMMON_ASSETS_MAPPINGS | {
    strethaddress_to_identifier('0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9'): 'FTT',
    strethaddress_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85'): 'FET',
    strethaddress_to_identifier('0xCC8Fa225D80b9c7D42F96e9570156c65D6cAAa25'): 'SLP',
    strethaddress_to_identifier('0xC581b735A1688071A1746c968e0798D642EDE491'): 'EURT',
    strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'): 'IMX',
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',
    'SOL-2': 'SOL',
    evm_address_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'COMP',  # noqa: E501
    evm_address_to_identifier('0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SXP',  # noqa: E501
    evm_address_to_identifier('0xa1faa113cbE53436Df28FF0aEe54275c13B40975', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ALPHA',  # noqa: E501
    evm_address_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DAI',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERP',  # noqa: E501
    evm_address_to_identifier('0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INJ',  # noqa: E501
    evm_address_to_identifier('0xaaAEBE6Fe48E54f431b0C390CfaF0b017d09D42d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CEL',  # noqa: E501
    evm_address_to_identifier('0x491604c0FDF08347Dd1fa4Ee062a822A5DD06B5D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CTSI',  # noqa: E501
    evm_address_to_identifier('0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GALA',  # noqa: E501
    evm_address_to_identifier('0x0996bFb5D057faa237640E2506BE7B4f9C46de0B', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'RNDR',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
}
