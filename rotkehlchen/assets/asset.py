import abc
import logging
from dataclasses import InitVar, dataclass, field
from functools import total_ordering
from typing import Any, NamedTuple, Optional, Union

from eth_utils import to_checksum_address

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V3
from rotkehlchen.chain.evm.decoding.aave.v3.constants import DEBT_TOKEN_SYMBOL_REGEX
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK
from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.constants.resolver import ChainID, evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset, WrongAssetType
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EVM_TOKEN_KINDS, ChecksumEvmAddress, Timestamp, TokenKind

from .types import ASSETS_WITH_NO_CRYPTO_ORACLES, NON_CRYPTO_ASSETS, AssetType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

UnderlyingTokenDBTuple = tuple[str, str, str]


class UnderlyingToken(NamedTuple):
    """Represents an underlying token of a token

    Is used for pool tokens, tokensets etc.
    """
    address: ChecksumEvmAddress
    token_kind: EVM_TOKEN_KINDS
    weight: FVal  # Floating percentage from 0 to 1

    def serialize(self) -> dict[str, Any]:
        return {
            'address': self.address,
            'token_kind': self.token_kind.serialize(),
            'weight': str(self.weight * 100),
        }

    @classmethod
    def deserialize_from_db(cls, entry: UnderlyingTokenDBTuple) -> 'UnderlyingToken':
        return UnderlyingToken(
            address=entry[0],  # type: ignore
            token_kind=TokenKind.deserialize_evm_from_db(entry[1]),
            weight=FVal(entry[2]),
        )

    def get_identifier(self, parent_chain: ChainID) -> str:
        return evm_address_to_identifier(
            address=str(self.address),
            chain_id=parent_chain,
            token_type=self.token_kind,
        )


@total_ordering
@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=False, frozen=True)
class Asset:
    """Base class for all assets"""
    identifier: str
    direct_field_initialization: InitVar[bool] = field(default=False)

    def __post_init__(self, direct_field_initialization: bool) -> None:  # pylint: disable=unused-argument
        if not isinstance(self.identifier, str):
            raise DeserializationError(
                'Tried to initialize an asset out of a non-string identifier',
            )

    def to_dict(self) -> dict[str, Any]:
        return {'identifier': self.identifier}

    def serialize(self) -> str:
        return self.identifier

    def get_asset_type(self) -> AssetType:
        """Returns type of the asset. Prefers to use the asset_type field if it exists"""
        if isinstance(self, AssetWithNameAndType):
            return self.asset_type

        return AssetResolver.get_asset_type(self.identifier)

    def exists(self, query_packaged_db: bool = True) -> bool:
        """Returns True if this asset exists. False otherwise

        If True, the asset's identifier also gets normalized if needed.
        """
        try:
            self.check_existence(query_packaged_db=query_packaged_db)
        except UnknownAsset:
            return False

        return True

    def check_existence(self, query_packaged_db: bool = True) -> 'Asset':
        """
        If this asset exists, returns the instance with normalized identifier set.
        If it doesn't, throws an UnknownAsset error.
        When the `query_packaged_db` is set to True and the checked asset is in the list
        of constant assets we try to copy it from the packaged global db.

        May raise:
        - UnknownAsset
        """
        normalized_id = AssetResolver.check_existence(self.identifier, query_packaged_db=query_packaged_db)  # noqa: E501
        object.__setattr__(self, 'identifier', normalized_id)
        return self

    def is_nft(self) -> bool:
        return self.identifier.startswith(NFT_DIRECTIVE)

    def is_fiat(self) -> bool:
        return self.get_asset_type() == AssetType.FIAT

    def is_asset_with_oracles(self) -> bool:
        return self.get_asset_type() not in ASSETS_WITH_NO_CRYPTO_ORACLES

    def is_evm_token(self) -> bool:
        return self.get_asset_type() == AssetType.EVM_TOKEN

    def is_crypto(self) -> bool:
        return self.get_asset_type() not in NON_CRYPTO_ASSETS

    def resolve(self) -> 'AssetWithNameAndType':
        """
        Returns the final representation for the current asset identifier. For example if we do
        dai = Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F').resolve()
        we will get in the variable dai the `EvmToken` representation of DAI. Same for other
        subclasses of Asset.

        May raise:
        - UnknownAsset
        """
        if self.identifier.startswith(NFT_DIRECTIVE):
            return Nft.initialize(
                identifier=self.identifier,
                chain_id=ChainID.ETHEREUM,
            )

        return AssetResolver.resolve_asset(identifier=self.identifier)

    def resolve_to_asset_with_name_and_type(self) -> 'AssetWithNameAndType':
        return AssetResolver.resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=AssetWithNameAndType,
        )

    def resolve_to_asset_with_symbol(self) -> 'AssetWithSymbol':
        return AssetResolver.resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=AssetWithSymbol,
        )

    def resolve_to_crypto_asset(self) -> 'CryptoAsset':
        return AssetResolver.resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=CryptoAsset,
        )

    def resolve_to_evm_token(self) -> 'EvmToken':
        return AssetResolver.resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=EvmToken,
        )

    def resolve_to_asset_with_oracles(self) -> 'AssetWithOracles':
        return AssetResolver.resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=AssetWithOracles,
        )

    def resolve_to_fiat_asset(self) -> 'FiatAsset':
        return AssetResolver.resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=FiatAsset,
        )

    def symbol_or_name(self) -> str:
        """
        If it is an asset with symbol, returns symbol. If it's not, returns name.
        May raise:
        - UnknownAsset if identifier is not in the db
        """
        try:
            with_symbol = self.resolve_to_asset_with_symbol()
        except WrongAssetType:
            with_name = self.resolve_to_asset_with_name_and_type()
            return with_name.name
        else:
            return with_symbol.symbol

    def __hash__(self) -> int:
        return hash(self.identifier)

    def __repr__(self) -> str:
        return f'<Asset identifier:{self.identifier}>'

    def __eq__(self, other: object) -> bool:
        if other is None:
            return False

        if isinstance(other, Asset):
            return self.identifier.lower() == other.identifier.lower()
        if isinstance(other, str):
            return self.identifier.lower() == other.lower()

        return False

    def __lt__(self, other: Union['Asset', str]) -> bool:
        if isinstance(other, Asset):
            return self.identifier < other.identifier
        if isinstance(other, str):
            return self.identifier < other
        # else (but should never happen due to type checking)
        raise NotImplementedError(f'Invalid comparison of asset with {type(other)}')

    def __str__(self) -> str:
        return self.identifier


