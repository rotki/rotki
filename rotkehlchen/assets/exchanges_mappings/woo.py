from rotkehlchen.constants.resolver import evm_address_to_identifier, strethaddress_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind

WOO_NAME_TO_TOKEN_SYMBOL = {
    'WOO': evm_address_to_identifier('0x4691937a7508860F876c9c0a2a617E7d9E945D4B', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'STG': evm_address_to_identifier('0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'ONE': 'ONE-2',
    'DODO': evm_address_to_identifier('0x43Dfc4159D86F3A37A5A4B3D4580b888ad7d4DDd', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'RNDR': evm_address_to_identifier('0x0996bFb5D057faa237640E2506BE7B4f9C46de0B', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'FXS': evm_address_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'IMX': strethaddress_to_identifier('0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF'),
    'RSR': evm_address_to_identifier('0x320623b8E4fF03373931769A31Fc52A4E78B5d70', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'PERP': evm_address_to_identifier('0xbC396689893D065F41bc2C6EcbeE5e0085233447', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'WLD': evm_address_to_identifier('0x163f8C2467924be0ae7B5347228CABF260318753', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'LDO': evm_address_to_identifier('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'MAGIC': evm_address_to_identifier('0xB0c7a3Ba49C7a6EaBa6cD4a96C55a1391070Ac9A', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'WSM': evm_address_to_identifier('0xB62E45c3Df611dcE236A6Ddc7A493d79F9DFadEf', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'FTMWOO': evm_address_to_identifier('0x6626c47c00F1D87902fc13EECfaC3ed06D5E8D8a', ChainID.FANTOM, EvmTokenKind.ERC20),  # noqa: E501
    # This entries below were retrieved from the woo API: https://api.woo.org/v1/public/token. It is used to resolve some woo token names to their symbol  # noqa: E501
    'ARB_USDCNATIVE': evm_address_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'AVAXC': 'AVAX',
    'AVAXC_USDC2': evm_address_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'BCHSV': 'BSV',
    'BSC_BTCB': 'BTC',
    'ETH-AETH': 'ETH',
    'ETH_AXS_NEW': evm_address_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'ETH_DAI_V1': evm_address_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'ETH_LRCV2': evm_address_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'ETH_UNISWAP': evm_address_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', ChainID.ETHEREUM, EvmTokenKind.ERC20),  # noqa: E501
    'FTM_WOO_2': evm_address_to_identifier('0x6626c47c00F1D87902fc13EECfaC3ed06D5E8D8a', ChainID.FANTOM, EvmTokenKind.ERC20),  # noqa: E501
    'TRON': 'TRX',
    'UATOM': 'ATOM',
}
