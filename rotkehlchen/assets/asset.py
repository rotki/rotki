import abc
import logging
from dataclasses import InitVar, dataclass, field
from functools import total_ordering
from typing import Any, NamedTuple, Optional, Union

from rotkehlchen.assets.exchanges_mappings.bittrex import WORLD_TO_BITTREX
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.constants.resolver import ChainID, evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset, WrongAssetType
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind, Timestamp

from .types import ASSETS_WITH_NO_CRYPTO_ORACLES, AssetType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

UnderlyingTokenDBTuple = tuple[str, str, str]


class UnderlyingToken(NamedTuple):
    """Represents an underlying token of a token

    Is used for pool tokens, tokensets etc.
    """
    address: ChecksumEvmAddress
    token_kind: EvmTokenKind
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
            token_kind=EvmTokenKind.deserialize_from_db(entry[1]),
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

    def __post_init__(self, direct_field_initialization: bool) -> None:  # pylint: disable=unused-argument  # noqa: E501
        if not isinstance(self.identifier, str):
            raise DeserializationError(
                'Tried to initialize an asset out of a non-string identifier',
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            'identifier': self.identifier,
        }

    def serialize(self) -> str:
        return self.identifier

    def check_existence(self) -> 'Asset':
        """
        If this asset exists, returns the instance. If it doesn't, throws an error.
        May raise:
        - UnknownAsset
        """
        # We don't need asset type, but using `get_asset_type` since it has all the functionality
        # that we need here
        AssetResolver().get_asset_type(self.identifier)
        return self

    def is_nft(self) -> bool:
        return self.identifier.startswith(NFT_DIRECTIVE)

    def is_fiat(self) -> bool:
        return AssetResolver().get_asset_type(self.identifier) == AssetType.FIAT

    def is_asset_with_oracles(self) -> bool:
        return AssetResolver().get_asset_type(self.identifier) not in ASSETS_WITH_NO_CRYPTO_ORACLES

    def is_evm_token(self) -> bool:
        return AssetResolver().get_asset_type(self.identifier) == AssetType.EVM_TOKEN

    def resolve(self) -> 'Asset':
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

        return AssetResolver().resolve_asset(identifier=self.identifier)

    def resolve_to_asset_with_name_and_type(self) -> 'AssetWithNameAndType':
        return AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=AssetWithNameAndType,
        )

    def resolve_to_asset_with_symbol(self) -> 'AssetWithSymbol':
        return AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=AssetWithSymbol,
        )

    def resolve_to_crypto_asset(self) -> 'CryptoAsset':
        return AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=CryptoAsset,
        )

    def resolve_to_evm_token(self) -> 'EvmToken':
        return AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=EvmToken,
        )

    def resolve_to_asset_with_oracles(self) -> 'AssetWithOracles':
        return AssetResolver().resolve_asset_to_class(
            identifier=self.identifier,
            expected_type=AssetWithOracles,
        )

    def resolve_to_fiat_asset(self) -> 'FiatAsset':
        return AssetResolver().resolve_asset_to_class(
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
            return with_symbol.symbol
        except WrongAssetType:
            with_name = self.resolve_to_asset_with_name_and_type()
            return with_name.name

    def __hash__(self) -> int:
        return hash(self.identifier)

    def __repr__(self) -> str:
        return f'<Asset identifier:{self.identifier}>'

    def __eq__(self, other: Any) -> bool:
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
class AssetWithNameAndType(Asset, metaclass=abc.ABCMeta):
    asset_type: AssetType = field(init=False)
    name: str = field(init=False)

    def to_dict(self) -> dict[str, Any]:
        return super().to_dict() | {
            'name': self.name,
            'asset_type': str(self.asset_type),
        }

    def __repr__(self) -> str:
        return f'<Asset identifier:{self.identifier} name:{self.name}>'

    def __str__(self) -> str:
        return f'{self.identifier}({self.name})'


class AssetWithSymbol(AssetWithNameAndType, metaclass=abc.ABCMeta):
    symbol: str = field(init=False)

    def to_dict(self) -> dict[str, Any]:
        return super().to_dict() | {'symbol': self.symbol}

    def __repr__(self) -> str:
        return f'<Asset identifier:{self.identifier} name:{self.name} symbol:{self.symbol}>'


class AssetWithOracles(AssetWithSymbol, metaclass=abc.ABCMeta):
    # None means no special mapping. '' means not supported
    cryptocompare: Optional[str] = field(init=False)
    coingecko: Optional[str] = field(init=False)

    def to_cryptocompare(self) -> str:
        """
        Returns the symbol with which to query cryptocompare for the asset
        May raise:
            - UnsupportedAsset if the asset is not supported by cryptocompare
        """
        cryptocompare_str = self.symbol if self.cryptocompare is None else self.cryptocompare
        # There is an asset which should not be queried in cryptocompare
        if cryptocompare_str is None or cryptocompare_str == '':
            raise UnsupportedAsset(f'{self.identifier} is not supported by cryptocompare')

        # Seems cryptocompare capitalizes everything. So cDAI -> CDAI
        return cryptocompare_str.upper()  # pylint: disable=no-member

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

    def has_oracle(self) -> bool:
        return self.has_coingecko() or self.cryptocompare is not None

    def to_bittrex(self) -> str:
        return WORLD_TO_BITTREX.get(self.identifier, self.identifier)

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
            name: Optional[str] = None,
            symbol: Optional[str] = None,
            coingecko: Optional[str] = None,
            cryptocompare: Optional[str] = '',
    ) -> 'FiatAsset':
        asset = FiatAsset(identifier=identifier, direct_field_initialization=True)
        object.__setattr__(asset, 'asset_type', AssetType.FIAT)
        object.__setattr__(asset, 'name', name)
        object.__setattr__(asset, 'symbol', symbol)
        object.__setattr__(asset, 'cryptocompare', cryptocompare)
        object.__setattr__(asset, 'coingecko', coingecko)
        return asset


