import logging
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final

import requests

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token, get_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.morpho.constants import MORPHO_VAULT_ABI
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_int
from rotkehlchen.types import (
    MORPHO_VAULT_PROTOCOL,
    CacheType,
    ChainID,
    EvmTokenKind,
    Price,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.inquirer import Inquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MORPHO_BLUE_API: Final = 'https://blue-api.morpho.org/graphql'
VAULT_QUERY_PAGE_SIZE: Final = 200
VAULT_QUERY: Final = 'items {address symbol name asset {address symbol name decimals} chain {id}}'


def _update_cache_timestamp(count: int | None = None) -> None:
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=[CacheType.MORPHO_VAULTS],
            value=str(count) if count is not None else '0',
        )


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


def query_morpho_vaults(database: 'DBHandler') -> None:
    """Query list of Morpho vaults and add the vault tokens to the global database."""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        last_vault_count = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.MORPHO_VAULTS,),
        )

    if (vault_list := _query_morpho_vaults_api()) is None:
        _update_cache_timestamp()  # Update timestamp to prevent repeated errors.
        return

    _update_cache_timestamp(count=(vault_count := len(vault_list)))

    try:
        if last_vault_count is not None and vault_count == int(last_vault_count):
            log.debug(f'Same number ({vault_count}) of Morpho vaults returned from API as previous query. Skipping vault processing.')  # noqa: E501
            return
    except ValueError:
        log.error(f'Failed to check last Morpho vault count due to {last_vault_count} not being an int')  # noqa: E501
        return

    for vault in vault_list:
        try:
            vault_chain_id = ChainID.deserialize_from_db(vault['chain']['id'])
            underlying_token = get_or_create_evm_token(
                userdb=database,
                evm_address=string_to_evm_address(vault['asset']['address']),
                chain_id=vault_chain_id,
                decimals=deserialize_int(vault['asset']['decimals']),
                name=vault['asset']['name'],
                symbol=vault['asset']['symbol'],
                encounter=TokenEncounterInfo(description='Querying Morpho vaults', should_notify=False),  # noqa: E501
            )
            get_or_create_evm_token(
                userdb=database,
                evm_address=string_to_evm_address(vault['address']),
                chain_id=vault_chain_id,
                protocol=MORPHO_VAULT_PROTOCOL,
                decimals=18,  # all morpho vaults have 18 decimals
                name=vault['name'],
                symbol=vault['symbol'],
                underlying_tokens=[UnderlyingToken(
                    address=underlying_token.evm_address,
                    token_kind=EvmTokenKind.ERC20,
                    weight=ONE,
                )],
                encounter=TokenEncounterInfo(description='Querying Morpho vaults', should_notify=False),  # noqa: E501
            )
        except (DeserializationError, KeyError) as e:
            error = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
            log.error(f'Failed to store token information for Morpho vault due to {error}. Vault: {vault}. Skipping...')  # noqa: E501


def get_morpho_vault_token_price(
        inquirer: 'Inquirer',
        vault_token: 'EvmToken',
        evm_inquirer: 'EvmNodeInquirer',
) -> Price:
    """Gets token price for a Morpho vault.
    Multiplies the vault's price per share by the underlying token's USD price.
    """
    try:
        price_per_share = evm_inquirer.call_contract(
            contract_address=vault_token.evm_address,
            abi=MORPHO_VAULT_ABI,
            method_name='convertToAssets',
            arguments=[int(1e18)],  # 1 share with 18 decimals
        )
    except RemoteError as e:
        log.error(f'Failed to get price per share for Morpho vault {vault_token} on {evm_inquirer.chain_id.label()}: {e}')  # noqa: E501
        return ZERO_PRICE

    if (
        len(vault_token.underlying_tokens) == 0 or
        (underlying_token := get_token(
            evm_address=vault_token.underlying_tokens[0].address,
            chain_id=evm_inquirer.chain_id,
        )) is None
    ):
        log.error(f'Failed to get underlying token for Morpho vault {vault_token} on {evm_inquirer.chain_id.label()}')  # noqa: E501
        return ZERO_PRICE

    formatted_pps = token_normalized_value(
        token_amount=price_per_share,
        token=underlying_token,
    )
    return Price(inquirer.find_usd_price(asset=underlying_token) * formatted_pps)
