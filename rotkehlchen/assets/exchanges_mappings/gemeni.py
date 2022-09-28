from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind

WORLD_TO_GEMINI = COMMON_ASSETS_MAPPINGS | {
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    strethaddress_to_identifier('0xCC8Fa225D80b9c7D42F96e9570156c65D6cAAa25'): 'SLP',
    strethaddress_to_identifier('0xba5BDe662c17e2aDFF1075610382B9B691296350'): 'RARE',
    strethaddress_to_identifier('0x18aAA7115705e8be94bfFEBDE57Af9BFc265B998'): 'AUDIO',
    strethaddress_to_identifier('0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85'): 'FET',
    strethaddress_to_identifier('0xd2877702675e6cEb975b4A1dFf9fb7BAF4C91ea9'): 'LUNA',
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0x9E32b13ce7f2E80A01932B42553652E053D6ed8e'): 'METI',
    evm_address_to_identifier('0x9E32b13ce7f2E80A01932B42553652E053D6ed8e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'METIS',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SNX',  # noqa: E501
    evm_address_to_identifier('0x4E15361FD6b4BB609Fa63C81A2be19d873717870', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FTM',  # noqa: E501
    evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FXS',  # noqa: E501
    evm_address_to_identifier('0x0954906da0Bf32d5479e25f46056d22f08464cab', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INDEX',  # noqa: E501
    evm_address_to_identifier('0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INJ',  # noqa: E501
    evm_address_to_identifier('0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MIM',  # noqa: E501
    evm_address_to_identifier('0x949D48EcA67b17269629c7194F4b727d4Ef9E5d6', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MC',  # noqa: E501
    evm_address_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LRC',  # noqa: E501
    evm_address_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LDO',  # noqa: E501
    evm_address_to_identifier('0x09a3EcAFa817268f77BE1283176B946C4ff2E608', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MIR',  # noqa: E501
    evm_address_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GRT',  # noqa: E501
    evm_address_to_identifier('0x9E32b13ce7f2E80A01932B42553652E053D6ed8e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'METI',  # noqa: E501
    evm_address_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'IMX',  # noqa: E501
}
