import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.decoding.stakedao.utils import STAKEDAO_API
from rotkehlchen.chain.evm.decoding.stakedao.v2.constants import CPT_STAKEDAO_V2
from rotkehlchen.chain.evm.decoding.utils import update_cached_vaults
from rotkehlchen.constants import ONE
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChainID, TokenKind
from rotkehlchen.utils.network import request_get

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Curve is the only strategy using V2 currently (as of Nov. 2025),
# but others are planned to be migrated.
SUPPORTED_STAKEDAO_V2_STRATEGIES: Final = {'curve'}


def _query_stakedao_v2_api(chain_id: ChainID) -> list[dict[str, Any]] | None:
    """Query StakeDAO V2 vaults from the API and return the vault data list or None on error."""
    vault_data: list[dict[str, Any]] = []
    for protocol in SUPPORTED_STAKEDAO_V2_STRATEGIES:
        try:
            vault_data.extend(request_get(
                url=f'{STAKEDAO_API}/strategies/v2/{protocol}/{chain_id.serialize()}.json',
            ))
        except (RemoteError, UnableToDecryptRemoteData) as e:
            log.error(f'Failed to retrieve StakeDAO {protocol} vaults on {chain_id.name} due to {e!s}')  # noqa: E501
            return None

    return vault_data


def _process_stakedao_v2_vault(
        database: 'DBHandler',
        vault: dict[str, Any],
        evm_inquirer: 'EvmNodeInquirer',
) -> None:
    """Process StakeDAO v2 vault data from the api and add its tokens to the database.
    May raise NotERC20Conformant, NotERC721Conformant, DeserializationError, and KeyError.
    """
    get_or_create_evm_token(
        userdb=database,
        evm_address=deserialize_evm_address(vault['vault']),
        chain_id=evm_inquirer.chain_id,
        protocol=CPT_STAKEDAO_V2,
        evm_inquirer=evm_inquirer,
        encounter=TokenEncounterInfo(should_notify=False),
        underlying_tokens=[UnderlyingToken(
            address=get_or_create_evm_token(
                userdb=database,
                evm_address=deserialize_evm_address(vault['lpToken']['address']),
                chain_id=evm_inquirer.chain_id,
                evm_inquirer=evm_inquirer,
                encounter=TokenEncounterInfo(should_notify=False),
            ).evm_address,
            weight=ONE,
            token_kind=TokenKind.ERC20,
        )],
    )


def query_stakedao_v2_vaults(evm_inquirer: 'EvmNodeInquirer') -> None:
    """Query StakeDAO V2 vaults from the API and create corresponding tokens."""
    update_cached_vaults(
        database=evm_inquirer.database,
        cache_key=(CacheType.STAKEDAO_V2_VAULTS, str(evm_inquirer.chain_id)),
        display_name='StakeDAO V2',
        chain=evm_inquirer.chain_id,
        query_vaults=lambda: _query_stakedao_v2_api(evm_inquirer.chain_id),
        process_vault=lambda db, vault: _process_stakedao_v2_vault(db, vault, evm_inquirer),
    )
