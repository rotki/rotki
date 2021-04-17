from typing import TYPE_CHECKING, Any, Dict, NamedTuple, Optional

from rotkehlchen.errors import DeserializationError
from rotkehlchen.utils.mixins import DBEnumMixIn

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

    @staticmethod
    def deserialize(value: str) -> 'AssetType':
        """Deserializes an asset type from a string. Probably sent via the API

        May raise DeserializationError if the value does not match an asset type
        """
        upper_str = value.replace(' ', '_').upper()
        asset_type = AssetType.__members__.get(upper_str, None)  # pylint: disable=no-member
        if asset_type is None:
            raise DeserializationError(f'Could not deserialize {value} as an asset type')

        return asset_type


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
