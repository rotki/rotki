import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token
from rotkehlchen.chain.evm.decoding.stakedao.constants import CPT_STAKEDAO
from rotkehlchen.chain.evm.utils import maybe_notify_cache_query_status
from rotkehlchen.constants import ONE
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChecksumEvmAddress, EVMTxHash, Timestamp, TokenKind
from rotkehlchen.utils.network import request_get_dict

if TYPE_CHECKING:
    from eth_typing.abi import ABI

    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

STAKEDAO_API: Final = 'https://api.stakedao.org/api'
# This is gotten from:
# https://github.com/stake-dao/api?tab=readme-ov-file#strategies-data
SUPPORTED_STAKEDAO_STRATEGIES: Final = {'curve', 'balancer', 'pendle', 'pancakeswap', 'angle'}
GAUGE_COMPACT_ABI: Final['ABI'] = [{'stateMutability': 'view', 'type': 'function', 'name': 'staking_token', 'inputs': [], 'outputs': [{'name': '', 'type': 'address'}]}]  # noqa: E501
LIQUITY_GAUGE_ABI: Final['ABI'] = [{'inputs': [], 'name': 'token', 'outputs': [{'name': '', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501


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

    all_gauges: set[ChecksumEvmAddress] = set()
    chain_id = evm_inquirer.chain_id.serialize()
    last_notified_ts, total_count = Timestamp(0), 0
    try:  # Query lockers
        response_data = request_get_dict(url=f'{STAKEDAO_API}/lockers')
        for item in response_data.get('parsed', []):
            try:
                if item['chainId'] != chain_id:
                    continue

                all_gauges.add(deserialize_evm_address(item['modules']['gauge']))
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

                    all_gauges.add(deserialize_evm_address(item['sdGauge']['address']))
                    total_count += 1
                    last_notified_ts = _notify_status(last_ts=last_notified_ts, total=total_count)
                except (KeyError, DeserializationError) as e:
                    msg = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
                    log.warning(f'Skipping stakedao strategy entry {item} due to {msg}')
                    continue

    except (RemoteError, UnableToDecryptRemoteData) as e:
        log.error(f'Failed to retrieve StakeDAO gauges for {chain_id} lockers and strategies from API due to {e!s}')  # noqa: E501

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.STAKEDAO_GAUGES, str(chain_id)),
            values=all_gauges,
        )

    last_notified_ts = _notify_status(last_ts=last_notified_ts, total=total_count, processed=total_count)  # noqa: E501


def ensure_gauge_token(
        gauge_address: ChecksumEvmAddress,
        evm_inquirer: 'EvmNodeInquirer',
        tx_hash: 'EVMTxHash',
) -> None:
    """Ensure that StakeDao tokens are present in the database

    Since we don't store all the tokens in the database this logic checks if
    we already have the token in the db with the right information and if that
    is not the case then it queries the chain to get the underlying token and
    create/update the token locally.

    May raise:
        - RemoteError
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        if (row := cursor.execute(
            'SELECT parent.protocol FROM evm_tokens AS parent '
            'JOIN underlying_tokens_list AS ut ON parent.identifier=ut.parent_token_entry '
            'JOIN evm_tokens AS underlying ON underlying.identifier=ut.identifier '
            'WHERE parent.address=? AND parent.chain=?',
            (gauge_address, evm_inquirer.chain_id.serialize_for_db()),
        ).fetchone()) is not None and row[0] == CPT_STAKEDAO:
            return  # nothing to do, token exists with correct protocol and underlying token

    try:
        staking_token = evm_inquirer.call_contract(
            contract_address=gauge_address,
            abi=GAUGE_COMPACT_ABI,
            method_name='staking_token',
        )
        underlying_addr = evm_inquirer.call_contract(
            contract_address=staking_token,
            abi=LIQUITY_GAUGE_ABI,
            method_name='token',
        )
    except RemoteError as e:
        log.error(
            f'Failed to pull stakedao token information for {gauge_address} at '
            f'{evm_inquirer.chain_id} due to {e}',
        )
        return

    encounter = TokenEncounterInfo(tx_ref=tx_hash, should_notify=False)
    get_or_create_evm_token(  # ensure that the token is edited and correct
        chain_id=evm_inquirer.chain_id,
        protocol=CPT_STAKEDAO,
        userdb=evm_inquirer.database,
        evm_address=gauge_address,
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
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
