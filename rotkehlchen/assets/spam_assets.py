import logging
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, Set

import requests
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SPAM_PROTOCOL, ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


MISSING_NAME_SPAM_TOKEN = 'Autodetected spam token'
MISSING_SYMBOL_SPAM_TOKEN = 'SPAM-TOKEN'

KNOWN_ETH_SPAM_TOKENS: Dict[ChecksumEvmAddress, Dict[str, Any]] = {
    # khex.net and said to be spam by etherscan
    string_to_evm_address('0x4AF9ab04615cB91e2EE8cbEDb43fb52eD205041B'): {
        'name': MISSING_NAME_SPAM_TOKEN,
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    # yLiquidate (YQI) seems to be a scam
    string_to_evm_address('0x3d3d5cCE38afb7a379B2C3175Ee56e2dC72CD7C8'): {
        'name': 'yLiquidate',
        'symbol': 'YQI',
        'decimals': 18,
    },
    # Old kick token
    string_to_evm_address('0xC12D1c73eE7DC3615BA4e37E4ABFdbDDFA38907E'): {
        'name': 'KICK TOKEN OLD',
        'symbol': 'KICK',
        'decimals': 18,
    },
    # kick token. Only can be withdrawn from their exchange
    string_to_evm_address('0x824a50dF33AC1B41Afc52f4194E2e8356C17C3aC'): {
        'name': 'KICK TOKEN',
        'symbol': 'KICK',
        'decimals': 18,
    },
    # Fake gear token warned by etherscan
    string_to_evm_address('0x6D38b496dCc9664C6908D8Afba6ff926887Fc359'): {
        'name': 'FAKE gear token',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    # EthTrader Contribution (CONTRIB) few txs and all failed
    string_to_evm_address('0xbe1fffB262a2C3e65c5eb90f93caf4eDC7d28c8d'): {
        'name': 'EthTrader Contribution',
        'symbol': 'CONTRIB',
        'decimals': 18,
    },
    string_to_evm_address('0x1412ECa9dc7daEf60451e3155bB8Dbf9DA349933'): {
        'name': 'a68.net',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    string_to_evm_address('0x82dfDB2ec1aa6003Ed4aCBa663403D7c2127Ff67'): {
        'name': 'akswap.io',
        'symbol': 'akswap.io',
        'decimals': 18,
    },
    string_to_evm_address('0x43661F4b1c67dd6c1e48C6Faf2887b22AeE3dDf5'): {
        'name': 'akswap.io',
        'symbol': 'akswap.io',
        'decimals': 18,
    },
    string_to_evm_address('0xF9d25EB4C75ed744596392cf89074aFaA43614a8'): {
        'name': 'UP1.org',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    string_to_evm_address('0x01454cdC3FAb2a026CC7d1CB2aEa9B909D5bA0EE'): {
        'name': 'deApy.org',
        'symbol': 'deApy.org',
        'decimals': 18,
    },
    string_to_evm_address('0x73885eb0dA4ba8B061acF1bfC5eA7073B07ccEA2'): {
        'name': 'Adidas fake token',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    string_to_evm_address('0xc85E0474068dbA5B49450c26879541EE6Cc94554'): {
        'name': 'KyDy.org',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    string_to_evm_address('0x1412ECa9dc7daEf60451e3155bB8Dbf9DA349933'): {
        'name': 'A68.net',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    # Apple spam/scam token
    string_to_evm_address('0x3c4f8Fe3Cf50eCA5439F8D4DE5BDf40Ae71860Ae'): {
        'name': 'Apple 29',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    # Blizzard spam/scam token
    string_to_evm_address('0xbb97a6449A6f5C53b7e696c8B5b6E6A53CF20143'): {
        'name': 'Activision Blizzard DAO',
        'symbol': 'BLIZZARD',
        'decimals': 18,
    },
    # Audi spam/scam token
    string_to_evm_address('0x9b9090DfA2cEbBef592144EE01Fe508f0c817B3A'): {
        'name': 'Audi Metaverse',
        'symbol': 'Audi',
        'decimals': 18,
    },
    # LunaV2.io (Luna Token)
    string_to_evm_address('0xAF0b2fBeDd5d1Fda457580FB3DAbAD1F5C8bBC36'): {
        'name': 'LunaV2.io',
        'symbol': 'Luna Token',
        'decimals': 18,
    },
    string_to_evm_address('0x3baB61Ad5D103Bb5b203C9092Eb3a5e11677a5D0'): {
        'name': 'ETH2Dao.net',
        'symbol': 'ETH2DAO.net',
        'decimals': 18,
    },
    string_to_evm_address('0x622651529Bda465277Cb890EF9176C442f42B338'): {
        'name': 'abekky.com',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    string_to_evm_address('0xED123a93aB410deD50D917EDfE256D45281B95D5'): {
        'name': 'SPAM TOKEN',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 18,
    },
    string_to_evm_address('0xb1A5FEcEBbfB02F6F44d69a4b7f096Af552C486B'): {
        'name': '(lidosr.xyz)',
        'symbol': MISSING_SYMBOL_SPAM_TOKEN,
        'decimals': 6,
    },
    string_to_evm_address('0x6D9541ba0f1039d0f8636b4f39D20A8a7464f357'): {
        'name': 'mdai.io',
        'symbol': 'mdai.io',
        'decimals': 18,
    },
    string_to_evm_address('0x17a10104CBC1eD155D083eaD9FCF5C3440bb50e8'): {
        'name': '$ USDCNotice.com',
        'symbol': '$ USDCNotice.com <- Visit to secure your wallet!',
        'decimals': 18,
    },
    string_to_evm_address('0x219B9040eB7D8d8c2E8E84B87CE9ac1C83071980'): {
        'name': 'Huobi Airdrop HuobiAirdrop.com',
        'symbol': 'HuobiAirdrop.com',
        'decimals': 18,
    },
    string_to_evm_address('0x3b0811f422cF7e9A46e7Ce22B1425A57949b5360'): {
        'name': '(sodefi.tech)',
        'symbol': '[sodefi.tech] Visit and claim rewards',
        'decimals': 6,
    },
    string_to_evm_address('0x471c3A7f132bc94938516CB2Bf6f02C7521D2797'): {
        'name': 'LUNA 2.0 (lunav2.io)',
        'symbol': 'LUNA 2.0 (lunav2.io)',
        'decimals': 18,
    },
    string_to_evm_address('0x4E0b2A80E158f8d28a2007866ab80B7f63bE6076'): {
        'name': 'Owlswap.org',
        'symbol': 'OWLT',
        'decimals': 18,
    },
    string_to_evm_address('0x4f4d22cA77222aE3D51e308C9A8F0E564F98e77A'): {
        'name': 'Bulleon Promo Token',
        'symbol': 'BULLEON-X',
        'decimals': 18,
    },
    string_to_evm_address('0x5D80A8D8CB80696073e82407968600A37e1dd780'): {
        'name': 'aave-sr.xyz',
        'symbol': 'Visit [aave-sr.xyz] and claim special rewards',
        'decimals': 6,
    },
    string_to_evm_address('0x695d4e4936C0DE413267C75ca684fc317e03A819'): {
        'name': 'ApeSnoop.com',
        'symbol': 'Ape Dog Coin',
        'decimals': 18,
    },
    string_to_evm_address('0x7B2f9706CD8473B4F5B7758b0171a9933Fc6C4d6'): {
        'name': 'An Etheal Promo',
        'symbol': 'HEALP',
        'decimals': 18,
    },
    string_to_evm_address('0x7C743517f34daEfc6477D44b0a2a12dE6fA38Ea2'): {
        'name': '! Uniswapv3LP.com !',
        'symbol': 'Uniswapv3LP.com',
        'decimals': 18,
    },
    string_to_evm_address('0x8f5a1Cb27cfeD6A640dE424e9c0abbCeaad0b620'): {
        'name': 'uETH.io',
        'symbol': 'uETH.io',
        'decimals': 18,
    },
    string_to_evm_address('0xAF0b2fBeDd5d1Fda457580FB3DAbAD1F5C8bBC36'): {
        'name': 'LunaV2.io (Luna Token)',
        'symbol': 'LunaV2.io (Luna Token)',
        'decimals': 18,
    },
    string_to_evm_address('0xCf39B7793512F03f2893C16459fd72E65D2Ed00c'): {
        'name': '$ UniswapLP.com',
        'symbol': 'UniswapLP.com',
        'decimals': 18,
    },
    string_to_evm_address('0xD4DE05944572D142fBf70F3f010891A35AC15188'): {
        'name': 'Bulleon Promo Token',
        'symbol': 'BULLEON PROMO',
        'decimals': 18,
    },
    string_to_evm_address('0xF0df09387693690b1E00D71eabF5E98e7955CFf4'): {
        'name': 'ENDO.network Promo Token',
        'symbol': 'ETP',
        'decimals': 18,
    },
    string_to_evm_address('0xc2e39D0Afa884192F2Cc55D841C2C8c5681DbF17'): {
        'name': '(avrc.xyz)',
        'symbol': 'avrc.xyz',
        'decimals': 6,
    },
    string_to_evm_address('0xd202ec9D73d8D66242312495e3F72248e8d08d60'): {
        'name': 'avrc',
        'symbol': 'okchat.io',
        'decimals': 18,
    },
    string_to_evm_address('0xB688d06d858E092EBB145394a1BA08C7a10E1F56'): {
        'name': 'acrone.site',
        'symbol': 'acrone.site',
        'decimals': 18,
    },
    string_to_evm_address('0xA36Ceec605d81aE74268Fda28A5c0Bd10b1D1f7C'): {
        'name': 'AaveLP.com',
        'symbol': 'AaveLP.com',
        'decimals': 18,
    },
}


def query_token_spam_list(db: 'DBHandler') -> Set[EvmToken]:
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
            token = EvmToken(ethaddress_to_identifier(checksumed_address))
        except UnknownAsset:
            continue
        if token is not None:
            tokens_to_ignore.add(token)

    # Try to add custom list
    for token_address, info in KNOWN_ETH_SPAM_TOKENS.items():
        try:
            own_token = get_or_create_evm_token(
                userdb=db,
                evm_address=token_address,
                chain=ChainID.ETHEREUM,
                protocol=SPAM_PROTOCOL,
                form_with_incomplete_data=True,
                decimals=info.get('decimals', 18),
                name=info.get('name', MISSING_NAME_SPAM_TOKEN),
                symbol=info.get('symbol', MISSING_SYMBOL_SPAM_TOKEN),
            )
        except (RemoteError, NotERC20Conformant) as e:
            log.debug(f'Skipping {checksumed_address} due to {str(e)}')
            continue
        if own_token is not None:
            tokens_to_ignore.add(own_token)

    return tokens_to_ignore


def update_spam_assets(write_cursor: 'DBCursor', db: 'DBHandler') -> int:
    """
    Update the list of ignored assets using query_token_spam_list and avoiding
    the addition of duplicates. It returns the amount of assets that were added
    to the ignore list
    """
    spam_tokens = query_token_spam_list(db)
    # order maters here. Make sure ignored_assets are queried after spam tokens creation
    # since it's possible for a token to exist in ignored assets but not global DB.
    # and in that case query_token_spam_list add it to the global DB
    with db.conn.read_ctx() as cursor:
        ignored_assets = {asset.identifier for asset in db.get_ignored_assets(cursor)}
    assets_added = 0
    for token in spam_tokens:
        if token.identifier in ignored_assets:
            continue

        db.add_to_ignored_assets(write_cursor=write_cursor, asset=token)
        assets_added += 1
    return assets_added
