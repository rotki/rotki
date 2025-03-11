import json
import logging
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, Optional, overload

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.limits import FREE_HISTORY_EVENTS_LIMIT
from rotkehlchen.db.constants import (
    ETH_STAKING_EVENT_FIELDS,
    ETH_STAKING_FIELD_LENGTH,
    EVM_EVENT_FIELDS,
    EVM_FIELD_LENGTH,
    EVMTX_DECODED,
    HISTORY_BASE_ENTRY_FIELDS,
    HISTORY_BASE_ENTRY_LENGTH,
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
)
from rotkehlchen.db.filtering import (
    ALL_EVENTS_DATA_JOIN,
    EVM_EVENT_JOIN,
    DBIgnoredAssetsFilter,
    EthDepositEventFilterQuery,
    EthWithdrawalFilterQuery,
    EvmEventFilterQuery,
    HistoryBaseEntryFilterQuery,
    HistoryEventFilterQuery,
)
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntry,
    HistoryBaseEntryType,
    HistoryEvent,
)
from rotkehlchen.history.events.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthWithdrawalEvent,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.price import query_usd_price_or_use_default
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import (
    EVM_EVMLIKE_LOCATIONS_TYPE,
    ChainID,
    EVMTxHash,
    Location,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def filter_ignore_asset_query(include_ignored_assets: bool = False) -> str:
    """Create and return the subquery to filter ignored assets. If `include_ignored_assets`
    is true then the filter is returned to include them."""
    ignored_asset_subquery = "SELECT value FROM multisettings WHERE name='ignored_asset')"
    if include_ignored_assets:
        return f'WHERE (asset IN ({ignored_asset_subquery}) '
    return f'WHERE (asset IS NULL OR asset NOT IN ({ignored_asset_subquery}) '


def maybe_filter_ignore_asset(
        filter_query: HistoryBaseEntryFilterQuery,
        include_ignored_assets: bool = False,
) -> str:
    """An auxiliary function to find if query_filter contains `DBIgnoredAssetsFilter`. If it does
    then return that filter clause. This is done where we want to filter ignored assets
    before applying the free limit. If `include_ignored_assets` is true then the filter is returned
    to include them."""
    for fil in filter_query.filters:
        if isinstance(fil, DBIgnoredAssetsFilter):
            return filter_ignore_asset_query(include_ignored_assets)
    return ''


class DBHistoryEvents:

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def add_history_event(
            self,
            write_cursor: 'DBCursor',
            event: HistoryBaseEntry,
            mapping_values: dict[str, int] | None = None,
    ) -> int | None:
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
        identifier = None  # overwritten by first write
        for idx, (insertquery, _, bindings) in enumerate(event.serialize_for_db()):
            if idx == 0:
                write_cursor.execute(f'INSERT OR IGNORE INTO {insertquery}', bindings)
                if write_cursor.rowcount == 0:
                    return None  # already exists
                identifier = write_cursor.lastrowid  # keep identifier to use in next insertions
            else:
                write_cursor.execute(f'INSERT OR IGNORE INTO {insertquery}', (identifier, *bindings))  # noqa: E501

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

    def edit_history_event(self, write_cursor: 'DBCursor', event: HistoryBaseEntry) -> None:
        """
        Edit a history entry to the DB with information provided by the user.
        NOTE: It edits all the fields except the extra_data one.

        May raise:
            - InputError if an error occurred.
        """
        for idx, (_, updatestr, bindings) in enumerate(event.serialize_for_db()):
            if idx == 0:  # base history event data
                try:
                    write_cursor.execute(f'{updatestr} WHERE identifier=?', (*bindings, event.identifier))  # noqa: E501
                except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                    raise InputError(
                        f'Tried to edit event to have event_identifier {event.event_identifier} '
                        f'and sequence_index {event.sequence_index} but it already exists',
                    ) from e
                if write_cursor.rowcount != 1:
                    raise InputError(f'Tried to edit event with id {event.identifier} but could not find it in the DB')  # noqa: E501

            else:  # all other data
                write_cursor.execute(f'{updatestr} WHERE identifier=?', (*bindings, event.identifier))  # noqa: E501

        # Also mark it as customized
        write_cursor.execute(
            'INSERT OR IGNORE INTO history_events_mappings(parent_identifier, name, value) '
            'VALUES(?, ?, ?)',
            (event.identifier, HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
        )

    def delete_history_events_by_identifier(
            self,
            identifiers: list[int],
            force_delete: bool = False,
    ) -> str | None:
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

    def delete_events_by_location(
            self,
            write_cursor: 'DBCursor',
            location: EVM_EVMLIKE_LOCATIONS_TYPE,
    ) -> None:
        """Delete all relevant non-customized events for a given location

        Also set evm_tx_mapping as non decoded so they can be redecoded later
        """
        customized_event_ids = self.get_customized_event_identifiers(cursor=write_cursor, location=location)  # noqa: E501
        whereclause = 'WHERE location=?'
        if (length := len(customized_event_ids)) != 0:
            whereclause += f' AND history_events.identifier NOT IN ({", ".join(["?"] * length)})'
            bindings = [location.serialize_for_db(), *customized_event_ids]
        else:
            bindings = (location.serialize_for_db(),)  # type: ignore  # different type of elements in the list

        transaction_hashes = write_cursor.execute(f'SELECT evm_events_info.tx_hash FROM history_events INNER JOIN evm_events_info ON history_events.identifier=evm_events_info.identifier {whereclause}', bindings).fetchall()  # noqa: E501
        write_cursor.execute(f'DELETE FROM history_events {whereclause}', bindings)

        if location != Location.ZKSYNC_LITE and len(transaction_hashes) != 0:
            write_cursor.executemany(
                'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?) AND value=?',  # noqa: E501
                [(x[0], location.to_chain_id(), EVMTX_DECODED) for x in transaction_hashes],
            )

    def delete_events_by_tx_hash(
            self,
            write_cursor: 'DBCursor',
            tx_hashes: list[EVMTxHash],
            location: EVM_EVMLIKE_LOCATIONS_TYPE,
            delete_customized: bool = False,
    ) -> None:
        """Delete all relevant (by transaction hash) history events except those that
        are customized. If delete_customized is True then delete those too.
        Only use with limited number of transactions!!!

        If you want to reset all decoded events better use the _reset_decoded_events
        code in v37 -> v38 upgrade as that is not limited to the number of transactions
        and won't potentially raise a too many sql variables error
        """
        customized_event_ids = []
        if not delete_customized:
            customized_event_ids = self.get_customized_event_identifiers(cursor=write_cursor, location=location)  # noqa: E501
        querystr = f'DELETE FROM history_events WHERE identifier IN (SELECT H.identifier from history_events H INNER JOIN evm_events_info E ON H.identifier=E.identifier AND E.tx_hash IN ({", ".join(["?"] * len(tx_hashes))}))'  # noqa: E501
        if (length := len(customized_event_ids)) != 0:
            querystr += f' AND identifier NOT IN ({", ".join(["?"] * length)})'
            bindings = [*tx_hashes, *customized_event_ids]
        else:
            bindings = tx_hashes  # type: ignore  # different type of elements in the list

        write_cursor.execute(querystr, bindings)

    def get_customized_event_identifiers(
            self,
            cursor: 'DBCursor',
            location: Location | None,
    ) -> list[int]:
        """Returns the identifiers of all the events in the database that have been customized

        Optionally filter by Location
        """
        if location is None:
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
                    location.serialize_for_db(),
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

    def _create_history_events_query(
            self,
            filter_query: HistoryBaseEntryFilterQuery,
            entries_limit: int,
            has_premium: bool,
            group_by_event_ids: bool = False,
    ) -> tuple[str, list]:
        """Returns the sql queries and bindings for the history events without pagination."""
        base_suffix = f'{HISTORY_BASE_ENTRY_FIELDS}, {EVM_EVENT_FIELDS}, {ETH_STAKING_EVENT_FIELDS} {ALL_EVENTS_DATA_JOIN}'  # noqa: E501
        if (ignore_asset_filter := maybe_filter_ignore_asset(filter_query, include_ignored_assets=True)) != '':  # noqa: E501
            ignore_asset_filter = (
                f' WHERE event_identifier NOT IN '
                f'(SELECT DISTINCT event_identifier FROM history_events {ignore_asset_filter})'
            )

        premium_base_suffix = f'{base_suffix} {ignore_asset_filter}'
        free_base_suffix = (
            f'* FROM (SELECT {base_suffix}) WHERE event_identifier IN ('
            f'SELECT DISTINCT event_identifier FROM history_events {ignore_asset_filter} '
            'ORDER BY timestamp DESC,sequence_index ASC LIMIT ?)'  # free query only select the last LIMIT groups  # noqa: E501
        )

        if has_premium:
            suffix, limit = premium_base_suffix, []
        else:
            suffix, limit = free_base_suffix, [entries_limit]

        if group_by_event_ids:
            filters, query_bindings = filter_query.prepare(
                with_group_by=True,
                with_pagination=False,
                without_ignored_asset_filter=True,
            )
            prefix = 'SELECT COUNT(*), *'
        else:
            filters, query_bindings = filter_query.prepare(with_pagination=False)
            prefix = 'SELECT *'

        return f'{prefix} FROM (SELECT {suffix}) {filters}', limit + query_bindings

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[True],
    ) -> list[tuple[int, HistoryBaseEntry]]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[False] = ...,
    ) -> list[HistoryBaseEntry]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: EthDepositEventFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[True],
    ) -> list[tuple[int, EthDepositEvent]]:
        ...

    @overload
    def get_history_events(
            self,
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
            filter_query: EthWithdrawalFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[False] = ...,
    ) -> list[EthWithdrawalEvent]:
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

    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery | EvmEventFilterQuery | EthDepositEventFilterQuery | EthWithdrawalFilterQuery,  # noqa: E501
            has_premium: bool,
            group_by_event_ids: bool = False,
    ) -> (
        list[tuple[int, HistoryBaseEntry]] | list[HistoryBaseEntry] |
        list[tuple[int, EvmEvent]] | list[EvmEvent] |
        list[tuple[int, EthDepositEvent]] | list[EthDepositEvent] |
        list[tuple[int, EthWithdrawalEvent]] | list[EthWithdrawalEvent]
    ):
        """Get all events from the DB, deserialized depending on the event type

        TODO: To not query all columns with all joins for all cases, we perhaps can
        peek on the entry type of the filter and adjust the SELECT fields accordingly?
        """
        base_query, filters_bindings = self._create_history_events_query(
            has_premium=has_premium,
            filter_query=filter_query,
            group_by_event_ids=group_by_event_ids,
            entries_limit=FREE_HISTORY_EVENTS_LIMIT,
        )
        if filter_query.pagination is not None:
            base_query = f'SELECT * FROM ({base_query}) {filter_query.pagination.prepare()}'

        ethereum_tracked_accounts = self.db.get_blockchain_accounts(cursor).get(
            SupportedBlockchain.ETHEREUM,
        )
        cursor.execute(base_query, filters_bindings)
        output: list[HistoryBaseEntry] | list[tuple[int, HistoryBaseEntry]] = []
        type_idx = 1 if group_by_event_ids else 0
        data_start_idx = type_idx + 1
        failed_to_deserialize = False
        for entry in cursor:
            entry_type = HistoryBaseEntryType(entry[type_idx])
            try:
                deserialized_event: HistoryEvent | AssetMovement | SwapEvent | (EvmEvent | (EthWithdrawalEvent | EthBlockEvent))  # noqa: E501
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
                    location_label_tuple = entry[data_start_idx + 5:data_start_idx + 6]
                    data = (
                        entry[data_start_idx:data_start_idx + 4] +
                        location_label_tuple +
                        entry[data_start_idx + 7:data_start_idx + 8] +
                        entry[data_start_idx + 10:data_start_idx + 12] +
                        entry[data_start_idx + HISTORY_BASE_ENTRY_LENGTH + EVM_FIELD_LENGTH:data_start_idx + HISTORY_BASE_ENTRY_LENGTH + EVM_FIELD_LENGTH + ETH_STAKING_FIELD_LENGTH + 1]  # noqa: E501
                    )
                    if entry_type == HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT:
                        deserialized_event = EthWithdrawalEvent.deserialize_from_db(data)
                    else:
                        deserialized_event = EthBlockEvent.deserialize_from_db(data, fee_recipient_tracked=location_label_tuple[0] in ethereum_tracked_accounts)  # noqa: E501

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
                    data = entry[data_start_idx:]
                    deserialized_event = (
                        AssetMovement if entry_type == HistoryBaseEntryType.ASSET_MOVEMENT_EVENT else  # noqa: E501
                        SwapEvent if entry_type == HistoryBaseEntryType.SWAP_EVENT else
                        HistoryEvent
                    ).deserialize_from_db(data)
            except (DeserializationError, UnknownAsset) as e:
                log.error(f'Failed to deserialize history event {entry} due to {e!s}')
                failed_to_deserialize = True
                continue

            if group_by_event_ids is True:
                output.append((entry[0], deserialized_event))  # type: ignore
            else:
                output.append(deserialized_event)  # type: ignore

        if failed_to_deserialize:
            self.db.msg_aggregator.add_error(
                'Could not deserialize one or more history event(s). '
                'Try redecoding the event(s) or check the logs for more details.',
            )

        return output

    @overload
    def get_history_events_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryBaseEntryFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[True],
            entries_limit: int | None = None,
    ) -> tuple[list[tuple[int, HistoryBaseEntry]], int, int]:
        ...

    @overload
    def get_history_events_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryBaseEntryFilterQuery,
            has_premium: bool,
            group_by_event_ids: Literal[False] = ...,
            entries_limit: int | None = None,
    ) -> tuple[list[HistoryBaseEntry], int, int]:
        ...

    @overload
    def get_history_events_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryBaseEntryFilterQuery,
            has_premium: bool,
            group_by_event_ids: bool = False,
            entries_limit: int | None = None,
    ) -> tuple[list[tuple[int, HistoryBaseEntry]] | list[HistoryBaseEntry], int, int]:
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
            entries_limit: int | None = None,
    ) -> tuple[list[tuple[int, HistoryBaseEntry]] | list[HistoryBaseEntry], int, int]:
        """Gets all history events for all types, based on the filter query.

        Also returns how many are the total found for the filter and the total found applying
        the limit if provided. Otherwise count_with_limit and count_without_limit are equal.
        """
        events = self.get_history_events(  # type: ignore  # is due to HistoryBaseEntryFilterQuery not possible to be overloaded in get_history_events
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
            entries_limit: int | None = None,
    ) -> tuple[int, int]:
        """
        Returns how many events matching the filter but ignoring pagination are in the DB.
        We return two integers. The first one being the number of events returned and the second
        the number of events if any limit is applied, otherwise the second value matches
        the first.
        """
        free_limit = FREE_HISTORY_EVENTS_LIMIT if entries_limit is None else entries_limit
        premium_query, premium_bindings = self._create_history_events_query(
            has_premium=True,
            filter_query=query_filter,
            group_by_event_ids=group_by_event_ids,
            entries_limit=free_limit,
        )
        count_without_limit = cursor.execute(
            f'SELECT COUNT(*) FROM ({premium_query})',
            premium_bindings,
        ).fetchone()[0]

        if entries_limit is None:
            return count_without_limit, count_without_limit

        free_query, free_bindings = self._create_history_events_query(
            has_premium=False,
            filter_query=query_filter,
            group_by_event_ids=group_by_event_ids,
            entries_limit=free_limit,
        )
        count_with_limit = cursor.execute(
            f'SELECT COUNT(*) FROM ({free_query})',
            free_bindings,
        ).fetchone()[0]
        return count_without_limit, count_with_limit

    def get_amount_stats(
            self,
            cursor: 'DBCursor',
            query_filters: str,
            bindings: list[Any],
    ) -> list[tuple[str, FVal]]:
        """Returns the sum of the amounts received by asset"""
        query = (
            'SELECT asset, SUM(CAST(amount AS REAL))'
            f'FROM history_events {query_filters} GROUP BY asset;'
        )
        cursor.execute(query, bindings)
        assets_amounts = []
        for row in cursor:
            try:
                asset = row[0]  # existence is guaranteed due the foreign key relation
                amount = deserialize_fval(
                    value=row[1],
                    name='total amount in history events stats',
                    location='get_amount_stats',
                )
                assets_amounts.append((asset, amount))
            except DeserializationError as e:
                log.debug(f'Failed to deserialize amount {row[1]}. {e!s}')
        return assets_amounts

    def get_amount_and_value_stats(
            self,
            cursor: 'DBCursor',
            query_filters: str,
            bindings: list[Any],
            counterparty: str,
    ) -> tuple[list[tuple[str, FVal, FVal]], FVal]:
        """Returns the sum of the amounts received by asset and the sum of USD value
        at the time of the events and the total USD value of all the assets queried.
        """
        total_events = cursor.execute(
            f'SELECT COUNT(*) FROM history_events {query_filters}',
            bindings,
        ).fetchone()[0]

        assets_amounts: dict[str, FVal] = defaultdict(FVal)
        assets_value: dict[str, FVal] = defaultdict(FVal)
        total_usd_value: FVal = ZERO
        query_location: str = 'get_amount_stats'
        log.debug(f'Will process {counterparty} stats for {total_events} events')
        send_ws_every_events = self.db.msg_aggregator.how_many_events_per_ws(total_events)
        for idx, row in enumerate(cursor.execute(
            f'SELECT asset, amount, timestamp FROM history_events {query_filters};',
            bindings,
        )):
            if idx % send_ws_every_events == 0:
                self.db.msg_aggregator.add_message(
                    message_type=WSMessageType.PROGRESS_UPDATES,
                    data={
                        'total': total_events,
                        'processed': idx,
                        'subtype': str(ProgressUpdateSubType.STATS_PRICE_QUERY),
                        'counterparty': counterparty,
                    },
                )

            try:
                asset = row[0]  # existence is guaranteed due the foreign key relation
                amount = deserialize_fval(
                    value=row[1],
                    name='total amount in history events stats',
                    location=query_location,
                )
                usd_price = query_usd_price_or_use_default(
                    asset=Asset(asset),
                    time=ts_ms_to_sec(row[2]),
                    default_value=ZERO,
                    location=query_location,
                )
                assets_amounts[asset] += amount
                assets_value[asset] += (usd_value := amount * usd_price)
                total_usd_value += usd_value
            except DeserializationError as e:
                log.debug(f'Failed to deserialize amount {row[1]}. {e!s}')

        # send final message
        self.db.msg_aggregator.add_message(
            message_type=WSMessageType.PROGRESS_UPDATES,
            data={
                'total': total_events,
                'processed': total_events,
                'subtype': str(ProgressUpdateSubType.STATS_PRICE_QUERY),
                'counterparty': counterparty,
            },
        )
        final_amounts = []
        for asset, amount in assets_amounts.items():
            final_amounts.append((asset, amount, assets_value[asset]))

        return final_amounts, total_usd_value

    def get_hidden_event_ids(self, cursor: 'DBCursor') -> list[int]:
        """Returns all event identifiers that should be hidden in the UI

        These are, at the moment, special cases where due to grouping different event
        types with similar info they all appear together but the UI should just show one.
        """
        # Only 1 type of hidden event for now
        cursor.execute(
            'SELECT E.identifier FROM history_events E LEFT JOIN eth_staking_events_info S '
            'ON E.identifier=S.identifier WHERE E.sequence_index=1 AND S.identifier IS NOT NULL '
            'AND (SELECT COUNT(*) FROM history_events E2 WHERE '
            'E2.event_identifier=E.event_identifier) > 2',
        )
        return [x[0] for x in cursor]

    def edit_event_extra_data(
            self,
            write_cursor: 'DBCursor',
            event: HistoryBaseEntry,
            extra_data: Mapping[str, Any],
    ) -> None:
        """Edit an event's extra data in the DB and save it. Does not turn it into
        a customized event. This is meant to be used programmatically.

        The given event should be one pulled from the DB, which means the identifier
        field should be populated.
        """
        assert event.identifier is not None, 'event should have identifier populated'
        write_cursor.execute(
            'UPDATE history_events SET extra_data=? WHERE identifier=?',
            (json.dumps(extra_data), event.identifier),
        )
        event.extra_data = extra_data

    def query_wrap_stats(self, from_ts: Timestamp, to_ts: Timestamp) -> dict[str, Any]:
        """Query simple statistics about the user to show them as a wrap for the year
        This logic is temporary and will be removed.
        """
        from_ts_ms, to_ts_ms = ts_sec_to_ms(from_ts), ts_sec_to_ms(to_ts)
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT SUM(CAST(amount AS FLOAT)) FROM history_events JOIN evm_events_info '
                'ON history_events.identifier=evm_events_info.identifier WHERE '
                "asset='ETH' AND type='spend' and subtype='fee' AND counterparty='gas' AND "
                'timestamp >= ? AND timestamp <= ?',
                (from_ts_ms, to_ts_ms),
            )
            if (amount := cursor.fetchone()[0]) is not None:
                eth_on_gas = str(amount)
            else:
                eth_on_gas = '0'

            cursor.execute(
                'SELECT location_label, SUM(CAST(amount AS FLOAT)) FROM history_events JOIN evm_events_info '  # noqa: E501
                'ON history_events.identifier=evm_events_info.identifier WHERE '
                "asset='ETH' AND type='spend' and subtype='fee' AND counterparty='gas' AND "
                'timestamp >= ? AND timestamp <= ? GROUP BY location_label',
                (from_ts_ms, to_ts_ms),
            )
            eth_on_gas_per_address = {row[0]: str(row[1]) for row in cursor}
            cursor.execute(
                'SELECT chain_id, COUNT(DISTINCT event_identifier) as tx_count FROM evm_events_info '  # noqa: E501
                'JOIN history_events ON evm_events_info.identifier = history_events.identifier '
                'JOIN evm_transactions ON evm_transactions.tx_hash = evm_events_info.tx_hash '
                'WHERE history_events.timestamp >= ? AND history_events.timestamp <= ? AND history_events.asset NOT IN '  # noqa: E501
                "(SELECT value FROM multisettings WHERE name = 'ignored_asset') GROUP BY chain_id",
                (from_ts_ms, to_ts_ms),
            )
            transactions_per_chain = {ChainID.deserialize_from_db(row[0]).name: row[1] for row in cursor}  # noqa: E501
            cursor.execute(
                'SELECT location, COUNT(*) from trades '
                'WHERE timestamp >= ? AND timestamp <= ? GROUP BY location',
                (from_ts, to_ts),
            )
            trades_by_exchange = {str(Location.deserialize_from_db(row[0])): row[1] for row in cursor}  # noqa: E501
            cursor.execute(
                """
                SELECT transaction_symbol, transaction_amount FROM gnosispay_data
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY transaction_symbol
                ORDER BY MAX(
                    CASE
                        WHEN transaction_symbol = 'EUR' THEN CAST(transaction_amount AS FLOAT)
                        ELSE CAST(billing_amount AS FLOAT)
                    END
                ) DESC
                """,
                (from_ts, to_ts),
            )
            gnosis_max_payments_by_currency = [
                {'symbol': symbol, 'amount': str(amount)}
                for symbol, amount in cursor
            ]
            cursor.execute(
                "SELECT unixepoch(date(datetime(timestamp/1000, 'unixepoch'), 'localtime'), 'utc'), COUNT(DISTINCT event_identifier) as tx_count "  # noqa: E501
                'FROM evm_events_info JOIN history_events ON evm_events_info.identifier = history_events.identifier '  # noqa: E501
                'WHERE timestamp >= ? AND timestamp <= ? AND history_events.asset NOT IN '
                "(SELECT value FROM multisettings WHERE name = 'ignored_asset') "
                "GROUP BY date(datetime(timestamp/1000, 'unixepoch'), 'localtime') ORDER BY "
                'tx_count DESC LIMIT 10',
                (from_ts_ms, to_ts_ms),
            )
            top_days_by_number_of_transactions = [{
                'timestamp': row[0],
                'amount': str(row[1]),
            } for row in cursor]

            cursor.execute(
                'SELECT counterparty, COUNT(DISTINCT tx_hash) AS unique_transaction_count '
                'FROM evm_events_info JOIN history_events ON '
                'evm_events_info.identifier = history_events.identifier '
                "WHERE counterparty IS NOT NULL AND counterparty != 'gas' "
                'GROUP BY counterparty ORDER BY unique_transaction_count DESC',
            )
            transactions_per_protocol = [
                {'protocol': row[0], 'transactions': row[1]}
                for row in cursor
            ]

        return {
            'eth_on_gas': eth_on_gas,
            'eth_on_gas_per_address': eth_on_gas_per_address,
            'transactions_per_chain': transactions_per_chain,
            'trades_by_exchange': trades_by_exchange,
            'gnosis_max_payments_by_currency': gnosis_max_payments_by_currency,
            'top_days_by_number_of_transactions': top_days_by_number_of_transactions,
            'transactions_per_protocol': transactions_per_protocol,
        }
