import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.decoding.stakedao.constants import CPT_STAKEDAO
from rotkehlchen.chain.evm.utils import maybe_notify_cache_query_status
from rotkehlchen.constants import ONE
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChecksumEvmAddress, Timestamp, TokenKind
from rotkehlchen.utils.network import request_get_dict

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

STAKEDAO_API: Final = 'https://api.stakedao.org/api'
# This is gotten from:
# https://github.com/stake-dao/api?tab=readme-ov-file#strategies-data
SUPPORTED_STAKEDAO_STRATEGIES: Final = {'curve', 'balancer', 'pendle', 'pancakeswap', 'angle'}


def query_stakedao_gauges(evm_inquirer: 'EvmNodeInquirer') -> None:
    """Query StakeDAO gauges for lockers and strategies from the API and cache them.

    Note that item['token'] in lockers and item['lpToken'] in strategies refer
    to the same concept —- the underlying protocol's pool token.
    """

    def _notify_status(last_ts: Timestamp, total: int, processed: int = 0) -> Timestamp:
        """Helper function to notify cache query status."""
        return maybe_notify_cache_query_status(
            msg_aggregator=evm_inquirer.database.msg_aggregator,
            last_notified_ts=last_ts,
            protocol='StakeDAO',
            chain=evm_inquirer.chain_id,
            processed=processed,
            total=total,
        )

    all_gauges: set[tuple[ChecksumEvmAddress, ChecksumEvmAddress]] = set()
    chain_id = evm_inquirer.chain_id.serialize()
    last_notified_ts, total_count = Timestamp(0), 0
    try:  # Query lockers
        response_data = request_get_dict(url=f'{STAKEDAO_API}/lockers')
        for item in response_data.get('parsed', []):
            try:
                if item['chainId'] != chain_id:
                    continue

                all_gauges.add((
                    deserialize_evm_address(item['modules']['gauge']),
                    deserialize_evm_address(item['token']['address']),
                ))
                total_count += 1
                last_notified_ts = _notify_status(last_ts=last_notified_ts, total=total_count)
            except (KeyError, DeserializationError) as e:
                msg = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
                log.warning(f'Skipping stakedao locker entry {item} due to {msg}')
                continue

        for protocol in SUPPORTED_STAKEDAO_STRATEGIES:  # Query strategies
            response_data = request_get_dict(url=f'{STAKEDAO_API}/strategies/{protocol}')
            for item in response_data.get('deployed', []):
                try:
                    if item['chainId'] != chain_id:
                        continue

                    all_gauges.add((
                        deserialize_evm_address(item['sdGauge']['address']),
                        deserialize_evm_address(item['lpToken']['address']),
                    ))
                    total_count += 1
                    last_notified_ts = _notify_status(last_ts=last_notified_ts, total=total_count)
                except (KeyError, DeserializationError) as e:
                    msg = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
                    log.warning(f'Skipping stakedao strategy entry {item} due to {msg}')
                    continue

    except (RemoteError, UnableToDecryptRemoteData) as e:
        log.error(f'Failed to retrieve StakeDAO gauges for {chain_id} lockers and strategies from API due to {e!s}')  # noqa: E501

    only_gauges, encounter = set(), TokenEncounterInfo(description=f'Querying stakedao gauges for {evm_inquirer.chain_name}', should_notify=False)  # noqa: E501
    for idx, (gauge_token_addr, underlying_addr) in enumerate(all_gauges, start=1):
        try:
            get_or_create_evm_token(
                chain_id=evm_inquirer.chain_id,
                protocol=CPT_STAKEDAO,
                userdb=evm_inquirer.database,
                evm_address=gauge_token_addr,
                evm_inquirer=evm_inquirer,
                encounter=encounter,
                underlying_tokens=[UnderlyingToken(
                    address=get_or_create_evm_token(
                        chain_id=evm_inquirer.chain_id,
                        evm_inquirer=evm_inquirer,
                        userdb=evm_inquirer.database,
                        evm_address=underlying_addr,
                        encounter=encounter,
                    ).evm_address,
                    weight=ONE,
                    token_kind=TokenKind.ERC20,
                )],
            )
            only_gauges.add(gauge_token_addr)
            last_notified_ts = _notify_status(last_ts=last_notified_ts, total=total_count, processed=idx)  # noqa: E501
        except NotERC20Conformant as e:
            log.error(f'Failed to add stake dao gauge {gauge_token_addr} for {evm_inquirer.chain_id} due to {e!s}')  # noqa: E501
            continue

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.STAKEDAO_GAUGES, str(chain_id)),
            values=only_gauges,
        )