@dataclass(init=True, repr=False, eq=False, order=False, unsafe_hash=False, frozen=True)
class AssetWithNameAndType(Asset, abc.ABC):
    asset_type: AssetType = field(init=False)
    name: str = field(init=False)

    def get_asset_data(self) -> dict[str, Any]:
        """Returns asset data as a dictionary"""
        raise NotImplementedError('Subclasses must implement get_asset_data')

    def to_dict(self) -> dict[str, Any]:
        return super().to_dict() | {
            'name': self.name,
            'asset_type': str(self.asset_type),
        }

    def __repr__(self) -> str:
        return f'<Asset identifier:{self.identifier} name:{self.name}>'

    def __str__(self) -> str:
        return f'{self.identifier}({self.name})'


class AssetWithSymbol(AssetWithNameAndType, abc.ABC):
    symbol: str = field(init=False)

    def to_dict(self) -> dict[str, Any]:
        return super().to_dict() | {'symbol': self.symbol}

    def __repr__(self) -> str:
        return f'<Asset identifier:{self.identifier} name:{self.name} symbol:{self.symbol}>'


class AssetWithOracles(AssetWithSymbol, abc.ABC):
    # None means no special mapping. '' means not supported
    cryptocompare: str | None = field(init=False)
    coingecko: str | None = field(init=False)

    def to_cryptocompare(self) -> str:
        """
        Returns the symbol with which to query cryptocompare for the asset
        May raise:
            - UnsupportedAsset if the asset is not supported by cryptocompare
        """
        # There is an asset which should not be queried in cryptocompare
        if self.cryptocompare is None or self.cryptocompare == '':
            raise UnsupportedAsset(f'{self.identifier} is not supported by cryptocompare')

        # Seems cryptocompare capitalizes everything. So cDAI -> CDAI
        return self.cryptocompare.upper()  # pylint: disable=no-member

    def to_coingecko(self) -> str:
        """
        Returns the symbol with which to query coingecko for the asset
        May raise:
            - UnsupportedAsset if the asset is not supported by coingecko
        """
        coingecko_str = '' if self.coingecko is None else self.coingecko
        # This asset has no coingecko mapping
        if coingecko_str == '':
            raise UnsupportedAsset(f'{self.identifier} is not supported by coingecko')
        return coingecko_str

    def has_coingecko(self) -> bool:
        return self.coingecko is not None and self.coingecko != ''

    def to_dict(self) -> dict[str, Any]:
        return super().to_dict() | {
            'cryptocompare': self.cryptocompare,
            'coingecko': self.coingecko,
        }


