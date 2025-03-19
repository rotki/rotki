import logging
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any

import requests

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.decoding.utils import get_vault_price, update_cached_vaults
from rotkehlchen.constants import ONE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.globaldb.cache import (
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_int
from rotkehlchen.types import (
    CURVE_LENDING_VAULTS_PROTOCOL,
    CacheType,
    ChainID,
    EvmTokenKind,
    Price,
)

from .constants import CURVE_VAULT_ABI

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.inquirer import Inquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _query_curve_lending_vaults_api() -> list[dict[str, Any]] | None:
    """Query Curve lending vaults from the api.
    Returns vault list or None if there was an error."""
    try:
        response_data = requests.get(
            url='https://api.curve.fi/v1/getLendingVaults/all',
            timeout=CachedSettings().get_timeout_tuple(),
        )
        vault_list = response_data.json()['data']['lendingVaultData']

    except (requests.RequestException, JSONDecodeError, TypeError, KeyError) as e:
        error = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
        log.error(f'Failed to retrieve Curve lending vaults from api due to {error}')
        return None

    return vault_list


def _process_curve_lending_vault(database: 'DBHandler', vault: dict[str, Any]) -> None:
    """Process Curve lending vault data from the api and add its tokens to the database.
    May raise NotERC20Conformant, NotERC721Conformant, DeserializationError, and KeyError."""
    if vault['blockchainId'] == 'fraxtal':
        return
    elif vault['blockchainId'] == 'arbitrum':
        vault_chain_id = ChainID.ARBITRUM_ONE
    else:
        vault_chain_id = ChainID.deserialize_from_name(vault['blockchainId'])

    underlying_token = get_or_create_evm_token(
        userdb=database,
        evm_address=deserialize_evm_address(vault['assets']['borrowed']['address']),
        chain_id=vault_chain_id,
        decimals=deserialize_int(vault['assets']['borrowed']['decimals']),
        symbol=vault['assets']['borrowed']['symbol'],
        encounter=TokenEncounterInfo(description='Querying Curve lending vaults', should_notify=False),  # noqa: E501
    )
    vault_token = get_or_create_evm_token(
        userdb=database,
        evm_address=deserialize_evm_address(vault['address']),
        chain_id=vault_chain_id,
        protocol=CURVE_LENDING_VAULTS_PROTOCOL,
        name=vault['name'],
        symbol='cvcrvUSD',
        underlying_tokens=[UnderlyingToken(
            address=underlying_token.evm_address,
            token_kind=EvmTokenKind.ERC20,
            weight=ONE,
        )],
        encounter=TokenEncounterInfo(description='Querying Curve lending vaults', should_notify=False),  # noqa: E501
    )
    if (gauge_address := vault.get('gaugeAddress')) is not None:
        get_or_create_evm_token(
            userdb=database,
            chain_id=vault_chain_id,
            name=f'Curve.fi {vault_token.name} Gauge Deposit',
            symbol=f'{vault_token.symbol}-gauge',
            evm_address=deserialize_evm_address(gauge_address),
            encounter=TokenEncounterInfo(description='Querying Curve lending vaults', should_notify=False),  # noqa: E501
        )

    # Cache the controller and AMM addresses to avoid having to make a call
    # to the vault contract when they're needed during decoding.
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=[CacheType.CURVE_LENDING_VAULT_CONTROLLER, vault_token.evm_address],
            value=vault['controllerAddress'],
        )
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=[CacheType.CURVE_LENDING_VAULT_AMM, vault_token.evm_address],
            value=vault['ammAddress'],
        )
        if gauge_address:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=[CacheType.CURVE_LENDING_VAULT_GAUGE, vault_token.evm_address],
                value=gauge_address,
            )


def query_curve_lending_vaults(database: 'DBHandler') -> None:
    """Query list of Curve lending vaults and add the vault tokens to the global database."""
    update_cached_vaults(
        database=database,
        cache_key=(CacheType.CURVE_LENDING_VAULTS,),
        display_name='Curve lending',
        query_vaults=_query_curve_lending_vaults_api,
        process_vault=_process_curve_lending_vault,
    )


def get_curve_vault_token_price(
        inquirer: 'Inquirer',
        vault_token: 'EvmToken',
        evm_inquirer: 'EvmNodeInquirer',
) -> Price:
    """Gets the token price for a Curve vault."""
    return get_vault_price(
        inquirer=inquirer,
        vault_token=vault_token,
        evm_inquirer=evm_inquirer,
        vault_abi=CURVE_VAULT_ABI,
        pps_method='pricePerShare',
        display_name='Curve vault',
    )
