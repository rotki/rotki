from typing import TYPE_CHECKING, Any, NamedTuple, Optional

from rotkehlchen.types import ChainID, TokenKind
from rotkehlchen.utils.mixins.enums import DBCharEnumMixIn

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress, SolanaAddress, Timestamp


class AssetType(DBCharEnumMixIn):
    """Represents the asset type and is a direct mapping to the global DB enum.
    We removed 19 (Binance) and 27 (Avalanche) since they are EVM tokens"""
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
    EOS_TOKEN = 20
    FUSION_TOKEN = 21
    LUNIVERSE_TOKEN = 22
    OTHER = 23  # OTHER and OWN chain are probably the same thing -- needs checking
    SOLANA_TOKEN = 25
    NFT = 26
    CUSTOM_ASSET = 27

    @staticmethod
    def is_crypto_asset(asset_type: 'AssetType') -> bool:
        crypto_asset_types_values = set(range(4, 27))
        crypto_asset_types_values.add(2)  # include `OWN_CHAIN`
        return asset_type.value in crypto_asset_types_values


ASSETS_WITH_NO_CRYPTO_ORACLES = {AssetType.NFT, AssetType.CUSTOM_ASSET}
NON_CRYPTO_ASSETS = {AssetType.CUSTOM_ASSET, AssetType.FIAT}
ASSET_TYPES_EXCLUDED_FOR_USERS = {AssetType.NFT}


class AssetData(NamedTuple):
    """Data of an asset. Keep in sync with assets/asset.py"""
    identifier: str
    name: str
    symbol: str
    asset_type: AssetType
    # Every asset should have a started timestamp except for FIAT which are
    # most of the times older than epoch
    started: Optional['Timestamp']
    forked: str | None
    swapped_for: str | None
    address: 'ChecksumEvmAddress | SolanaAddress | None'
    chain_id: ChainID | None
    token_kind: TokenKind | None
    decimals: int | None
    # None means, no special mapping. '' means not supported
    cryptocompare: str | None
    coingecko: str | None
    protocol: str | None

    def serialize(self) -> dict[str, Any]:
        result = self._asdict()  # pylint: disable=no-member
        result.pop('identifier')
        result.pop('chain_id')
        result['asset_type'] = str(self.asset_type)
        if self.chain_id is not None:
            result['evm_chain'] = self.chain_id.to_name()
        if self.token_kind is not None:
            result['token_kind'] = self.token_kind.serialize()
        return result
