import json
import logging
import re
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal

import gevent
from gevent.lock import Semaphore
from pysqlcipher3 import dbapi2 as sqlcipher

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
from rotkehlchen.history.events.structures.eth2 import EthBlockEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium, has_premium_check
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.data_structures import LRUCacheWithRemove
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import ts_now

from .constants import (
    CPT_ETH2,
    FREE_VALIDATORS_LIMIT,
    UNKNOWN_VALIDATOR_INDEX,
    VALIDATOR_STATS_QUERY_BACKOFF_EVERY_N_VALIDATORS,
    VALIDATOR_STATS_QUERY_BACKOFF_TIME,
    VALIDATOR_STATS_QUERY_BACKOFF_TIME_RANGE,
)
from .structures import (
    PerformanceStatusFilter,
    ValidatorDailyStats,
    ValidatorDetailsWithStatus,
    ValidatorID,
)
from .utils import create_profit_filter_queries

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.filtering import Eth2DailyStatsFilterQuery
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
            pubkey_to_ownership = dbeth2.get_pubkey_to_ownership(cursor)

        if len(pubkey_to_ownership) == []:
            return {}  # nothing detected

        balances = self.beacon_inquirer.get_balances(
            indices_or_pubkeys=list(pubkey_to_ownership.keys()),
            has_premium=has_premium_check(self.premium),
        )
        for pubkey, balance in balances.items():
            if (ownership_proportion := pubkey_to_ownership.get(pubkey, ONE)) != ONE:
                balances[pubkey] = balance * ownership_proportion

        return balances

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
        """
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
                else:  # can only be EXITED
                    got_indices = dbeth2.get_exited_validator_indices(cursor)

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

        withdrawals_filter_query, exits_filter_query, execution_filter_query = create_profit_filter_queries(  # noqa: E501
            from_ts=from_ts,
            to_ts=to_ts,
            validator_indices=list(to_filter_indices) if to_filter_indices is not None else None,
            tracked_addresses=accounts.eth,  # needed to exclude block recipients not tracked
        )

        with self.database.conn.read_ctx() as cursor:
            withdrawals_amounts, exits_pnl, execution_rewards_amounts = dbeth2.get_validators_profit(  # noqa: E501
                cursor=cursor,
                exits_filter_query=exits_filter_query,
                withdrawals_filter_query=withdrawals_filter_query,
                execution_filter_query=execution_filter_query,
            )

        pnls: defaultdict[int, dict] = defaultdict(dict)
        sums: defaultdict[str, FVal] = defaultdict(FVal)
        for key_label, mapping in (
                ('withdrawals', withdrawals_amounts),
                ('exits', exits_pnl),
                ('execution', execution_rewards_amounts),
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
            balances = self.beacon_inquirer.get_balances(
                indices_or_pubkeys=list(to_query_indices),
                has_premium=has_premium_check(self.premium),
            )
            for pubkey, balance in balances.items():
                entry = pnls[pubkey_to_index[pubkey]]
                if 'exits' in entry:
                    continue  # no outstanding balance for exits

                if balance.amount == ZERO:
                    continue

                outstanding_pnl = balance.amount - FVal(32)
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
            data['apr'] = ((YEAR_IN_SECONDS * validator_sum) / (profit_to_ts - profit_from_ts)) / 32  # noqa: E501
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
            deposit_events = dbevents.get_history_events(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(
                    event_types=[HistoryEventType.STAKING],
                    event_subtypes=[HistoryEventSubType.DEPOSIT_ASSET],
                    counterparties=[CPT_ETH2],
                ),
                has_premium=True,  # need all events here
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

    def _maybe_backoff_beaconchain(self, now: Timestamp) -> None:
        should_backoff = (
            now - self.last_stats_query_ts < VALIDATOR_STATS_QUERY_BACKOFF_TIME_RANGE and
            self.validator_stats_queried >= VALIDATOR_STATS_QUERY_BACKOFF_EVERY_N_VALIDATORS
        )
        if should_backoff:
            log.debug(
                f'Queried {self.validator_stats_queried} validators in the last '
                f'{VALIDATOR_STATS_QUERY_BACKOFF_TIME_RANGE} seconds. Backing off for '
                f'{VALIDATOR_STATS_QUERY_BACKOFF_TIME} seconds.',
            )
            self.validator_stats_queried = 0
            gevent.sleep(VALIDATOR_STATS_QUERY_BACKOFF_TIME)

    def _query_services_for_validator_daily_stats(
            self,
            to_ts: Timestamp,
    ) -> None:
        """Goes through all saved validators and sees which need to have their stats requeried"""
        now = ts_now()
        dbeth2 = DBEth2(self.database)
        result = dbeth2.get_validators_to_query_for_stats(up_to_ts=to_ts)

        for validator_index, last_ts, exit_ts in result:
            self._maybe_backoff_beaconchain(now=now)
            new_stats = self.beacon_inquirer.query_validator_daily_stats(
                validator_index=validator_index,
                last_known_timestamp=last_ts,
                exit_ts=exit_ts,
            )
            self.validator_stats_queried += 1
            self.last_stats_query_ts = now

            if len(new_stats) != 0:
                dbeth2.add_validator_daily_stats(stats=new_stats)

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
            last_query = self.database.get_dynamic_cache(
                cursor=cursor,
                name=DBCacheDynamic.WITHDRAWALS_TS,
                address=address,
            )

        from_ts = Timestamp(0)
        if last_query is not None and to_ts - (from_ts := last_query) <= HOUR_IN_SECONDS * 3:
            return

        log.debug(f'Querying {address} ETH withdrawals from {from_ts} to {to_ts}')

        try:
            untracked_validator_indices = self.ethereum.etherscan.get_withdrawals(
                address=address,
                period=TimestampOrBlockRange('timestamps', from_ts, to_ts),
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

    def get_validator_daily_stats(
            self,
            cursor: 'DBCursor',
            filter_query: 'Eth2DailyStatsFilterQuery',
            only_cache: bool,
    ) -> tuple[list[ValidatorDailyStats], int, FVal]:
        """Gets the daily stats eth2 validators depending on the given filter.

        This won't detect new validators

        Will query for new validator daily stats if only_cache is False.

        May raise:
        - RemoteError due to problems with beaconcha.in
        """
        if only_cache is False:
            self._query_services_for_validator_daily_stats(to_ts=filter_query.to_ts)

        dbeth2 = DBEth2(self.database)
        return dbeth2.get_validator_daily_stats_and_limit_info(cursor, filter_query=filter_query)

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
        """
        dbeth2 = DBEth2(self.database)
        if self.premium is None:
            with self.database.conn.read_ctx() as cursor:
                tracked_validators = dbeth2.get_validators(cursor)
            if len(tracked_validators) >= FREE_VALIDATORS_LIMIT:
                raise PremiumPermissionError(
                    f'Adding validator {validator_index} {public_key} would take you '
                    f'over the free limit of {FREE_VALIDATORS_LIMIT} for tracked validators',
                )

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

        result[0].ownership_proportion = ownership_proportion
        with self.database.user_write() as write_cursor:
            # by now we have a valid index and pubkey. Add to DB
            dbeth2.add_or_update_validators(write_cursor, [result[0]])

    def combine_block_with_tx_events(self) -> None:
        """Get all mev reward block production events and combine them with the
        transaction events if they can be found"""
        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT B_H.identifier, B_T.block_number, B_H.notes FROM evm_transactions B_T '
                'LEFT JOIN evm_events_info B_E '
                'ON B_T.tx_hash=B_E.tx_hash LEFT JOIN history_events B_H '
                'ON B_E.identifier=B_H.identifier WHERE '
                'B_H.asset="ETH" AND B_H.type="receive" AND B_H.subtype="none" '
                'AND B_T.block_number=('
                'SELECT A_S.is_exit_or_blocknumber '
                'FROM history_events A_H LEFT JOIN eth_staking_events_info A_S '
                'ON A_H.identifier=A_S.identifier WHERE A_H.subtype="mev reward" AND '
                'A_S.is_exit_or_blocknumber=B_T.block_number AND '
                'A_H.amount=B_H.amount AND A_H.location_label=B_H.location_label)',
            )
            result = cursor.fetchall()

        changes = [(
            EthBlockEvent.form_event_identifier(entry[1]),
            2,
            f'{entry[2]} as mev reward for block {entry[1]}',
            HistoryEventType.STAKING.serialize(),
            HistoryEventSubType.MEV_REWARD.serialize(),
            entry[0],
        ) for entry in result]
        with self.database.user_write() as write_cursor:
            for changes_entry in changes:
                try:
                    write_cursor.execute(
                        'UPDATE history_events '
                        'SET event_identifier=?, sequence_index=?, notes=?, type=?, subtype=?'
                        'WHERE identifier=?',
                        changes_entry,
                    )
                except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                    log.warning(f'Could not update history events with {changes_entry} in combine_block_with_tx_events due to {e!s}')  # noqa: E501
                    # already exists. Probably right after resetting events? Delete old one
                    write_cursor.execute('DELETE FROM history_events WHERE identifier=?', (changes_entry[5],))  # noqa: E501

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
            validator_indices = list(dbeth2.get_active_validator_indices(cursor))

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
                'SELECT H.identifier, H.amount, E.extra_data from history_events H LEFT JOIN eth_staking_events_info S '  # noqa: E501
                'ON H.identifier=S.identifier LEFT JOIN evm_events_info E '
                'ON E.identifier=H.identifier WHERE S.validator_index=?',
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
            validators.append((result.validator_index, result.public_key, '1.0'))

        if len(staking_changes) == 0:
            return

        with self.database.user_write() as write_cursor:
            write_cursor.executemany(
                'UPDATE eth_staking_events_info SET validator_index=? WHERE identifier=?',
                staking_changes,
            )
            write_cursor.executemany(
                'UPDATE history_events SET notes=? WHERE identifier=?',
                history_changes,
            )
            write_cursor.executemany(
                'UPDATE evm_events_info SET extra_data=null WHERE identifier=?',
                [(x[1],) for x in staking_changes],
            )
            write_cursor.executemany(
                'INSERT OR IGNORE INTO eth2_validators(validator_index, public_key, ownership_proportion) VALUES(?, ?, ?)',  # noqa: E501
                validators,
            )

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        """Just add validators to DB."""
        try:
            self.detect_and_refresh_validators([address])
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Did not manage to query beaconcha.in api for address {address} due to {e!s}.'
                f' If you have Eth2 staked balances the final balance results may not be accurate',
            )

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        with self.database.user_write() as write_cursor:
            self.database.delete_eth2_daily_stats(write_cursor)
