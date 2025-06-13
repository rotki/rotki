import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.decoding.utils import get_vault_price, update_cached_vaults
from rotkehlchen.constants.misc import ONE
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_int
from rotkehlchen.types import (
    CacheType,
    ChainID,
    EvmTokenKind,
    Price,
)
from rotkehlchen.utils.network import request_get

from .constants import BEEFY_VAULT_ABI, CPT_BEEFY_FINANCE

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.inquirer import Inquirer


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _query_beefy_vaults_api(chain: ChainID) -> list[dict[str, Any]] | None:
    """Query Beefy finance API for all vaults on the given chain."""
    try:
        return request_get(url=f'https://api.beefy.finance/vaults/all/{chain.value}')  # type: ignore[return-value]  # we get a list of dictionaries from the api
    except (RemoteError, UnableToDecryptRemoteData) as e:
        log.error(f'Failed to retrieve Beefy vaults for {chain} due to {e!s}')
        return None


def _process_beefy_vault(
        database: 'DBHandler',
        vault: dict[str, Any],
        evm_inquirer: 'EvmNodeInquirer',
) -> None:
    """Process beefy finance vault data from the api and add its tokens to the database.
    May raise:
    - NotERC20Conformant
    - DeserializationError
    - KeyError
    """
    underlying_token = get_or_create_evm_token(
        userdb=database,
        evm_inquirer=evm_inquirer,
        evm_address=deserialize_evm_address(vault['tokenAddress']),
        chain_id=evm_inquirer.chain_id,
        decimals=deserialize_int(vault['tokenDecimals']),
        encounter=(encounter := TokenEncounterInfo(
            description='Querying Beefy finance vaults',
            should_notify=False,
        )),
    )
    get_or_create_evm_token(
        userdb=database,
        evm_address=deserialize_evm_address(vault['earnedTokenAddress']),
        chain_id=evm_inquirer.chain_id,
        evm_inquirer=evm_inquirer,
        protocol=CPT_BEEFY_FINANCE,
        underlying_tokens=[UnderlyingToken(
            address=underlying_token.evm_address,
            token_kind=EvmTokenKind.ERC20,
            weight=ONE,
        )],
        encounter=encounter,
    )


def query_beefy_vaults(evm_inquirer: 'EvmNodeInquirer') -> None:
    """Query list of Beefy finance vaults and add the vault tokens to the global database."""
    update_cached_vaults(
        database=evm_inquirer.database,
        cache_key=(CacheType.BEEFY_VAULTS, str(evm_inquirer.chain_id.value)),
        display_name='Beefy finance',
        query_vaults=lambda: _query_beefy_vaults_api(evm_inquirer.chain_id),
        process_vault=lambda db, entry: _process_beefy_vault(db, entry, evm_inquirer),
    )


def query_beefy_vault_price(
        inquirer: 'Inquirer',
        vault_token: 'EvmToken',
        evm_inquirer: 'EvmNodeInquirer',
) -> Price:
    """Gets the token price for a Beefy vault."""
    return get_vault_price(
        inquirer=inquirer,
        vault_token=vault_token,
        evm_inquirer=evm_inquirer,
        display_name='Beefy finance',
        vault_abi=BEEFY_VAULT_ABI,
        pps_method='getPricePerFullShare',
    )
