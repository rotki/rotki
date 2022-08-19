from typing import TYPE_CHECKING, Any, Dict, NamedTuple, Optional
from rotkehlchen.constants.resolver import ChainID
from rotkehlchen.types import EvmTokenKind

from rotkehlchen.utils.mixins.dbenum import DBEnumMixIn

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress, Timestamp


class AssetType(DBEnumMixIn):
    FIAT = 1
    OWN_CHAIN = 2
    EVM_TOKEN = 3
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
    NFT = 26


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
    address: Optional['ChecksumEvmAddress']
    chain: Optional[ChainID]
    token_kind: Optional[EvmTokenKind]
    decimals: Optional[int]
    # None means, no special mapping. '' means not supported
    cryptocompare: Optional[str]
    coingecko: Optional[str]
    protocol: Optional[str]

    def serialize(self) -> Dict[str, Any]:
        result = self._asdict()  # pylint: disable=no-member
        result.pop('identifier')
        result['asset_type'] = str(self.asset_type)
        if self.chain is not None:
            result['chain'] = self.chain.serialize()
        if self.token_kind is not None:
            result['token_kind'] = self.token_kind.serialize()
        return result
