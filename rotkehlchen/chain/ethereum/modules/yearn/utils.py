import logging
from json import JSONDecodeError
from typing import TYPE_CHECKING

import requests

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.types import string_to_evm_address
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
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

YEARN_OLD_API = 'https://api.yearn.finance/v1/chains/1/vaults/all'


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_yearn_vaults(db: 'DBHandler') -> None:
    """Query yearn API and ensure that all the tokens exists locally. If it exists but the protocol
    is not the correct one the asset will be edited.
    TODO: After Optimism gets merged we need to move this logic to a periodic task as we do with
    curve pools.

    May raise:
    - RemoteError
    """
    try:
        response = requests.get(YEARN_OLD_API)
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RemoteError(f'Failed to obtain yearn vault information. {str(e)}') from e
    except (DeserializationError, JSONDecodeError) as e:
        raise RemoteError(f'Failed to deserialize data from cryptoscamdb. {str(e)}') from e

    if not isinstance(data, list):
        raise RemoteError(f'Unexpected format from yearn vaults reponse. Expected a list, got {data}')  # noqa: E501

    for vault in data:
        if vault['type'] == 'v1':
            vault_type = YEARN_VAULTS_V1_PROTOCOL
        elif vault['type'] == 'v2':
            vault_type = YEARN_VAULTS_V2_PROTOCOL
        else:
            logging.error(f'Found yearn token with unknown version {vault}')
            continue

        underlying_token = get_or_create_evm_token(
            userdb=db,
            evm_address=string_to_evm_address(vault['token']['address']),
            chain=ChainID.ETHEREUM,
            form_with_incomplete_data=True,
            decimals=vault['token']['decimals'],
            name=vault['token']['name'],
            symbol=vault['token']['symbol'],
        )

        vault_token = get_or_create_evm_token(
            userdb=db,
            evm_address=string_to_evm_address(vault['address']),
            chain=ChainID.ETHEREUM,
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

        # if it existed but the protocol is not correct edit it. Can happen if it was auto added
        # before this logic existed or executed.
        if vault_token.protocol != vault_type:
            log.debug(f'Editing yearn asset {vault_token}')
            # we have to use setattr since vault_token is frozen
            object.__setattr__(vault_token, 'protocol', vault_type)
            GlobalDBHandler().edit_evm_token(vault_token)
