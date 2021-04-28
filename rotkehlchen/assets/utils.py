import logging
from typing import Any, Dict, Optional, Union, overload

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.typing import ChecksumEthAddress

from .asset import Asset, EthereumToken
from .typing import AssetType
from .unknown_asset import UNKNOWN_TOKEN_KEYS, SerializeAsDictKeys, UnknownEthereumToken

log = logging.getLogger(__name__)


def get_ethereum_token(
        symbol: str,
        ethereum_address: ChecksumEthAddress,
        name: Optional[str] = None,
        decimals: Optional[int] = None,
) -> Union[EthereumToken, UnknownEthereumToken]:
    """Given a token symbol and address return the <EthereumToken>, otherwise
    an <UnknownEthereumToken>.
    """
    ethereum_token: Union[EthereumToken, UnknownEthereumToken]
    try:
        ethereum_token = EthereumToken(ethereum_address)
    except (UnknownAsset, DeserializationError):
        log.warning(
            f'Encountered unknown asset {symbol} with address '
            f'{ethereum_address}. Instantiating UnknownEthereumToken',
        )
        ethereum_token = UnknownEthereumToken(
            ethereum_address=ethereum_address,
            symbol=symbol,
            name=name,
            decimals=decimals,
        )

    return ethereum_token


@overload
def serialize_ethereum_token(
        ethereum_token: EthereumToken,
        unknown_ethereum_token_keys: SerializeAsDictKeys = UNKNOWN_TOKEN_KEYS,
) -> str:
    ...


@overload
def serialize_ethereum_token(
        ethereum_token: UnknownEthereumToken,
        unknown_ethereum_token_keys: SerializeAsDictKeys = UNKNOWN_TOKEN_KEYS,
) -> Dict[str, Any]:
    ...


def serialize_ethereum_token(
        ethereum_token: Union[EthereumToken, UnknownEthereumToken],
        unknown_ethereum_token_keys: SerializeAsDictKeys = UNKNOWN_TOKEN_KEYS,
) -> Union[str, Dict[str, Any]]:
    if isinstance(ethereum_token, EthereumToken):
        return ethereum_token.serialize()

    if isinstance(ethereum_token, UnknownEthereumToken):
        return ethereum_token.serialize_as_dict(keys=unknown_ethereum_token_keys)

    raise AssertionError(f'Unexpected ethereum token type: {type(ethereum_token)}')


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
        # may be an ethereum token so let's search by symbol
        maybe_asset = get_asset_by_symbol(symbol, asset_type=AssetType.ETHEREUM_TOKEN)
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
