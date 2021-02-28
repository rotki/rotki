import logging
from typing import Any, Dict, Optional, Union, overload

from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.typing import ChecksumEthAddress

from .asset import EthereumToken
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
    is_unknown_asset = False

    try:
        ethereum_token = EthereumToken(symbol)
    except (UnknownAsset, DeserializationError):
        is_unknown_asset = True
    else:
        if ethereum_token.ethereum_address != ethereum_address:
            is_unknown_asset = True

    if is_unknown_asset:
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


@overload  # noqa: F811
def serialize_ethereum_token(
        ethereum_token: EthereumToken,
        unknown_ethereum_token_keys: SerializeAsDictKeys = UNKNOWN_TOKEN_KEYS,
) -> str:
    ...


@overload  # noqa: F811
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
