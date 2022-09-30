from typing import Dict, Final
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind


# Assets that need mapping in almost all the exchanges
COMMON_ASSETS_MAPPINGS: Final[Dict[str, str]] = {
    evm_address_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AXS',  # noqa: E501
    evm_address_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDC',  # noqa: E501
    evm_address_to_identifier('0x6B175474E89094C44Da98b954EedeAC495271d0F', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'DAI',  # noqa: E501
    evm_address_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'USDT',  # noqa: E501
    evm_address_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MATIC',  # noqa: E501
    evm_address_to_identifier('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'YFI',  # noqa: E501
    evm_address_to_identifier('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'WBTC',  # noqa: E501
    evm_address_to_identifier('0x514910771AF9Ca656af840dff83E8264EcF986CA', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LINK',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SUSHI',  # noqa: E501
    evm_address_to_identifier('0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'AAVE',  # noqa: E501
    evm_address_to_identifier('0x111111111117dC0aa78b770fA6A738034120C302', ChainID.ETHEREUM, EvmTokenKind.ERC20): '1INCH',  # noqa: E501
    evm_address_to_identifier('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'UNI',  # noqa: E501
    evm_address_to_identifier('0xba100000625a3754423978a60c9317c58a424e3D', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAL',  # noqa: E501
    evm_address_to_identifier('0x4E15361FD6b4BB609Fa63C81A2be19d873717870', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FTM',  # noqa: E501
    evm_address_to_identifier('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'MANA',  # noqa: E501
    evm_address_to_identifier('0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'LRC',  # noqa: E501
    evm_address_to_identifier('0xc944E90C64B2c07662A292be6244BDf05Cda44a7', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'GRT',  # noqa: E501
}
