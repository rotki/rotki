import logging
from typing import TYPE_CHECKING, List, Optional

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.typing import ChecksumEthAddress

from .asset import Asset, EthereumToken, UnderlyingToken
from .typing import AssetType

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

log = logging.getLogger(__name__)


def add_ethereum_token_to_db(token_data: EthereumToken) -> EthereumToken:
    """Adds an ethereum token to the DB and returns it

    May raise:
    - InputError if token already exists in the DB
    """
    globaldb = GlobalDBHandler()
    globaldb.add_asset(
        asset_id=token_data.identifier,
        asset_type=AssetType.ETHEREUM_TOKEN,
        data=token_data,
    )
    # This can, but should not raise UnknownAsset, DeserializationError
    return EthereumToken(token_data.ethereum_address, form_with_incomplete_data=True)


def get_or_create_ethereum_token(
        userdb: 'DBHandler',
        symbol: str,
        ethereum_address: ChecksumEthAddress,
        name: Optional[str] = None,
        decimals: Optional[int] = None,
        protocol: Optional[str] = None,
        underlying_tokens: Optional[List[UnderlyingToken]] = None,
) -> EthereumToken:
    """Given a token symbol and address return the <EthereumToken>

    If the token exists in the GlobalDB it's returned. If not it's created and added.
    Note: if the token already exists but the other arguments don't match the
    existing token will still be silently returned
    """
    try:
        ethereum_token = EthereumToken(ethereum_address)
    except (UnknownAsset, DeserializationError):
        log.info(
            f'Encountered unknown asset {symbol} with address '
            f'{ethereum_address}. Adding it to the global DB',
        )
        token_data = EthereumToken.initialize(
            address=ethereum_address,
            name=name,
            decimals=decimals,
            symbol=symbol,
            protocol=protocol,
            underlying_tokens=underlying_tokens,
        )
        # This can but should not raise InputError since it should not already exist
        ethereum_token = add_ethereum_token_to_db(token_data)
        userdb.add_asset_identifiers([ethereum_token.identifier])

    return ethereum_token


def get_asset_by_symbol(symbol: str, asset_type: Optional[AssetType] = None) -> Optional[Asset]:
    """Gets an asset by symbol from the DB.

    If no asset with that symbol or multiple assets with the same
    symbol are found returns None
    """
    if symbol == 'ETH':
        return A_ETH  # ETH can be ETH and ETH2 in the DB

    assets_data = GlobalDBHandler().get_assets_with_symbol(symbol, asset_type)
    if len(assets_data) != 1:
        return None

    return Asset(assets_data[0].identifier)


def symbol_to_asset_or_token(symbol: str) -> Asset:
    """Tries to turn the given symbol to an asset or an ethereum Token

    May raise:
    - UnknownAsset if an asset can't be found by the symbol or if
    more than one tokens match this symbol
    """
    try:
        asset = Asset(symbol)
    except UnknownAsset:
        # Let's search by symbol if a single asset matches
        maybe_asset = get_asset_by_symbol(symbol)
        if maybe_asset is None:
            raise
        asset = maybe_asset

    return asset


def symbol_to_ethereum_token(symbol: str) -> EthereumToken:
    """Tries to turn the given symbol to an ethereum token

    May raise:
    - UnknownAsset if an ethereum token can't be found by the symbol or if
    more than one tokens match this symbol
    """
    maybe_asset = get_asset_by_symbol(symbol, asset_type=AssetType.ETHEREUM_TOKEN)
    if maybe_asset is None:
        raise UnknownAsset(symbol)

    # ignore type here since the identifier has to match an ethereum token at this point
    return EthereumToken.from_asset(maybe_asset)  # type: ignore
