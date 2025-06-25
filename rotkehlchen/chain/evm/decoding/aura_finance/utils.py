import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset, UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.utils import update_cached_vaults
from rotkehlchen.constants import ONE
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, Price, TokenKind

from .constants import AURA_BOOSTER_ABI, CHAIN_ID_TO_BOOSTER_ADDRESSES, CPT_AURA_FINANCE

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.inquirer import Inquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_aura_pools(evm_inquirer: 'EvmNodeInquirer') -> None:
    update_cached_vaults(
        display_name='Aura Finance',
        database=evm_inquirer.database,
        query_vaults=lambda: _query_aura_pools(evm_inquirer),
        process_vault=_process_aura_pool,
        cache_key=(CacheType.AURA_POOLS, str(evm_inquirer.chain_id.value)),
    )


def _process_aura_pool(database: 'DBHandler', vault: dict[str, Any]) -> None:
    """Store Aura pool data.

    May raise:
    - NotERC20Conformant
    """
    chain_id = vault['chain_id']
    chain_name = chain_id.to_name()
    encounter = TokenEncounterInfo(
        description=f'Querying {chain_name} aura finance balances',
        should_notify=False,
    )
    aura_pool_token = get_or_create_evm_token(
        userdb=database,
        evm_address=vault['aura_pool_token'],
        chain_id=chain_id,
        encounter=encounter,
        underlying_tokens=[
            UnderlyingToken(
                address=get_or_create_evm_token(
                    userdb=database,
                    chain_id=chain_id,
                    evm_address=vault['underlying_bpt_token'],
                    encounter=encounter,
                ).evm_address,
                token_kind=TokenKind.ERC20,
                weight=ONE,
            ),
        ],
        protocol=CPT_AURA_FINANCE,
    )

    if aura_pool_token.protocol != CPT_AURA_FINANCE:
        log.debug(
            f'Updating protocol for {chain_name} aura finance '
            f'asset {aura_pool_token}',
        )
        GlobalDBHandler.set_token_protocol_if_missing(
            token=aura_pool_token,
            new_protocol=CPT_AURA_FINANCE,
        )


def _query_aura_pools(evm_inquirer: 'EvmNodeInquirer') -> list[dict[str, Any]] | None:
    """Query Aura pool data from the chain, returning None if the query fails."""
    booster_contract = EvmContract(
        address=CHAIN_ID_TO_BOOSTER_ADDRESSES[evm_inquirer.chain_id],
        abi=AURA_BOOSTER_ABI,
        deployed_block=0,  # unused in this context
    )
    try:
        latest_pools_count = evm_inquirer.call_contract(
            abi=booster_contract.abi,
            method_name='poolLength',
            contract_address=booster_contract.address,
        )
        results = evm_inquirer.multicall(
            calls=[
                (
                    booster_contract.address,
                    booster_contract.encode(
                        method_name='poolInfo',
                        arguments=[idx],
                    ),
                ) for idx in range(latest_pools_count)
            ],
        )
    except RemoteError as e:
        log.error(f'Failed to retrieve {evm_inquirer.chain_name} aura pools due to {e!s}')
        return None

    if len(results) == 0:
        log.debug(f'No aura pools found on {evm_inquirer.chain_name}')
        return None

    pools = []
    for idx, result in enumerate(results):
        try:
            pool_info = booster_contract.decode(
                result=result,
                method_name='poolInfo',
                arguments=[idx],
            )
            pools.append({
                'chain_id': evm_inquirer.chain_id,
                'aura_pool_token': deserialize_evm_address(pool_info[3]),
                'underlying_bpt_token': deserialize_evm_address(pool_info[0]),
            })
        except (IndexError, DeserializationError) as e:
            log.error(
                f'Failed to decode pool info for index {idx} on {evm_inquirer.chain_name}: {e!s}. '
                'Skipping...',
            )
            continue

    return pools


def get_aura_pool_price(inquirer: 'Inquirer', token: 'EvmToken') -> Price:
    """Get the USD price for an Aura pool token by using its underlying BPT token price."""
    if token.underlying_tokens is None or len(token.underlying_tokens) == 0:
        log.warning(
            f'No underlying token found for aura pool token {token} on {token.chain_id.to_name()}. '  # noqa: E501
            'This indicates pools data has not been queried yet.',
        )
        return ZERO_PRICE

    underlying_asset = Asset(evm_address_to_identifier(
        address=token.underlying_tokens[0].address,
        chain_id=token.chain_id,
        token_type=TokenKind.ERC20,
    ))
    return inquirer.find_usd_price(underlying_asset)
