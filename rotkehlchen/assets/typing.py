from typing import TYPE_CHECKING, Any, Dict, NamedTuple, Optional, Tuple

from rotkehlchen.utils.mixins.dbenum import DBEnumMixIn

if TYPE_CHECKING:
    from rotkehlchen.typing import ChecksumEthAddress, Timestamp


class AssetType(DBEnumMixIn):
    FIAT = 1
    OWN_CHAIN = 2
    ETHEREUM_TOKEN = 3
    OMNI_TOKEN = 4
    NEO_TOKEN = 5
    COUNTERPARTY_TOKEN = 6
    BITSHARES_TOKEN = 7
    ARDOR_TOKEN = 8
    NXT_TOKEN = 9
    UBIQ_TOKEN = 10
    NUBITS_TOKEN = 11
    BURST_TOKEN = 12
    WAVES_TOKEN = 13
    QTUM_TOKEN = 14
    STELLAR_TOKEN = 15
    TRON_TOKEN = 16
    ONTOLOGY_TOKEN = 17
    VECHAIN_TOKEN = 18
    BINANCE_TOKEN = 19
    EOS_TOKEN = 20
    FUSION_TOKEN = 21
    LUNIVERSE_TOKEN = 22
    OTHER = 23
    AVALANCHE_TOKEN = 24
    SOLANA_TOKEN = 25
    POLYGON_TOKEN = 26
    XDAI_TOKEN = 27
    OKEX_TOKEN = 28
    FANTOM_TOKEN = 29
    ARBITRUM_TOKEN = 30
    OPTIMISM_TOKEN = 31

    @classmethod
    def evm_assets(cls) -> Tuple['AssetType', ...]:
        return (
            AssetType.ETHEREUM_TOKEN,
            AssetType.POLYGON_TOKEN,
            AssetType.XDAI_TOKEN,
            AssetType.AVALANCHE_TOKEN,
            AssetType.OKEX_TOKEN,
            AssetType.FANTOM_TOKEN,
            AssetType.ARBITRUM_TOKEN,
            AssetType.OPTIMISM_TOKEN,
        )


class AssetData(NamedTuple):
    """Data of an asset. Keep in sync with assets/asset.py"""
    identifier: str
    name: str
    symbol: str
    asset_type: AssetType
    # Every asset should have a started timestamp except for FIAT which are
    # most of the times older than epoch
    started: Optional['Timestamp']
    forked: Optional[str]
    swapped_for: Optional[str]
    ethereum_address: Optional['ChecksumEthAddress']
    decimals: Optional[int]
    # None means, no special mapping. '' means not supported
    cryptocompare: Optional[str]
    coingecko: Optional[str]
    protocol: Optional[str]

    def serialize(self) -> Dict[str, Any]:
        result = self._asdict()  # pylint: disable=no-member
        result.pop('identifier')
        result['asset_type'] = str(self.asset_type)
        return result
