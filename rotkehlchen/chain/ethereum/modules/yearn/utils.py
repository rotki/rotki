import logging
from json import JSONDecodeError
from typing import TYPE_CHECKING

import requests

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.misc import ONE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    YEARN_VAULTS_V1_PROTOCOL,
    YEARN_VAULTS_V2_PROTOCOL,
    ChainID,
    EvmTokenKind,
    GeneralCacheType,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

YEARN_OLD_API = 'https://api.yearn.finance/v1/chains/1/vaults/all'


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_yearn_vaults(db: 'DBHandler') -> None:
    """Query yearn API and ensure that all the tokens exist locally. If they exist but the protocol
    is not the correct one, then the asset will be edited.

    May raise:
    - RemoteError
    """
    try:
        response = requests.get(YEARN_OLD_API)
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RemoteError(f'Failed to obtain yearn vault information. {str(e)}') from e
    except (DeserializationError, JSONDecodeError) as e:
        raise RemoteError(f"Failed to deserialize data from yearn's old api. {str(e)}") from e

    if not isinstance(data, list):
        raise RemoteError(f'Unexpected format from yearn vaults reponse. Expected a list, got {data}')  # noqa: E501

    # get from the cache the number of vaults processed in the last execution of this function.
    # If it was the same number of vaults this response has then we don't need to take
    # action since vaults are not removed from their API response.
    yearn_api_cache: list[str] = GlobalDBHandler().get_general_cache_values(
        key_parts=[GeneralCacheType.YEARN_VAULTS],
    )
    if len(yearn_api_cache) == 1 and int(yearn_api_cache[0]) == len(data):
        logging.debug(
            f'Previous query of yearn vaults returned {yearn_api_cache[0]} vaults and last API '
            f'response had the same amount of vaults. Not processing the API response since '
            f'it is identical to what we have.',
        )
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            # update the timestamp of the last time this vaults were queried
            GlobalDBHandler().set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=[GeneralCacheType.YEARN_VAULTS],
                values=[yearn_api_cache[0]],
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
            underlying_token = get_or_create_evm_token(
                userdb=db,
                evm_address=string_to_evm_address(vault['token']['address']),
                chain_id=ChainID.ETHEREUM,
                form_with_incomplete_data=True,
                decimals=vault['token']['decimals'],
                name=vault['token']['name'],
                symbol=vault['token']['symbol'],
            )
            vault_token = get_or_create_evm_token(
                userdb=db,
                evm_address=string_to_evm_address(vault['address']),
                chain_id=ChainID.ETHEREUM,
                protocol=vault_type,
                form_with_incomplete_data=True,
                decimals=vault['decimals'],
                name=vault['name'],
                symbol=vault['symbol'],
                underlying_tokens=[UnderlyingToken(
                    address=underlying_token.evm_address,
                    token_kind=EvmTokenKind.ERC20,
                    weight=ONE,
                )],
            )
        except KeyError as e:
            log.error(
                f'Failed to store token information for yearn {vault_type} vault due to '
                f'missing key {str(e)}. Vault: {vault}. Skipping...',
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
        # Delete the old value cached and store in the cache the amount of vaults
        # processed in this response.
        GlobalDBHandler().delete_general_cache(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.YEARN_VAULTS],
        )
        GlobalDBHandler().set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.YEARN_VAULTS],
            values=[str(len(data))],
        )
