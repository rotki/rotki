import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.decoding.stakedao.constants import CPT_STAKEDAO
from rotkehlchen.constants import ONE
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChecksumEvmAddress, EvmTokenKind
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
    """Query StakeDAO gauges for lockers and strategies from the API and cache them."""
    all_gauges: set[tuple[ChecksumEvmAddress, ChecksumEvmAddress]] = set()
    chain_id = evm_inquirer.chain_id.serialize()
    try:  # Query lockers
        response_data = request_get_dict(url=f'{STAKEDAO_API}/lockers')
        for item in response_data.get('parsed', []):
            try:
                if item['chainId'] != chain_id:
                    continue

                all_gauges.add((
                    deserialize_evm_address(item['modules']['gauge']),
                    deserialize_evm_address(item['sdToken']['address']),  # underlying token
                ))
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
                        deserialize_evm_address(item['vault']),  # underlying token
                    ))
                except (KeyError, DeserializationError) as e:
                    msg = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
                    log.warning(f'Skipping stakedao strategy entry {item} due to {msg}')
                    continue

    except (RemoteError, UnableToDecryptRemoteData) as e:
        log.error(f'Failed to retrieve StakeDAO gauges for {chain_id} lockers and strategies from API due to {e!s}')  # noqa: E501

    only_gauges = set()
    for gauge_token_addr, underlying_addr in all_gauges:
        try:
            get_or_create_evm_token(
                chain_id=evm_inquirer.chain_id,
                protocol=CPT_STAKEDAO,
                userdb=evm_inquirer.database,
                evm_address=gauge_token_addr,
                underlying_tokens=[UnderlyingToken(
                    address=get_or_create_evm_token(
                        chain_id=evm_inquirer.chain_id,
                        evm_inquirer=evm_inquirer,
                        userdb=evm_inquirer.database,
                        evm_address=underlying_addr,
                    ).evm_address,
                    weight=ONE,
                    token_kind=EvmTokenKind.ERC20,
                )],
            )
            only_gauges.add(gauge_token_addr)
        except NotERC20Conformant as e:
            log.error(f'Failed to add stake dao gauge {gauge_token_addr} for {evm_inquirer.chain_id} due to {e!s}')  # noqa: E501
            continue

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.STAKEDAO_GAUGES, str(chain_id)),
            values=only_gauges,
        )