@dataclass(init=True, repr=False, eq=False, order=False, unsafe_hash=False, frozen=True)
class FiatAsset(AssetWithOracles):

    def __post_init__(self, direct_field_initialization: bool) -> None:
        super().__post_init__(direct_field_initialization)
        if direct_field_initialization is True:
            return

        resolved = AssetResolver().resolve_asset_to_class(self.identifier, FiatAsset)
        object.__setattr__(self, 'identifier', resolved.identifier)
        object.__setattr__(self, 'asset_type', resolved.asset_type)
        object.__setattr__(self, 'name', resolved.name)
        object.__setattr__(self, 'symbol', resolved.symbol)
        object.__setattr__(self, 'cryptocompare', resolved.cryptocompare)
        object.__setattr__(self, 'coingecko', resolved.coingecko)

    @classmethod
    def initialize(
            cls: type['FiatAsset'],
            identifier: str,
            name: str | None = None,
            symbol: str | None = None,
            coingecko: str | None = None,
            cryptocompare: str | None = '',
    ) -> 'FiatAsset':
        asset = FiatAsset(identifier=identifier, direct_field_initialization=True)
        object.__setattr__(asset, 'asset_type', AssetType.FIAT)
        object.__setattr__(asset, 'name', name)
        object.__setattr__(asset, 'symbol', symbol)
        object.__setattr__(asset, 'cryptocompare', cryptocompare)
        object.__setattr__(asset, 'coingecko', coingecko)
        return asset

    def get_asset_data(self) -> dict[str, Any]:
        """Returns asset data as a dictionary for this FiatAsset"""
        return {
            'identifier': self.identifier,
            'name': self.name,
            'symbol': self.symbol,
            'asset_type': self.asset_type,
            'started': None,
            'forked': None,
            'swapped_for': None,
            'address': None,
            'chain_id': None,
            'token_kind': None,
            'decimals': None,
            'cryptocompare': self.cryptocompare,
            'coingecko': self.coingecko,
            'protocol': None,
        }


