import logging
from typing import TYPE_CHECKING, Final

from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import Asset, UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants import ONE
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.misc import NotERC20Conformant
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value_at_ts,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, EvmTokenKind, Price
from rotkehlchen.utils.misc import ts_now

from .constants import AURA_BOOSTER_ABI, CHAIN_ID_TO_BOOSTER_ADDRESSES, CPT_AURA_FINANCE

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.inquirer import Inquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_aura_pools(evm_inquirer: 'EvmNodeInquirer') -> None:
    """Query and store Aura Finance pools data.

    May raise:
        - RemoteError: If blockchain queries fail
    """
    booster_contract = EvmContract(
        address=CHAIN_ID_TO_BOOSTER_ADDRESSES[evm_inquirer.chain_id],
        abi=AURA_BOOSTER_ABI,
        deployed_block=0,
    )
    latest_pools_count = evm_inquirer.call_contract(
        abi=booster_contract.abi,
        method_name='poolLength',
        contract_address=booster_contract.address,
    )
    cache_key: Final = (CacheType.AURA_POOLS, evm_inquirer.chain_name)
    with GlobalDBHandler().conn.read_ctx() as cursor:
        if (cached_pools_count_str := globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=cache_key,
        )) is None:
            cached_pools_count = 0
        else:
            cached_pools_count = int(cached_pools_count_str)

    now = ts_now()
    if latest_pools_count == cached_pools_count:
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_unique_cache_value_at_ts(
                write_cursor=write_cursor,
                key_parts=cache_key,
                value=str(latest_pools_count),
                timestamp=now,
            )
        return None

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
    if len(results) == 0:
        log.debug(f'No Aura pools found on {evm_inquirer.chain_name}')
        return None

    for idx, result in enumerate(results):
        try:
            pool_info = booster_contract.decode(
                result=result,
                method_name='poolInfo',
                arguments=[idx],
            )
            aura_pool_token_address = to_checksum_address(pool_info[3])
            underlying_bpt_token_address = to_checksum_address(pool_info[0])
        except (IndexError, ValueError) as e:
            log.error(
                f'Failed to decode pool info for index {idx} on {evm_inquirer.chain_name}: {e!s}. '
                'Skipping...',
            )
            continue

        try:
            aura_pool_token = get_or_create_evm_token(
                userdb=evm_inquirer.database,
                evm_address=aura_pool_token_address,
                chain_id=evm_inquirer.chain_id,
                encounter=TokenEncounterInfo(
                    description=f'Querying {evm_inquirer.chain_name} aura finance balances',
                    should_notify=False,
                ),
                underlying_tokens=[
                    UnderlyingToken(
                        address=get_or_create_evm_token(
                            userdb=evm_inquirer.database,
                            chain_id=evm_inquirer.chain_id,
                            evm_address=underlying_bpt_token_address,
                            encounter=TokenEncounterInfo(
                                description=f'Querying {evm_inquirer.chain_name} aura finance balances',  # noqa: E501
                                should_notify=False,
                            ),
                        ).evm_address,
                        token_kind=EvmTokenKind.ERC20,
                        weight=ONE,
                    ),
                ],
                protocol=CPT_AURA_FINANCE,
            )
        except NotERC20Conformant as e:
            log.error(
                f'Failed to create/get token for address {aura_pool_token_address} '
                f'on {evm_inquirer.chain_name}: {e!s}. Skipping...',
            )
            continue

        if aura_pool_token.protocol != CPT_AURA_FINANCE:
            log.debug(
                f'Updating protocol for {evm_inquirer.chain_name} {CPT_AURA_FINANCE} '
                f'asset {aura_pool_token}',
            )
            GlobalDBHandler.set_token_protocol_if_missing(
                token=aura_pool_token,
                new_protocol=CPT_AURA_FINANCE,
            )

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_unique_cache_value_at_ts(
            write_cursor=write_cursor,
            key_parts=cache_key,
            value=str(latest_pools_count),
            timestamp=now,
        )


def get_aura_pool_price(inquirer: 'Inquirer', token: 'EvmToken') -> Price:
    """Get the USD price for an Aura pool token by using its underlying BPT token price."""
    underlying_asset = Asset(evm_address_to_identifier(
        address=token.underlying_tokens[0].address,
        chain_id=token.chain_id,
        token_type=EvmTokenKind.ERC20,
    ))
    return inquirer.find_usd_price(underlying_asset)
