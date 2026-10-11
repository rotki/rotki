import json
import logging
import re
from collections import defaultdict
from threading import Lock
from typing import TYPE_CHECKING, Any, Final, Literal

from rotkehlchen.api.websockets.typedefs import UserMessageRecord
from rotkehlchen.chain.ethereum.modules.eth2.beacon import BeaconInquirer
from rotkehlchen.chain.evm.transactions import CHAIN_TOP_LAG
from rotkehlchen.chain.evm.types import EvmIndexer
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS, HOUR_IN_SECONDS, YEAR_IN_SECONDS
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.eth2 import DBEth2, IncludeExcludeFilterData
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.api import PremiumPermissionError
from rotkehlchen.errors.misc import (
    APIKeyNotAvailable,
    ChainNotSupported,
    IndexerRangeStartsLater,
    InputError,
    RemoteError,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan import EtherscanAccountHistory
from rotkehlchen.externalapis.nuthatch import Nuthatch
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.eth2 import EthBlockEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium, UserLimitType, get_user_limit, has_premium_check
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_address,
    deserialize_fval,
    deserialize_int,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Eth2PubKey,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.user_messages import NetworkFailure
from rotkehlchen.utils.data_structures import LRUCacheWithRemove
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import from_wei, ts_now, ts_sec_to_ms

from .constants import (
    CPT_ETH2,
    MAX_EFFECTIVE_BALANCE,
    MIN_EFFECTIVE_BALANCE,
    UNKNOWN_VALIDATOR_INDEX,
)
from .structures import (
    PerformanceStatusFilter,
    ValidatorDetailsWithStatus,
    ValidatorID,
)
from .utils import (
    create_profit_filter_queries,
    merge_nest_ranges,
    nest_range_settled,
    nest_ranges,
    timestamp_to_slot,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.accounting.structures.balance import Balance
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.beaconchain.service import BeaconChain
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ETH_STAKED_CACHE_TIME: Final = 7200  # 2 hours in seconds
BLOCK_REWARD_SEQUENCE: Final = 0
MEV_REWARD_SEQUENCE: Final = 1


class Eth2(EthereumModule):
    """Module representation for Eth2"""

    def __init__(
            self,
            ethereum_inquirer: EthereumInquirer,
            database: DBHandler,
            premium: Premium | None,
            msg_aggregator: MessagesAggregator,
            beaconchain: BeaconChain,
            beacon_rpc_endpoint: str | None,
    ) -> None:
        self.database = database
        self.premium = premium
        self.ethereum = ethereum_inquirer
        self.beacon_inquirer = BeaconInquirer(
            rpc_endpoint=beacon_rpc_endpoint,
            beaconchain=beaconchain,
        )
        self.msg_aggregator = msg_aggregator
        self._told_nest_coverage_incomplete = False
        self.last_stats_query_ts = 0
        self.validator_stats_queried = 0
        self.deposits_re = re.compile(r'.*validator with pubkey (?P<pubkey>.*)\. Deposit.*|.*Deposit.*ETH to validator (?P<index>\d+)$')  # noqa: E501
        self.withdrawals_query_lock = Lock()
        # Each entry stores the filter args it was computed with alongside the result,
        # so that reading and validating the cache is a single atomic get: keeping the
        # args in a separate attribute allowed a concurrent get_performance with other
        # filters to pair one request's args with another request's result
        self.performance_cache: LRUCacheWithRemove[tuple[Timestamp, Timestamp], tuple[tuple[list[ChecksumEvmAddress] | None, list[int] | None, PerformanceStatusFilter], dict[str, dict]]] = LRUCacheWithRemove(maxsize=3)  # noqa: E501
        # Total staked cache variables
        self._cached_total_staked: FVal
        self._cached_staked_timestamp = Timestamp(0)

    def _get_closest_performance_cache_key(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> tuple[Timestamp, Timestamp]:
        """Check if there is any close timestamps in the performance cache and returns them"""
        # snapshot_keys: the unlocked live iterator would raise RuntimeError if another
        # thread's get()/add() reorders the underlying OrderedDict mid-iteration
        for key_from_ts, key_to_ts in self.performance_cache.snapshot_keys():
            if abs(key_from_ts - from_ts) <= HOUR_IN_SECONDS * 12 and abs(key_to_ts - to_ts) <= HOUR_IN_SECONDS * 2:  # noqa: E501
                return key_from_ts, key_to_ts

        return from_ts, to_ts

    def _set_staked_cache(self, value: FVal, timestamp: Timestamp) -> None:
        """Set or reset the cached total staked amount"""
        self._cached_total_staked = value
        self._cached_staked_timestamp = timestamp

    def _get_total_eth_staked(self) -> FVal:
        """Calculate total ETH staked by all tracked validators

        Results are cached for a few hours to avoid expensive repeated calculations.
        """
        if (now := ts_now()) - self._cached_staked_timestamp <= ETH_STAKED_CACHE_TIME:
            return self._cached_total_staked

        dbeth2 = DBEth2(self.database)
        with self.database.conn.read_ctx() as cursor:
            pubkey_to_ownership = dbeth2.get_active_pubkeys_to_ownership(cursor)

        if len(pubkey_to_ownership) == 0:
            self._set_staked_cache(ZERO, now)
            return ZERO

        balance_mapping = self.beacon_inquirer.get_balances(
            indices_or_pubkeys=list(pubkey_to_ownership.keys()),
            has_premium=self.premium is not None,
        )

        total_staked = ZERO
        for pubkey, balance in balance_mapping.items():
            ownership = pubkey_to_ownership.get(pubkey, ONE)
            total_staked += balance.amount * ownership

        self._set_staked_cache(total_staked, now)
        return total_staked

    def _check_eth_staking_limit(self, validator_balance: FVal, ownership_proportion: FVal) -> None:  # noqa: E501
        """Check if adding more stake would exceed ETH staking limit

        May raise:
        - PremiumPermissionError if the limit would be exceeded
        - RemoteError if balances could not be queried
        """
        if validator_balance == ZERO and ownership_proportion == ZERO:
            return

        current_staked = self._get_total_eth_staked()
        additional_stake = validator_balance * ownership_proportion
        new_total = current_staked + additional_stake

        limit, _ = get_user_limit(self.premium, UserLimitType.ETH_STAKED)

        if new_total > limit:
            raise PremiumPermissionError(
                f'ETH staking limit exceeded. Current staked: {current_staked} ETH, '
                f'limit: {limit} ETH. Would be: {new_total} ETH',
                extra_dict={
                    'limit_info': {
                        'current_staked': str(current_staked),
                        'staking_limit': str(limit),
                    },
                },
            )

    def get_balances(
            self,
            addresses: Sequence[ChecksumEvmAddress],
            fetch_validators_for_eth1: bool,
    ) -> dict[Eth2PubKey, Balance]:
        """
        Returns a mapping of validator public key to eth balance.
        If fetch_validators_for_eth1 is true then each eth1 address is also checked
        for the validators it has deposited and the deposits are fetched.

        May Raise:
        - RemoteError from beaconcha.in api
        """
        dbeth2 = DBEth2(self.database)
        if fetch_validators_for_eth1:
            try:
                self.detect_and_refresh_validators(addresses)
            except RemoteError as e:
                log.error(f'Skipping eth2 validator detection during balance query due to {e!s}')

        with self.database.conn.read_ctx() as cursor:
            pubkey_to_ownership = dbeth2.get_active_pubkeys_to_ownership(cursor)

        if len(pubkey_to_ownership) == 0:
            return {}  # nothing detected

        balances = self.beacon_inquirer.get_balances(
            indices_or_pubkeys=list(pubkey_to_ownership.keys()),
            has_premium=has_premium_check(self.premium),
        )
        for pubkey, balance in balances.items():
            if (ownership_proportion := pubkey_to_ownership.get(pubkey, ONE)) != ONE:
                balances[pubkey] = balance * ownership_proportion

        return balances

    @staticmethod
    def _time_weighted_balance_sum(
            balance_data: dict[TimestampMS, FVal],
            from_ts_ms: TimestampMS,
            to_ts_ms: TimestampMS,
    ) -> FVal:
        """Calculate the sum of (balance * time) for APR calculation.
        This is the core calculation needed for proper APR with balance changes.
        Works in milliseconds like the original _time_weighted_average function.
        """
        if len(balance_data) == 0:
            return ZERO
        elif len(balance_data) == 1:
            return next(iter(balance_data.values())) * (to_ts_ms - from_ts_ms)

        sorted_times = sorted(balance_data.keys())
        filtered_times = [ts for ts in sorted_times if from_ts_ms <= ts <= to_ts_ms]
        if len(filtered_times) == 0:  # There are no timestamps in the range specified.
            # First try to use the value at the latest timestamp before to_ts_ms
            if len(before_ts_list := [ts for ts in sorted_times if ts <= to_ts_ms]) != 0:
                balance = balance_data[before_ts_list[-1]]
            else:  # If none before to_ts_ms, simply use the earliest ts
                balance = balance_data[sorted_times[0]]
            return balance * (to_ts_ms - from_ts_ms)

        total_balance_time = ZERO
        filtered_times.append(to_ts_ms)
        for idx, current_ts in enumerate(filtered_times[:-1]):
            # sum += balance * duration for which this was the balance
            total_balance_time += balance_data[current_ts] * (filtered_times[idx + 1] - current_ts)

        return total_balance_time

    def get_performance(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            limit: int,
            offset: int,
            ignore_cache: bool,
            addresses: list[ChecksumEvmAddress] | None = None,
            validator_indices: list[int] | None = None,
            status: PerformanceStatusFilter = PerformanceStatusFilter.ALL,
    ) -> dict[str, Any]:
        """Calculate and return the performance since the given timestamp for each validator.

        Optionally filtered by:
        - execution address/es (associated as either deposit or withdrawal address)
        - validator indices

        May raise:
        - PremiumPermissionError if ETH staking limit is exceeded for non-premium users
        """
        # Check ETH staking limit for non-premium users
        self._check_eth_staking_limit(ZERO, ZERO)
        cache_key = self._get_closest_performance_cache_key(from_ts, to_ts)
        with self.database.conn.read_ctx() as cursor:
            result = cursor.execute('SELECT COUNT(*) FROM eth2_validators').fetchone()
            total_validators = result[0] if result[0] is not None else 0

        if (
                not ignore_cache and
                (cache_entry := self.performance_cache.get(cache_key)) is not None and
                cache_entry[0] == (addresses, validator_indices, status) and
                (result := cache_entry[1])
        ):  # return pagination on cached data
            return {
                'validators': dict(list(result['validators'].items())[offset: offset + limit]),
                'sums': result['sums'],
                'entries_total': total_validators,
                'entries_found': len(result['validators']),
            }

        index_to_pubkey, index_to_activation_ts, index_to_withdrawable_ts = {}, {}, {}
        dbeth2 = DBEth2(self.database)
        all_validator_indices = set()
        with self.database.conn.read_ctx() as cursor:
            for entry in cursor.execute('SELECT validator_index, public_key, activation_timestamp, withdrawable_timestamp FROM eth2_validators WHERE validator_index IS NOT NULL'):  # noqa: E501
                index_to_pubkey[entry[0]] = entry[1]
                if entry[2] is not None:
                    index_to_activation_ts[entry[0]] = entry[2]
                if entry[3] is not None:
                    index_to_withdrawable_ts[entry[0]] = entry[3]
                all_validator_indices.add(entry[0])
            pubkey_to_index = {x[1]: x[0] for x in cursor.execute('SELECT validator_index, public_key FROM eth2_validators WHERE validator_index IS NOT NULL')}  # noqa: E501

        to_filter_indices, to_query_indices = None, None
        if validator_indices is not None:
            to_filter_indices = set(validator_indices)
            to_query_indices = to_filter_indices

        if status != PerformanceStatusFilter.ALL:
            with self.database.conn.read_ctx() as cursor:
                if status == PerformanceStatusFilter.ACTIVE:
                    got_indices = dbeth2.get_active_validator_indices(cursor)
                elif status == PerformanceStatusFilter.CONSOLIDATED:
                    got_indices = set(dbeth2.get_consolidated_validators(cursor))
                else:  # can only be EXITED
                    got_indices = dbeth2.get_exited_validator_indices(
                        cursor=cursor,
                        validator_indices=validator_indices,
                    )

            to_filter_indices = got_indices if to_filter_indices is None else to_filter_indices & got_indices  # noqa: E501
            to_query_indices = got_indices if to_query_indices is None else to_query_indices & got_indices  # noqa: E501

        if addresses is not None:
            with self.database.conn.read_ctx() as cursor:
                associated_indices = dbeth2.get_associated_with_addresses_validator_indices(
                    cursor=cursor,
                    addresses=addresses,
                )
            to_query_indices = associated_indices if to_query_indices is None else to_query_indices & associated_indices  # noqa: E501
            # also add the to_filter_indices since this will enable deposit association
            # to validator index by address. We need to do this instead of adding
            # addresses to filter arguments since then we would be ANDing the filters
            # which would end up returning no values for many validators
            to_filter_indices = associated_indices if to_filter_indices is None else to_filter_indices | associated_indices  # noqa: E501

        with self.database.conn.read_ctx() as cursor:
            accounts = self.database.get_blockchain_accounts(cursor)

        balances_over_time, withdrawals_pnl, exits_pnl = dbeth2.process_validators_balances_and_pnl(  # noqa: E501
            from_ts=from_ts,
            to_ts=to_ts,
            validator_indices=to_filter_indices,
        )
        blocks_execution_filter_query, mev_execution_filter_query = create_profit_filter_queries(
            from_ts=from_ts,
            to_ts=to_ts,
            validator_indices=list(to_filter_indices) if to_filter_indices is not None else None,
            tracked_addresses=accounts.eth,  # needed to exclude block recipients not tracked
        )

        with self.database.conn.read_ctx() as cursor:
            blocks_rewards_amounts, mev_rewards_amounts = dbeth2.get_validators_block_and_mev_rewards(  # noqa: E501
                cursor=cursor,
                blocks_execution_filter_query=blocks_execution_filter_query,
                mev_execution_filter_query=mev_execution_filter_query,
                to_filter_indices=to_filter_indices,
            )

        pnls: defaultdict[int, dict] = defaultdict(dict)
        sums: defaultdict[str, FVal] = defaultdict(FVal)
        for key_label, mapping in (
                ('withdrawals', withdrawals_pnl),
                ('exits', exits_pnl),
                ('execution_blocks', blocks_rewards_amounts),
                ('execution_mev', mev_rewards_amounts),
        ):
            for vindex, amount in mapping.items():
                if amount == ZERO:
                    continue

                pnls[vindex][key_label] = amount
                pnls[vindex]['sum'] = pnls[vindex].get('sum', ZERO) + amount
                sums[key_label] += amount
                sums['sum'] += amount

        # if we check until a recent timestamp we should also take into account
        # outstanding rewards not yet withdrawn
        now = ts_now()
        if to_query_indices is None:
            to_query_indices = all_validator_indices

        if now - to_ts <= DAY_IN_SECONDS:
            _, accumulating_validators = dbeth2.group_validators_by_type(
                database=self.database,
                validator_indices=to_query_indices,
            )
            balances = self.beacon_inquirer.get_balances(
                indices_or_pubkeys=list(to_query_indices),
                has_premium=has_premium_check(self.premium),
            )
            for pubkey, balance in balances.items():
                if balance.amount == ZERO:
                    continue

                entry = pnls[v_index := pubkey_to_index[pubkey]]
                if 'exits' in entry:
                    continue  # no outstanding balance for exits

                if v_index in accumulating_validators:
                    if balance.amount < MAX_EFFECTIVE_BALANCE:
                        continue  # no outstanding balance for accumulating validators with balance less than 2048  # noqa: E501
                    max_balance = MAX_EFFECTIVE_BALANCE
                else:
                    max_balance = MIN_EFFECTIVE_BALANCE

                # consolidated validators with pending withdrawals have small balances below max_balance,  # noqa: E501
                # causing negative outstanding rewards. so, take absolute value to avoid negatives and  # noqa: E501
                # cap at actual balance since outstanding rewards can't exceed validator holdings
                outstanding_pnl = min(abs(balance.amount - max_balance), balance.amount)
                entry['outstanding_consensus_pnl'] = outstanding_pnl
                sums['outstanding_consensus_pnl'] += outstanding_pnl
                entry['sum'] = entry.get('sum', ZERO) + outstanding_pnl
                sums['sum'] += outstanding_pnl

        sum_apr, count_apr = ZERO, ZERO
        for vindex, data in pnls.items():
            count_apr += 1
            if (validator_sum := data.get('sum')) is None:
                continue

            profit_from_ts = max(index_to_activation_ts.get(vindex, from_ts), from_ts)
            profit_to_ts = min(index_to_withdrawable_ts.get(vindex, to_ts), to_ts)

            # Calculate APR for all validators
            # APR is total_profits * YEAR_IN_SECONDS divided by sum(balance_i * time_i)
            balance_time_sum_ms = self._time_weighted_balance_sum(
                balance_data=balances_over_time[vindex],
                from_ts_ms=ts_sec_to_ms(profit_from_ts),
                to_ts_ms=ts_sec_to_ms(profit_to_ts),
            )
            # Convert balance_time_sum from milliseconds to seconds for APR calculation
            balance_time_sum_seconds = balance_time_sum_ms / 1000

            data['apr'] = (
                (validator_sum * YEAR_IN_SECONDS) / balance_time_sum_seconds
                if balance_time_sum_seconds > ZERO else ZERO
            )
            sum_apr += data['apr']

        if count_apr != ZERO:
            sums['apr'] = sum_apr / count_apr

        result = {'validators': pnls, 'sums': sums}
        # save cache & return pagination on the data
        self.performance_cache.add(cache_key, ((addresses, validator_indices, status), result))
        return {
            'validators': dict(list(result['validators'].items())[offset: offset + limit]),
            'sums': result['sums'],
            'entries_total': total_validators,
            'entries_found': len(result['validators']),
        }

    def _get_saved_deposit_validators(self) -> dict[ChecksumEvmAddress, set[int | Eth2PubKey]]:
        """Read the decoded DB history events to find deposit validators by address.

        Handles both entry types:
        1. 'Deposit X ETH to validator with pubkey {pubkey}...'
        2. 'Deposit X ETH to validator {validator_index}'
        """
        dbevents = DBHistoryEvents(self.database)
        with self.database.conn.read_ctx() as cursor:
            deposit_events = dbevents.get_history_events_internal(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(
                    type_and_subtype_combinations=[
                        (HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET),
                    ],
                    counterparties=[CPT_ETH2],
                    entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.EVM_EVENT, HistoryBaseEntryType.ETH_DEPOSIT_EVENT]),  # noqa: E501
                ),
            )

        validators: dict[ChecksumEvmAddress, set[int | Eth2PubKey]] = defaultdict(set)
        for event in deposit_events:
            if (notes := event.notes_or_auto()) is None:
                log.error(f'Could not match extraction regex for {event} due to absence of notes')  # should not really happen  # noqa: E501
                continue

            # Check if it matches either type 1 (with pubkey) or type 2 (with validator index)
            if (match := self.deposits_re.match(notes)) is not None:
                if (location_label := event.location_label) is None:
                    log.error('Could not find depositor address for eth2 deposit', notes=notes)
                    continue
                try:
                    depositor = deserialize_evm_address(location_label)
                except DeserializationError:
                    log.error('Could not deserialize eth2 depositor address', location_label=location_label, notes=notes)  # noqa: E501
                    continue

                if (pubkey := match.group('pubkey')) is not None:
                    validators[depositor].add(Eth2PubKey(pubkey))
                elif (validator_index := getattr(event, 'validator_index', None)) is not None:
                    validators[depositor].add(validator_index)
                else:
                    validators[depositor].add(int(match.group('index')))
            else:
                log.error('Could not match eth2 deposit extraction regex', notes=notes)

        return validators

    def _get_saved_deposit_addresses(self) -> set[ChecksumEvmAddress]:
        """Read the decoded DB history events to find addresses with ETH2 deposits."""
        return set(self._get_saved_deposit_validators())

    def query_services_for_validator_withdrawals(
            self,
            addresses: Sequence[ChecksumEvmAddress],
            to_ts: Timestamp,
    ) -> None:
        """Goes through all given addresses, queries for the latest withdrawals
        and saves them in the DB. Uses multiple sources. Also detects which of
        these withdrawals may have been exits.
        """
        with self.withdrawals_query_lock:
            for address in addresses:
                self.query_single_address_withdrawals(address, to_ts)

            self.detect_exited_validators()

    def _fetch_withdrawals_from_external_sources(
            self,
            address: ChecksumEvmAddress,
            period: TimestampOrBlockRange | None,
    ) -> set[int] | None:
        """Query the indexers that answer withdrawals as etherscan does (etherscan, and a nuthatch
        nest) in the configured order, etherscan always among them, with a blockscout fallback.
        Without a block range, only blockscout, which takes none, is asked.
        Returns untracked validator indices, or None if every source fails.
        """
        sources: list[EtherscanAccountHistory] = [
            indexer for _, indexer in self.ethereum._get_indexers_in_order()
            if isinstance(indexer, EtherscanAccountHistory)
        ]
        if self.ethereum.etherscan not in sources:  # tried before blockscout, as it always was
            sources.append(self.ethereum.etherscan)
        for source in sources:
            if period is None:
                break
            try:
                return source.get_withdrawals(address=address, period=period)
            except (DeserializationError, RemoteError) as e:
                log.error(
                    'Failed to query ethereum withdrawals for %s through %s due to %s. '
                    'Will try the next source.',
                    address,
                    source.name,
                    e,
                )

        try:
            return self.ethereum.blockscout.query_withdrawals(address)
        except (DeserializationError, RemoteError, KeyError) as othere:
            msg = str(othere)
            if isinstance(othere, KeyError):
                msg = f'Missing key entry for {msg}'
            log.error(f'Failed to query ethereum withdrawals for {address} through blockscout due to {msg}. Bailing out for now.')  # noqa: E501

        return None

    def query_single_address_withdrawals(self, address: ChecksumEvmAddress, to_ts: Timestamp) -> None:  # noqa: E501
        to_ts = self._staking_query_end(to_ts)
        with self.database.conn.read_ctx() as cursor:
            # Get the last query timestamp for this address and a count of this address's
            # validators that are either active, exited but never queried, or exited and
            # queried but exited_timestamp is after last query timestamp.
            key_name = DBCacheDynamic.WITHDRAWALS_TS.get_db_key(address=address)
            last_query, validator_count = cursor.execute(
                'SELECT kv.value, COUNT(*) FROM eth2_validators ev '
                'LEFT JOIN key_value_cache kv ON kv.name=? WHERE ev.withdrawal_address=? AND '
                '(ev.exited_timestamp IS NULL OR kv.name IS NULL OR ev.exited_timestamp > kv.value)',  # noqa: E501
                (key_name, address),
            ).fetchone()

        if validator_count == 0:
            return

        from_ts = Timestamp(0)
        if (
            last_query is not None and
            to_ts - (from_ts := Timestamp(int(last_query))) <= HOUR_IN_SECONDS * 3
        ):
            return

        log.debug(f'Querying {address} ETH withdrawals from {from_ts} to {to_ts}')
        try:
            period: TimestampOrBlockRange | None = self.ethereum.maybe_timestamp_to_block_range(TimestampOrBlockRange('timestamps', from_ts, to_ts))  # noqa: E501
        except RemoteError as e:  # blockscout, which takes no range, can still answer
            log.warning(f'Could not turn the withdrawals range of {address} into blocks: {e!s}')
            period = None
        untracked_validator_indices = self._fetch_withdrawals_from_external_sources(address, period)  # noqa: E501
        if untracked_validator_indices is None:
            # Nothing is recorded, so the next query asks for the same range again.
            self.msg_aggregator.add_warning(
                f'Could not query the ethereum withdrawals of {address} from any source. '
                'They will be retried by the next query.',
                classification=NetworkFailure(record=UserMessageRecord.VALIDATOR, error='every withdrawals source failed'),  # noqa: E501
                subject=Location.ETHEREUM,
            )
            return

        # pull data for newly detected validators and save them in the DB
        details = self.beacon_inquirer.get_validator_data(indices_or_pubkeys=list(untracked_validator_indices))  # noqa: E501
        with self.database.user_write() as write_cursor:
            DBEth2(self.database).add_or_update_validators_except_ownership(
                write_cursor,
                validators=details,
            )
            self.database.set_dynamic_cache(
                write_cursor=write_cursor,
                name=DBCacheDynamic.WITHDRAWALS_TS,
                value=to_ts,
                address=address,
            )

    def detect_and_refresh_validators(self, addresses: Sequence[ChecksumEvmAddress]) -> None:
        """Go through the list of eth1 addresses and find all eth2 validators associated
        with them via deposit along with their details.

        May raise RemoteError due to beaconcha.in or beacon node connection"""
        with self.database.conn.read_ctx() as cursor:  # get non finalized saved validator
            cursor.execute('SELECT validator_index, public_key FROM eth2_validators WHERE withdrawable_timestamp IS NULL AND exited_timestamp IS NULL')  # noqa: E501
            validators_to_refresh = {ValidatorID(index=x[0], public_key=x[1]) for x in cursor}

        # Prefer validator identifiers parsed from decoded deposit events. Beaconcha.in V2 may
        # reject deposit_address selectors depending on the API subscription tier.
        known_pubkeys = {validator.public_key for validator in validators_to_refresh}
        saved_deposit_validators = self._get_saved_deposit_validators()
        saved_validator_indices = set()
        for address, validator_identifiers in saved_deposit_validators.items():
            if address not in addresses:
                continue

            for identifier in validator_identifiers:
                if isinstance(identifier, int):
                    saved_validator_indices.add(identifier)
                else:
                    if identifier in known_pubkeys:
                        continue

                    validators_to_refresh.add(ValidatorID(index=None, public_key=identifier))
                    known_pubkeys.add(identifier)

        # refresh validator data. Use index if existing otherwise public key
        details = self.beacon_inquirer.get_validator_data(
            indices_or_pubkeys=[
                *(x.index if x.index is not None else x.public_key for x in validators_to_refresh),
                *saved_validator_indices,
            ],
        )
        with self.database.user_write() as write_cursor:
            DBEth2(self.database).add_or_update_validators_except_ownership(
                write_cursor,
                validators=details,
            )

        # Invalidate cache if any validators were added/updated
        self._set_staked_cache(ZERO, Timestamp(0))

    def get_validators(
            self,
            ignore_cache: bool,
            addresses: Sequence[ChecksumEvmAddress],
            validator_indices: set[int] | None,
    ) -> list[ValidatorDetailsWithStatus]:
        """Go through the list of eth1 addresses and find all eth2 validators associated
        with them along with their details.

        Also optionally filter returned data by a set of validator_indices

        May raise RemoteError due to beaconcha.in or beacon node connection"""
        if ignore_cache:
            self.detect_and_refresh_validators(addresses)

        with self.database.conn.read_ctx() as cursor:
            return DBEth2(self.database).get_validators_with_status(cursor, validator_indices)

    def add_validator(
            self,
            validator_index: int | None,
            public_key: Eth2PubKey | None,
            ownership_proportion: FVal,
    ) -> None:
        """Adds the given validator to the DB. Due to marshmallow here at least
        either validator_index or public key is not None.

        May raise:
        - RemoteError if there is a problem with querying beaconcha.in or beacon node for more info
        - InputError if the validator is already in the DB
        - PremiumPermissionError if adding this validator would exceed ETH staking limits
        """
        dbeth2 = DBEth2(self.database)

        query_key: int | Eth2PubKey
        field: Literal['validator_index', 'public_key']
        if validator_index is not None:
            query_key = validator_index
            field = 'validator_index'
        else:  # guaranteed to exist by marshmallow
            query_key = public_key  # type: ignore
            field = 'public_key'

        with self.database.conn.read_ctx() as cursor:
            if dbeth2.validator_exists(cursor, field=field, arg=query_key):
                raise InputError(f'Validator {query_key} already exists in the DB')

        # at this point we gotta refresh validator data
        result = self.beacon_inquirer.get_validator_data(indices_or_pubkeys=[query_key])  # mypy fails to see it's a list of one # type: ignore  # noqa: E501

        if len(result) != 1:
            raise RemoteError(
                f'Validator data for {query_key} could not be found. Likely invalid validator.')

        if result[0].validator_index is None:
            raise RemoteError(f'Validator {result[0].public_key} has no index assigned yet')

        # Get the actual validator balance (to check the staking limit)
        balance_mapping = self.beacon_inquirer.get_balances(
            indices_or_pubkeys=[result[0].public_key],
            has_premium=self.premium is not None,
        )
        if (validator_balance := balance_mapping.get(result[0].public_key)) is None:
            raise RemoteError(f'No balance was returned for validator {result[0].public_key}')

        # Check ETH staking limit with actual validator balance
        self._check_eth_staking_limit(validator_balance.amount, ownership_proportion)

        result[0].ownership_proportion = ownership_proportion
        with self.database.user_write() as write_cursor:
            # by now we have a valid index and pubkey. Add to DB
            dbeth2.add_or_update_validators(write_cursor, [result[0]])

        # Invalidate cache since we added a new validator
        self._set_staked_cache(ZERO, Timestamp(0))

    def _fetch_validated_blocks_from_external_sources(
            self,
            address: ChecksumEvmAddress,
            period: TimestampOrBlockRange,
            only: EvmIndexer | None = None,
    ) -> list[dict[str, Any]] | None:
        """Query produced blocks from available indexers in the user-defined order.

        Returns None if all indexers fail with ChainNotSupported, NotImplementedError, or
        RemoteError.

        May raise:
        - Any unexpected exception raised by an indexer implementation.
        """
        tried_indexers = []
        for name, indexer in self.ethereum._get_indexers_in_order():
            if only is not None and name != only:
                continue
            # The fallback asks by withdrawal address and moves validators on from the answer,
            # which a nest's answer, address coverage through its finalized head, cannot support.
            if only is None and name == EvmIndexer.NUTHATCH:
                continue
            tried_indexers.append(indexer.name)
            try:
                return indexer.get_validated_blocks(address=address, period=period)
            except (ChainNotSupported, NotImplementedError, RemoteError) as e:
                log.warning(f'Failed to query ethereum validated blocks for {address} through {indexer.name} due to {e}. Will try next indexer.')  # noqa: E501

        log.error(
            f'Failed to query ethereum validated blocks for {address}. '
            f'No indexer from the configured order could provide them. Tried: {tried_indexers}',
        )
        return None

    @staticmethod
    def _deserialize_validated_block(entry: dict[str, Any]) -> tuple[int, Timestamp, FVal]:
        """Deserialize an indexer block-production entry.

        May raise:
        - DeserializationError if required fields are missing or malformed.
        - TypeError or ValueError if field values have unexpected types.
        """
        if (block_number_str := entry.get(
            'blockNumber', entry.get('block_number', entry.get('height')),
        )) is None:
            raise DeserializationError('Missing block number in validated block entry')
        if (timestamp_str := entry.get('timeStamp', entry.get('timestamp'))) is None:
            raise DeserializationError('Missing timestamp in validated block entry')

        block_number = deserialize_int(block_number_str, location='validated blocks query')
        timestamp = deserialize_timestamp(timestamp_str)
        reward = from_wei(deserialize_fval(
            value=entry.get('blockReward', entry.get('block_reward', entry.get('reward', 0))),
            name='block reward',
            location='validated blocks query',
        ))
        return block_number, timestamp, reward

    def _get_proposer_index_for_validated_block(
            self,
            block_number: int,
            timestamp: Timestamp,
            active_indices: list[int],
            allow_sole_active: bool = True,
    ) -> int | None:
        """Determine which tracked validator proposed an execution block.

        A configured beacon node is authoritative. If it cannot answer, return None instead of
        falling back to a heuristic. Without a beacon node, an indexer's block found by a
        validator's withdrawal address is attributed when a single tracked validator was active
        for that address at the block timestamp, unless `allow_sole_active` is off: a nest finds
        blocks by any tracked address, which says nothing about who proposed them.
        """
        if self.beacon_inquirer.node is not None:
            try:
                proposer_index = self.beacon_inquirer.node.query_block_proposer(
                    slot=timestamp_to_slot(timestamp),
                )
            except (KeyError, ValueError, RemoteError) as e:
                log.error(f'Failed to query proposer for produced block {block_number} due to {e!s}')  # noqa: E501
                return None
            else:
                return proposer_index if proposer_index in active_indices else None

        if allow_sole_active and len(active_indices) == 1:
            return active_indices[0]

        log.error(f'Could not determine proposer for produced block {block_number} without a beacon node and with multiple active validators')  # noqa: E501
        return None

    def _get_and_store_produced_blocks_from_indexers(
            self,
            indices: list[int],
            update_cache: bool,
    ) -> bool:
        """Get produced blocks via the indexers other than a nuthatch nest, as the fallback when
        beaconcha.in is unavailable.

        Etherscan and Blockscout expose produced blocks by execution-layer address, while rotki
        tracks produced-block freshness and PnL by validator index. To bridge this, load the
        requested validators in DB chunks, group them by withdrawal address, and query each address
        once for the union of the validators' active/non-cached time ranges. Each returned block is
        then filtered back to validators active at the block timestamp. If a beacon node is
        configured, use it to confirm the proposer index for the execution block slot; otherwise
        only attribute the block when exactly one queried validator was active for that address at
        that timestamp. The per-validator produced-block query cache is updated after successful
        processing.

        Returns whether every validator was covered: each had a withdrawal address, each address
        was answered and each block attributed.
        """
        if len(indices) == 0:
            return True

        now = self._staking_query_end(ts_now())
        validators_by_address: dict[ChecksumEvmAddress, list[tuple[int, Timestamp, Timestamp]]] = defaultdict(list)  # noqa: E501
        with self.database.conn.read_ctx() as cursor:
            for chunk, placeholders in get_query_chunks(indices):
                validator_rows = cursor.execute(
                    'SELECT validator_index, withdrawal_address, activation_timestamp, exited_timestamp '  # noqa: E501
                    f'FROM eth2_validators WHERE validator_index IN ({placeholders}) AND withdrawal_address IS NOT NULL',  # noqa: E501
                    chunk,
                ).fetchall()
                for validator_index, raw_address, activation_ts, exited_ts in validator_rows:
                    if activation_ts is None:
                        continue

                    if update_cache is False:
                        last_query_ts = Timestamp(0)
                    else:
                        last_query_ts = self.database.get_dynamic_cache(
                            cursor=cursor,
                            name=DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS,
                            index=validator_index,
                        ) or Timestamp(0)
                    from_ts = max(Timestamp(activation_ts), last_query_ts)
                    to_ts = min(Timestamp(exited_ts) if exited_ts is not None else now, now)
                    if from_ts < to_ts:
                        validators_by_address[deserialize_evm_address(raw_address)].append((
                            validator_index,
                            from_ts,
                            to_ts,
                        ))

            ethereum_tracked_accounts = self.database.get_blockchain_accounts(cursor).eth

        # A validator with no withdrawal address has no address to ask an indexer about.
        addressed = {index for ranges in validators_by_address.values() for index, _, _ in ranges}

        queried_indices: set[int] = set()
        # Validators with a block in their range not yet fully stored, so their range is asked
        # again rather than recorded as queried.
        incomplete_indices: set[int] = set()
        unanswered: list[ChecksumEvmAddress] = []
        every_address = self._all_addressed(indices, addressed)
        for address, validator_ranges in validators_by_address.items():
            from_ts = min(entry[1] for entry in validator_ranges)
            to_ts = max(entry[2] for entry in validator_ranges)
            log.debug(f'Querying produced blocks for validator withdrawal address {address} from {from_ts} to {to_ts}')  # noqa: E501
            try:
                period = self.ethereum.maybe_timestamp_to_block_range(TimestampOrBlockRange('timestamps', from_ts, to_ts))  # noqa: E501
            except RemoteError as e:
                log.warning(f'Could not turn the produced blocks range of {address} into blocks: {e!s}')  # noqa: E501
                blocks = None
            else:
                blocks = self._fetch_validated_blocks_from_external_sources(address=address, period=period)  # noqa: E501
            if blocks is None:
                every_address = False
                unanswered.append(address)  # nothing else will cover the address
                continue

            queried_indices.update(validator_index for validator_index, _, _ in validator_ranges)
            incomplete, attributed = self._store_validated_blocks(
                address=address,
                validators=validator_ranges,
                blocks=blocks,
                tracked_accounts=ethereum_tracked_accounts,
                blocks_without_mev=None,
                allow_sole_active=True,
            )
            incomplete_indices |= incomplete
            every_address &= attributed

        if len(unanswered) != 0:  # their validators keep their last query time, so are retried
            self.msg_aggregator.add_warning(
                f'Could not query the produced blocks of {", ".join(unanswered)} from any source. '
                'They will be retried by the next query.',
                classification=NetworkFailure(record=UserMessageRecord.VALIDATOR, error='every produced blocks source failed'),  # noqa: E501
                subject=Location.ETHEREUM,
            )

        if update_cache:
            with self.database.user_write() as write_cursor:
                for index in queried_indices - incomplete_indices:
                    self.database.set_dynamic_cache(
                        write_cursor=write_cursor,
                        name=DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS,
                        value=now,
                        index=index,
                    )

        return every_address

    def _get_and_store_produced_blocks_from_nest(self, blocks_without_mev: set[int]) -> None:
        """Store the produced blocks a nuthatch nest finds for the tracked Ethereum addresses.

        A nest finds the blocks whose fee recipient, or whose builder's payment, is a tracked
        address, and the relays name the proposer. That is coverage of addresses, not of
        validators: a validator's block whose rewards went to an address not tracked is not found.
        So nothing here moves a validator's produced-block query time on. Each address's progress
        is kept by block, through the nest's finalized head, since the nest serves no further. A
        block is booked to the tracked validator a relay or a configured beacon node names as its
        proposer, whatever its withdrawal address, and to nobody otherwise.

        A relay can publish a block's record late, and the nest asks the relays again for
        UNRECORDED_MEV_RETRY_WINDOW after it first served a range, so the ranges it served are
        asked about again until that has passed. The blocks left stored without an MEV reward are
        added to `blocks_without_mev`.
        """
        try:
            nest = self._nest()
            bound_block, bound_ts = nest.finalized_head()
        except RemoteError as e:
            log.warning(f'Not asking the nuthatch nest for produced blocks: {e!s}')
            return

        self._repair_nest_cursors()
        with self.database.user_write() as write_cursor:
            self.database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.NUTHATCH_PRODUCED_LAST_RUN,
                value=ts_now(),
            )
        if len(validators := self._tracked_validators(bound_ts)) == 0:
            return
        self._forget_nest_progress_for_new_validators({index for index, _, _ in validators})

        try:  # no validator proposed before the first one tracked was active
            first_block = self.ethereum.get_blocknumber_by_time(ts=min(entry[1] for entry in validators))  # noqa: E501
        except RemoteError as e:
            log.warning(f'Not asking the nuthatch nest for produced blocks: {e!s}')
            return

        with self.database.conn.read_ctx() as cursor:
            tracked_accounts = self.database.get_blockchain_accounts(cursor).eth
            progress = {address: self.database.get_dynamic_cache(
                cursor=cursor,
                name=DBCacheDynamic.NEST_PRODUCED_BLOCKS_THROUGH,
                address=address,
            ) for address in tracked_accounts}

        served: list[tuple[ChecksumEvmAddress, int, int]] = []
        for address in tracked_accounts:
            through = progress[address]
            if (from_block := first_block if through is None else max(first_block, through + 1)) > bound_block:  # noqa: E501
                continue
            if (answer := self._ask_nest(nest, address, from_block, bound_block)) is None:
                continue
            from_block, blocks = answer

            self._store_validated_blocks(
                address=address,
                validators=validators,
                blocks=blocks,
                tracked_accounts=tracked_accounts,
                blocks_without_mev=blocks_without_mev,
                allow_sole_active=False,
            )
            with self.database.user_write() as write_cursor:
                self.database.set_dynamic_cache(
                    write_cursor=write_cursor,
                    name=DBCacheDynamic.NEST_PRODUCED_BLOCKS_THROUGH,
                    value=bound_block,
                    address=address,
                )
            served.append((address, from_block, bound_block))

        self._ask_nest_again(
            asked_at=ts_now(),
            served=served,
            validators=validators,
            tracked_accounts=tracked_accounts,
            blocks_without_mev=blocks_without_mev,
        )

    def _store_validated_blocks(
            self,
            address: ChecksumEvmAddress,
            validators: list[tuple[int, Timestamp, Timestamp]],
            blocks: list[dict[str, Any]],
            tracked_accounts: Sequence[ChecksumEvmAddress],
            blocks_without_mev: set[int] | None,
            allow_sole_active: bool,
    ) -> tuple[set[int], bool]:
        """Store the produced blocks an indexer answered for `address`, each booked to the one of
        `validators`, with when each was active, that proposed it. A block already stored gets
        only what it lacks: its MEV reward, once a relay recorded it.

        Returns the validators with a block that could not be stored, and whether every block was
        attributed to its proposer.
        """
        dbevents = DBHistoryEvents(self.database)
        incomplete: set[int] = set()
        attributed = True
        for entry in blocks:
            try:
                block_number, timestamp, reward = self._deserialize_validated_block(entry)
            except (DeserializationError, TypeError, ValueError) as e:
                log.error(f'Failed to deserialize validated block entry {entry} due to {e!s}')
                incomplete.update(index for index, _, _ in validators)  # whose block is unknown
                continue

            active_indices = [
                validator_index for validator_index, active_from_ts, active_to_ts in validators
                if active_from_ts <= timestamp <= active_to_ts
            ]
            if len(active_indices) == 0:
                continue

            stored = self._stored_block_events(block_number)
            if BLOCK_REWARD_SEQUENCE in stored and (
                MEV_REWARD_SEQUENCE in stored or entry.get('mev') != 'relay'
            ):  # nothing new to add for it
                if MEV_REWARD_SEQUENCE not in stored and blocks_without_mev is not None:
                    blocks_without_mev.add(block_number)
                continue

            if (pubkey := entry.get('proposerPubkey')):
                # A relay named the proposer: one of these validators, or none of them.
                if (proposer_index := self._proposer_by_pubkey(
                    pubkey=pubkey,
                    active_indices=active_indices,
                )) is None:
                    continue
            elif (proposer_index := self._get_proposer_index_for_validated_block(
                block_number=block_number,
                timestamp=timestamp,
                active_indices=active_indices,
                allow_sole_active=allow_sole_active,
            )) is None:
                attributed = False  # a source that can name the proposer should be asked
                incomplete.update(active_indices)
                continue

            # A nuthatch nest also lists the relay-built blocks whose fee recipient was the
            # builder, with what the relays say they paid this address.
            fee_recipient = deserialize_evm_address(entry.get('feeRecipient') or address)
            # Either event already stored is not added again: the insert ignores it.
            events = [EthBlockEvent(
                validator_index=proposer_index,
                timestamp=ts_sec_to_ms(timestamp),
                amount=reward,
                fee_recipient=fee_recipient,
                fee_recipient_tracked=fee_recipient in tracked_accounts,
                block_number=block_number,
                is_mev_reward=False,
            )]
            mev_amount, mev_recipient = None, fee_recipient
            if (
                entry.get('mev') == 'relay' and
                (mev_recipient_raw := entry.get('mevRecipient'))
            ):
                mev_recipient = deserialize_evm_address(mev_recipient_raw)
                # Paid to the block's own fee recipient, the block reward already counts what
                # the block paid; only a builder's separate transfer is more.
                mev_amount = entry.get('paymentValue' if mev_recipient == fee_recipient else 'mevReward')  # noqa: E501
            if mev_amount:
                events.append(EthBlockEvent(
                    validator_index=proposer_index,
                    timestamp=ts_sec_to_ms(timestamp),
                    amount=from_wei(deserialize_fval(
                        value=mev_amount,
                        name='mev reward',
                        location='validated blocks query',
                    )),
                    fee_recipient=mev_recipient,
                    fee_recipient_tracked=mev_recipient in tracked_accounts,
                    block_number=block_number,
                    is_mev_reward=True,
                ))
            with self.database.user_write() as write_cursor:
                for event in events:
                    dbevents.add_history_event(write_cursor=write_cursor, event=event)
            # No relay record ('unrecorded') is not "no MEV". Of the other sources only
            # beaconcha.in knows a block's MEV; the other indexers list blocks without it.
            if len(events) == 1 and blocks_without_mev is not None:
                blocks_without_mev.add(block_number)

        return incomplete, attributed

    def _staking_query_end(self, end_ts: Timestamp) -> Timestamp:
        """Where a staking query asked to end at end_ts stops. With a nuthatch nest in Ethereum's
        indexer order, CHAIN_TOP_LAG seconds behind now, as transaction syncs are: a nest refuses
        to turn a time past its newest block into a block, and now nearly always is."""
        if EvmIndexer.NUTHATCH in (name for name, _ in self.ethereum._get_indexers_in_order()):
            return Timestamp(min(end_ts, ts_now() - CHAIN_TOP_LAG))
        return end_ts

    def _nest(self) -> Nuthatch:
        """The nuthatch nest in Ethereum's indexer order.

        May raise:
        - RemoteError if the order names none
        """
        for name, indexer in self.ethereum._get_indexers_in_order():
            if name == EvmIndexer.NUTHATCH and isinstance(indexer, Nuthatch):
                return indexer
        raise RemoteError("Ethereum's indexer order names no nuthatch nest")

    def _ask_nest_again(
            self,
            asked_at: Timestamp,
            served: list[tuple[ChecksumEvmAddress, int, int]],
            validators: list[tuple[int, Timestamp, Timestamp]],
            tracked_accounts: Sequence[ChecksumEvmAddress],
            blocks_without_mev: set[int] | None,
    ) -> None:
        """Ask the nest again about the ranges it served, and remember the ones it served now. A
        range is forgotten only after an answer given once the nest has stopped asking the relays
        about it; one it cannot answer stays for the next time."""
        with self.database.conn.read_ctx() as cursor:
            remembered = nest_ranges(self.database.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.NUTHATCH_PRODUCED_RANGES,
            ))
        ranges = []
        for address, from_block, to_block, served_at in remembered:
            if (answer := self._ask_nest(self._nest(), address, from_block, to_block)) is None:
                ranges.append((address, from_block, to_block, served_at))
                continue
            _, attributed = self._store_validated_blocks(
                address=address,
                validators=validators,
                blocks=answer[1],
                tracked_accounts=tracked_accounts,
                blocks_without_mev=blocks_without_mev,
                allow_sole_active=False,
            )
            # Kept while a block in it has nobody to book it to, so a beacon node configured
            # later can still name the proposer.
            if not attributed or not nest_range_settled(served_at=served_at, asked_at=asked_at):
                ranges.append((address, from_block, to_block, served_at))

        ranges += [(address, from_block, to_block, asked_at) for address, from_block, to_block in served]  # noqa: E501
        with self.database.user_write() as write_cursor:
            self.database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.NUTHATCH_PRODUCED_RANGES,
                value=json.dumps([list(entry) for entry in merge_nest_ranges(ranges)]),
            )

    def _ask_nest(
            self,
            nest: Nuthatch,
            address: ChecksumEvmAddress,
            from_block: int,
            to_block: int,
    ) -> tuple[int, list[dict[str, Any]]] | None:
        """The produced blocks the nest has for `address` over the blocks, and the block they
        start from: the nest's own first block if its history starts later. None if it cannot
        answer."""
        try:
            return from_block, nest.get_validated_blocks(address=address, period=TimestampOrBlockRange('blocks', from_block, to_block))  # noqa: E501
        except IndexerRangeStartsLater as e:
            if not from_block < e.first_block <= to_block:
                log.warning(f'Could not ask the nuthatch nest for the produced blocks of {address}: {e!s}')  # noqa: E501
                return None
            return self._ask_nest(nest, address, e.first_block, to_block)
        except RemoteError as e:
            log.warning(f'Could not ask the nuthatch nest for the produced blocks of {address}: {e!s}')  # noqa: E501
            return None

    def _forget_nest_progress_for_new_validators(self, validators: set[int]) -> None:
        """A block of a validator not tracked then was passed over, so once one is added the
        addresses' history is asked about again."""
        with self.database.conn.read_ctx() as cursor:
            known = set(json.loads(self.database.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.NUTHATCH_PRODUCED_VALIDATORS,
            ) or '[]'))
        if validators <= known:
            return
        prefix = DBCacheDynamic.NEST_PRODUCED_BLOCKS_THROUGH.value[0].removesuffix('{address}')
        with self.database.user_write() as write_cursor:
            write_cursor.execute('DELETE FROM key_value_cache WHERE name LIKE ?', (f'{prefix}%',))
            self.database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.NUTHATCH_PRODUCED_VALIDATORS,
                value=json.dumps(sorted(validators)),
            )

    def _tracked_validators(self, now: Timestamp) -> list[tuple[int, Timestamp, Timestamp]]:
        """Every tracked validator, with when it was active."""
        with self.database.conn.read_ctx() as cursor:
            return [
                (index, Timestamp(activation_ts), Timestamp(exited_ts) if exited_ts is not None else now)  # noqa: E501
                for index, activation_ts, exited_ts in cursor.execute(
                    'SELECT validator_index, activation_timestamp, exited_timestamp '
                    'FROM eth2_validators WHERE activation_timestamp IS NOT NULL',
                )
            ]

    def _repair_nest_cursors(self) -> None:
        """Drop the produced-block query times a nest's answers moved validators on to, before
        those answers were known to cover addresses only, so the validators are asked again."""
        prefix = DBCacheDynamic.NEST_PRODUCED_BLOCKS_QUERY_TS.value[0].removesuffix('{index}')
        with self.database.user_write() as write_cursor:
            for (name,) in write_cursor.execute(
                'SELECT name FROM key_value_cache WHERE name LIKE ?',
                (f'{prefix}%',),
            ).fetchall():
                index = int(name.removeprefix(prefix))
                for key in (
                    DBCacheDynamic.NEST_PRODUCED_BLOCKS_QUERY_TS,
                    DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS,
                ):
                    self.database.delete_dynamic_cache(write_cursor=write_cursor, name=key, index=str(index))  # noqa: E501

    def _block_proposers(self, blocks: set[int]) -> set[int]:
        """The validators the stored produced blocks are booked to."""
        with self.database.conn.read_ctx() as cursor:
            return {row[0] for block in blocks for row in cursor.execute(
                'SELECT info.validator_index FROM history_events he '
                'JOIN eth_staking_events_info info ON info.identifier=he.identifier '
                'WHERE he.group_identifier=? AND he.sequence_index=0',
                (EthBlockEvent.form_group_identifier(block),),
            )}

    def _mev_recheck(self) -> set[int]:
        with self.database.conn.read_ctx() as cursor:
            return set(json.loads(self.database.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.NUTHATCH_MEV_RECHECK,
            ) or '[]'))

    def _set_mev_recheck(self, blocks: set[int]) -> None:
        with self.database.user_write() as write_cursor:
            self.database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.NUTHATCH_MEV_RECHECK,
                value=json.dumps(sorted(blocks)),
            )

    def _stored_block_events(self, block_number: int) -> dict[int, int]:
        """The block's stored events, reward and MEV reward, by sequence index, each with the
        validator it is booked to."""
        with self.database.conn.read_ctx() as cursor:
            return dict(cursor.execute(
                'SELECT he.sequence_index, info.validator_index FROM history_events he '
                'JOIN eth_staking_events_info info ON info.identifier=he.identifier '
                'WHERE he.group_identifier=?',
                (EthBlockEvent.form_group_identifier(block_number),),
            ).fetchall())

    def _all_addressed(self, indices: list[int], addressed: set[int]) -> bool:
        """Whether every validator left out of `addressed` was left out for being up to date,
        rather than for having no withdrawal address to ask about."""
        if len(missing := set(indices) - addressed) == 0:
            return True

        with self.database.conn.read_ctx() as cursor:
            for chunk, placeholders in get_query_chunks(list(missing)):
                if cursor.execute(
                    f'SELECT COUNT(*) FROM eth2_validators WHERE validator_index IN ({placeholders}) '  # noqa: E501
                    'AND withdrawal_address IS NULL',
                    chunk,
                ).fetchone()[0] != 0:
                    return False
        return True

    def _proposer_by_pubkey(self, pubkey: str, active_indices: list[int]) -> int | None:
        """The tracked active validator with the public key a relay named as the proposer."""
        with self.database.conn.read_ctx() as cursor:
            row = cursor.execute(
                'SELECT validator_index FROM eth2_validators WHERE public_key=?',
                (pubkey.lower(),),
            ).fetchone()
        return row[0] if row is not None and row[0] in active_indices else None

    def get_and_store_produced_blocks(
            self,
            indices: list[int],
            update_cache: bool = True,
    ) -> None:
        """Query and store produced blocks: from a nuthatch nest when the indexer order names
        one, then beaconcha.in, then the other indexers when beaconcha.in is unavailable.

        Only beaconcha.in, and the other indexers by withdrawal address, cover validators. The
        nest covers the tracked addresses, so without either the validators' coverage is
        incomplete, and the user is told so.
        """
        with self.beacon_inquirer.beaconchain.produced_blocks_lock:
            # The nest goes first and beaconcha.in still runs after it, so a block the nest could
            # not attribute or see is still found there; a block already stored is never added
            # twice by either path.
            blocks_without_mev: set[int] = set()
            order = [name for name, _ in self.ethereum._get_indexers_in_order()]
            if EvmIndexer.NUTHATCH in order:
                self._get_and_store_produced_blocks_from_nest(blocks_without_mev)
            # Kept until beaconcha.in has been asked about them, so a run where it fails or has
            # no key leaves them for a later one.
            recheck = self._mev_recheck() | blocks_without_mev
            self._set_mev_recheck(recheck)
            if self.beacon_inquirer.beaconchain.has_api_key():
                try:
                    seen = self.beacon_inquirer.beaconchain._get_and_store_produced_blocks(
                        # with whose blocks are to be rechecked, even if no longer queried
                        indices=sorted(set(indices) | self._block_proposers(recheck)),
                        update_cache=update_cache,
                        recheck_blocks=recheck,
                    )
                except (APIKeyNotAvailable, RemoteError) as e:
                    log.warning(f'Failed to query produced blocks via beaconcha.in due to {e!s}. Falling back to indexers.')  # noqa: E501
                else:
                    self._set_mev_recheck(recheck - seen)
                    return

            if any(name != EvmIndexer.NUTHATCH for name in order):
                self._get_and_store_produced_blocks_from_indexers(
                    indices=indices,
                    update_cache=update_cache,
                )
            elif not self._told_nest_coverage_incomplete:
                self._told_nest_coverage_incomplete = True
                self.msg_aggregator.add_warning(
                    'Produced blocks come only from the nuthatch nest, which finds the blocks '
                    'whose rewards went to a tracked address. A validator block paid to an '
                    'address you do not track is not found. Add a beaconcha.in API key, or '
                    "another indexer to Ethereum's order, for complete validator coverage.",
                    classification=NetworkFailure(record=UserMessageRecord.VALIDATOR, error='no source covers every validator'),  # noqa: E501
                    subject=Location.ETHEREUM,
                )

    def combine_block_with_tx_events(self) -> None:
        """Get all mev reward block production events and combine them with the
        transaction events if they can be found"""
        DBEth2(self.database).combine_block_with_tx_events()

    def detect_exited_validators(self) -> None:
        """This function will detect any validators that have exited from the ones that
        are last known to be active and set the DB values accordingly"""
        now = ts_now()
        with self.database.user_write() as write_cursor:
            self.database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.LAST_WITHDRAWALS_EXIT_QUERY_TS,
                value=now,
            )

        dbeth2 = DBEth2(self.database)
        with self.database.conn.read_ctx() as cursor:
            # get validators that haven't had any withdrawals marked as exits yet
            validator_indices = [row[0] for row in cursor.execute(
                """
                SELECT DISTINCT v.validator_index
                FROM eth2_validators v
                LEFT JOIN eth_staking_events_info s ON s.validator_index = v.validator_index AND s.is_exit_or_blocknumber = 1
                WHERE v.validator_index IS NOT NULL
                AND s.validator_index IS NULL
                """,  # noqa: E501
            )]

        if len(validator_indices) == 0:
            return

        try:
            validator_data = self.beacon_inquirer.get_validator_data(validator_indices)
        except (RemoteError, DeserializationError) as e:
            log.error(f'Could not query validator data due to {e}')
            return

        needed_validators: list[tuple[int, Timestamp]] = []
        for entry in validator_data:
            if entry.withdrawable_timestamp is None:
                continue

            # this is a slashed/exited validator
            if entry.validator_index is None:
                log.error(f'An exited validator does not contain an index: {entry}. Should never happen.')  # noqa: E501
                continue

            needed_validators.append((entry.validator_index, entry.withdrawable_timestamp))

        if len(needed_validators) == 0:
            return

        with self.database.user_write() as write_cursor:
            for index, withdrawable_ts in needed_validators:
                dbeth2.set_validator_exit(
                    write_cursor=write_cursor,
                    index=index,
                    withdrawable_timestamp=withdrawable_ts,
                )

    def refresh_activated_validators_deposits(self) -> None:
        """It's possible that when an eth deposit gets decoded and created the validator
        index is not known since at the time the validator was waiting in the activation queue.

        To fix that we periodically check if the validator got activated, and if yes we fetch
        and save the index.
        """
        pubkey_to_data: dict[Eth2PubKey, tuple[int, str]] = {}
        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT H.identifier, H.amount, H.extra_data from history_events H LEFT JOIN eth_staking_events_info S '  # noqa: E501
                'ON H.identifier=S.identifier WHERE S.validator_index=?',
                (UNKNOWN_VALIDATOR_INDEX,),
            )
            for entry in cursor:
                try:
                    public_key = json.loads(entry[2])['public_key']
                except (json.JSONDecodeError, KeyError):
                    log.error(f'Non json or unexpected extra data {entry[2]} found for evm event with identifier {entry[0]}')  # noqa: E501
                    continue

                pubkey_to_data[public_key] = (entry[0], entry[1])

        if len(pubkey_to_data) == 0:
            return

        # now check validator data for all these keys
        try:
            results = self.beacon_inquirer.get_validator_data(indices_or_pubkeys=list(pubkey_to_data))  # noqa: E501
        except (RemoteError, DeserializationError) as e:
            log.error(f'During refreshing activated validator deposits got error: {e!s}')
            return

        staking_changes = []
        validators = []
        for result in results:
            identifier, _ = pubkey_to_data[result.public_key]
            if result.validator_index is None:
                continue  # no index set yet

            staking_changes.append((result.validator_index, identifier))
            validators.append((result.validator_index, result.public_key, result.validator_type.serialize_for_db(), '1.0'))  # noqa: E501

        if len(staking_changes) == 0:
            return

        with self.database.user_write() as write_cursor:
            write_cursor.executemany(
                'UPDATE eth_staking_events_info SET validator_index=? WHERE identifier=?',
                staking_changes,
            )
            write_cursor.executemany(  # the deposit notes follow the validator index, see EthDepositEvent.auto_notes  # noqa: E501
                'UPDATE history_events SET extra_data=null, notes=NULL WHERE identifier=?',
                [(identifier,) for _, identifier in staking_changes],
            )
            write_cursor.executemany(
                'INSERT OR IGNORE INTO eth2_validators(validator_index, public_key, validator_type, ownership_proportion) VALUES(?, ?, ?, ?)',  # noqa: E501
                validators,
            )

    def _adjust_blockproduction_at_account_modification(
            self,
            address: ChecksumEvmAddress,
            event_type: Literal[HistoryEventType.INFORMATIONAL, HistoryEventType.STAKING],
    ) -> None:
        """Modify any existing block proposals to be staking and no longer informational
           if the fee recipient is the newly added address and vice versa if the fee recipient
           is the removed address then turn to informational."""
        with self.database.user_write() as write_cursor:
            DBHistoryEvents(self.database).update_events_and_track(
                write_cursor=write_cursor,
                where_clause='WHERE entry_type=? AND sequence_index=0 AND location_label=?',
                where_bindings=(HistoryBaseEntryType.ETH_BLOCK_EVENT.serialize_for_db(), address),
                set_clause='SET type=?',
                set_bindings=(event_type.serialize(),),
            )

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        """
        - Add validators to the DB for the new address if any
        - Adjust the existing block production events to maybe not be informational.
        """
        try:
            self.detect_and_refresh_validators([address])
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Did not manage to query beaconcha.in api for address {address} due to {e!s}.'
                f' If you have Eth2 staked balances the final balance results may not be accurate',
                classification=NetworkFailure(record=UserMessageRecord.VALIDATOR, error=str(e)),
                subject=Location.ETHEREUM,
            )

        self._adjust_blockproduction_at_account_modification(address, HistoryEventType.STAKING)
        # whether the address' withdrawals count as ours changed, so the performance results
        # computed from them are no longer valid. The persisted data derived from them is
        # dropped by the chains aggregator, which runs even when this module is not active.
        self.performance_cache.clear()

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        """
        Adjust existing block production events to become informational if they involve the address
        """
        self._adjust_blockproduction_at_account_modification(address, HistoryEventType.INFORMATIONAL)  # noqa: E501
        self.performance_cache.clear()  # its results counted this address' withdrawals

        with self.database.conn.write_ctx() as write_cursor:
            self.database.delete_dynamic_cache(
                write_cursor=write_cursor,
                name=DBCacheDynamic.WITHDRAWALS_TS,
                address=address,
            )

    def deactivate(self) -> None:
        pass