@dataclass(init=True, repr=False, eq=False, order=False, unsafe_hash=False, frozen=True)
class CryptoAsset(AssetWithOracles):
    started: Timestamp | None = field(init=False)
    forked: Optional['CryptoAsset'] = field(init=False)
    swapped_for: Optional['CryptoAsset'] = field(init=False)

    def __post_init__(self, direct_field_initialization: bool) -> None:
        super().__post_init__(direct_field_initialization)
        if direct_field_initialization is True:
            return

        resolved = AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=CryptoAsset,
        )
        object.__setattr__(self, 'identifier', resolved.identifier)
        object.__setattr__(self, 'asset_type', resolved.asset_type)
        object.__setattr__(self, 'name', resolved.name)
        object.__setattr__(self, 'symbol', resolved.symbol)
        object.__setattr__(self, 'cryptocompare', resolved.cryptocompare)
        object.__setattr__(self, 'coingecko', resolved.coingecko)
        object.__setattr__(self, 'started', resolved.started)
        object.__setattr__(self, 'forked', resolved.forked)
        object.__setattr__(self, 'swapped_for', resolved.swapped_for)

    @classmethod
    def initialize(
            cls: type['CryptoAsset'],
            identifier: str,
            asset_type: AssetType,
            name: str | None = None,
            symbol: str | None = None,
            coingecko: str | None = None,
            cryptocompare: str | None = '',
            started: Timestamp | None = None,
            forked: Optional['CryptoAsset'] = None,
            swapped_for: Optional['CryptoAsset'] = None,
    ) -> 'CryptoAsset':
        asset = CryptoAsset(identifier=identifier, direct_field_initialization=True)
        object.__setattr__(asset, 'asset_type', asset_type)
        object.__setattr__(asset, 'name', name)
        object.__setattr__(asset, 'symbol', symbol)
        object.__setattr__(asset, 'cryptocompare', cryptocompare)
        object.__setattr__(asset, 'coingecko', coingecko)
        object.__setattr__(asset, 'started', started)
        object.__setattr__(asset, 'forked', forked)
        object.__setattr__(asset, 'swapped_for', swapped_for)
        return asset

    def to_dict(self) -> dict[str, Any]:
        forked, swapped_for = None, None
        if self.forked is not None:
            forked = self.forked.identifier
        if self.swapped_for is not None:
            swapped_for = self.swapped_for.identifier

        return super().to_dict() | {
            'name': self.name,
            'symbol': self.symbol,
            'asset_type': str(self.asset_type),
            'started': self.started,
            'forked': forked,
            'swapped_for': swapped_for,
            'cryptocompare': self.cryptocompare,
            'coingecko': self.coingecko,
        }

    def get_asset_data(self) -> dict[str, Any]:
        """Returns asset data as a dictionary for this CryptoAsset"""
        return {
            'identifier': self.identifier,
            'name': self.name,
            'symbol': self.symbol,
            'asset_type': self.asset_type,
            'started': self.started,
            'forked': self.forked.identifier if self.forked is not None else None,
            'swapped_for': self.swapped_for.identifier if self.swapped_for is not None else None,
            'address': None,
            'chain_id': None,
            'token_kind': None,
            'decimals': None,
            'cryptocompare': self.cryptocompare,
            'coingecko': self.coingecko,
            'protocol': None,
        }


class CustomAsset(AssetWithNameAndType):
    notes: str | None = field(init=False)
    custom_asset_type: str = field(init=False)

    @classmethod
    def initialize(
            cls: type['CustomAsset'],
            identifier: str,
            name: str,
            custom_asset_type: str,
            notes: str | None = None,
    ) -> 'CustomAsset':
        asset = CustomAsset(identifier=identifier)
        object.__setattr__(asset, 'asset_type', AssetType.CUSTOM_ASSET)
        object.__setattr__(asset, 'name', name)
        object.__setattr__(asset, 'custom_asset_type', custom_asset_type)
        object.__setattr__(asset, 'notes', notes)
        return asset

    @classmethod
    def deserialize_from_db(
            cls: type['CustomAsset'],
            entry: tuple[str, str, str, str | None],
    ) -> 'CustomAsset':
        """
        Takes a `custom_asset` entry from DB and turns it into a `CustomAsset` instance.
        May raise:
        - DeserializationError if the identifier is not a string
        """
        return cls.initialize(
            identifier=entry[0],
            name=entry[1],
            custom_asset_type=entry[2],
            notes=entry[3],
        )

    def serialize_for_db(self) -> tuple[str, str, str | None]:
        return (
            self.identifier,
            self.custom_asset_type,
            self.notes,
        )

    def get_asset_data(self) -> dict[str, Any]:
        """Returns asset data as a dictionary for this CustomAsset"""
        return {
            'identifier': self.identifier,
            'name': self.name,
            'symbol': '',  # Custom assets don't have symbols
            'asset_type': self.asset_type,
            'started': None,
            'forked': None,
            'swapped_for': None,
            'address': None,
            'chain_id': None,
            'token_kind': None,
            'decimals': None,
            'cryptocompare': None,
            'coingecko': None,
            'protocol': None,
        }

    def to_dict(self, export_with_type: bool = True) -> dict[str, Any]:
        result = super().to_dict() | {
            'identifier': self.identifier,
            'custom_asset_type': self.custom_asset_type,
            'notes': self.notes,
        }
        if export_with_type is False:
            result.pop('asset_type')

        return result


EthereumTokenDBTuple = tuple[
    str,                  # identifier
    str,                  # address
    str,                  # chain id
    str,                  # token type
    int | None,        # decimals
    str | None,        # name
    str | None,        # symbol
    int | None,        # started
    str | None,        # swapped_for
    str | None,        # coingecko
    str | None,        # cryptocompare
    str | None,        # protocol
]


