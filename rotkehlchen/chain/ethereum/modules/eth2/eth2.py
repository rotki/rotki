import json
import logging
import re
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Final, Literal

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.eth2.beacon import BeaconInquirer
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS, HOUR_IN_SECONDS, YEAR_IN_SECONDS
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.api import PremiumPermissionError
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium, UserLimitType, get_user_limit, has_premium_check
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Eth2PubKey,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.data_structures import LRUCacheWithRemove
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms

from .constants import (
    CPT_ETH2,
    MAX_EFFECTIVE_BALANCE,
    MIN_EFFECTIVE_BALANCE,
    UNKNOWN_VALIDATOR_INDEX,
)

ETH_STAKED_CACHE_TIME: Final = 7200  # 2 hours in seconds
from .structures import (
    PerformanceStatusFilter,
    ValidatorDetailsWithStatus,
    ValidatorID,
)
from .utils import create_profit_filter_queries

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.beaconchain.service import BeaconChain

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Eth2(EthereumModule):
    """Module representation for Eth2"""

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Premium | None,
            msg_aggregator: MessagesAggregator,
            beaconchain: 'BeaconChain',
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
        self.last_stats_query_ts = 0
        self.validator_stats_queried = 0
        self.deposits_pubkey_re = re.compile(r'.*validator with pubkey (.*)\. Deposit.*')
        self.withdrawals_query_lock = Semaphore()
        # This is a cache that is kept only for the last performance cache address, indices args
        self.performance_cache: LRUCacheWithRemove[tuple[Timestamp, Timestamp], dict[str, dict]] = LRUCacheWithRemove(maxsize=3)  # noqa: E501
        self.performance_cache_args: tuple[list[ChecksumEvmAddress] | None, list[int] | None, PerformanceStatusFilter] = (None, None, PerformanceStatusFilter.ALL)  # noqa: E501
        # Total staked cache variables
        self._cached_total_staked: FVal
        self._cached_staked_timestamp = Timestamp(0)

    def _get_closest_performance_cache_key(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> tuple[Timestamp, Timestamp]:
        """Check if there is any close timestamps in the performance cache and returns them"""
        for key_from_ts, key_to_ts in self.performance_cache:
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
            self.detect_and_refresh_validators(addresses)

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
                self.performance_cache_args == (addresses, validator_indices, status) and
                (result := self.performance_cache.get(cache_key))
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
        self.performance_cache.add(cache_key, result)  # save cache & return pagination on the data
        self.performance_cache_args = (addresses, validator_indices, status)
        return {
            'validators': dict(list(result['validators'].items())[offset: offset + limit]),
            'sums': result['sums'],
            'entries_total': total_validators,
            'entries_found': len(result['validators']),
        }

    def _get_saved_pubkey_to_deposit_address(self) -> dict[Eth2PubKey, ChecksumEvmAddress]:
        """Read the decoded DB history events to find out public keys -> deposit addresses

        This will just return the data for the currently decoded history events.
        And also has a really ugly hack since it takes the public key from the notes.
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
                ),
            )

        result = {}
        for event in deposit_events:
            if event.notes is None:
                log.error(  # should not really happen
                    f'Could not match the pubkey extraction regex for {event} '
                    f'due to absence of notes',
                )
                continue

            match = self.deposits_pubkey_re.match(event.notes)
            if match is None:
                log.error(f'Could not match the pubkey extraction regex for "{event.notes}"')
                continue  # should not really happen though

            groups = match.groups()
            if len(groups) != 1:
                log.error(f'Could not match group for pubkey extraction regex for "{event.notes}"')
                continue  # should not really happen though

            result[Eth2PubKey(groups[0])] = event.location_label

        return result  # type: ignore  # location_label is set for this event

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

    def query_single_address_withdrawals(self, address: ChecksumEvmAddress, to_ts: Timestamp) -> None:  # noqa: E501
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
            period = self.ethereum.maybe_timestamp_to_block_range(TimestampOrBlockRange('timestamps', from_ts, to_ts))  # noqa: E501
            untracked_validator_indices = self.ethereum.etherscan.get_withdrawals(
                address=address,
                period=period,
            )
        except (DeserializationError, RemoteError) as e:
            log.error(f'Failed to query ethereum withdrawals for {address} through etherscan due to {e}. Will try blockscout.')  # noqa: E501
            try:
                untracked_validator_indices = self.ethereum.blockscout.query_withdrawals(address)
            except (DeserializationError, RemoteError, KeyError) as othere:
                msg = str(othere)
                if isinstance(othere, KeyError):
                    msg = f'Missing key entry for {msg}'

                log.error(f'Failed to query ethereum withdrawals for {address} through blockscout due to {msg}. Bailing out for now.')  # noqa: E501
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
        pubkey_to_deposit: dict[Eth2PubKey, ChecksumEvmAddress] = {}
        pubkey_to_index: dict[Eth2PubKey, int] = {}
        with self.database.conn.read_ctx() as cursor:  # get non finalized saved validator
            cursor.execute('SELECT validator_index, public_key FROM eth2_validators WHERE withdrawable_timestamp IS NULL')  # noqa: E501
            validators_to_refresh = {ValidatorID(index=x[0], public_key=x[1]) for x in cursor}
            cursor.execute('SELECT public_key FROM eth2_validators WHERE withdrawable_timestamp IS NOT NULL')  # noqa: E501
            finalized_validator_pubkeys = {x[0] for x in cursor}

        for address in addresses:
            validators = self.beacon_inquirer.get_eth1_address_validators(address)
            for validator in validators:
                if validator.index is not None:
                    pubkey_to_index[validator.public_key] = validator.index

                pubkey_to_deposit[validator.public_key] = address
                if validator.public_key not in finalized_validator_pubkeys:
                    validators_to_refresh.add(validator)

        # Check all our currently decoded deposits for known public keys and map to depositors
        pubkey_to_depositor = self._get_saved_pubkey_to_deposit_address()
        for public_key, depositor in pubkey_to_depositor.items():
            if public_key in finalized_validator_pubkeys:
                continue

            index = pubkey_to_index.get(public_key)
            validators_to_refresh.add(ValidatorID(index=index, public_key=public_key))
            pubkey_to_deposit[public_key] = depositor

        # refresh validator data. Use index if existing otherwise public key
        details = self.beacon_inquirer.get_validator_data(
            indices_or_pubkeys=[x.index if x.index is not None else x.public_key for x in validators_to_refresh],  # noqa: E501
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
        history_changes = []
        validators = []
        for result in results:
            identifier, amount_str = pubkey_to_data[result.public_key]
            if result.validator_index is None:
                continue  # no index set yet

            staking_changes.append((result.validator_index, identifier))
            history_changes.append((f'Deposit {amount_str} ETH to validator {result.validator_index}', identifier))  # noqa: E501
            validators.append((result.validator_index, result.public_key, result.validator_type.serialize_for_db(), '1.0'))  # noqa: E501

        if len(staking_changes) == 0:
            return

        with self.database.user_write() as write_cursor:
            write_cursor.executemany(
                'UPDATE eth_staking_events_info SET validator_index=? WHERE identifier=?',
                staking_changes,
            )
            write_cursor.executemany(
                'UPDATE history_events SET extra_data=null, notes=? WHERE identifier=?',
                history_changes,
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
            write_cursor.execute(
                'UPDATE history_events SET type=? WHERE entry_type=? AND sequence_index=0 AND location_label=?',  # noqa: E501
                (
                    event_type.serialize(),
                    HistoryBaseEntryType.ETH_BLOCK_EVENT.serialize_for_db(),
                    address,
                ),
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
            )

        self._adjust_blockproduction_at_account_modification(address, HistoryEventType.STAKING)

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        """
        Adjust existing block production events to become informational if they involve the address
        """
        self._adjust_blockproduction_at_account_modification(address, HistoryEventType.INFORMATIONAL)  # noqa: E501

        with self.database.conn.write_ctx() as write_cursor:
            self.database.delete_dynamic_cache(
                write_cursor=write_cursor,
                name=DBCacheDynamic.WITHDRAWALS_TS,
                address=address,
            )

    def deactivate(self) -> None:
        pass
