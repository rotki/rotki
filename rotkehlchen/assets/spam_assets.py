import logging
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Set

import requests
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.utils import get_or_create_ethereum_token
from rotkehlchen.chain.ethereum.types import string_to_ethereum_address
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SPAM_PROTOCOL

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


KNOWN_ETH_SPAM_TOKENS = [
    # khex.net and said to be spam by etherscan
    string_to_ethereum_address('0x4AF9ab04615cB91e2EE8cbEDb43fb52eD205041B'),
    # erc token, seems to be a spam token
    string_to_ethereum_address('0x78d9A9355a7823887868492c47368956ea473618'),
    # yLiquidate (YQI) seems to be a scam
    string_to_ethereum_address('0x3d3d5cCE38afb7a379B2C3175Ee56e2dC72CD7C8'),
    # Old kick token
    string_to_ethereum_address('0xC12D1c73eE7DC3615BA4e37E4ABFdbDDFA38907E'),
    # kick token
    string_to_ethereum_address('0x824a50dF33AC1B41Afc52f4194E2e8356C17C3aC'),
    # Fake gear token
    string_to_ethereum_address('0x6D38b496dCc9664C6908D8Afba6ff926887Fc359'),
    # EthTrader Contribution (CONTRIB) few txs and all failed
    string_to_ethereum_address('0xbe1fffB262a2C3e65c5eb90f93caf4eDC7d28c8d'),
    # a68.net pishing/hack
    string_to_ethereum_address('0x1412ECa9dc7daEf60451e3155bB8Dbf9DA349933'),
    # akswap.io
    string_to_ethereum_address('0x82dfDB2ec1aa6003Ed4aCBa663403D7c2127Ff67'),
    # up1 pishing token
    string_to_ethereum_address('0xF9d25EB4C75ed744596392cf89074aFaA43614a8'),
    # deapy.org scam token
    string_to_ethereum_address('0x01454cdC3FAb2a026CC7d1CB2aEa9B909D5bA0EE'),
]


def query_token_spam_list(db: 'DBHandler') -> Set[EthereumToken]:
    """Generate a set of assets that can be ignored combining information of cryptoscamdb
    and the list of spam assets KNOWN_ETH_SPAM_TOKENS. This function also makes sure to get the
    bad assets in the list of cryptoscamdb and ensures that they exists in the globaldb before
    trying to add them.

    TODO
    This function tries to add as assets to the globaldb the tokens listed in
    KNOWN_ETH_SPAM_TOKENS and not the ones coming from cryptoscamdb. The reason is that until the
    v2 of the API the response contains both spam addresses and tokens and there is no way to know
    if the address is for a contract or not. Checking if the address is a contract takes too much
    time. When V2 gets released this can be fixed.
    May raise:
    - RemoteError
    """
    try:
        response = requests.get(
            url='https://api.cryptoscamdb.org/v1/addresses',
            timeout=DEFAULT_TIMEOUT_TUPLE,
        )
        data = response.json()
        success, tokens_info = data['success'], data['result']
    except requests.exceptions.RequestException as e:
        raise RemoteError(f'Failed to retrieve information from cryptoscamdb. {str(e)}') from e
    except (DeserializationError, JSONDecodeError) as e:
        raise RemoteError(f'Failed to deserialize data from cryptoscamdb. {str(e)}') from e
    except KeyError as e:
        raise RemoteError(
            f'Response from cryptoscamdb doesn\'t contain expected key. {str(e)}',
        ) from e

    if success is False:
        log.error(f'Failed to deserialize data from cryptoscamdb. {data}')
        raise RemoteError(
            'Failed to deserialize data from cryptoscamdb. Check the logs '
            'to get more information',
        )

    tokens_to_ignore = set()
    for token_addr, token_data in tokens_info.items():
        if not token_addr.startswith('0x') or token_data[0]['type'] != 'scam':
            continue
        try:
            checksumed_address = to_checksum_address(token_addr)
        except ValueError as e:
            log.debug(f'Failed to read address from cryptoscamdb. {str(e)}')
            continue
        try:
            token = EthereumToken(checksumed_address)
        except UnknownAsset:
            continue
        if token is not None:
            tokens_to_ignore.add(token)

    # Try to add custom list
    for token_address in KNOWN_ETH_SPAM_TOKENS:
        try:
            own_token = get_or_create_ethereum_token(
                userdb=db,
                ethereum_address=token_address,
                protocol=SPAM_PROTOCOL,
                form_with_incomplete_data=True,
                decimals=18,
                name='Autodetected spam token',
            )
        except (RemoteError, NotERC20Conformant) as e:
            log.debug(f'Skipping {checksumed_address} due to {str(e)}')
            continue
        if own_token is not None:
            tokens_to_ignore.add(own_token)

    return tokens_to_ignore


def update_spam_assets(db: 'DBHandler') -> int:
    """
    Update the list of ignored assets using query_token_spam_list and avoiding
    the addition of duplicates. It returns the amount of assets that were added
    to the ignore list
    """
    ignored_assets = {asset.identifier for asset in db.get_ignored_assets()}
    spam_tokens = query_token_spam_list(db)
    assets_added = 0
    for token in spam_tokens:
        if token.identifier in ignored_assets:
            continue
        db.add_to_ignored_assets(token)
        assets_added += 1
    return assets_added
