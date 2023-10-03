import copy
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal, Optional, Union, overload

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures.base import (
    HistoryBaseEntry,
    HistoryBaseEntryType,
    HistoryEvent,
)
from rotkehlchen.accounting.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthStakingEvent,
    EthWithdrawalEvent,
)
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.limits import FREE_HISTORY_EVENTS_LIMIT
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.db.filtering import (
    ALL_EVENTS_DATA_JOIN,
    EVM_EVENT_JOIN,
    DBEqualsFilter,
    DBIgnoredAssetsFilter,
    DBIgnoreValuesFilter,
    EthDepositEventFilterQuery,
    EvmEventFilterQuery,
    HistoryBaseEntryFilterQuery,
    HistoryEventFilterQuery,
)
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import (
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    EVMTxHash,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


HISTORY_BASE_ENTRY_FIELDS = 'entry_type, history_events.identifier, event_identifier, sequence_index, timestamp, location, location_label, asset, amount, usd_value, notes, type, subtype '  # noqa: E501
HISTORY_BASE_ENTRY_LENGTH = 12

EVM_EVENT_FIELDS = 'tx_hash, counterparty, product, address, extra_data'
EVM_FIELD_LENGTH = 5

ETH_STAKING_EVENT_FIELDS = 'validator_index, is_exit_or_blocknumber'
ETH_STAKING_FIELD_LENGTH = 2


class DBHistoryEvents:

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def add_history_event(
            self,
            write_cursor: 'DBCursor',
            event: HistoryBaseEntry,
            mapping_values: Optional[dict[str, int]] = None,
    ) -> Optional[int]:
        """Insert a single history entry to the DB. Returns its identifier or
        None if it already exists. This function serializes the event depending
        on type to the appropriate DB tables.

        Optionally map it to a specific value used to map attributes
        to some events

        May raise:
        - DeserializationError if the event could not be serialized for the DB
        - sqlcipher.IntegrityError: If the asset of the added history event does not exist in
        the DB. Can only happen if an event with an unresolved asset is passed.
        """
        db_tuples = event.serialize_for_db()
        write_cursor.execute(
            'INSERT OR IGNORE INTO history_events(entry_type, event_identifier, sequence_index,'
            'timestamp, location, location_label, asset, amount, usd_value, notes,'
            'type, subtype) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            db_tuples[0],
        )
        if write_cursor.rowcount == 0:
            return None  # already exists

        identifier = write_cursor.lastrowid
        if isinstance(event, EvmEvent):
            write_cursor.execute(  # this also writes for eth deposit events
                'INSERT OR IGNORE INTO evm_events_info(identifier, tx_hash, counterparty, product,'
                'address, extra_data) VALUES (?, ?, ?, ?, ?, ?)',
                (identifier, *db_tuples[1]),
            )
        if isinstance(event, EthStakingEvent):
            idx = 2 if isinstance(event, EthDepositEvent) else 1
            write_cursor.execute(
                'INSERT OR IGNORE INTO eth_staking_events_info(identifier, validator_index, '
                'is_exit_or_blocknumber) VALUES (?, ?, ?)',
                (identifier, *db_tuples[idx]),
            )

        if mapping_values is not None:
            write_cursor.executemany(
                'INSERT OR IGNORE INTO history_events_mappings(parent_identifier, name, value) '
                'VALUES(?, ?, ?)',
                [(identifier, k, v) for k, v in mapping_values.items()],
            )

        return identifier

    def add_history_events(
            self,
            write_cursor: 'DBCursor',
            history: Sequence[HistoryBaseEntry],
    ) -> None:
        """Insert a list of history events in the database.

        Check add_history_event() to see possible Exceptions
        """
        for event in history:
            self.add_history_event(
                write_cursor=write_cursor,
                event=event,
            )

    def edit_history_event(self, event: HistoryBaseEntry) -> tuple[bool, str]:
        """
        Edit a history entry to the DB with information provided by the user.
        NOTE: It edits all the fields except the extra_data one.
        """
        with self.db.user_write() as cursor:
            db_tuples = event.serialize_for_db()
            try:
                cursor.execute(
                    'UPDATE history_events SET entry_type=?, event_identifier=?, '
                    'sequence_index=?, timestamp=?, location=?, location_label=?, asset=?, '
                    'amount=?, usd_value=?, notes=?, type=?, subtype=? WHERE identifier=?',
                    (*db_tuples[0], event.identifier),
                )
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                msg = (
                    f'Tried to edit event to have event_identifier {event.event_identifier} '  # noqa: E501
                    f'and sequence_index {event.sequence_index} but it already exists'
                )
                return False, msg

            if isinstance(event, EvmEvent):
                cursor.execute(
                    'UPDATE evm_events_info SET tx_hash=?, counterparty=?, product=?, address=? WHERE identifier=?',    # noqa: E501
                    (*db_tuples[1][:-1], event.identifier),  # -1 is without extra data
                )
            elif isinstance(event, EthStakingEvent):
                cursor.execute(
                    'UPDATE eth_staking_events_info SET validator_index=?, is_exit_or_blocknumber=? WHERE identifier=?',  # noqa: E501
                    (*db_tuples[1], event.identifier),
                )

            if cursor.rowcount != 1:
                msg = f'Tried to edit event with id {event.identifier} but could not find it in the DB'  # noqa: E501
                return False, msg

            # Also mark it as customized
            cursor.execute(
                'INSERT OR IGNORE INTO history_events_mappings(parent_identifier, name, value) '
                'VALUES(?, ?, ?)',
                (event.identifier, HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
            )

        return True, ''

    def delete_history_events_by_identifier(
            self,
            identifiers: list[int],
            force_delete: bool = False,
    ) -> Optional[str]:
        """
        Delete the history events with the given identifiers. If deleting an event
        makes it the last event of a transaction hash then do not allow deletion
        unless force_delete is True. The reason for this limitation is that if a
        user deletes the last event of a transaction there is no way at the moment
        to retrieve it as the caller(the frontend) no longer knows the transaction
        hash to redecode.

        With force_delete True, the frontend specifically keeps the transaction hash
        and calls redecode right after.

        If any identifier is missing the entire call fails and an error message
        is returned. Otherwise None is returned.
        """
        for identifier in identifiers:
            if force_delete is False:
                with self.db.conn.read_ctx() as cursor:
                    cursor.execute(
                        'SELECT COUNT(*) == 1 FROM history_events WHERE event_identifier=(SELECT '
                        'event_identifier FROM history_events WHERE identifier=? AND entry_type=?)',  # noqa: E501
                        (identifier, HistoryBaseEntryType.EVM_EVENT.serialize_for_db()),
                    )
                    if bool(cursor.fetchone()[0]) is True:
                        return (
                            f'Tried to remove history event with id {identifier} '
                            f'which was the last event of a transaction'
                        )

            with self.db.user_write() as write_cursor:
                write_cursor.execute(
                    'DELETE FROM history_events WHERE identifier=?', (identifier,),
                )
                affected_rows = write_cursor.rowcount
            if affected_rows != 1:
                return (
                    f'Tried to remove history event with id {identifier} which does not exist'
                )

        return None

    def delete_events_by_tx_hash(
            self,
            write_cursor: 'DBCursor',
            tx_hashes: list[EVMTxHash],
            chain_id: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    ) -> None:
        """Delete all relevant (by transaction hash) history events except those that
        are customized. Only use with limited number of transactions!!!

        If you want to reset all decoded events better use the _reset_decoded_events
        code in v37 -> v38 upgrade as that is not limited to the number of transactions
        and won't potentially raise a too many sql variables error
        """
        customized_event_ids = self.get_customized_event_identifiers(cursor=write_cursor, chain_id=chain_id)  # noqa: E501
        length = len(customized_event_ids)
        querystr = f'DELETE FROM history_events WHERE identifier IN (SELECT H.identifier from history_events H INNER JOIN evm_events_info E ON H.identifier=E.identifier AND E.tx_hash IN ({", ".join(["?"] * len(tx_hashes))}))'  # noqa: E501
        if length != 0:
            querystr += f' AND identifier NOT IN ({", ".join(["?"] * length)})'
            bindings = [*tx_hashes, *customized_event_ids]
        else:
            bindings = tx_hashes  # type: ignore  # different type of elements in the list
        write_cursor.execute(querystr, bindings)

    def get_customized_event_identifiers(
            self,
            cursor: 'DBCursor',
            chain_id: Optional[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE],
    ) -> list[int]:
        """Returns the identifiers of all the events in the database that have been customized

        Optionally filter by chain_id
        """
        if chain_id is None:
            cursor.execute(
                'SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?',
                (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
            )
        else:
            cursor.execute(
                'SELECT A.parent_identifier FROM history_events_mappings A JOIN '
                'history_events_mappings B ON A.parent_identifier=B.parent_identifier AND '
                'A.name=? AND A.value=? '
                'JOIN history_events C ON C.identifier=A.parent_identifier AND C.location=?',
                (
                    HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED,
                    Location.from_chain_id(chain_id).serialize_for_db(),
                ),
            )

        return [x[0] for x in cursor]

    def get_evm_event_by_identifier(self, identifier: int) -> Optional['EvmEvent']:
        """Returns the EVM event with the given identifier"""
        with self.db.conn.read_ctx() as cursor:
            event_data = cursor.execute(
                f'SELECT {HISTORY_BASE_ENTRY_FIELDS}, {EVM_EVENT_FIELDS} {EVM_EVENT_JOIN} WHERE history_events.identifier=? AND entry_type=?',  # noqa: E501
                (identifier, HistoryBaseEntryType.EVM_EVENT.value),
            ).fetchone()
            if event_data is None:
                log.debug(f'Didnt find evm event with identifier {identifier}')
                return None

        try:
            deserialized = EvmEvent.deserialize_from_db(event_data[1:])
        except (DeserializationError, UnknownAsset) as e:
            log.debug(f'Failed to deserialize evm event {event_data} due to {e!s}')
            return None

        return deserialized

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[True],
    ) -> list[tuple[int, HistoryEvent]]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[False] = ...,
    ) -> list[HistoryEvent]:
        ...

    @overload
    def get_history_events(  # type: ignore  # cant match since EthDepositEvent is EvmEvent
            self,  # no idea how to properly type this situation with overloads here
            cursor: 'DBCursor',
            filter_query: EthDepositEventFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[True],
    ) -> list[tuple[int, EthDepositEvent]]:
        ...

    @overload
    def get_history_events(  # type: ignore  # cant match since EthDepositEvent is EvmEvent
            self,  # no idea how to properly type this situation with overloads here
            cursor: 'DBCursor',
            filter_query: EthDepositEventFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[False] = ...,
    ) -> list[EthDepositEvent]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: EvmEventFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[True],
    ) -> list[tuple[int, EvmEvent]]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: EvmEventFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[False] = ...,
    ) -> list[EvmEvent]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: Union[HistoryEventFilterQuery, EvmEventFilterQuery, EthDepositEventFilterQuery],  # noqa: E501
            has_premium: bool,
            group_by_event_ids: bool = False,
    ) -> Union[
        list[tuple[int, HistoryEvent]], list[HistoryEvent],
        list[tuple[int, EvmEvent]], list[EvmEvent],
        list[tuple[int, EthDepositEvent]], list[EthDepositEvent],
    ]:
        """
        This fallback is needed due to
        https://github.com/python/mypy/issues/6113#issuecomment-869828434
        """

    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: Union[HistoryEventFilterQuery, EvmEventFilterQuery, EthDepositEventFilterQuery],  # noqa: E501
            has_premium: bool,
            group_by_event_ids: bool = False,
    ) -> Union[
        list[tuple[int, HistoryEvent]], list[HistoryEvent],
        list[tuple[int, EvmEvent]], list[EvmEvent],
        list[tuple[int, EthDepositEvent]], list[EthDepositEvent],
    ]:
        """Get all events from the DB, deserialized depending on the event type

        TODO: To not query all columns with all joins for all cases, we perhaps can
        peek on the entry type of the filter and adjust the SELECT fields accordingly?
        """
        free_query_group_by = ''
        free_query_count = ''
        base_prefix = 'SELECT '
        type_idx = 0
        special_free_query = False
        if group_by_event_ids is True:
            if has_premium:
                base_prefix += 'COUNT(*), '
            else:  # a bit ugly conditions to keep limit at groups for free users
                free_query_count = 'COUNT(*), '
                for fil in filter_query.filters:
                    if isinstance(fil, DBIgnoredAssetsFilter):
                        # Also don't count spam asset transactions in the limit
                        free_query_group_by = 'WHERE (asset IS NULL OR asset NOT IN (SELECT value FROM multisettings WHERE name="ignored_asset")) '  # noqa: E501
                        break
                free_query_group_by += 'GROUP BY event_identifier'
                special_free_query = True

            type_idx = 1

        prepared_query, bindings = filter_query.prepare(
            with_group_by=group_by_event_ids,
            special_free_query=special_free_query,
        )

        if has_premium is True:
            base_query = f'{base_prefix} {HISTORY_BASE_ENTRY_FIELDS}, {EVM_EVENT_FIELDS}, {ETH_STAKING_EVENT_FIELDS} {ALL_EVENTS_DATA_JOIN}'  # noqa: E501
        else:
            base_query = f'{base_prefix} * FROM (SELECT {free_query_count} {HISTORY_BASE_ENTRY_FIELDS}, {EVM_EVENT_FIELDS}, {ETH_STAKING_EVENT_FIELDS} {ALL_EVENTS_DATA_JOIN} {free_query_group_by} ORDER BY timestamp DESC, sequence_index ASC LIMIT ?) '  # noqa: E501
            bindings.insert(0, FREE_HISTORY_EVENTS_LIMIT)

        cursor.execute(base_query + prepared_query, bindings)
        output: Union[list[HistoryBaseEntry], list[tuple[int, HistoryBaseEntry]]] = []  # type: ignore  # noqa: E501
        data_start_idx = type_idx + 1
        for entry in cursor:
            entry_type = HistoryBaseEntryType(entry[type_idx])
            try:
                deserialized_event: Union[HistoryEvent, EvmEvent, EthWithdrawalEvent, EthBlockEvent]  # noqa: E501
                # Deserialize event depending on its type
                if entry_type == HistoryBaseEntryType.EVM_EVENT:
                    data = (
                        entry[data_start_idx:data_start_idx + HISTORY_BASE_ENTRY_LENGTH + 1] +
                        entry[data_start_idx + HISTORY_BASE_ENTRY_LENGTH + 1:data_start_idx + HISTORY_BASE_ENTRY_LENGTH + EVM_FIELD_LENGTH + 1]    # noqa: E501
                    )
                    deserialized_event = EvmEvent.deserialize_from_db(data)
                elif entry_type in (
                        HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT,
                        HistoryBaseEntryType.ETH_BLOCK_EVENT,
                ):
                    data = (
                        entry[data_start_idx:data_start_idx + 1] +
                        entry[data_start_idx + 3:data_start_idx + 4] +
                        entry[data_start_idx + 5:data_start_idx + 6] +
                        entry[data_start_idx + 7:data_start_idx + 9] +
                        entry[data_start_idx + 11:data_start_idx + 12] +
                        entry[data_start_idx + HISTORY_BASE_ENTRY_LENGTH + EVM_FIELD_LENGTH:data_start_idx + HISTORY_BASE_ENTRY_LENGTH + EVM_FIELD_LENGTH + ETH_STAKING_FIELD_LENGTH + 1]  # noqa: E501
                    )
                    if entry_type == HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT:
                        deserialized_event = EthWithdrawalEvent.deserialize_from_db(data)
                    else:
                        deserialized_event = EthBlockEvent.deserialize_from_db(data)

                elif entry_type == HistoryBaseEntryType.ETH_DEPOSIT_EVENT:
                    data = (
                        entry[data_start_idx:data_start_idx + 4] +
                        entry[data_start_idx + 5:data_start_idx + 6] +
                        entry[data_start_idx + 7:data_start_idx + 9] +
                        entry[data_start_idx + HISTORY_BASE_ENTRY_LENGTH:data_start_idx + HISTORY_BASE_ENTRY_LENGTH + 1] +  # noqa: E501
                        entry[data_start_idx + HISTORY_BASE_ENTRY_LENGTH + EVM_FIELD_LENGTH:data_start_idx + HISTORY_BASE_ENTRY_LENGTH + EVM_FIELD_LENGTH + 1]  # noqa: E501
                    )
                    deserialized_event = EthDepositEvent.deserialize_from_db(data)

                else:
                    data = entry[data_start_idx:HISTORY_BASE_ENTRY_LENGTH + 1]
                    deserialized_event = HistoryEvent.deserialize_from_db(entry[data_start_idx:])
            except (DeserializationError, UnknownAsset) as e:
                log.debug(f'Failed to deserialize history event {entry} due to {e!s}')
                continue

            if group_by_event_ids is True:
                output.append((entry[0], deserialized_event))  # type: ignore
            else:
                output.append(deserialized_event)  # type: ignore

        return output  # type: ignore # This is due to needing a generic HistoryBaseEntry return in this function, but the overloads would not work since HistoryEvent` is the same. Essentially the non-abstract version of HistoryBaseEntry   # noqa: E501

    @overload
    def get_history_events_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryBaseEntryFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[True],
            entries_limit: Optional[int] = None,
    ) -> tuple[list[tuple[int, HistoryBaseEntry]], int, int]:
        ...

    @overload
    def get_history_events_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryBaseEntryFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[False] = ...,
            entries_limit: Optional[int] = None,
    ) -> tuple[list[HistoryBaseEntry], int, int]:
        ...

    @overload
    def get_history_events_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryBaseEntryFilterQuery,
            has_premium: bool,
            group_by_event_ids: bool = False,
            entries_limit: Optional[int] = None,
    ) -> tuple[Union[list[tuple[int, HistoryBaseEntry]], list[HistoryBaseEntry]], int, int]:
        """
        This fallback is needed due to
        https://github.com/python/mypy/issues/6113#issuecomment-869828434
        """

    def get_history_events_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: 'HistoryBaseEntryFilterQuery',
            has_premium: bool,
            group_by_event_ids: bool = False,
            entries_limit: Optional[int] = None,
    ) -> tuple[Union[list[tuple[int, HistoryBaseEntry]], list[HistoryBaseEntry]], int, int]:
        """Gets all history events for all types, based on the filter query.

        Also returns how many are the total found for the filter and the total found applying
        the limit if provided. Otherwise count_with_limit and count_without_limit are equal.
        """
        events = self.get_history_events(  # type: ignore  # is due to HistoryBaseEntryFilterQuery not possible to be overloaded in get_history_events  # noqa: E501
            cursor=cursor,
            filter_query=filter_query,
            has_premium=has_premium,
            group_by_event_ids=group_by_event_ids,
        )
        count_without_limit, count_with_limit = self.get_history_events_count(
            cursor=cursor,
            query_filter=filter_query,
            group_by_event_ids=group_by_event_ids,
            entries_limit=entries_limit,
        )
        return events, count_without_limit, count_with_limit

    def get_base_entries_missing_prices(
            self,
            query_filter: HistoryBaseEntryFilterQuery,
            ignored_assets: Optional[list[str]] = None,
    ) -> list[tuple[str, FVal, Asset, Timestamp]]:
        """
        Searches base entries missing usd prices that have not previously been checked in
        this session.
        """
        # Use a deepcopy to avoid mutations in the filter query if it is used later
        new_query_filter = copy.deepcopy(query_filter)
        new_query_filter.filters.append(
            DBEqualsFilter(and_op=True, column='usd_value', value='0'),
        )
        if ignored_assets is not None:
            new_query_filter.filters.append(
                DBIgnoreValuesFilter(
                    and_op=True,
                    column='history_events.identifier',
                    values=ignored_assets,
                ),
            )
        return self.rows_missing_prices_in_base_entries(filter_query=new_query_filter)

    def rows_missing_prices_in_base_entries(
            self,
            filter_query: HistoryBaseEntryFilterQuery,
    ) -> list[tuple[str, FVal, Asset, Timestamp]]:
        """
        Get missing prices for history base entries based on filter query
        """
        query, bindings = filter_query.prepare()
        query = f'SELECT history_events.identifier, amount, asset, timestamp {ALL_EVENTS_DATA_JOIN}' + query  # noqa: E501
        result = []
        cursor = self.db.conn.cursor()
        cursor.execute(query, bindings)
        for identifier, amount_raw, asset_identifier, timestamp in cursor:
            try:
                amount = deserialize_fval(
                    value=amount_raw,
                    name='historic base entry usd_value query',
                    location='query_missing_prices',
                )
                result.append(
                    (
                        identifier,
                        amount,
                        Asset(asset_identifier).check_existence(),
                        ts_ms_to_sec(TimestampMS(timestamp)),
                    ),
                )
            except DeserializationError as e:
                log.error(
                    f'Failed to read value from historic base entry {identifier} '
                    f'with amount. {e!s}',
                )
            except UnknownAsset as e:
                log.error(
                    f'Failed to read asset from historic base entry {identifier} '
                    f'with asset identifier {asset_identifier}. {e!s}',
                )
        return result

    def get_entries_assets_history_events(
            self,
            cursor: 'DBCursor',
            query_filter: HistoryEventFilterQuery,
    ) -> list[Asset]:
        """Returns asset from base entry events using the desired filter"""
        query, bindings = query_filter.prepare(with_pagination=False)
        query = 'SELECT DISTINCT asset from history_events ' + query
        assets = []
        cursor.execute(query, bindings)
        for asset_id in cursor:
            try:
                assets.append(Asset(asset_id[0]).check_existence())
            except (UnknownAsset, DeserializationError) as e:
                self.db.msg_aggregator.add_error(
                    f'Found asset {asset_id} in the base history events table and '
                    f'is not in the assets database. {e!s}',
                )
        return assets

    def get_history_events_count(
            self,
            cursor: 'DBCursor',
            query_filter: HistoryBaseEntryFilterQuery,
            group_by_event_ids: bool = False,
            entries_limit: Optional[int] = None,
    ) -> tuple[int, int]:
        """
        Returns how many events matching the filter but ignoring pagination are in the DB.
        We return two integers. The first one being the number of events returned and the second
        the number of events if any limit is applied, otherwise the second value matches
        the first.
        """
        prepared_query, bindings = query_filter.prepare(with_pagination=False)
        # we need to select everything because any column could be used in the filter
        query = 'SELECT * ' + query_filter.get_join_query() + prepared_query
        if group_by_event_ids:
            query = f'SELECT event_identifier FROM ({query}) GROUP BY event_identifier'
        query = f'SELECT COUNT(*) FROM ({query})'
        count_without_limit = cursor.execute(query, bindings).fetchone()[0]

        if entries_limit is not None:
            query = 'SELECT * ' + query_filter.get_join_query()
            if group_by_event_ids:  # we take the groups before the limit has been applied
                query += ' GROUP BY event_identifier '
            query += ' ORDER BY timestamp DESC LIMIT ?'
            bindings.insert(0, entries_limit)
            query = f'SELECT COUNT(*) FROM ({query}) ' + prepared_query

            count_with_limit = cursor.execute(query, bindings).fetchone()[0]
            return count_without_limit, count_with_limit

        return count_without_limit, count_without_limit

    def get_value_stats(
            self,
            cursor: 'DBCursor',
            query_filters: str,
            bindings: list[Any],
    ) -> tuple[FVal, list[tuple[str, FVal, FVal]]]:
        """Returns the sum of the USD value at the time of acquisition and the amount received
        by asset
        TODO: At the moment this function is used by liquity and kraken. Change it to use a filter
        instead of query string and bindings when the refactor of the history events is made.
        """
        usd_value = ZERO
        try:
            query = 'SELECT SUM(CAST(usd_value AS REAL)) FROM history_events ' + query_filters
            result = cursor.execute(query, bindings).fetchone()[0]  # count(*) always returns
            if result is not None:
                usd_value = deserialize_fval(
                    value=result,
                    name='usd value in history events stats',
                    location='get_value_stats',
                )
        except DeserializationError as e:
            log.error(f'Didnt get correct valid usd_value for history_events query. {e!s}')

        query = (
            f'SELECT asset, SUM(CAST(amount AS REAL)), SUM(CAST(usd_value AS REAL)) '
            f'FROM history_events {query_filters}'
            f' GROUP BY asset;'
        )
        cursor.execute(query, bindings)
        assets_amounts = []
        for row in cursor:
            try:
                asset = row[0]  # existence is guaranteed due the foreign key relation
                amount = deserialize_fval(
                    value=row[1],
                    name='total amount in history events stats',
                    location='get_value_stats',
                )
                sum_of_usd_values = deserialize_fval(
                    value=row[2],
                    name='total usd value in history events stats',
                    location='get_value_stats',
                )
                assets_amounts.append((asset, amount, sum_of_usd_values))
            except DeserializationError as e:
                log.debug(f'Failed to deserialize amount {row[1]}. {e!s}')
        return usd_value, assets_amounts

    def get_hidden_event_ids(self, cursor: 'DBCursor') -> list[int]:
        """Returns all event identifiers that should be hidden in the UI

        These are, at the moment, special cases where due to grouping different event
        types with similar info they all appear together but the UI should just show one.
        """
        # Only 1 type of hidden event for now
        cursor.execute(
            'SELECT E.identifier FROM history_events E LEFT JOIN eth_staking_events_info S '
            'ON E.identifier=S.identifier WHERE E.sequence_index=1 AND S.identifier IS NOT NULL '
            'AND 3=(SELECT COUNT(*) FROM history_events E2 WHERE '
            'E2.event_identifier=E.event_identifier)',
        )
        result = [x[0] for x in cursor]
        return result
