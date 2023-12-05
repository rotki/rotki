from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind

WORLD_TO_BYBIT = COMMON_ASSETS_MAPPINGS | {
    evm_address_to_identifier('0x4d224452801ACEd8B2F0aebE155379bb5D594381', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'APE',  # noqa: E501
    evm_address_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LDO',  # noqa: E501
    evm_address_to_identifier('0x6982508145454Ce325dDbE47a25d4ec3d2311933', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PEPE',  # noqa: E501
    evm_address_to_identifier('0x582d872A1B094FC48F5DE31D3B73F2D9bE47def1', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TON',  # noqa: E501
    evm_address_to_identifier('0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'INJ',  # noqa: E501
    evm_address_to_identifier('0xf486ad071f3bEE968384D2E39e2D8aF0fCf6fd46', ChainID.BINANCE, EvmTokenKind.ERC20): 'VELO',  # noqa: E501
    evm_address_to_identifier('0x808507121B80c02388fAd14726482e061B8da827', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PENDLE',  # noqa: E501
    evm_address_to_identifier('0x0000000000085d4780B73119b644AE5ecd22b376', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'TUSD',  # noqa: E501
    evm_address_to_identifier('0xEd04915c23f00A313a544955524EB7DBD823143d', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ACH',  # noqa: E501
    evm_address_to_identifier('0xf4d2888d29D722226FafA5d9B24F9164c092421E', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LOOKS',  # noqa: E501
    evm_address_to_identifier('0x477bC8d23c634C154061869478bce96BE6045D12', ChainID.BINANCE, EvmTokenKind.ERC20): 'SFUND',  # noqa: E501
    evm_address_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'IMX',  # noqa: E501
    evm_address_to_identifier('0xcAfE001067cDEF266AfB7Eb5A286dCFD277f3dE5', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PSP',  # noqa: E501
    evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PERP',  # noqa: E501
}
