from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import (
    A_AVAX,
    A_BCH,
    A_BSC_BNB,
    A_BTC,
    A_DOT,
    A_ETH,
    A_ETH2,
    A_KSM,
    A_POL,
    A_SOL,
    A_XDAI,
)
from rotkehlchen.types import SupportedBlockchain


def test_supported_blockchain_native_token():
    """Test the native token identifiers are valid and exist in the DB"""
    expected_assets = {
        SupportedBlockchain.ETHEREUM: A_ETH,
        SupportedBlockchain.ETHEREUM_BEACONCHAIN: A_ETH2,
        SupportedBlockchain.BITCOIN: A_BTC,
        SupportedBlockchain.BITCOIN_CASH: A_BCH,
        SupportedBlockchain.KUSAMA: A_KSM,
        SupportedBlockchain.AVALANCHE: A_AVAX,
        SupportedBlockchain.POLKADOT: A_DOT,
        SupportedBlockchain.OPTIMISM: A_ETH,
        SupportedBlockchain.POLYGON_POS: A_POL,
        SupportedBlockchain.ARBITRUM_ONE: A_ETH,
        SupportedBlockchain.BASE: A_ETH,
        SupportedBlockchain.GNOSIS: A_XDAI,
        SupportedBlockchain.SCROLL: A_ETH,
        SupportedBlockchain.BINANCE_SC: A_BSC_BNB,
        SupportedBlockchain.ZKSYNC_LITE: A_ETH,
        SupportedBlockchain.SOLANA: A_SOL,
    }
    for chain in SupportedBlockchain:
        assert expected_assets[chain] == Asset(chain.get_native_token_id())
