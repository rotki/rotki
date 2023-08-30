import logging
from json import JSONDecodeError
from typing import TYPE_CHECKING, Optional

import requests

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenSeenAt, get_or_create_evm_token
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.utils import read_integer
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    YEARN_VAULTS_V1_PROTOCOL,
    YEARN_VAULTS_V2_PROTOCOL,
    CacheType,
    ChainID,
    EvmTokenKind,
    Timestamp,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler

YEARN_OLD_API = 'https://api.yearn.finance/v1/chains/1/vaults/all'


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_yearn_vaults(db: 'DBHandler', ethereum_inquirer: 'EthereumInquirer') -> None:
    """Query yearn API and ensure that all the tokens exist locally. If they exist but the protocol
    is not the correct one, then the asset will be edited.

    May raise:
    - RemoteError
    """
    try:
        response = requests.get(YEARN_OLD_API, timeout=CachedSettings().get_timeout_tuple())
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RemoteError(f'Failed to obtain yearn vault information. {e!s}') from e
    except (DeserializationError, JSONDecodeError) as e:
        raise RemoteError(f"Failed to deserialize data from yearn's old api. {e!s}") from e

    if not isinstance(data, list):
        raise RemoteError(f'Unexpected format from yearn vaults reponse. Expected a list, got {data}')  # noqa: E501

    # get from the cache the number of vaults processed in the last execution of this function.
    # If it was the same number of vaults this response has then we don't need to take
    # action since vaults are not removed from their API response.
    with GlobalDBHandler().conn.read_ctx() as cursor:
        yearn_api_cache: Optional[str] = globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
        )
    if yearn_api_cache is not None and int(yearn_api_cache) == len(data):
        logging.debug(
            f'Previous query of yearn vaults returned {yearn_api_cache} vaults and last API '
            f'response had the same amount of vaults. Not processing the API response since '
            f'it is identical to what we have.',
        )
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            # update the timestamp of the last time this vaults were queried
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.YEARN_VAULTS,),
                value=yearn_api_cache,
            )
        return

    for vault in data:
        if 'type' not in vault:
            log.error(f'Could not identify the yearn vault type for {vault}. Skipping...')
            continue

        if vault['type'] == 'v1':
            vault_type = YEARN_VAULTS_V1_PROTOCOL
        elif vault['type'] == 'v2':
            vault_type = YEARN_VAULTS_V2_PROTOCOL
        else:
            log.error(f'Found yearn token with unknown version {vault}. Skipping...')
            continue

        try:
            block_data = ethereum_inquirer.get_block_by_number(vault['inception'])
            block_timestamp = Timestamp(read_integer(block_data, 'timestamp', 'yearn vault query'))
        except (KeyError, DeserializationError) as e:
            log.error(
                f'Failed to store token information for yearn {vault_type} vault due to '
                f'missing key {e!s}. Vault: {vault}. Skipping...',
            )
            continue

        try:
            underlying_token = get_or_create_evm_token(
                userdb=db,
                evm_address=string_to_evm_address(vault['token']['address']),
                chain_id=ChainID.ETHEREUM,
                decimals=vault['token']['decimals'],
                name=vault['token']['name'],
                symbol=vault['token']['symbol'],
                seen=TokenSeenAt(description=f'Querying {vault_type} balances'),
            )
            vault_token = get_or_create_evm_token(
                userdb=db,
                evm_address=string_to_evm_address(vault['address']),
                chain_id=ChainID.ETHEREUM,
                protocol=vault_type,
                decimals=vault['decimals'],
                name=vault['name'],
                symbol=vault['symbol'],
                underlying_tokens=[UnderlyingToken(
                    address=underlying_token.evm_address,
                    token_kind=EvmTokenKind.ERC20,
                    weight=ONE,
                )],
                started=block_timestamp,
                seen=TokenSeenAt(description=f'Querying {vault_type} balances'),
            )
        except KeyError as e:
            log.error(
                f'Failed to store token information for yearn {vault_type} vault due to '
                f'missing key {e!s}. Vault: {vault}. Skipping...',
            )
            continue

        # if it existed but the protocol is not correct edit it. Can happen if it was auto added
        # before this logic existed or executed.
        if vault_token.protocol != vault_type:
            log.debug(f'Editing yearn asset {vault_token}')
            # we have to use setattr since vault_token is frozen
            object.__setattr__(vault_token, 'protocol', vault_type)
            GlobalDBHandler().edit_evm_token(vault_token)

    # Store in the globaldb cache the number of vaults processed from this call to the API
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        # overwrites the old value cached and store in the cache the amount of vaults
        # processed in this response.

        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=(CacheType.YEARN_VAULTS,),
            value=str(len(data)),
        )
