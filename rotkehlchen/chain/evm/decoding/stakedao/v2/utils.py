import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.decoding.stakedao.utils import STAKEDAO_API
from rotkehlchen.chain.evm.decoding.stakedao.v2.constants import CPT_STAKEDAO_V2
from rotkehlchen.chain.evm.utils import maybe_notify_cache_query_status
from rotkehlchen.constants import ONE
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_set_general_cache_values,
    globaldb_update_cache_last_ts,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChainID, Timestamp, TokenKind
from rotkehlchen.utils.network import request_get

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

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


def ensure_stakedao_v2_vault_token_exists(
        evm_inquirer: 'EvmNodeInquirer',
        vault: 'ChecksumEvmAddress',
        underlying: 'ChecksumEvmAddress',
) -> None:
    """Ensure that a StakeDAO V2 vault token and its underlying token exist in the database."""
    get_or_create_evm_token(
        userdb=evm_inquirer.database,
        evm_address=vault,
        chain_id=evm_inquirer.chain_id,
        protocol=CPT_STAKEDAO_V2,
        evm_inquirer=evm_inquirer,
        encounter=TokenEncounterInfo(should_notify=False),
        underlying_tokens=[UnderlyingToken(
            address=get_or_create_evm_token(
                userdb=evm_inquirer.database,
                evm_address=underlying,
                chain_id=evm_inquirer.chain_id,
                evm_inquirer=evm_inquirer,
                encounter=TokenEncounterInfo(should_notify=False),
            ).evm_address,
            weight=ONE,
            token_kind=TokenKind.ERC20,
        )],
    )


def query_stakedao_v2_vaults(chain_id: ChainID, msg_aggregator: 'MessagesAggregator') -> None:
    """Query StakeDAO V2 vaults from the API and cache the vault and underlying token addresses."""
    if (vault_data := _query_stakedao_v2_api(chain_id)) is None:
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_update_cache_last_ts(
                write_cursor=write_cursor,
                cache_type=CacheType.STAKEDAO_V2_VAULTS,
                key_parts=(str(chain_id.serialize()),),
            )  # Update cache timestamp to prevent repeated errors.
        return

    cache_entries, last_notified_ts, total_entries = [], Timestamp(0), len(vault_data)
    for idx, vault in enumerate(vault_data):
        try:
            cache_entries.append(','.join((
                deserialize_evm_address(vault['vault']),
                deserialize_evm_address(vault['lpToken']['address']),
            )))
        except (DeserializationError, KeyError) as e:
            error = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
            log.error(
                'Failed to cache StakeDAO V2 vault address and underlying token address for '
                f'vault {vault} due to {error}. Skipping.',
            )

        last_notified_ts = maybe_notify_cache_query_status(
            msg_aggregator=msg_aggregator,
            last_notified_ts=last_notified_ts,
            protocol=CPT_STAKEDAO_V2,
            chain=chain_id,
            processed=idx + 1,
            total=total_entries,
        )

    if len(cache_entries) > 0:
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(CacheType.STAKEDAO_V2_VAULTS, str(chain_id.serialize())),
                values=cache_entries,
            )
