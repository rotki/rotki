import logging
from typing import Optional, Union

from rotkehlchen.errors import UnknownAsset
from rotkehlchen.typing import ChecksumEthAddress

from .asset import EthereumToken
from .unknown_asset import UnknownEthereumToken


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
    except UnknownAsset:
        is_unknown_asset = True
    else:
        if ethereum_token.ethereum_address != ethereum_address:
            is_unknown_asset = True

    if is_unknown_asset:
        log.error(
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