@dataclass(init=True, repr=False, eq=False, order=False, unsafe_hash=False, frozen=True)
class EvmToken(CryptoAsset):
    evm_address: ChecksumEvmAddress = field(init=False)
    chain_id: ChainID = field(init=False)
    token_kind: EVM_TOKEN_KINDS = field(init=False)
    decimals: int | None = field(init=False)
    protocol: str | None = field(init=False)
    underlying_tokens: list[UnderlyingToken] = field(init=False)

    def __post_init__(self, direct_field_initialization: bool) -> None:
        super().__post_init__(direct_field_initialization)
        if direct_field_initialization is True:
            return

        resolved = AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=EvmToken,
        )
        object.__setattr__(self, 'asset_type', AssetType.EVM_TOKEN)
        object.__setattr__(self, 'evm_address', resolved.evm_address)
        object.__setattr__(self, 'chain_id', resolved.chain_id)
        object.__setattr__(self, 'token_kind', resolved.token_kind)
        object.__setattr__(self, 'decimals', resolved.decimals)
        object.__setattr__(self, 'protocol', resolved.protocol)
        object.__setattr__(self, 'underlying_tokens', resolved.underlying_tokens)

    @classmethod
    def initialize(  # type: ignore  # signature is incompatible with super type
            cls: type['EvmToken'],
            address: ChecksumEvmAddress,
            chain_id: ChainID,
            token_kind: EVM_TOKEN_KINDS,
            name: str | None = None,
            symbol: str | None = None,
            started: Timestamp | None = None,
            forked: CryptoAsset | None = None,
            swapped_for: CryptoAsset | None = None,
            coingecko: str | None = None,
            cryptocompare: str | None = '',
            decimals: int | None = None,
            protocol: str | None = None,
            underlying_tokens: list[UnderlyingToken] | None = None,
            collectible_id: str | None = None,
    ) -> 'EvmToken':
        identifier = evm_address_to_identifier(
            address=address,
            chain_id=chain_id,
            token_type=token_kind,
            collectible_id=collectible_id,
        )
        asset = EvmToken(identifier=identifier, direct_field_initialization=True)
        object.__setattr__(asset, 'asset_type', AssetType.EVM_TOKEN)
        object.__setattr__(asset, 'name', name)
        object.__setattr__(asset, 'symbol', symbol)
        object.__setattr__(asset, 'cryptocompare', cryptocompare)
        object.__setattr__(asset, 'coingecko', coingecko)
        object.__setattr__(asset, 'started', started)
        object.__setattr__(asset, 'forked', forked)
        object.__setattr__(asset, 'swapped_for', swapped_for)
        object.__setattr__(asset, 'evm_address', address)
        object.__setattr__(asset, 'chain_id', chain_id)
        object.__setattr__(asset, 'token_kind', token_kind)
        object.__setattr__(asset, 'decimals', decimals)
        object.__setattr__(asset, 'protocol', protocol)
        object.__setattr__(asset, 'underlying_tokens', underlying_tokens)
        return asset

    @classmethod
    def deserialize_from_db(
            cls: type['EvmToken'],
            entry: EthereumTokenDBTuple,
            underlying_tokens: list[UnderlyingToken] | None = None,
    ) -> 'EvmToken':
        """May raise UnknownAsset if the swapped for asset can't be recognized
        That error would be bad because it would mean somehow an unknown id made it into the DB
        """
        swapped_for = CryptoAsset(entry[8]) if entry[8] is not None else None
        return EvmToken.initialize(
            address=entry[1],  # type: ignore
            chain_id=ChainID(entry[2]),
            token_kind=TokenKind.deserialize_evm_from_db(entry[3]),
            decimals=entry[4],
            name=entry[5],
            symbol=entry[6] if entry[6] is not None else '',
            started=Timestamp(entry[7]),  # type: ignore
            swapped_for=swapped_for,
            coingecko=entry[9],
            cryptocompare=entry[10],
            protocol=entry[11],
            underlying_tokens=underlying_tokens,
        )

    def to_dict(self) -> dict[str, Any]:
        underlying_tokens = [x.serialize() for x in self.underlying_tokens] if self.underlying_tokens is not None else None  # noqa: E501
        return super().to_dict() | {
            'address': self.evm_address,
            'evm_chain': self.chain_id.to_name(),
            'token_kind': self.token_kind.serialize(),
            'decimals': self.decimals,
            'protocol': self.protocol,
            'underlying_tokens': underlying_tokens,
        }

    def get_decimals(self) -> int:
        return 18 if self.decimals is None else self.decimals

    def is_liability(self) -> bool:
        """Returns True if the token is a liability token, False if it's an asset token"""
        return (
            self.protocol in (CPT_AAVE_V3, CPT_SPARK) and
            DEBT_TOKEN_SYMBOL_REGEX.match(self.symbol) is not None
        )

    def get_asset_data(self) -> dict[str, Any]:
        """Returns asset data as a dictionary for this EvmToken"""
        return {
            'identifier': self.identifier,
            'name': self.name,
            'symbol': self.symbol,
            'asset_type': self.asset_type,
            'started': self.started,
            'forked': self.forked.identifier if self.forked is not None else None,
            'swapped_for': self.swapped_for.identifier if self.swapped_for is not None else None,
            'address': self.evm_address,
            'chain_id': self.chain_id,
            'token_kind': self.token_kind,
            'decimals': self.decimals,
            'cryptocompare': self.cryptocompare,
            'coingecko': self.coingecko,
            'protocol': self.protocol,
        }


