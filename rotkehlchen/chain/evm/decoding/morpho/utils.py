import logging
from collections import defaultdict
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final

import requests

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.morpho.constants import CPT_MORPHO, MORPHO_VAULT_ABI
from rotkehlchen.chain.evm.decoding.utils import get_vault_price, update_cached_vaults
from rotkehlchen.constants import EXP18_INT, ONE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_int
from rotkehlchen.types import (
    CacheType,
    ChainID,
    Price,
    TokenKind,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.inquirer import Inquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MORPHO_BLUE_API: Final = 'https://blue-api.morpho.org/graphql'
MORPHO_REWARDS_API: Final = 'https://rewards.morpho.org/v1/programs'
VAULT_QUERY_PAGE_SIZE: Final = 200
VAULT_QUERY: Final = 'items {address symbol name asset {address symbol name decimals} chain {id}}'


def _query_morpho_vaults_api() -> list[dict[str, Any]] | None:
    """Query morpho vaults from the morpho blue api.
    Returns vault list or None if there was an error."""
    all_vaults, offset = [], 0
    while True:
        try:
            response_data = requests.post(
                url=MORPHO_BLUE_API,
                json={'query': f'query {{ vaults(first:{VAULT_QUERY_PAGE_SIZE} skip:{offset}) {{ {VAULT_QUERY} }} }}'},  # noqa: E501
                headers={'Content-Type': 'application/json'},
                timeout=CachedSettings().get_timeout_tuple(),
            )
            vault_list = response_data.json()['data']['vaults']['items']
            all_vaults.extend(vault_list)
            offset += VAULT_QUERY_PAGE_SIZE
            if len(vault_list) < VAULT_QUERY_PAGE_SIZE:
                break  # no more vaults to retrieve

        except (requests.RequestException, JSONDecodeError, TypeError, KeyError) as e:
            error = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
            log.error(f'Failed to retrieve morpho vaults from api due to {error}')
            return None

    return all_vaults


def _process_morpho_vault(database: 'DBHandler', vault: dict[str, Any]) -> None:
    """Process Morpho vault data from the api and add its tokens to the database.
    May raise NotERC20Conformant, NotERC721Conformant, DeserializationError, and KeyError."""
    vault_chain_id = ChainID.deserialize_from_db(vault['chain']['id'])
    underlying_token = get_or_create_evm_token(
        userdb=database,
        evm_address=deserialize_evm_address(vault['asset']['address']),
        chain_id=vault_chain_id,
        decimals=deserialize_int(
            value=vault['asset']['decimals'],
            location='morpho vault underlying token decimals',
        ),
        name=vault['asset']['name'],
        symbol=vault['asset']['symbol'],
        encounter=(encounter := TokenEncounterInfo(
            description='Querying Morpho vaults',
            should_notify=False,
        )),
    )
    get_or_create_evm_token(
        userdb=database,
        evm_address=deserialize_evm_address(vault['address']),
        chain_id=vault_chain_id,
        protocol=CPT_MORPHO,
        decimals=DEFAULT_TOKEN_DECIMALS,  # all morpho vaults have 18 decimals
        name=vault['name'],
        symbol=vault['symbol'],
        underlying_tokens=[UnderlyingToken(
            address=underlying_token.evm_address,
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
        encounter=encounter,
    )


def query_morpho_vaults(database: 'DBHandler', chain_id: ChainID) -> None:
    """Query list of Morpho vaults and add the vault tokens to the global database."""
    update_cached_vaults(
        database=database,
        cache_key=(CacheType.MORPHO_VAULTS,),
        display_name='Morpho',
        chain=chain_id,
        query_vaults=_query_morpho_vaults_api,
        process_vault=_process_morpho_vault,
    )


def query_morpho_reward_distributors() -> None:
    """Query Morpho reward distributor addresses from the api and cache them."""
    try:
        response_data = requests.get(
            url=MORPHO_REWARDS_API,
            timeout=CachedSettings().get_timeout_tuple(),
        ).json().get('data', [])
    except (requests.RequestException, AttributeError) as e:  # AttributeError to handle if the json is not a dict  # noqa: E501
        log.error(f'Failed to retrieve morpho reward distributors from api due to {e!s}')
        return

    distributors: dict[ChainID, set] = defaultdict(set)
    for item in response_data:
        try:
            distributors[ChainID.deserialize(item['chain_id'])].add(
                deserialize_evm_address(item['distributor']['address']),
            )
        except (DeserializationError, TypeError, KeyError) as e:
            error = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
            log.error(f'Failed to deserialize morpho reward distributor entry from api due to {error}')  # noqa: E501

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        for chain_id, addresses in distributors.items():
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(CacheType.MORPHO_REWARD_DISTRIBUTORS, str(chain_id)),
                values=addresses,
            )


def get_morpho_vault_token_price(
        inquirer: 'Inquirer',
        vault_token: 'EvmToken',
        evm_inquirer: 'EvmNodeInquirer',
) -> Price:
    """Gets the token price for a Morpho vault."""
    return get_vault_price(
        inquirer=inquirer,
        vault_token=vault_token,
        evm_inquirer=evm_inquirer,
        display_name='Morpho',
        vault_abi=MORPHO_VAULT_ABI,
        pps_method='convertToAssets',
        pps_method_args=[EXP18_INT],  # 1 share with 18 decimals
    )
