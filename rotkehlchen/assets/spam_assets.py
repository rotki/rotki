import logging
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Set

import requests
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


KNOWN_ETH_SPAM_TOKENS = [
    # khex.net and said to be spam by etherscan
    strethaddress_to_identifier('0x4AF9ab04615cB91e2EE8cbEDb43fb52eD205041B'),
    # erc token, seems to be a spam token
    strethaddress_to_identifier('0x78d9A9355a7823887868492c47368956ea473618'),
    # yLiquidate (YQI) seems to be a scam
    strethaddress_to_identifier('0x3d3d5cCE38afb7a379B2C3175Ee56e2dC72CD7C8'),
    # Old kick token
    strethaddress_to_identifier('0xC12D1c73eE7DC3615BA4e37E4ABFdbDDFA38907E'),
    # kick token
    strethaddress_to_identifier('0x824a50dF33AC1B41Afc52f4194E2e8356C17C3aC'),
    # Fake gear token
    strethaddress_to_identifier('0x6D38b496dCc9664C6908D8Afba6ff926887Fc359'),
    # EthTrader Contribution (CONTRIB) few txs and all failed
    strethaddress_to_identifier('0xbe1fffB262a2C3e65c5eb90f93caf4eDC7d28c8d'),
    # a68.net pishing/hack
    strethaddress_to_identifier('0x1412ECa9dc7daEf60451e3155bB8Dbf9DA349933'),
    # akswap.io
    strethaddress_to_identifier('0x82dfDB2ec1aa6003Ed4aCBa663403D7c2127Ff67'),
    # up1 pishing token
    strethaddress_to_identifier('0xF9d25EB4C75ed744596392cf89074aFaA43614a8'),
    # deapy.org scam token
    strethaddress_to_identifier('0x01454cdC3FAb2a026CC7d1CB2aEa9B909D5bA0EE'),
]


def query_token_spam_list() -> Set[EthereumToken]:
    try:
        response = requests.get(
            url='https://api.cryptoscamdb.org/v1/addresses',
            timeout=DEFAULT_TIMEOUT_TUPLE,
        )
        data = response.json()
        success, tokens_info = data['success'], data['result']
    except requests.exceptions.RequestException as e:
        log.debug(f'Failed to retrieve information from cryptoscamdb. {str(e)}')
    except (DeserializationError, JSONDecodeError) as e:
        log.debug(f'Failed to deserialize data from cryptoscamdb. {str(e)}')
    except KeyError as e:
        log.debug(f'Response from cryptoscamdb doesn\'t contain expected key. {str(e)}')

    if success is False:
        log.error(f'Failed to retrieve cryptoscamdb information {data}')

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
    for token_identifier in KNOWN_ETH_SPAM_TOKENS:
        try:
            own_token = EthereumToken.from_identifier(token_identifier)
        except UnknownAsset:
            continue
        if own_token is not None:
            tokens_to_ignore.add(own_token)

    return tokens_to_ignore


def update_spam_assets(db: 'DBHandler') -> int:
    ignored_assets = {asset.identifier for asset in db.get_ignored_assets()}
    spam_tokens = query_token_spam_list()
    assets_added = 0
    for token in spam_tokens:
        if token.identifier in ignored_assets:
            continue
        db.add_to_ignored_assets(token)
        assets_added += 1
    return assets_added