class Nft(EvmToken):

    def __post_init__(self, direct_field_initialization: bool) -> None:
        if direct_field_initialization is True:
            return

        identifier_parts = self.identifier[len(NFT_DIRECTIVE):].split('_')
        if len(identifier_parts) == 0 or len(identifier_parts[0]) == 0:
            raise UnknownAsset(self.identifier)
        address = to_checksum_address(identifier_parts[0])
        object.__setattr__(self, 'asset_type', AssetType.EVM_TOKEN)
        object.__setattr__(self, 'name', f'nft with id {self.identifier}')
        object.__setattr__(self, 'symbol', self.identifier[len(NFT_DIRECTIVE):])
        object.__setattr__(self, 'cryptocompare', None)
        object.__setattr__(self, 'coingecko', None)
        object.__setattr__(self, 'started', None)
        object.__setattr__(self, 'forked', None)
        object.__setattr__(self, 'swapped_for', None)
        object.__setattr__(self, 'evm_address', address)
        object.__setattr__(self, 'chain_id', ChainID.ETHEREUM)
        object.__setattr__(self, 'token_kind', TokenKind.ERC721)
        object.__setattr__(self, 'decimals', 0)
        object.__setattr__(self, 'protocol', None)
        object.__setattr__(self, 'underlying_tokens', None)

    @classmethod
    def initialize(  # type: ignore  # signature is incompatible with super type
            cls: type['EvmToken'],
            identifier: str,
            chain_id: ChainID,
            name: str | None = None,
            symbol: str | None = None,
    ) -> 'Nft':
        # TODO: This needs to change once we correctly track NFTs
        asset = Nft(identifier=identifier, direct_field_initialization=True)
        identifier_parts = identifier[len(NFT_DIRECTIVE):].split('_')
        if len(identifier_parts) == 0 or len(identifier_parts[0]) == 0:
            raise UnknownAsset(identifier)
        address = identifier_parts[0]

        nft_name = f'nft with id {identifier}' if name is None else name
        nft_symbol = identifier[len(NFT_DIRECTIVE):] if symbol is None else symbol
        object.__setattr__(asset, 'asset_type', AssetType.EVM_TOKEN)
        object.__setattr__(asset, 'name', nft_name)
        object.__setattr__(asset, 'symbol', nft_symbol)
        object.__setattr__(asset, 'cryptocompare', None)
        object.__setattr__(asset, 'coingecko', None)
        object.__setattr__(asset, 'started', None)
        object.__setattr__(asset, 'forked', None)
        object.__setattr__(asset, 'swapped_for', None)
        object.__setattr__(asset, 'evm_address', address)
        object.__setattr__(asset, 'chain_id', chain_id)
        object.__setattr__(asset, 'token_kind', TokenKind.ERC721)
        object.__setattr__(asset, 'decimals', 0)
        object.__setattr__(asset, 'protocol', None)
        object.__setattr__(asset, 'underlying_tokens', None)
        return asset