@dataclass(init=True, repr=False, eq=False, order=False, unsafe_hash=False, frozen=True)
class CryptoAsset(AssetWithOracles):
    started: Optional[Timestamp] = field(init=False)
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
            name: Optional[str] = None,
            symbol: Optional[str] = None,
            coingecko: Optional[str] = None,
            cryptocompare: Optional[str] = '',
            started: Optional[Timestamp] = None,
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


class CustomAsset(AssetWithNameAndType):
    notes: Optional[str] = field(init=False)
    custom_asset_type: str = field(init=False)

    @classmethod
    def initialize(
        cls: type['CustomAsset'],
        identifier: str,
        name: str,
        custom_asset_type: str,
        notes: Optional[str] = None,
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
            entry: tuple[str, str, str, Optional[str]],
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

    def serialize_for_db(self) -> tuple[str, str, Optional[str]]:
        return (
            self.identifier,
            self.custom_asset_type,
            self.notes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            'identifier': self.identifier,
            'name': self.name,
            'custom_asset_type': self.custom_asset_type,
            'notes': self.notes,
        }


EthereumTokenDBTuple = tuple[
    str,                  # identifier
    str,                  # address
    str,                  # chain id
    str,                  # token type
    Optional[int],        # decimals
    Optional[str],        # name
    Optional[str],        # symbol
    Optional[int],        # started
    Optional[str],        # swapped_for
    Optional[str],        # coingecko
    Optional[str],        # cryptocompare
    Optional[str],        # protocol
]


@dataclass(init=True, repr=False, eq=False, order=False, unsafe_hash=False, frozen=True)
class EvmToken(CryptoAsset):
    evm_address: ChecksumEvmAddress = field(init=False)
    chain_id: ChainID = field(init=False)
    token_kind: EvmTokenKind = field(init=False)
    decimals: int = field(init=False)
    protocol: str = field(init=False)
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
            token_kind: EvmTokenKind,
            name: Optional[str] = None,
            symbol: Optional[str] = None,
            started: Optional[Timestamp] = None,
            forked: Optional[CryptoAsset] = None,
            swapped_for: Optional[CryptoAsset] = None,
            coingecko: Optional[str] = None,
            cryptocompare: Optional[str] = '',
            decimals: Optional[int] = None,
            protocol: Optional[str] = None,
            underlying_tokens: Optional[list[UnderlyingToken]] = None,
    ) -> 'EvmToken':
        identifier = evm_address_to_identifier(
            address=address,
            chain_id=chain_id,
            token_type=token_kind,
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
            underlying_tokens: Optional[list[UnderlyingToken]] = None,
    ) -> 'EvmToken':
        """May raise UnknownAsset if the swapped for asset can't be recognized
        That error would be bad because it would mean somehow an unknown id made it into the DB
        """
        swapped_for = CryptoAsset(entry[8]) if entry[8] is not None else None
        return EvmToken.initialize(
            address=entry[1],  # type: ignore
            chain_id=ChainID(entry[2]),
            token_kind=EvmTokenKind.deserialize_from_db(entry[3]),
            decimals=entry[4],
            name=entry[5],
            symbol=entry[6],
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


class Nft(EvmToken):

    def __post_init__(self, direct_field_initialization: bool) -> None:
        if direct_field_initialization is True:
            return

        identifier_parts = self.identifier[len(NFT_DIRECTIVE):].split('_')
        if len(identifier_parts) == 0 or len(identifier_parts[0]) == 0:
            raise UnknownAsset(self.identifier)
        address = identifier_parts[0]
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
        object.__setattr__(self, 'token_kind', EvmTokenKind.ERC721)
        object.__setattr__(self, 'decimals', 0)
        object.__setattr__(self, 'protocol', None)
        object.__setattr__(self, 'underlying_tokens', None)

    @classmethod
    def initialize(  # type: ignore  # signature is incompatible with super type
            cls: type['EvmToken'],
            identifier: str,
            chain_id: ChainID,
            name: Optional[str] = None,
            symbol: Optional[str] = None,
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
        object.__setattr__(asset, 'token_kind', EvmTokenKind.ERC721)
        object.__setattr__(asset, 'decimals', 0)
        object.__setattr__(asset, 'protocol', None)
        object.__setattr__(asset, 'underlying_tokens', None)
        return asset
