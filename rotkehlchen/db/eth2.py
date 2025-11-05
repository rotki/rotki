import json
import logging
from collections import defaultdict
from collections.abc import Collection
from typing import TYPE_CHECKING, Literal

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.chain.ethereum.modules.eth2.constants import CPT_ETH2, MIN_EFFECTIVE_BALANCE
from rotkehlchen.chain.ethereum.modules.eth2.structures import (
    ValidatorDetails,
    ValidatorDetailsWithStatus,
    ValidatorType,
)
from rotkehlchen.chain.ethereum.modules.eth2.utils import form_withdrawal_notes
from rotkehlchen.constants import WEEK_IN_MILLISECONDS, ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.filtering import (
    ETH_STAKING_EVENT_JOIN,
    EthStakingEventFilterQuery,
    EthWithdrawalFilterQuery,
    EvmEventFilterQuery,
    HistoryEventFilterQuery,
    WithdrawalTypesFilter,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryBaseEntryType
from rotkehlchen.history.events.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthWithdrawalEvent,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Eth2PubKey,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DBEth2:

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def validator_exists(
            self,
            cursor: 'DBCursor',
            field: Literal['validator_index', 'public_key'],
            arg: int | Eth2PubKey,
    ) -> bool:
        cursor.execute(f'SELECT COUNT(*) from eth2_validators WHERE {field}=?', (arg,))
        return cursor.fetchone()[0] == 1  # count always returns

    def get_active_pubkeys_to_ownership(self, cursor: 'DBCursor') -> dict[Eth2PubKey, FVal]:
        return {x[0]: FVal(x[1]) for x in cursor.execute('SELECT public_key, ownership_proportion FROM eth2_validators WHERE exited_timestamp IS NULL')}  # noqa: E501

    def get_validators(self, cursor: 'DBCursor') -> list[ValidatorDetails]:
        cursor.execute(
            'SELECT validator_index, public_key, validator_type, ownership_proportion, withdrawal_address, '  # noqa: E501
            'activation_timestamp, withdrawable_timestamp, exited_timestamp FROM eth2_validators;',
        )
        return [ValidatorDetails.deserialize_from_db(x) for x in cursor]

    def get_consolidated_validators(self, cursor: 'DBCursor') -> dict[int, int]:
        """Returns a mapping of source validator index to target validator index
        for all validators that have been consolidated.
        """
        cursor.execute(
            'SELECT e.extra_data FROM history_events AS e LEFT JOIN chain_events_info ON chain_events_info.identifier=e.identifier '  # noqa: E501
            'WHERE chain_events_info.counterparty = ? AND e.type = ? AND e.subtype = ? ',
            (CPT_ETH2, HistoryEventType.INFORMATIONAL.serialize(), HistoryEventSubType.CONSOLIDATE.serialize()),  # noqa: E501
        )
        consolidation_indices = {}
        for raw_extra_data in cursor:
            try:
                extra_data = json.loads(raw_extra_data[0])
                consolidation_indices[extra_data['source_validator_index']] = extra_data['target_validator_index']  # noqa: E501
            except (KeyError, json.JSONDecodeError) as e:  # should never happen
                log.error(f'Unable to decode extra data from eth2 consolidation event {raw_extra_data} due to {e}')  # noqa: E501

        return consolidation_indices

    def get_validators_with_status(
            self,
            cursor: 'DBCursor',
            validator_indices: set[int] | None,
    ) -> list[ValidatorDetailsWithStatus]:
        result: list[ValidatorDetailsWithStatus] = []
        exited_indices = self.get_exited_validator_indices(
            cursor=cursor,
            validator_indices=validator_indices,
        )
        consolidated_indices = self.get_consolidated_validators(cursor)
        cursor.execute(
            'SELECT validator_index, public_key, validator_type, ownership_proportion, withdrawal_address, '  # noqa: E501
            'activation_timestamp, withdrawable_timestamp, exited_timestamp FROM eth2_validators;',
        )
        for entry in cursor:
            validator = ValidatorDetailsWithStatus.deserialize_from_db(entry)
            validator.determine_status(
                exited_indices=exited_indices,
                consolidated_indices=consolidated_indices,
            )
            result.append(validator)

        if validator_indices is not None:
            result = [x for x in result if x.validator_index is not None and x.validator_index in validator_indices]  # noqa: E501

        return result

    def get_active_validator_indices(self, cursor: 'DBCursor') -> set[int]:
        """Returns the indices of the tracked validators that we know have not exited and are not consolidated"""  # noqa: E501
        consolidated_indices = set(self.get_consolidated_validators(cursor))
        cursor.execute(
            'SELECT validator_index from eth2_validators WHERE exited_timestamp IS NULL',
        )
        return {x[0] for x in cursor} - consolidated_indices

    @staticmethod
    def get_exited_validator_indices(cursor: 'DBCursor', validator_indices: Collection[int] | None) -> set[int]:  # noqa: E501
        """Returns the indices of tracked validators that we know have exited.
        If `validator_indices` is provided, results are filtered to include only those indices.
        """
        query = 'SELECT validator_index FROM eth2_validators WHERE exited_timestamp IS NOT NULL'
        if validator_indices is not None:
            return {
                row[0]
                for chunk, placeholders in get_query_chunks(data=list(validator_indices))
                for row in cursor.execute(
                    f'{query} AND validator_index IN ({placeholders})',
                    tuple(chunk),
                )
            }
        else:
            return {x[0] for x in cursor.execute(query)}

    def get_associated_with_addresses_validator_indices(
            self,
            cursor: 'DBCursor',
            addresses: list[ChecksumEvmAddress],
    ) -> set[int]:
        """Returns indices of validators that are associated with the given addresses.

        Association means either it's a withdrawal address for any validator or
        has been used as a fee recipient for a validator or deposited to a validator.
        """
        questionmarks = '?' * len(addresses)
        cursor.execute(
            f'SELECT S.validator_index FROM eth_staking_events_info S LEFT JOIN '
            f'history_events H on S.identifier=H.identifier WHERE H.location_label IN '
            f'({",".join(questionmarks)})', addresses,
        )
        return {x[0] for x in cursor}

    def set_validator_exit(
            self,
            write_cursor: 'DBCursor',
            index: int,
            withdrawable_timestamp: Timestamp,
    ) -> None:
        """If the validator has withdrawal events, find last one and mark as exit if after withdrawable ts"""  # noqa: E501
        write_cursor.execute(
            'SELECT HE.identifier, HE.timestamp, HE.amount FROM history_events HE LEFT JOIN '
            'eth_staking_events_info SE ON SE.identifier = HE.identifier '
            'WHERE SE.validator_index=? AND HE.entry_type=? ORDER BY HE.timestamp DESC LIMIT 1',
            (index, HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT.value),
        )
        if (latest_result := write_cursor.fetchone()) is None:
            return  # no event found so nothing to do

        if (exit_ts := ts_ms_to_sec(latest_result[1])) >= withdrawable_timestamp:
            write_cursor.execute(
                'UPDATE eth_staking_events_info SET is_exit_or_blocknumber=? WHERE identifier=?',
                (1, latest_result[0]),
            )
            write_cursor.execute(
                'UPDATE history_events SET notes=? WHERE identifier=?',
                (form_withdrawal_notes(is_exit=True, validator_index=index, amount=latest_result[2]), latest_result[0]),  # noqa: E501
            )
            write_cursor.execute(
                'UPDATE eth2_validators SET exited_timestamp=? WHERE validator_index=?',
                (exit_ts, index),
            )

    def add_or_update_validators_except_ownership(
            self,
            write_cursor: 'DBCursor',
            validators: list[ValidatorDetails],
    ) -> None:
        """Adds or update validator data but keeps the ownership already in the DB"""
        self.add_or_update_validators(
            write_cursor=write_cursor,
            validators=validators,
            updatable_attributes=('validator_index', 'validator_type', 'withdrawal_address', 'activation_timestamp', 'withdrawable_timestamp'),  # noqa: E501
        )

    def add_or_update_validators(
            self,
            write_cursor: 'DBCursor',
            validators: list[ValidatorDetails],
            updatable_attributes: tuple[str, ...] = ('validator_index', 'ownership_proportion', 'validator_type', 'withdrawal_address', 'activation_timestamp', 'withdrawable_timestamp', 'exited_timestamp'),  # noqa: E501
    ) -> None:
        """Adds or updates validator data

        This used to do an INSERT OR REPLACE with an executemany. While that approach
        was simpler and "worked" it also killed all foreign key relations and since
        at the time of writing the daily stats have a foreign key relation to this table
        all the daily stats were deleted.
        """
        for validator in validators:
            result = write_cursor.execute(
                'SELECT validator_index, public_key, validator_type, ownership_proportion, withdrawal_address, '  # noqa: E501
                'activation_timestamp, withdrawable_timestamp, exited_timestamp '
                'FROM eth2_validators WHERE public_key=?', (validator.public_key,),
            ).fetchone()
            if result is not None:  # update case
                db_validator = ValidatorDetails.deserialize_from_db(result)
                for attr in updatable_attributes:
                    if getattr(db_validator, attr) != (new_value := getattr(validator, attr)):
                        if attr == 'validator_type':
                            new_value = new_value.serialize_for_db()

                        write_cursor.execute(
                            f'UPDATE eth2_validators SET {attr}=? WHERE public_key=?',
                            (new_value, validator.public_key),
                        )
            else:  # insertion case
                write_cursor.execute(
                    'INSERT INTO '
                    'eth2_validators(validator_index, public_key, validator_type, ownership_proportion, withdrawal_address, activation_timestamp, withdrawable_timestamp, exited_timestamp) VALUES(?, ?, ?, ?, ?, ?, ?, ?)',  # noqa: E501
                    validator.serialize_for_db(),
                )

    def edit_validator_ownership(self, write_cursor: 'DBCursor', validator_index: int, ownership_proportion: FVal) -> None:  # noqa: E501
        """Edits the ownership proportion for a validator identified by its index.
        May raise:
        - InputError if we try to edit a non existing validator.
        """
        write_cursor.execute(
            'UPDATE eth2_validators SET ownership_proportion=? WHERE validator_index = ?',
            (str(ownership_proportion), validator_index),
        )
        if write_cursor.rowcount == 0:
            raise InputError(
                f'Tried to edit validator with index {validator_index} '
                f'that is not in the database',
            )

    def delete_validators(self, validator_indices: list[int]) -> None:
        """Deletes the given validators from the DB. Due to marshmallow here at least one
        of the two arguments is not None.

        Also delete all events where that validator index is involved.

        May raise:
        - InputError if any of the given validators to delete does not exist in the DB
        """
        indices_num = len(validator_indices)
        question_marks = ['?'] * indices_num
        with self.db.user_write() as cursor:
            # Delete from the validators table. This should also delete from daily_staking_details
            placeholders = ','.join(question_marks)
            cursor.execute(
                f'DELETE FROM eth2_validators WHERE validator_index IN '
                f'({placeholders})',
                validator_indices,
            )
            if cursor.rowcount != len(validator_indices):
                raise InputError(
                    f'Tried to delete eth2 validator/s with indices {validator_indices} '
                    f'from the DB but at least one of them did not exist',
                )

            # Delete from the events table, all staking events except for deposits.
            # We keep deposits since they are associated with the address and are EVM transactions
            cursor.execute(
                f'DELETE FROM history_events WHERE identifier in (SELECT S.identifier '
                f'FROM eth_staking_events_info S WHERE S.validator_index IN '
                f'({",".join(question_marks)})) AND entry_type != ?',
                (*validator_indices, HistoryBaseEntryType.ETH_DEPOSIT_EVENT.serialize_for_db()),
            )

            # Delete cached timestamps
            cursor.execute(
                f'DELETE FROM key_value_cache WHERE name IN ({placeholders})',
                [
                    DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS.get_db_key(index=index)
                    for index in validator_indices
                ],
            )

    @staticmethod
    def _validator_stats_process_queries(
            cursor: 'DBCursor',
            amount_querystr: str,
            filter_query: EthStakingEventFilterQuery,
    ) -> dict[int, FVal]:
        """Execute DB query and extract numerical value per validator after using filter_query
        Return a dict of validator index to sum of amounts per validator in the filter
        """
        base_query = f'SELECT validator_index, {amount_querystr} ' + ETH_STAKING_EVENT_JOIN
        query, bindings = filter_query.prepare(with_pagination=False, with_order=False)
        cursor.execute(base_query + query + ' GROUP BY eth_staking_events_info.validator_index', bindings)  # noqa: E501

        return {entry[0]: FVal(entry[1]) for entry in cursor}

    def group_validators_by_type(
            self,
            database: 'DBHandler',
            validator_indices: set[int] | None,
    ) -> tuple[list[int], list[int]]:
        """Group validators into two categories: non-accumulating (0x00, 0x01) and accumulating (0x02).
        If no validator indices are specified, all known validators will be returned.
        Returns a tuple containing the non-accumulating and accumulating validators in two lists.
        """  # noqa: E501
        where_strs = ['']
        bindings_list: list[tuple[int | str, ...]] = [()]
        if validator_indices is not None:
            where_strs, bindings_list = [], []
            for chunk, placeholders in get_query_chunks(data=list(validator_indices)):
                where_strs.append(f'AND validator_index IN ({placeholders})')
                bindings_list.append(tuple(chunk))

        with database.conn.read_ctx() as cursor:
            validator_lists = [
                [
                    row[0]
                    for where_str, bindings in zip(where_strs, bindings_list, strict=False)
                    for row in cursor.execute(
                        f'SELECT validator_index FROM eth2_validators WHERE validator_type {operator} ? {where_str}',  # noqa: E501
                        [ValidatorType.ACCUMULATING.value, *bindings],
                    )
                ] for operator in ('!=', '=')
            ]

        return tuple(validator_lists)  # type: ignore  # will be two list[int]

    def _query_chunked_withdrawal_amount_sums(
            self,
            cursor: 'DBCursor',
            from_ts: Timestamp,
            to_ts: Timestamp,
            amount_querystr: str,
            validator_indices: list[int],
            withdrawal_types_filter: WithdrawalTypesFilter,
    ) -> dict[int, FVal]:
        """Query eth2 withdrawal amount sums in chunks to avoid using too many placeholders."""
        withdrawal_sums: dict[int, FVal] = defaultdict(lambda: ZERO)
        for chunk, _ in get_query_chunks(data=validator_indices):
            for key, value in self._validator_stats_process_queries(
                cursor=cursor,
                amount_querystr=amount_querystr,
                filter_query=EthWithdrawalFilterQuery.make(
                    from_ts=from_ts,
                    to_ts=to_ts,
                    validator_indices=chunk,  # type: ignore  # chunk will be a list[int]
                    event_types=[HistoryEventType.STAKING],
                    event_subtypes=[HistoryEventSubType.REMOVE_ASSET],
                    entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT]),
                    withdrawal_types_filter=withdrawal_types_filter,
                ),
            ).items():
                withdrawal_sums[key] += value

        return withdrawal_sums

    def process_non_accumulating_validators_balances_and_pnl(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            validator_indices: list[int],
            balances_over_time: dict[int, dict[TimestampMS, FVal]],
            withdrawals_pnl: dict[int, FVal],
            exits_pnl: dict[int, FVal],
    ) -> tuple[dict[int, dict[TimestampMS, FVal]], dict[int, FVal], dict[int, FVal]]:
        """Process non-accumulating validators, setting the balances and retrieving the pnl from
        withdrawals and exits.

        Since non-accumulating validators will have an effective balance of 32, we can simply
        set a single entry of 32 at to_ts in balances_over_time.

        Returns the `balances_over_time`, `withdrawals_pnl` and `exits_pnl` dicts in a tuple.
        """
        to_ts_ms = ts_sec_to_ms(to_ts)
        for validator in validator_indices:  # All non-accumulating validators have an effective balance of 32  # noqa: E501
            balances_over_time[validator][to_ts_ms] = MIN_EFFECTIVE_BALANCE

        with self.db.conn.read_ctx() as cursor:
            consolidated_validators = self.get_consolidated_validators(cursor)
            withdrawals_pnl.update(self._query_chunked_withdrawal_amount_sums(
                cursor=cursor,
                from_ts=from_ts,
                to_ts=to_ts,
                amount_querystr='SUM(CAST(amount AS REAL))',
                validator_indices=validator_indices,
                withdrawal_types_filter=WithdrawalTypesFilter.ONLY_PARTIAL,
            ))
            for v_index, exit_amount in self._query_chunked_withdrawal_amount_sums(
                cursor=cursor,
                amount_querystr='amount',
                from_ts=from_ts,
                to_ts=to_ts,
                validator_indices=validator_indices,
                withdrawal_types_filter=WithdrawalTypesFilter.ONLY_EXITS,
            ).items():
                if v_index in consolidated_validators:
                    withdrawals_pnl[v_index] += FVal(exit_amount)
                else:  # for non-consolidated validators, add it to exits
                    exits_pnl[v_index] += (FVal(exit_amount) - MIN_EFFECTIVE_BALANCE)

        return balances_over_time, withdrawals_pnl, exits_pnl

    def process_accumulating_validators_balances_and_pnl(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            validator_indices: list[int],
            balances_over_time: dict[int, dict[TimestampMS, FVal]],
            withdrawals_pnl: dict[int, FVal],
            exits_pnl: dict[int, FVal],
    ) -> tuple[dict[int, dict[TimestampMS, FVal]], dict[int, FVal], dict[int, FVal]]:
        """Process historical events for accumulating validators, retrieving their balances
        over time and pnl from withdrawals and exits.

        Returns the `balances_over_time`, `withdrawals_pnl` and `exits_pnl` dicts in a tuple.
        """
        events_db = DBHistoryEvents(self.db)
        events: list[HistoryBaseEntry] = []
        with self.db.conn.read_ctx() as cursor:
            cached_balances_over_time, cached_withdrawals_pnl, cached_exits_pnl, cached_last_stored_ts = self._load_eth2_validator_cache(  # noqa: E501
                cursor=cursor,
                from_ts=from_ts,
                to_ts=to_ts,
                validator_indices=validator_indices,
            )
            from_ts = Timestamp(cached_last_stored_ts + 1) if cached_last_stored_ts > 0 else from_ts  # noqa: E501

            for filter_query in (EthStakingEventFilterQuery.make(
                from_ts=from_ts,
                to_ts=to_ts,
                validator_indices=validator_indices,
                event_types=[HistoryEventType.STAKING],
                event_subtypes=[
                    HistoryEventSubType.DEPOSIT_ASSET,
                    HistoryEventSubType.REMOVE_ASSET,
                ],
                entry_types=IncludeExcludeFilterData(values=[
                    HistoryBaseEntryType.ETH_DEPOSIT_EVENT,
                    HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT,
                ]),
            ), EvmEventFilterQuery.make(
                from_ts=from_ts,
                to_ts=to_ts,
                event_types=[HistoryEventType.INFORMATIONAL],
                event_subtypes=[HistoryEventSubType.CONSOLIDATE],
                counterparties=[CPT_ETH2],
            )):
                events.extend(events_db.get_history_events_internal(
                    cursor=cursor,
                    filter_query=filter_query,  # type: ignore[arg-type]  # no overload for EthStakingEventFilterQuery
                ))

            # Get withdrawal request events for each validator
            withdrawal_request_events = defaultdict(list)
            for request_event in events_db.get_history_events_internal(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(
                    to_ts=to_ts,
                    event_types=[HistoryEventType.INFORMATIONAL],
                    event_subtypes=[HistoryEventSubType.REMOVE_ASSET],
                    counterparties=[CPT_ETH2],
                    order_by_rules=[('timestamp', False)],  # reverse so we get the first request before a withdrawal below  # noqa: E501
                ),
            ):
                if (
                    request_event.extra_data is not None and
                    (v_index := request_event.extra_data.get('validator_index')) in validator_indices  # noqa: E501
                ):  # only keep related withdrawal requests
                    withdrawal_request_events[v_index].append(request_event)

        balances_over_time.update(cached_balances_over_time)
        withdrawals_pnl.update(cached_withdrawals_pnl)
        exits_pnl.update(cached_exits_pnl)

        from_ts_ms, to_ts_ms = ts_sec_to_ms(from_ts), ts_sec_to_ms(to_ts)
        validator_balances: dict[int, FVal] = defaultdict(lambda: ZERO)
        # This mapping is for skimming withdrawals per timestamp to properly cache and filter by time range  # noqa: E501
        withdrawals_pnl_over_time:  dict[int, dict[TimestampMS, FVal]] = defaultdict(lambda: defaultdict(lambda: ZERO))  # noqa: E501
        for event in sorted(events, key=lambda x: x.timestamp):  # Process all related events and populate the relevant mappings  # noqa: E501
            if isinstance(event, EthDepositEvent):
                validator_balances[v_index := event.validator_index] += event.amount
            elif isinstance(event, EthWithdrawalEvent):
                v_index = event.validator_index
                if event.is_exit_or_blocknumber is True:  # Exit withdrawals
                    if from_ts_ms <= event.timestamp <= to_ts_ms:  # only count pnl within the specified range  # noqa: E501
                        exits_pnl[v_index] = event.amount - validator_balances[v_index]
                        validator_balances[v_index] = ZERO
                    else:
                        continue
                else:  # Partial withdrawals
                    for request_event in withdrawal_request_events.get(v_index, []):
                        if request_event.timestamp <= event.timestamp and request_event.amount == event.amount:  # requested partial withdrawal  # noqa: E501
                            validator_balances[v_index] -= event.amount
                            withdrawal_request_events[v_index].remove(request_event)  # remove this request event so we don't match it again.  # noqa: E501
                            break
                    else:  # skimming withdrawal - doesn't change the effective balance, but is counted as profit  # noqa: E501
                        withdrawals_pnl_over_time[v_index][event.timestamp] += event.amount
                        continue
            elif (
                event.event_type == HistoryEventType.INFORMATIONAL and
                event.event_subtype == HistoryEventSubType.CONSOLIDATE and
                event.extra_data is not None and
                (source_validator := event.extra_data.get('source_validator_index')) is not None and  # noqa: E501
                (target_validator := event.extra_data.get('target_validator_index')) is not None
            ):
                if target_validator not in validator_indices:
                    continue

                # Find the last balance of the source validator (the amount being consolidated)
                if source_validator not in balances_over_time:  # need to process the source validator's history  # noqa: E501
                    if source_validator in validator_indices:  # Prevent recursively reprocessing the source validator  # noqa: E501
                        log.warning(
                            'Failed to find events for consolidation source validator '
                            f'{source_validator}. Skipping consolidation event.',
                        )
                        continue

                    new_balances_over_time, _, _ = self.process_validators_balances_and_pnl(
                        from_ts=from_ts,
                        to_ts=to_ts,
                        validator_indices={source_validator},
                    )
                    balances_over_time.update(new_balances_over_time)

                # else we've already processed the source validator
                source_balances = balances_over_time[source_validator]
                validator_balances[v_index := target_validator] += source_balances[max(source_balances.keys())]  # noqa: E501
            else:
                log.warning(f'Encountered unexpected event {event} during validator event processing.')  # noqa: E501
                continue

            balances_over_time[v_index][event.timestamp] = validator_balances[v_index]

        with self.db.conn.write_ctx() as write_cursor:
            self._save_eth2_validator_cache(
                write_cursor=write_cursor,
                to_ts=to_ts,
                balances_over_time=balances_over_time,
                withdrawals_pnl_over_time=withdrawals_pnl_over_time,
                exits_pnl=exits_pnl,
            )

        # recreate the withdrawals pnl to only include pnl in that timeframe.
        for v_index, balances in withdrawals_pnl_over_time.items():
            for ts, balance in balances.items():
                if from_ts_ms <= ts <= to_ts_ms:  # only count pnl within the specified range  # noqa: E501
                    withdrawals_pnl[v_index] += balance

        return balances_over_time, withdrawals_pnl, exits_pnl

    def process_validators_balances_and_pnl(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            validator_indices: set[int] | None,
    ) -> tuple[dict[int, dict[TimestampMS, FVal]], dict[int, FVal], dict[int, FVal]]:
        """Process validators for their balances over time and pnl from withdrawals and exits.
        Returns a tuple of three dicts organizing the following by validator index:
        - dict of balances over time, mapping validator indices to their balance history (timestamps → balance values),
          used for time-weighted average calculations
        - pnl from withdrawals
        - pnl from exits
        """  # noqa: E501
        non_accumulating_validators, accumulating_validators = self.group_validators_by_type(
            database=self.db,
            validator_indices=validator_indices,
        )
        balances_over_time: dict[int, dict[TimestampMS, FVal]] = defaultdict(lambda: defaultdict(lambda: ZERO))  # noqa: E501
        withdrawals_pnl: dict[int, FVal] = defaultdict(lambda: ZERO)
        exits_pnl: dict[int, FVal] = defaultdict(lambda: ZERO)
        for validators, func in (
            (non_accumulating_validators, self.process_non_accumulating_validators_balances_and_pnl),  # noqa: E501
            (accumulating_validators, self.process_accumulating_validators_balances_and_pnl),
        ):
            if len(validators) != 0:
                func(
                    from_ts=from_ts,
                    to_ts=to_ts,
                    validator_indices=validators,
                    balances_over_time=balances_over_time,
                    withdrawals_pnl=withdrawals_pnl,
                    exits_pnl=exits_pnl,
                )

        return balances_over_time, withdrawals_pnl, exits_pnl

    @staticmethod
    def _load_eth2_validator_cache(
            cursor: 'DBCursor',
            from_ts: Timestamp,
            to_ts: Timestamp,
            validator_indices: list[int] | None,
    ) -> tuple[dict[int, dict[TimestampMS, FVal]], dict[int, FVal], dict[int, FVal], Timestamp]:
        """Return cached validator balance and PnL data from the database.

        Only includes entries within the given time range and (optionally) the specified validator indices.
        Returns a tuple containing:
        - Balances over time for each validator
        - Withdrawals PnL for each validator
        - Exits PnL for each validator
        - The latest timestamp found in the cache or 0 if no data is cached

        This is only used for accumulating validators since it involves a lot of processing.
        """  # noqa: E501
        latest_ts: Timestamp = Timestamp(0)
        balances_over_time: dict[int, dict[TimestampMS, FVal]] = defaultdict(lambda: defaultdict(lambda: ZERO))  # noqa: E501
        exits_pnl: dict[int, FVal] = defaultdict(lambda: ZERO)
        withdrawals_pnl: dict[int, FVal] = defaultdict(lambda: ZERO)

        query = """SELECT validator_index, timestamp, balance, withdrawals_pnl, exit_pnl
        FROM eth_validators_data_cache WHERE timestamp >= ? AND timestamp <= ?"""
        bindings: list = [ts_sec_to_ms(from_ts), ts_sec_to_ms(to_ts)]
        if validator_indices is not None and len(validator_indices) != 0:
            query += f" AND validator_index IN ({','.join(['?'] * len(validator_indices))})"
            bindings.extend(validator_indices)
        cursor.execute(f'{query} ORDER BY timestamp ASC', bindings)

        for v_index, timestamp, str_balance, withdrawal_pnl, exit_pnl in cursor:
            if (balance := FVal(str_balance)) > ZERO:  # store balance data only if balance > 0
                balances_over_time[v_index][timestamp] = FVal(balance)

            # accumulate PnL data
            withdrawals_pnl[v_index] += FVal(withdrawal_pnl)
            exits_pnl[v_index] += FVal(exit_pnl)
            if (ts_in_sec := ts_ms_to_sec(timestamp)) > latest_ts:
                latest_ts = ts_in_sec

        return balances_over_time, withdrawals_pnl, exits_pnl, latest_ts

    @staticmethod
    def _save_eth2_validator_cache(
            write_cursor: 'DBCursor',
            to_ts: Timestamp,
            balances_over_time: dict[int, dict[TimestampMS, FVal]],
            withdrawals_pnl_over_time: dict[int, dict[TimestampMS, FVal]],
            exits_pnl: dict[int, FVal],
    ) -> None:
        """Save validator balance and PnL data to the database, once per week per validator.

        This function caches validator data weekly instead of daily to reduce database size.
        The cached data is used for faster lookups when needed.

        For each (validator, week), sums all values falling within that week across:
        - balances_over_time
        - withdrawals_pnl
        - exits_pnl

        Stores the weekly totals under the week end timestamp.
        This is only used for accumulating validators since it involves a lot of processing.
        """
        query = """INSERT OR REPLACE INTO eth_validators_data_cache (
            validator_index, timestamp, balance, withdrawals_pnl, exit_pnl
        ) VALUES (?, ?, ?, ?, ?)"""

        last_week_ts = ts_sec_to_ms(to_ts) - (ts_sec_to_ms(to_ts) % WEEK_IN_MILLISECONDS) + (WEEK_IN_MILLISECONDS - 1)  # Calculate the last week's timestamp (aligned to week boundary)  # noqa: E501
        grouped: dict[tuple[int, int], dict[str, FVal]] = defaultdict(lambda: {  # Aggregates data by (validator_index, week_start_ts) for weekly storage  # noqa: E501
            'balance': ZERO,
            'withdrawals_pnl': ZERO,
            'exit_pnl': ZERO,
        })

        for balance_key, balances in [
            ('balance', balances_over_time),
            ('withdrawals_pnl', withdrawals_pnl_over_time),
        ]:
            for validator_index, ts_map in balances.items():
                for ts, val in ts_map.items():
                    key = (validator_index, ts + (WEEK_IN_MILLISECONDS - (ts % WEEK_IN_MILLISECONDS)) - 1)  # noqa: E501
                    grouped[key][balance_key] += val

        for v_index, pnl_amount in exits_pnl.items():
            key = (v_index, last_week_ts)
            grouped[key]['exit_pnl'] += pnl_amount

        for (validator_index, week_ts), values in grouped.items():
            write_cursor.execute(query, (
                validator_index,
                week_ts,
                str(values['balance']),
                str(values['withdrawals_pnl']),
                str(values['exit_pnl']),
            ))

    def get_validators_block_and_mev_rewards(
            self,
            cursor: 'DBCursor',
            blocks_execution_filter_query: EthStakingEventFilterQuery,
            mev_execution_filter_query: HistoryEventFilterQuery,
            to_filter_indices: set[int] | None,
    ) -> tuple[dict[int, FVal], dict[int, FVal]]:
        """Query EL block and mev reward amounts for the given filter.

        Returns each of the different amount sums for the period per validator
        """
        blocks_rewards_amounts = self._validator_stats_process_queries(
            cursor=cursor,
            amount_querystr='SUM(CAST(amount AS REAL))',  # note: has precision issues
            filter_query=blocks_execution_filter_query,
        )

        # For MEV we need to do this in python due to validator index being in extra data
        # This is also why we pass
        mev_rewards_amounts: dict[int, FVal] = defaultdict(FVal)
        query, bindings = mev_execution_filter_query.prepare(with_pagination=False, with_order=False)  # noqa: E501
        query = 'SELECT amount, extra_data FROM history_events ' + query
        for amount_str, extra_data_raw in cursor.execute(query, bindings):
            if extra_data_raw is None:
                log.warning('During validators profit query got an event without extra_data')
                continue

            try:
                extra_data = json.loads(extra_data_raw)
            except json.JSONDecodeError:
                log.error(f'Could not decode {extra_data_raw=} as json')
                continue

            if (validator_index := extra_data.get('validator_index')) is None:
                log.warning(f'During validators profit query got extra_data {extra_data} without a validator index')  # noqa: E501
                continue

            if to_filter_indices is not None and validator_index not in to_filter_indices:
                continue

            mev_rewards_amounts[validator_index] += FVal(amount_str)

        return blocks_rewards_amounts, mev_rewards_amounts

    def redecode_block_production_events(self, block_numbers: list[int] | None = None) -> None:
        """Reprocess eth block production events from the db.
        - Resets event type depending on whether the fee recipient address is tracked.
        - Combine mev reward events with evm tx events
        Optionally limit to only events for the specified block numbers.
        """
        with self.db.conn.write_ctx() as write_cursor:
            tracked_addresses = self.db.get_single_blockchain_addresses(
                cursor=write_cursor,
                blockchain=SupportedBlockchain.ETHEREUM,
            )
            for event_type, operation in (
                (HistoryEventType.STAKING, 'IN'),
                (HistoryEventType.INFORMATIONAL, 'NOT IN'),
            ):
                query = (
                    'UPDATE history_events SET type=? WHERE entry_type=? AND subtype=? '
                    f"AND location_label {operation} ({','.join('?' * len(tracked_addresses))})"
                )
                bindings = [
                    event_type.serialize(),
                    HistoryBaseEntryType.ETH_BLOCK_EVENT.value,
                    HistoryEventSubType.BLOCK_PRODUCTION.serialize(),
                    *tracked_addresses,
                ]
                if block_numbers is not None and len(block_numbers) > 0:
                    query += (
                        ' AND identifier IN (SELECT identifier FROM eth_staking_events_info '
                        f"WHERE is_exit_or_blocknumber IN ({','.join('?' * len(block_numbers))}))"
                    )
                    bindings += block_numbers

                write_cursor.execute(query, bindings)

        self.combine_block_with_tx_events(block_numbers=block_numbers)

    def combine_block_with_tx_events(self, block_numbers: list[int] | None = None) -> None:
        """Get mev reward block production events and combine them with the transaction events
        if they can be found. Optionally limit to only events for the specified block numbers.
        """
        log.debug('Entered combining of blocks with tx events')
        query = (
            """WITH mev_rewards AS (
                SELECT A_H.location_label, A_S.is_exit_or_blocknumber, A_S.validator_index FROM
                history_events A_H JOIN eth_staking_events_info A_S ON A_H.identifier = A_S.identifier
            WHERE A_H.subtype = ?)
            SELECT B_H.identifier, B_T.block_number, B_H.notes, B_T.tx_hash, mev.validator_index FROM evm_transactions B_T
            JOIN chain_events_info B_E ON B_T.tx_hash = B_E.tx_ref
            JOIN history_events B_H ON B_E.identifier = B_H.identifier
            LEFT JOIN mev_rewards mev ON mev.is_exit_or_blocknumber = B_T.block_number
            AND mev.location_label = B_H.location_label WHERE B_H.asset = ? AND B_H.type = ?
            AND B_H.subtype = ? AND mev.validator_index IS NOT NULL"""  # noqa: E501
        )
        bindings: list[int | str] = [
            HistoryEventSubType.MEV_REWARD.serialize(),
            A_ETH.identifier,
            HistoryEventType.RECEIVE.serialize(),
            HistoryEventSubType.NONE.serialize(),
        ]
        queries_and_bindings = []
        if block_numbers is not None and len(block_numbers) > 0:
            for chunk, placeholders in get_query_chunks(data=block_numbers):
                queries_and_bindings.append((
                    f'{query} AND B_T.block_number IN ({placeholders})',
                    bindings + list(chunk),
                ))
        else:
            queries_and_bindings = [(query, bindings)]

        with self.db.conn.read_ctx() as cursor:
            changes = [
                (
                    (group_identifier := EthBlockEvent.form_group_identifier(entry[1])),
                    group_identifier,
                    f'{entry[2]} as mev reward for block {entry[1]} in {(tx_hash := deserialize_evm_tx_hash(entry[3]))!s}',  # noqa: E501
                    HistoryEventType.STAKING.serialize(),
                    HistoryEventSubType.MEV_REWARD.serialize(),
                    json.dumps({'validator_index': entry[4]}),  # extra data
                    entry[0],  # identifier
                    tx_hash,
                ) for q, b in queries_and_bindings for entry in cursor.execute(q, b)
            ]

        if (change_count := len(changes)) == 0:
            log.debug('No tx events to combine with block events')
            return

        log.debug(f'Will combine {change_count} tx events with block events')
        with self.db.user_write() as write_cursor:
            for changes_entry in changes:
                result = write_cursor.execute(
                    'SELECT COUNT(*) FROM history_events HE LEFT JOIN chain_events_info CE ON '
                    'HE.identifier = CE.identifier WHERE HE.group_identifier=? AND CE.tx_ref=?',
                    (changes_entry[0], changes_entry[7]),
                ).fetchone()[0]
                if result == 1:  # Has already been moved.
                    log.debug(f'Did not move history event with {changes_entry} in combine_block_with_tx_events since event with same tx_hash already combined in the block')  # noqa: E501
                    write_cursor.execute('DELETE FROM history_events WHERE identifier=?', (changes_entry[6],))  # noqa: E501
                    continue

                try:
                    write_cursor.execute(
                        'UPDATE history_events '
                        'SET group_identifier=?, sequence_index=('
                        'SELECT MAX(sequence_index) FROM history_events E2 WHERE E2.group_identifier=?)+1, '  # noqa: E501
                        'notes=?, type=?, subtype=?, extra_data=? WHERE identifier=?',
                        changes_entry[:-1],
                    )
                except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                    log.warning(f'Could not update history events with {changes_entry} in combine_block_with_tx_events due to {e!s}')  # noqa: E501
                    # already exists. Probably right after resetting events? Delete old one
                    write_cursor.execute('DELETE FROM history_events WHERE identifier=?', (changes_entry[6],))  # noqa: E501

        log.debug('Finished combining of blocks with tx events')
