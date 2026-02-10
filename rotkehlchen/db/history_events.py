import json
import logging
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Optional, TypeAlias, cast, overload

from solders.solders import Signature
from sqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.bitcoin.bch.constants import BCH_GROUP_IDENTIFIER_PREFIX
from rotkehlchen.chain.bitcoin.btc.constants import BTC_GROUP_IDENTIFIER_PREFIX
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.constants import (
    CHAIN_EVENT_FIELDS,
    CHAIN_EVENT_NULL_FIELDS,
    CHAIN_FIELD_LENGTH,
    ETH_STAKING_EVENT_FIELDS,
    ETH_STAKING_EVENT_NULL_FIELDS,
    ETH_STAKING_FIELD_LENGTH,
    GROUP_HAS_IGNORED_ASSETS_FIELD,
    HISTORY_BASE_ENTRY_FIELDS,
    HISTORY_BASE_ENTRY_LENGTH,
    HISTORY_MAPPING_KEY_STATE,
    TX_DECODED,
    HistoryEventLinkType,
    HistoryMappingState,
)
from rotkehlchen.db.filtering import (
    ALL_EVENTS_DATA_JOIN,
    EVENTS_WITH_COUNTERPARTY_JOIN,
    DBMultiIntegerFilter,
    EthDepositEventFilterQuery,
    EthWithdrawalFilterQuery,
    EvmEventFilterQuery,
    HistoryBaseEntryFilterQuery,
    HistoryEventFilterQuery,
    HistoryEventWithCounterpartyFilterQuery,
    HistoryEventWithTxRefFilterQuery,
    SolanaEventFilterQuery,
)
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.constants import ALL_SUPPORTED_EXCHANGES
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.constants import CHAIN_ENTRY_TYPES, STAKING_ENTRY_TYPES
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
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.solana_swap import SolanaSwapEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.history.price import query_price_or_use_default
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import (
    BLOCKCHAIN_LOCATIONS_TYPE,
    CHAINS_WITH_TRANSACTIONS,
    BTCTxId,
    ChainID,
    ChecksumEvmAddress,
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

HistoryEventsReturnType: TypeAlias = list[HistoryBaseEntry] | list[tuple[int, HistoryBaseEntry]]


@dataclass(frozen=True)
class HistoryEventsResult:
    events: HistoryEventsReturnType
    ignored_group_identifiers: set[str]


@dataclass(frozen=True)
class HistoryEventsWithCountResult(HistoryEventsResult):
    entries_found: int
    entries_with_limit: int


class DBHistoryEvents:

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def _mark_events_modified(
            self,
            write_cursor: 'DBCursor',
            timestamp: TimestampMS,
    ) -> None:
        """Track earliest modified event timestamp and when modification occurred."""
        # Historical balances processing is temporarily disabled.

    def _execute_and_track_modified(
            self,
            write_cursor: 'DBCursor',
            result: 'DBCursor | Sequence[tuple[TimestampMS]]',
    ) -> int:
        """Iterate cursor results, track earliest timestamp, and return count.
        Single-pass iteration to compute both count and minimum timestamp.
        """
        count, min_ts = 0, None
        for (ts,) in result:
            count += 1
            if min_ts is None or ts < min_ts:
                min_ts = ts

        # TODO (balances): add _mark_events_modified for min_ts if count > 0
        return count

    def delete_events_and_track(
            self,
            write_cursor: 'DBCursor',
            where_clause: str,
            where_bindings: tuple,
    ) -> int:
        """Delete history_events and track the earliest affected timestamp for cache invalidation.
        Also cleans up any cached original positions for the deleted events.

        Returns the number of rows deleted.
        """
        deleted_ids, timestamps = [], []
        if len(rows := write_cursor.execute(
            f'DELETE FROM history_events {where_clause} RETURNING timestamp, identifier',
            where_bindings,
        ).fetchall()) > 0:
            for row in rows:
                timestamps.append((row[0],))
                deleted_ids.append(str(row[1]))
            write_cursor.execute(
                "DELETE FROM key_value_cache WHERE name LIKE 'customized_event_original_%' "
                f"AND value IN ({','.join('?' * len(deleted_ids))})",
                deleted_ids,
            )
        return self._execute_and_track_modified(
            write_cursor=write_cursor,
            result=timestamps,
        )

    def update_events_and_track(
            self,
            write_cursor: 'DBCursor',
            where_clause: str,
            where_bindings: tuple,
            set_clause: str,
            set_bindings: tuple = (),
    ) -> int:
        """Update history_events and track the earliest affected timestamp for cache invalidation.

        This method exists because edit_history_event requires a HistoryEvent object,
        making it unsuitable for bulk updates.

        Returns the number of rows updated.
        """
        return self._execute_and_track_modified(
            write_cursor=write_cursor,
            result=write_cursor.execute(
                f'UPDATE history_events {set_clause} {where_clause} RETURNING timestamp',
                set_bindings + where_bindings,
            ),
        )

    def add_history_event(
            self,
            write_cursor: 'DBCursor',
            event: HistoryBaseEntry,
            mapping_values: dict[str, HistoryMappingState] | None = None,
            skip_tracking: bool = False,
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

        write_cursor.execute(
            'UPDATE history_events SET ignored=(CASE WHEN EXISTS '
            "(SELECT 1 FROM multisettings WHERE name = 'ignored_asset' AND value = ?) "
            'THEN 1 ELSE 0 END) WHERE identifier=?',
            (event.asset.identifier, identifier),
        )

        if mapping_values is not None:
            write_cursor.executemany(
                'INSERT OR IGNORE INTO history_events_mappings(parent_identifier, name, value) '
                'VALUES(?, ?, ?)',
                [(identifier, k, v.serialize_for_db()) for k, v in mapping_values.items()],
            )

        # TODO (balances): add _mark_events_modified for event.timestamp if not skip_tracking
        return identifier

    def add_history_events(
            self,
            write_cursor: 'DBCursor',
            history: Sequence[HistoryBaseEntry],
    ) -> None:
        """Insert a list of history events in the database with batched modification tracking.

        This method batches modification tracking for efficiency:
        - Instead of calling _mark_events_modified() for each event,
          it collects the minimum timestamp and calls it once at the end.
        - Example: For 100 events, this reduces cache updates from 200 to 2.

        Check add_history_event() to see possible Exceptions
        """
        if not history:
            return

        min_timestamp: TimestampMS | None = None

        # Add all events WITHOUT calling _mark_events_modified for each
        for event in history:
            if (
                self.add_history_event(
                    write_cursor=write_cursor,
                    event=event,
                    skip_tracking=True,  # Skip tracking per-event
                ) is not None  # Only track if event was actually added (not a duplicate)
                and (min_timestamp is None or event.timestamp < min_timestamp)
            ):
                # Track the minimum timestamp
                min_timestamp = event.timestamp

        # Call tracking ONCE for the entire batch with minimum timestamp
        # TODO (balances): add _mark_events_modified for min_timestamp if min_timestamp is not None

    @staticmethod
    def save_history_event_backup(
            write_cursor: 'DBCursor',
            identifier: int | None,
    ) -> None:
        """Create a backup copy of an event before modifying it so it can be restored to its
        original state later. Use insert or ignore so we keep the earliest original version if
        multiple edits happen.
        """
        if write_cursor.execute(
            'INSERT OR IGNORE INTO history_events_backup '
            'SELECT * FROM history_events WHERE identifier=?',
            (identifier,),
        ).rowcount == 0:
            return  # A backup already exists for this event

        write_cursor.execute(
            'INSERT INTO chain_events_info_backup '
            'SELECT * FROM chain_events_info WHERE identifier=?',
            (identifier,),
        )

    @staticmethod
    def maybe_restore_history_events_from_backup(
            write_cursor: 'DBCursor',
            identifiers: list[int],
    ) -> None:
        """Restore multiple history events to their original backed-up state in bulk.
        Events without a backup are silently skipped.
        """
        for chunk, placeholders in get_query_chunks(identifiers):
            for table in ('history_events', 'chain_events_info'):
                write_cursor.execute(
                    f'INSERT OR REPLACE INTO {table} '
                    f'SELECT * FROM {table}_backup WHERE identifier IN ({placeholders})',
                    chunk,
                )
            # Delete backup entries (also deletes backup chain info via foreign key)
            write_cursor.execute(
                f'DELETE FROM history_events_backup WHERE identifier IN ({placeholders})',
                chunk,
            )

    def restore_matched_events_before_purge(
            self,
            write_cursor: 'DBCursor',
            location: Location,
    ) -> None:
        """Undo asset movement matching for events linked to the purged location.

        Matched events on the other side still carry modified fields from the matching process.
        This restores them from backup and removes any auto-created adjustment events.
        """
        link_type_db = HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db()
        location_db = location.serialize_for_db()
        events_to_restore: set[int] = set()

        # grab all matched pairs that touch this location, along with each side's location
        # so we can figure out which side survives the purge and needs restoration
        for left_id, right_id, left_loc, right_loc in write_cursor.execute(
            'SELECT L.left_event_id, L.right_event_id, '
            'HL.location, HR.location '
            'FROM history_event_links L '
            'INNER JOIN history_events HL ON HL.identifier = L.left_event_id '
            'INNER JOIN history_events HR ON HR.identifier = L.right_event_id '
            'WHERE L.link_type = ? AND (HL.location = ? OR HR.location = ?)',
            (link_type_db, location_db, location_db),
        ):
            if left_loc == location_db and right_loc != location_db:
                events_to_restore.add(right_id)
            elif right_loc == location_db and left_loc != location_db:
                events_to_restore.add(left_id)
            # both sides belong to the purged location, nothing to restore

        if len(events_to_restore) == 0:
            return

        # clean up any adjustment events that were auto-created during matching
        # on the surviving side (adjustments in the purged location get deleted with the purge)
        for chunk, placeholders in get_query_chunks(list(events_to_restore)):
            self.delete_events_and_track(
                write_cursor=write_cursor,
                where_clause=(
                    f'WHERE type = ? AND group_identifier IN '
                    f'(SELECT group_identifier FROM history_events '
                    f'WHERE identifier IN ({placeholders})) '
                    f'AND identifier IN (SELECT parent_identifier FROM history_events_mappings '
                    f'WHERE name = ? AND value = ?)'
                ),
                where_bindings=(
                    HistoryEventType.EXCHANGE_ADJUSTMENT.serialize(),
                    *chunk,
                    HISTORY_MAPPING_KEY_STATE,
                    HistoryMappingState.AUTO_MATCHED.serialize_for_db(),
                ),
            )

        # put each surviving event back to its pre-match state
        self.maybe_restore_history_events_from_backup(
            write_cursor=write_cursor,
            identifiers=list(events_to_restore),
        )

        # and drop their AUTO_MATCHED mappings in one go
        for chunk, placeholders in get_query_chunks(list(events_to_restore)):
            write_cursor.execute(
                f'DELETE FROM history_events_mappings '
                f'WHERE parent_identifier IN ({placeholders}) '
                f'AND name = ? AND value = ?',
                (*chunk, HISTORY_MAPPING_KEY_STATE, HistoryMappingState.AUTO_MATCHED.serialize_for_db()),  # noqa: E501
            )

    def edit_history_event(
            self,
            write_cursor: 'DBCursor',
            event: HistoryBaseEntry,
            mapping_state: HistoryMappingState = HistoryMappingState.CUSTOMIZED,
            save_backup: bool = False,
    ) -> None:
        """
        Edit a history entry to the DB with information provided by the user.
        NOTE: It edits all the fields except the extra_data one.
        Marks the event with the specified mapping state.
        Only tracks modification for balance cache invalidation if balance-affecting
        fields change (timestamp, asset, amount, type, subtype, location_label).

        May raise:
            - InputError if an error occurred.
        """
        old_data = write_cursor.execute(
            'SELECT timestamp, asset, amount, type, subtype, location_label, sequence_index '
            'FROM history_events WHERE identifier=?',
            (event.identifier,),
        ).fetchone()

        if save_backup:
            self.save_history_event_backup(write_cursor=write_cursor, identifier=event.identifier)

        for idx, (_, updatestr, bindings) in enumerate(event.serialize_for_db()):
            if idx == 0:  # base history event data
                try:
                    write_cursor.execute(
                        f'{updatestr}, ignored=(CASE WHEN EXISTS '
                        "(SELECT 1 FROM multisettings WHERE name = 'ignored_asset' AND value = ?) "
                        'THEN 1 ELSE 0 END) WHERE identifier=?',
                        (*bindings, event.asset.identifier, event.identifier))
                except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                    raise InputError(
                        f'Tried to edit event to have group_identifier {event.group_identifier} '
                        f'and sequence_index {event.sequence_index} but it already exists',
                    ) from e
                if write_cursor.rowcount != 1:
                    raise InputError(f'Tried to edit event with id {event.identifier} but could not find it in the DB')  # noqa: E501

            else:  # all other data
                write_cursor.execute(f'{updatestr} WHERE identifier=?', (*bindings, event.identifier))  # noqa: E501

        # Mark as customized and store original position for duplicate prevention during redecode.
        # Only store original position on first customization (when INSERT succeeds).
        if self.set_event_mapping_state(
            write_cursor=write_cursor,
            event=event,
            mapping_state=mapping_state,
        ) and mapping_state == HistoryMappingState.CUSTOMIZED and isinstance(event, OnchainEvent):
            write_cursor.execute(
                'INSERT INTO key_value_cache (name, value) VALUES (?, ?)',
                (DBCacheDynamic.CUSTOMIZED_EVENT_ORIGINAL_SEQ_IDX.get_db_key(
                    group_identifier=event.group_identifier,
                    sequence_index=old_data[6],
                ), str(event.identifier)),
            )

        # Track modification only if balance-affecting fields changed. cannot be None here
        if old_data[:6] == (
            event.timestamp,
            event.asset.identifier,
            str(event.amount),
            event.event_type.serialize(),
            event.event_subtype.serialize(),
            event.location_label,
        ):
            return

        # TODO (balances): add _mark_events_modified for min(old_data[0], event.timestamp)

    @staticmethod
    def set_event_mapping_state(
            write_cursor: 'DBCursor',
            event: HistoryBaseEntry,
            mapping_state: HistoryMappingState,
    ) -> bool:
        """Mark an event with the specified mapping state

        Returns True if newly marked with this state, False if it was already marked.
        """
        write_cursor.execute(
            'INSERT OR IGNORE INTO history_events_mappings(parent_identifier, name, value) '
            'VALUES(?, ?, ?)',
            (event.identifier, HISTORY_MAPPING_KEY_STATE, mapping_state.serialize_for_db()),
        )
        return write_cursor.rowcount == 1

    def get_history_events_identifiers(
            self,
            filter_query: 'HistoryBaseEntryFilterQuery',
    ) -> list[int]:
        """Get the identifiers of history events matching the given filter.

        This is useful for bulk operations where we need to know which events
        match a filter before performing an action on them.
        """
        filters, query_bindings = filter_query.prepare(
            with_pagination=False,
            with_order=False,
        )
        query = f'SELECT history_events.identifier AS history_events_identifier {ALL_EVENTS_DATA_JOIN}' + filters  # noqa: E501
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(query, query_bindings)
            return [row[0] for row in cursor]

    def delete_history_events_by_filter(
            self,
            filter_query: 'HistoryBaseEntryFilterQuery',
            force_delete: bool = False,
            requested_identifiers: list[int] | None = None,
    ) -> tuple[int, str | None]:
        """Delete history events matching the given filter query.

        Returns (count_deleted, error_msg). error_msg is None on success.
        """
        if len(ids_to_delete := self.get_history_events_identifiers(filter_query=filter_query)) == 0:  # noqa: E501
            return 0, None

        if requested_identifiers is not None and len(missing_ids := set(requested_identifiers) - set(ids_to_delete)) != 0:  # noqa: E501
            return 0, f'Tried to remove history event(s) with id(s) {missing_ids} which do not exist'  # noqa: E501

        if (error_msg := self.delete_history_events_by_identifier(
            identifiers=ids_to_delete,
            force_delete=force_delete,
        )) is not None:
            return 0, error_msg

        return len(ids_to_delete), None

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
        is returned. Otherwise, None is returned.
        """
        for identifier in identifiers:
            if force_delete is False:
                with self.db.conn.read_ctx() as cursor:
                    cursor.execute(
                        'SELECT COUNT(*) == 1 FROM history_events WHERE group_identifier=(SELECT '
                        'group_identifier FROM history_events WHERE identifier=? AND entry_type=?)',  # noqa: E501
                        (identifier, HistoryBaseEntryType.EVM_EVENT.serialize_for_db()),
                    )
                    if bool(cursor.fetchone()[0]) is True:
                        return (
                            f'Tried to remove history event with id {identifier} '
                            f'which was the last event of a transaction'
                        )

            with self.db.user_write() as write_cursor:
                if self.delete_events_and_track(
                    write_cursor=write_cursor,
                    where_clause='WHERE identifier=?',
                    where_bindings=(identifier,),
                ) != 1:
                    return f'Tried to remove history event with id {identifier} which does not exist'  # noqa: E501

        return None

    def reset_eth_staking_data(
            self,
            entry_type: Literal[HistoryBaseEntryType.ETH_BLOCK_EVENT, HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT],  # noqa: E501
    ) -> None:
        """Reset Ethereum staking events and related cache data.
        Removes all stored events of the specified type and clears associated
        cache entries to enable fresh data retrieval.
        """
        with self.db.conn.write_ctx() as write_cursor:
            self.delete_events_and_track(
                write_cursor=write_cursor,
                where_clause='WHERE entry_type=?',
                where_bindings=(entry_type.serialize_for_db(),),
            )
            if entry_type == HistoryBaseEntryType.ETH_BLOCK_EVENT:
                key_parts = [DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS.value[0][:30]]
            else:
                key_parts = [
                    DBCacheDynamic.WITHDRAWALS_TS.value[0].split('_')[0],
                    DBCacheDynamic.WITHDRAWALS_IDX.value[0].split('_')[0],
                ]

            self.db.delete_dynamic_caches(write_cursor=write_cursor, key_parts=key_parts)

    def delete_location_events(
            self,
            write_cursor: 'DBCursor',
            location: BLOCKCHAIN_LOCATIONS_TYPE,
            address: str | None,
    ) -> None:
        """Delete all uncustomized history events for the given location and optionally address.
        For EVM and Solana, only deletes events that also have a corresponding tx in the DB.
        Also avoids deleting any events that are matched with asset movements.
        """
        events_to_keep_num = write_cursor.execute(
            'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value IN (?, ?)',
            (customized_bindings := (
                HISTORY_MAPPING_KEY_STATE,
                HistoryMappingState.CUSTOMIZED.serialize_for_db(),
                HistoryMappingState.AUTO_MATCHED.serialize_for_db(),
            )),
        ).fetchone()[0]
        if location.is_bitcoin():
            join_or_where = 'WHERE'
        else:
            sub_query = (
                'SELECT signature FROM solana_transactions'
                if location == Location.SOLANA else
                'SELECT tx_hash FROM evm_transactions'
            )
            join_or_where = (
                'INNER JOIN chain_events_info C ON H.identifier=C.identifier '
                f'AND C.tx_ref IN ({sub_query}) AND'
            )

        base_query = f'SELECT H.identifier from history_events H {join_or_where} H.location = ?'
        bindings: tuple = (location.serialize_for_db(),)
        filter_conditions = ''
        if events_to_keep_num != 0:
            filter_conditions += ' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value IN (?, ?))'  # noqa: E501
            bindings += customized_bindings
        if address is not None:
            filter_conditions += ' AND location_label = ?'
            bindings += (address,)

        self.delete_events_and_track(
            write_cursor=write_cursor,
            where_clause=f'WHERE identifier IN ({base_query}){filter_conditions}',
            where_bindings=bindings,
        )

    def reset_events_for_redecode(
            self,
            write_cursor: 'DBCursor',
            location: BLOCKCHAIN_LOCATIONS_TYPE,
    ) -> None:
        """Reset the given location's events, etc. for re-decoding.
        Handles different cases depending on the location:
        * Bitcoin - simply deletes all non-customized bitcoin events.
        * EVM and EVM-like - deletes non-customized events that also have a corresponding
          transaction in the evm_transactions table.
        * EVM - removes the TX_DECODED evm_tx_mappings to enable re-processing.
        """
        self.delete_location_events(
            write_cursor=write_cursor,
            location=location,
            address=None,
        )

        # zksynclite's decode status is stored in zksynclite_transactions.is_decoded
        # and btc/bch don't have the individual txs or decoded status in the db
        if location.is_evm():  # so only delete mappings here for evm and solana locations
            write_cursor.execute(
                'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions) AND value=?',  # noqa: E501
                (TX_DECODED,),
            )
        elif location == Location.SOLANA:
            write_cursor.execute(
                'DELETE from solana_tx_mappings WHERE tx_id IN (SELECT identifier FROM solana_transactions) AND value=?',  # noqa: E501
                (TX_DECODED,),
            )

    def delete_events_by_tx_ref(
            self,
            write_cursor: 'DBCursor',
            tx_refs: Sequence[EVMTxHash | BTCTxId | Signature],
            location: BLOCKCHAIN_LOCATIONS_TYPE,
            delete_customized: bool = False,
    ) -> None:
        """Delete all relevant (by transaction hash) history events except those that
        are customized. If delete_customized is True then delete those too.
        Only use with limited number of transactions!!!

        If you want to reset all decoded events better use the _reset_decoded_events
        code in v37 -> v38 upgrade as that is not limited to the number of transactions
        and won't potentially raise a too many sql variables error
        """
        placeholders = ', '.join(['?'] * len(tx_refs))
        bindings: list[str | bytes]
        if location.is_bitcoin():
            where_str = f'WHERE group_identifier IN ({placeholders})'
            id_prefix = BTC_GROUP_IDENTIFIER_PREFIX if location == Location.BITCOIN else BCH_GROUP_IDENTIFIER_PREFIX  # noqa: E501
            bindings = [f'{id_prefix}{tx_hash}' for tx_hash in tx_refs]
        else:
            where_str = (
                f'WHERE identifier IN (SELECT identifier FROM chain_events_info '
                f'WHERE tx_ref IN ({placeholders}))'
            )
            if location == Location.SOLANA:
                bindings = [x.to_bytes() for x in tx_refs]  # type: ignore[union-attr]  # hashes will be solana signatures
            else:
                bindings = list(tx_refs)  # type: ignore  # different type of elements in the list

        if (
            delete_customized is False and
            (length := len(customized_event_ids := self.get_event_mapping_states(
                cursor=write_cursor,
                location=location,
                mapping_state=HistoryMappingState.CUSTOMIZED,
            ))) != 0
        ):
            where_str += f' AND identifier NOT IN ({", ".join(["?"] * length)})'
            bindings.extend(customized_event_ids)  # type: ignore  # different type of elements in the list

        self.delete_events_and_track(
            write_cursor=write_cursor,
            where_clause=where_str,
            where_bindings=tuple(bindings),
        )

    @staticmethod
    @overload
    def get_event_mapping_states(
            cursor: 'DBCursor',
            location: Location | None,
            mapping_state: HistoryMappingState,
    ) -> list[int]:
        ...

    @staticmethod
    @overload
    def get_event_mapping_states(
            cursor: 'DBCursor',
            location: Location | None,
            mapping_state: None = None,
    ) -> dict[int, list[HistoryMappingState]]:
        ...

    @staticmethod
    def get_event_mapping_states(
            cursor: 'DBCursor',
            location: Location | None,
            mapping_state: HistoryMappingState | None = None,
    ) -> dict[int, list[HistoryMappingState]] | list[int]:
        """Get the mapping states of each event in the database that has a mapping state,
        optionally filtered by Location or
        """
        where_str = 'A.name = ? '
        bindings: list[Any] = [HISTORY_MAPPING_KEY_STATE]
        if mapping_state is not None:
            where_str += 'AND A.value = ? '
            bindings.append(mapping_state.serialize_for_db())

        if location is None:
            cursor.execute(
                f'SELECT parent_identifier, value FROM history_events_mappings A WHERE {where_str}',  # noqa: E501
                bindings,
            )
        else:
            cursor.execute(
                'SELECT A.parent_identifier, A.value FROM history_events_mappings A JOIN '
                f'history_events_mappings B ON A.parent_identifier=B.parent_identifier AND {where_str}'  # noqa: E501
                'JOIN history_events C ON C.identifier=A.parent_identifier AND C.location=?',
                (*bindings, location.serialize_for_db()),
            )

        if mapping_state is not None:
            return [x[0] for x in cursor]

        mapping_states = defaultdict(list)
        for (identifier, state_value) in cursor:
            mapping_states[identifier].append(HistoryMappingState(state_value))

        return mapping_states

    def get_evm_event_by_identifier(self, identifier: int) -> Optional['EvmEvent']:
        """Returns the EVM event with the given identifier"""
        with self.db.conn.read_ctx() as cursor:
            event_data = cursor.execute(
                f'SELECT {HISTORY_BASE_ENTRY_FIELDS}, {CHAIN_EVENT_FIELDS} {EVENTS_WITH_COUNTERPARTY_JOIN} WHERE history_events.identifier=? AND entry_type=?',  # noqa: E501
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

    @staticmethod
    def _create_history_events_query(
            filter_query: HistoryBaseEntryFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: bool = False,
            match_exact_events: bool = True,
            include_order: bool = True,
    ) -> tuple[str, list]:
        """Returns the sql queries and bindings for the history events without pagination."""
        chain_fields, staking_fields, join_clause = DBHistoryEvents._build_events_query_parts(
            filter_query=filter_query,
        )
        # group_has_ignored_assets is added at the END so existing slicing logic is not affected.
        # It's computed via a window function to detect groups with ignored assets even when
        # those rows are filtered out by exclude_ignored_assets.
        base_suffix = f'{HISTORY_BASE_ENTRY_FIELDS}, {chain_fields}, {staking_fields}, {GROUP_HAS_IGNORED_ASSETS_FIELD} {join_clause}'  # noqa: E501
        if aggregate_by_group_ids:
            filters, query_bindings = filter_query.prepare(
                with_group_by=True,
                with_pagination=False,
                with_order=match_exact_events is True and include_order is True,  # skip order when we want the whole group of events since we order in an outer part of the query later  # noqa: E501
                without_ignored_asset_filter=True,
            )
            prefix = 'SELECT COUNT(*), *'
        else:
            filters, query_bindings = filter_query.prepare(
                with_order=match_exact_events is True and include_order is True,  # same as above
                with_pagination=False,
            )
            prefix = 'SELECT *'

        if entries_limit is None:
            suffix, limit = base_suffix, []
        else:
            suffix, limit = (
                f'* FROM (SELECT {base_suffix}) WHERE group_identifier IN ('
                'SELECT DISTINCT group_identifier FROM history_events '
                'ORDER BY timestamp DESC, sequence_index ASC LIMIT ?)'  # only select the last LIMIT groups  # noqa: E501
            ), [entries_limit]

        if match_exact_events is False:  # return all group events instead of just the filtered ones.  # noqa: E501
            if include_order is True and filter_query.order_by is not None:
                order_by = filter_query.order_by.prepare()
            else:
                order_by = ''

            return (
                (
                    f'{prefix} FROM (SELECT {base_suffix} WHERE group_identifier IN '
                    f'(SELECT group_identifier FROM (SELECT {suffix}) {filters}) {order_by})'
                ),
                limit + query_bindings,
            )

        return f'{prefix} FROM (SELECT {suffix}) {filters}', limit + query_bindings

    @staticmethod
    def _build_events_query_parts(
            filter_query: HistoryBaseEntryFilterQuery,
    ) -> tuple[str, str, str]:
        entry_type_filter_values: Sequence[int] | None = None
        for filter_ in filter_query.filters:
            if (
                isinstance(filter_, DBMultiIntegerFilter) and
                filter_.column == 'entry_type' and
                filter_.operator == 'IN'
            ):
                entry_type_filter_values = filter_.values
                break

        include_chain = include_staking = False
        if entry_type_filter_values is None:
            include_chain = include_staking = True
        else:
            entry_types = {HistoryBaseEntryType(value) for value in entry_type_filter_values}
            include_chain = len(entry_types & CHAIN_ENTRY_TYPES) > 0
            include_staking = len(entry_types & STAKING_ENTRY_TYPES) > 0

        if include_chain:
            chain_fields = CHAIN_EVENT_FIELDS
            chain_join = (
                'LEFT JOIN chain_events_info ON '
                'history_events.identifier=chain_events_info.identifier '
            )
        else:
            chain_fields = CHAIN_EVENT_NULL_FIELDS
            chain_join = ''

        if include_staking:
            staking_fields = ETH_STAKING_EVENT_FIELDS
            staking_join = (
                'LEFT JOIN eth_staking_events_info ON '
                'history_events.identifier=eth_staking_events_info.identifier '
            )
        else:
            staking_fields = ETH_STAKING_EVENT_NULL_FIELDS
            staking_join = ''

        return (
            chain_fields,
            staking_fields,
            f'FROM history_events {chain_join}{staking_join}',
        )

    @staticmethod
    def _create_history_events_count_query(
            filter_query: HistoryBaseEntryFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: bool = False,
    ) -> tuple[str, list]:
        """Returns a lightweight sql query for counting history events."""
        base_suffix = f'{filter_query.get_columns()} {filter_query.get_join_query()}'
        if aggregate_by_group_ids:
            filters, query_bindings = filter_query.prepare(
                with_group_by=True,
                with_pagination=False,
                with_order=False,
                without_ignored_asset_filter=True,
            )
        else:
            filters, query_bindings = filter_query.prepare(
                with_order=False,
                with_pagination=False,
            )

        if entries_limit is None:
            suffix, limit = base_suffix, []
        else:
            suffix, limit = (
                f'* FROM (SELECT {base_suffix}) WHERE group_identifier IN ('
                'SELECT DISTINCT group_identifier FROM history_events '
                'ORDER BY timestamp DESC, sequence_index ASC LIMIT ?)'
            ), [entries_limit]

        return f'SELECT * FROM (SELECT {suffix}) {filters}', limit + query_bindings

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[True],
            match_exact_events: bool = ...,
    ) -> list[tuple[int, HistoryBaseEntry]]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[HistoryBaseEntry]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: EthDepositEventFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[True],
            match_exact_events: bool,
    ) -> list[tuple[int, EthDepositEvent]]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: EthDepositEventFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[EthDepositEvent]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: EthWithdrawalFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[EthWithdrawalEvent]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: EvmEventFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[True],
            match_exact_events: bool,
    ) -> list[tuple[int, EvmEvent]]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: EvmEventFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[EvmEvent]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: SolanaEventFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[True],
            match_exact_events: bool,
    ) -> list[tuple[int, SolanaEvent]]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: SolanaEventFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[SolanaEvent]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventWithCounterpartyFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[True],
            match_exact_events: bool,
    ) -> list[tuple[int, SolanaEvent | EvmEvent]]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventWithCounterpartyFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[SolanaEvent | EvmEvent]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventWithTxRefFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[True],
            match_exact_events: bool,
    ) -> list[tuple[int, SolanaEvent | EvmEvent | HistoryEvent]]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventWithTxRefFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[SolanaEvent | EvmEvent | HistoryEvent]:
        ...

    @overload
    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery | HistoryEventWithCounterpartyFilterQuery | HistoryEventWithTxRefFilterQuery | SolanaEventFilterQuery | EvmEventFilterQuery | EthDepositEventFilterQuery | EthWithdrawalFilterQuery,  # noqa: E501
            entries_limit: int | None,
            aggregate_by_group_ids: bool = ...,
            match_exact_events: bool = ...,
    ) -> (
        list[tuple[int, HistoryBaseEntry]] | list[HistoryBaseEntry] |
        list[tuple[int, SolanaEvent | EvmEvent]] | list[SolanaEvent | EvmEvent] |
        list[tuple[int, SolanaEvent | EvmEvent | HistoryEvent]] | list[SolanaEvent | EvmEvent | HistoryEvent] |  # noqa: E501
        list[tuple[int, SolanaEvent]] | list[SolanaEvent] |
        list[tuple[int, EvmEvent]] | list[EvmEvent] |
        list[tuple[int, EthDepositEvent]] | list[EthDepositEvent] |
        list[tuple[int, EthWithdrawalEvent]] | list[EthWithdrawalEvent]
    ):
        """
        This fallback is needed for runtime boolean values that can't be resolved
        to literal types at type checking time.
        """

    def get_history_events(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery | HistoryEventWithCounterpartyFilterQuery | HistoryEventWithTxRefFilterQuery | SolanaEventFilterQuery | EvmEventFilterQuery | EthDepositEventFilterQuery | EthWithdrawalFilterQuery,  # noqa: E501
            entries_limit: int | None,
            aggregate_by_group_ids: bool = False,
            match_exact_events: bool = True,
    ) -> (
        list[tuple[int, HistoryBaseEntry]] | list[HistoryBaseEntry] |
        list[tuple[int, SolanaEvent | EvmEvent]] | list[SolanaEvent | EvmEvent] |
        list[tuple[int, SolanaEvent | EvmEvent | HistoryEvent]] | list[SolanaEvent | EvmEvent | HistoryEvent] |  # noqa: E501
        list[tuple[int, SolanaEvent]] | list[SolanaEvent] |
        list[tuple[int, EvmEvent]] | list[EvmEvent] |
        list[tuple[int, EthDepositEvent]] | list[EthDepositEvent] |
        list[tuple[int, EthWithdrawalEvent]] | list[EthWithdrawalEvent]
    ):
        """Get all events from the DB, deserialized depending on the event type."""
        result = self._get_history_events_with_ignored_groups(
            cursor=cursor,
            filter_query=filter_query,
            entries_limit=entries_limit,
            aggregate_by_group_ids=aggregate_by_group_ids,
            match_exact_events=match_exact_events,
        )
        return result.events

    def _get_history_events_with_ignored_groups(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryBaseEntryFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: bool = False,
            match_exact_events: bool = True,
    ) -> HistoryEventsResult:
        base_query, filters_bindings = self._create_history_events_query(
            filter_query=filter_query,
            aggregate_by_group_ids=aggregate_by_group_ids,
            match_exact_events=match_exact_events,
            entries_limit=entries_limit,
            include_order=True,
        )
        if filter_query.pagination is not None:
            base_query = f'SELECT * FROM ({base_query}) {filter_query.pagination.prepare()}'

        ethereum_tracked_accounts: set[ChecksumEvmAddress] | None = None
        cursor.execute(base_query, filters_bindings)
        output_grouped: list[tuple[int, HistoryBaseEntry]] = []
        output_flat: list[HistoryBaseEntry] = []
        ignored_group_identifiers: set[str] = set()
        type_idx = 1 if aggregate_by_group_ids else 0
        data_start_idx = type_idx + 1
        failed_to_deserialize = False
        # Fixed position of group_has_ignored_assets (after entry_type, base, chain, staking).
        # JOINs like state_markers may add columns at the end, so we use fixed index.
        group_has_ignored_assets_idx = (
            type_idx + 1 + HISTORY_BASE_ENTRY_LENGTH +
            CHAIN_FIELD_LENGTH + ETH_STAKING_FIELD_LENGTH
        )

        for entry in cursor:
            # group_has_ignored_assets is computed via MAX(ignored) OVER window function,
            # so it detects groups with ignored assets even when those rows are filtered out.
            group_has_ignored_assets = entry[group_has_ignored_assets_idx] == 1
            entry_type = HistoryBaseEntryType(entry[type_idx])
            try:
                deserialized_event: HistoryBaseEntry
                # Deserialize event depending on its type
                if entry_type == HistoryBaseEntryType.EVM_EVENT:
                    data = (
                        entry[data_start_idx:data_start_idx + HISTORY_BASE_ENTRY_LENGTH + 1] +
                        entry[data_start_idx + HISTORY_BASE_ENTRY_LENGTH + 1:data_start_idx + HISTORY_BASE_ENTRY_LENGTH + CHAIN_FIELD_LENGTH + 1]    # noqa: E501
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
                        entry[data_start_idx + HISTORY_BASE_ENTRY_LENGTH + CHAIN_FIELD_LENGTH:data_start_idx + HISTORY_BASE_ENTRY_LENGTH + CHAIN_FIELD_LENGTH + ETH_STAKING_FIELD_LENGTH + 1]  # noqa: E501
                    )
                    if entry_type == HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT:
                        deserialized_event = EthWithdrawalEvent.deserialize_from_db(data)
                    else:
                        if ethereum_tracked_accounts is None:  # do the query only once if needed
                            with self.db.conn.read_ctx() as second_cursor:
                                second_cursor.execute(
                                    'SELECT account FROM blockchain_accounts WHERE blockchain=?',
                                    (SupportedBlockchain.ETHEREUM.get_key().upper(),),
                                )
                                ethereum_tracked_accounts = {string_to_evm_address(row[0]) for row in second_cursor}  # noqa: E501

                        deserialized_event = EthBlockEvent.deserialize_from_db(data, fee_recipient_tracked=location_label_tuple[0] in ethereum_tracked_accounts)  # noqa: E501

                elif entry_type == HistoryBaseEntryType.ETH_DEPOSIT_EVENT:
                    data = (
                        entry[data_start_idx:data_start_idx + 4] +
                        entry[data_start_idx + 5:data_start_idx + 6] +
                        entry[data_start_idx + 7:data_start_idx + 9] +
                        entry[data_start_idx + HISTORY_BASE_ENTRY_LENGTH:data_start_idx + HISTORY_BASE_ENTRY_LENGTH + 1] +  # noqa: E501
                        entry[data_start_idx + HISTORY_BASE_ENTRY_LENGTH + CHAIN_FIELD_LENGTH:data_start_idx + HISTORY_BASE_ENTRY_LENGTH + CHAIN_FIELD_LENGTH + 1]  # noqa: E501
                    )
                    deserialized_event = EthDepositEvent.deserialize_from_db(data)
                elif entry_type == HistoryBaseEntryType.SOLANA_EVENT:
                    deserialized_event = SolanaEvent.deserialize_from_db(
                        entry[data_start_idx:data_start_idx + HISTORY_BASE_ENTRY_LENGTH + 1] +
                        entry[data_start_idx + HISTORY_BASE_ENTRY_LENGTH + 1:data_start_idx + HISTORY_BASE_ENTRY_LENGTH + CHAIN_FIELD_LENGTH + 1],  # noqa: E501
                    )
                else:
                    data = entry[data_start_idx:group_has_ignored_assets_idx]
                    deserialized_event = (
                        AssetMovement if entry_type == HistoryBaseEntryType.ASSET_MOVEMENT_EVENT else  # noqa: E501
                        SwapEvent if entry_type == HistoryBaseEntryType.SWAP_EVENT else
                        EvmSwapEvent if entry_type == HistoryBaseEntryType.EVM_SWAP_EVENT else
                        SolanaSwapEvent if entry_type == HistoryBaseEntryType.SOLANA_SWAP_EVENT else  # noqa: E501
                        HistoryEvent
                    ).deserialize_from_db(data)
            except (DeserializationError, UnknownAsset) as e:
                log.error(f'Failed to deserialize history event {entry} due to {e!s}')
                failed_to_deserialize = True
                continue

            if group_has_ignored_assets:
                ignored_group_identifiers.add(deserialized_event.group_identifier)

            if aggregate_by_group_ids is True:
                output_grouped.append((entry[0], deserialized_event))
            else:
                output_flat.append(deserialized_event)

        if failed_to_deserialize:
            self.db.msg_aggregator.add_error(
                'Could not deserialize one or more history event(s). '
                'Try redecoding the event(s) or check the logs for more details.',
            )

        if aggregate_by_group_ids is True:
            return HistoryEventsResult(
                events=output_grouped,
                ignored_group_identifiers=ignored_group_identifiers,
            )
        return HistoryEventsResult(
            events=output_flat,
            ignored_group_identifiers=ignored_group_identifiers,
        )

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery,
            aggregate_by_group_ids: Literal[True],
            match_exact_events: bool = ...,
    ) -> list[tuple[int, HistoryBaseEntry]]:
        ...

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[HistoryBaseEntry]:
        ...

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: EthDepositEventFilterQuery,
            aggregate_by_group_ids: Literal[True],
            match_exact_events: bool,
    ) -> list[tuple[int, EthDepositEvent]]:
        ...

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: EthDepositEventFilterQuery,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[EthDepositEvent]:
        ...

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: EthWithdrawalFilterQuery,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[EthWithdrawalEvent]:
        ...

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: EvmEventFilterQuery,
            aggregate_by_group_ids: Literal[True],
            match_exact_events: bool,
    ) -> list[tuple[int, EvmEvent]]:
        ...

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: EvmEventFilterQuery,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[EvmEvent]:
        ...

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: SolanaEventFilterQuery,
            aggregate_by_group_ids: Literal[True],
            match_exact_events: bool,
    ) -> list[tuple[int, SolanaEvent]]:
        ...

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: SolanaEventFilterQuery,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[SolanaEvent]:
        ...

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventWithCounterpartyFilterQuery,
            aggregate_by_group_ids: Literal[True],
            match_exact_events: bool,
    ) -> list[tuple[int, SolanaEvent | EvmEvent]]:
        ...

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventWithCounterpartyFilterQuery,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[SolanaEvent | EvmEvent]:
        ...

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventWithTxRefFilterQuery,
            aggregate_by_group_ids: Literal[True],
            match_exact_events: bool,
    ) -> list[tuple[int, SolanaEvent | EvmEvent | HistoryEvent]]:
        ...

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventWithTxRefFilterQuery,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> list[SolanaEvent | EvmEvent | HistoryEvent]:
        ...

    @overload
    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery | HistoryEventWithCounterpartyFilterQuery | HistoryEventWithTxRefFilterQuery | SolanaEventFilterQuery | EvmEventFilterQuery | EthDepositEventFilterQuery | EthWithdrawalFilterQuery,  # noqa: E501
            aggregate_by_group_ids: bool = ...,
            match_exact_events: bool = ...,
    ) -> (
        list[tuple[int, HistoryBaseEntry]] | list[HistoryBaseEntry] |
        list[tuple[int, SolanaEvent | EvmEvent]] | list[SolanaEvent | EvmEvent] |
        list[tuple[int, SolanaEvent | EvmEvent | HistoryEvent]] | list[SolanaEvent | EvmEvent | HistoryEvent] |  # noqa: E501
        list[tuple[int, SolanaEvent]] | list[SolanaEvent] |
        list[tuple[int, EvmEvent]] | list[EvmEvent] |
        list[tuple[int, EthDepositEvent]] | list[EthDepositEvent] |
        list[tuple[int, EthWithdrawalEvent]] | list[EthWithdrawalEvent]
    ):
        """
        This fallback is needed for runtime boolean values that can't be resolved
        to literal types at type checking time.
        """

    def get_history_events_internal(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryEventFilterQuery | HistoryEventWithCounterpartyFilterQuery | HistoryEventWithTxRefFilterQuery | SolanaEventFilterQuery | EvmEventFilterQuery | EthDepositEventFilterQuery | EthWithdrawalFilterQuery,  # noqa: E501
            aggregate_by_group_ids: bool = False,
            match_exact_events: bool = True,
    ) -> (
        list[tuple[int, HistoryBaseEntry]] | list[HistoryBaseEntry] |
        list[tuple[int, SolanaEvent | EvmEvent]] | list[SolanaEvent | EvmEvent] |
        list[tuple[int, SolanaEvent | EvmEvent | HistoryEvent]] | list[SolanaEvent | EvmEvent | HistoryEvent] |  # noqa: E501
        list[tuple[int, SolanaEvent]] | list[SolanaEvent] |
        list[tuple[int, EvmEvent]] | list[EvmEvent] |
        list[tuple[int, EthDepositEvent]] | list[EthDepositEvent] |
        list[tuple[int, EthWithdrawalEvent]] | list[EthWithdrawalEvent]
    ):
        """Internal method that gets all events from the DB without limit restrictions.

        This method is used internally by the system and in tests where we need
        to retrieve all events without applying premium tier limits.
        """
        return self.get_history_events(
            cursor=cursor,
            filter_query=filter_query,
            entries_limit=None,
            aggregate_by_group_ids=aggregate_by_group_ids,
            match_exact_events=match_exact_events,
        )

    @overload
    def get_history_events_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryBaseEntryFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[True],
            match_exact_events: bool,
    ) -> HistoryEventsWithCountResult:
        ...

    @overload
    def get_history_events_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryBaseEntryFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: Literal[False] = ...,
            match_exact_events: bool = ...,
    ) -> HistoryEventsWithCountResult:
        ...

    @overload
    def get_history_events_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: HistoryBaseEntryFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: bool = False,
            match_exact_events: bool = ...,
    ) -> HistoryEventsWithCountResult:
        """
        This fallback is needed due to
        https://github.com/python/mypy/issues/6113#issuecomment-869828434
        """

    def get_history_events_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: 'HistoryBaseEntryFilterQuery',
            entries_limit: int | None,
            aggregate_by_group_ids: bool = False,
            match_exact_events: bool = False,
    ) -> HistoryEventsWithCountResult:
        """Gets all history events for all types, based on the filter query.

        Also returns how many are the total found for the filter and the total found applying
        the limit if provided. Otherwise count_with_limit and count_without_limit are equal.
        """
        events_result = self._get_history_events_with_ignored_groups(
            cursor=cursor,
            filter_query=filter_query,
            entries_limit=entries_limit,
            aggregate_by_group_ids=aggregate_by_group_ids,
            match_exact_events=match_exact_events,
        )
        count_without_limit, count_with_limit = self.get_history_events_count(
            cursor=cursor,
            query_filter=filter_query,
            entries_limit=entries_limit,
            aggregate_by_group_ids=aggregate_by_group_ids,
        )
        return HistoryEventsWithCountResult(
            events=events_result.events,
            entries_found=count_without_limit,
            entries_with_limit=count_with_limit,
            ignored_group_identifiers=events_result.ignored_group_identifiers,
        )

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
        with self.db.conn.read_ctx() as cursor:
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

    def get_history_event_group_position(
            self,
            group_identifier: str,
            filter_query: HistoryBaseEntryFilterQuery,
    ) -> int | None:
        """Get the 0-based position of the given group in the filtered and sorted
        list of groups (timestamp DESC, group_identifier as tiebreaker).

        The filter_query is used to restrict which events are considered, matching
        the same filtering applied when viewing history events.

        Returns the position (0-based offset of the group among all distinct groups),
        or None if the group does not exist in the filtered results.
        """
        with self.db.conn.read_ctx() as cursor:
            # Build the full grouped query using the same logic as the main events query
            # This correctly handles all filter types (EVM, Solana, etc.) with proper JOINs
            query, query_bindings = self._create_history_events_query(
                filter_query=filter_query,
                entries_limit=None,
                aggregate_by_group_ids=True,
                include_order=False,
            )

            # Get the target group's max timestamp from the filtered groups
            target_ts_result = cursor.execute(
                f'SELECT MAX(timestamp) FROM ({query}) WHERE group_identifier = ?',
                query_bindings + [group_identifier],
            ).fetchone()
            if target_ts_result is None or target_ts_result[0] is None:
                return None

            target_group_ts = target_ts_result[0]

            # Count how many distinct groups in the filtered set sort before the target group
            # in timestamp DESC order (with group_identifier as tiebreaker for equal timestamps)
            return cursor.execute(
                'SELECT COUNT(*) FROM ('
                f'  SELECT group_identifier, MAX(timestamp) as group_ts FROM ({query})'
                '  GROUP BY group_identifier'
                '  HAVING group_ts > ? OR (group_ts = ? AND group_identifier < ?)'
                ')',
                query_bindings + [target_group_ts, target_group_ts, group_identifier],
            ).fetchone()[0]

    def get_history_events_count(
            self,
            cursor: 'DBCursor',
            query_filter: HistoryBaseEntryFilterQuery,
            aggregate_by_group_ids: bool = False,
            entries_limit: int | None = None,
    ) -> tuple[int, int]:
        """
        Returns how many events matching the filter but ignoring pagination are in the DB.
        We return two integers. The first one being the number of events returned and the second
        the number of events if any limit is applied, otherwise the second value matches
        the first.
        """
        query_without_limit, query_without_limit_bindings = (
            self._create_history_events_count_query(
                filter_query=query_filter,
                aggregate_by_group_ids=aggregate_by_group_ids,
                entries_limit=None,
            )
        )
        count_without_limit = cursor.execute(
            f'SELECT COUNT(*) FROM ({query_without_limit})',
            query_without_limit_bindings,
        ).fetchone()[0]

        # When we have a limit but the total is already smaller or equal,
        # just return the total for both counts
        if entries_limit is None or count_without_limit <= entries_limit:
            return count_without_limit, count_without_limit

        # Otherwise, get the limited count
        query_with_limit, query_with_limit_bindings = self._create_history_events_count_query(
            filter_query=query_filter,
            aggregate_by_group_ids=aggregate_by_group_ids,
            entries_limit=entries_limit,
        )
        count_with_limit = cursor.execute(
            f'SELECT COUNT(*) FROM ({query_with_limit})',
            query_with_limit_bindings,
        ).fetchone()[0]

        # If we're grouping by event IDs and got 0 results but should have some,
        # fall back to using the minimum of limit and total
        if aggregate_by_group_ids and count_with_limit == 0 and entries_limit > 0:
            count_with_limit = min(entries_limit, count_without_limit)

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
        """Returns the sum of the amounts received by asset and the sum of value in main currency
        at the time of the events and the total value of all the assets queried in main currency.
        """
        total_events = cursor.execute(
            f'SELECT COUNT(*) FROM history_events {query_filters}',
            bindings,
        ).fetchone()[0]

        assets_amounts: dict[str, FVal] = defaultdict(FVal)
        assets_value: dict[str, FVal] = defaultdict(FVal)
        total_value: FVal = ZERO
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
                price = query_price_or_use_default(
                    asset=Asset(asset),
                    time=ts_ms_to_sec(row[2]),
                    default_value=ZERO,
                    location=query_location,
                )
                assets_amounts[asset] += amount
                assets_value[asset] += (value := amount * price)
                total_value += value
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

        return final_amounts, total_value

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
            'E2.group_identifier=E.group_identifier) > 2',
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
                'SELECT SUM(CAST(amount AS FLOAT)) FROM history_events JOIN chain_events_info '
                'ON history_events.identifier=chain_events_info.identifier WHERE '
                "asset='ETH' AND type='spend' and subtype='fee' AND counterparty='gas' AND "
                'timestamp >= ? AND timestamp <= ?',
                (from_ts_ms, to_ts_ms),
            )
            if (amount := cursor.fetchone()[0]) is not None:
                eth_on_gas = str(amount)
            else:
                eth_on_gas = '0'

            skip_spam_assets = "history_events.asset NOT IN (SELECT value FROM multisettings WHERE name = 'ignored_asset')"  # noqa: E501
            cursor.execute(
                'SELECT location_label, SUM(CAST(amount AS FLOAT)) FROM history_events JOIN chain_events_info '  # noqa: E501
                'ON history_events.identifier=chain_events_info.identifier WHERE '
                "asset='ETH' AND type='spend' and subtype='fee' AND counterparty='gas' AND "
                'timestamp >= ? AND timestamp <= ? GROUP BY location_label',
                (from_ts_ms, to_ts_ms),
            )
            eth_on_gas_per_address = {row[0]: str(row[1]) for row in cursor}
            cursor.execute(
                'SELECT chain_id, COUNT(DISTINCT group_identifier) as tx_count FROM chain_events_info '  # noqa: E501
                'JOIN history_events ON chain_events_info.identifier = history_events.identifier '
                'JOIN evm_transactions ON evm_transactions.tx_hash = chain_events_info.tx_ref '
                'WHERE history_events.timestamp >= ? AND history_events.timestamp <= ? AND '
                f'{skip_spam_assets} GROUP BY chain_id',
                (from_ts_ms, to_ts_ms),
            )
            transactions_per_chain: dict[str, int] = {}
            for row in cursor:
                chain = ChainID.deserialize_from_db(row[0]).to_blockchain()
                transactions_per_chain[chain.name] = row[1]

            cursor.execute(
                'SELECT COUNT(DISTINCT history_events.group_identifier) FROM chain_events_info '
                'JOIN history_events ON chain_events_info.identifier = history_events.identifier '
                'WHERE history_events.location = ? AND history_events.timestamp >= ? AND history_events.timestamp <= ? '  # noqa: E501
                f'AND {skip_spam_assets}',
                (Location.SOLANA.serialize_for_db(), from_ts_ms, to_ts_ms),
            )
            if solana_count := cursor.fetchone()[0]:
                transactions_per_chain[SupportedBlockchain.SOLANA.name] = solana_count

            cursor.execute(
                'SELECT location, COUNT(DISTINCT group_identifier) FROM history_events '
                'WHERE location IN (?, ?) AND timestamp >= ? AND timestamp <= ? '
                f'AND {skip_spam_assets} GROUP BY location',
                (
                    Location.BITCOIN.serialize_for_db(),
                    Location.BITCOIN_CASH.serialize_for_db(),
                    from_ts_ms,
                    to_ts_ms,
                ),
            )
            for row in cursor:
                chain = SupportedBlockchain.from_location(Location.deserialize_from_db(row[0]))  # type: ignore  # Location here is only blockchain locations
                transactions_per_chain[chain.name] = row[1]

            cursor.execute(
                f'SELECT location, COUNT(DISTINCT group_identifier) AS unique_events FROM history_events '  # noqa: E501
                f'WHERE location IN ({",".join("?" * len(possible_trades_locations := ALL_SUPPORTED_EXCHANGES + (Location.EXTERNAL,)))}) AND timestamp BETWEEN ? AND ? GROUP BY location',  # noqa: E501
                (*[i.serialize_for_db() for i in possible_trades_locations], from_ts_ms, to_ts_ms),
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

            placeholders = ','.join('?' * len(CHAINS_WITH_TRANSACTIONS))
            bindings = tuple(Location.from_chain(blockchain).serialize_for_db() for blockchain in CHAINS_WITH_TRANSACTIONS)  # noqa: E501
            cursor.execute(
                "SELECT unixepoch(date(datetime(timestamp/1000, 'unixepoch'), 'localtime'), 'utc'), COUNT(DISTINCT group_identifier) as tx_count "  # noqa: E501
                f'FROM history_events WHERE location IN ({placeholders}) '
                'AND timestamp >= ? AND timestamp <= ? AND asset NOT IN '
                "(SELECT value FROM multisettings WHERE name = 'ignored_asset') "
                "GROUP BY date(datetime(timestamp/1000, 'unixepoch'), 'localtime') ORDER BY "
                'tx_count DESC LIMIT 10',
                (*bindings, from_ts_ms, to_ts_ms),
            )
            top_days_by_number_of_transactions = [{
                'timestamp': row[0],
                'amount': str(row[1]),
            } for row in cursor]

            cursor.execute(
                'SELECT counterparty, COUNT(DISTINCT tx_ref) AS unique_transaction_count '
                'FROM chain_events_info JOIN history_events ON '
                'chain_events_info.identifier = history_events.identifier '
                "WHERE counterparty IS NOT NULL AND counterparty != 'gas' "
                'AND timestamp BETWEEN ? AND ? '
                'GROUP BY counterparty ORDER BY unique_transaction_count DESC',
                (from_ts_ms, to_ts_ms),
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

    def process_matched_asset_movements(
            self,
            cursor: 'DBCursor',
            aggregate_by_group_ids: bool,
            events_result: list[tuple[int, HistoryBaseEntry]] | list[HistoryBaseEntry],
            entries_found: int,
            entries_with_limit: int,
            entries_total: int,
            ignored_group_identifiers: set[str],
    ) -> tuple[
        list[tuple[int, HistoryBaseEntry]] | list[HistoryBaseEntry],
        dict[str, str],
        int,
        int,
        int,
        set[str],
    ]:
        """Process the events_result joining asset movements with the group of their matched event.

        Handles two cases:
        - aggregate_by_group_ids is True: Only one entry for each movement & matched event pair
         is included, with its grouped_events_num incremented to account for the other events
         that will be included in that group. This entry will be given the group_identifier of the
         matched event when the events are serialized (references the joined_group_ids dict).
        - aggregate_by_group_ids is False: If a matched event group_identifier is included in the
         result, the corresponding asset movement events are added to the result.

        Returns a tuple containing the processed events, joined group ids dict, entries found,
        entries with limit, entries total, and group identifiers with ignored assets.
        """
        movement_group_to_match_info: dict[str, list[tuple[int, str, int]]] = defaultdict(list)
        match_group_to_movement_info: dict[str, tuple[str, int]] = {}
        joined_group_ids: dict[str, str] = {}
        if len(events_result) == 0:
            return (
                events_result,
                joined_group_ids,
                entries_found,
                entries_with_limit,
                entries_total,
                ignored_group_identifiers,
            )

        if aggregate_by_group_ids:
            events_list = [event for _, event in cast('list[tuple[int, HistoryBaseEntry]]', events_result)]  # noqa: E501
        else:
            events_list = cast('list[HistoryBaseEntry]', events_result)

        result_group_ids = {event.group_identifier for event in events_list}
        group_ids_to_count: set[str] = set()
        matched_rows: list[tuple[int, int, str, str, int, int]] = []
        for chunk, placeholders in get_query_chunks(list(result_group_ids)):
            # First, find the ids of all movements associated with the provided events in a cte,
            # then load the info for these movements and all events that may be matched with them.
            # This properly handles getting all associated events no matter which event from a
            # matched pair or multi-match group is present in the events_list here.
            for row in cursor.execute(
                'WITH movement_ids AS ('
                    'SELECT DISTINCT history_event_links.left_event_id '
                    'FROM history_event_links JOIN history_events ON history_events.identifier IN '
                    '(history_event_links.right_event_id, history_event_links.left_event_id) '
                    'WHERE history_event_links.link_type = ? '
                    f'AND history_events.group_identifier IN ({placeholders})'
                ') SELECT history_event_links.left_event_id, history_event_links.right_event_id, '
                'movement_events_join.group_identifier, match_events_join.group_identifier, '
                'movement_events_join.entry_type, match_events_join.entry_type '
                'FROM history_event_links '
                'JOIN history_events movement_events_join ON '
                'movement_events_join.identifier = history_event_links.left_event_id '
                'JOIN history_events match_events_join ON '
                'match_events_join.identifier = history_event_links.right_event_id '
                'WHERE history_event_links.link_type = ? AND '
                'history_event_links.left_event_id IN movement_ids',
                (
                    HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),
                    *chunk,
                    HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),
                ),
            ):
                matched_rows.append((
                    int(row[0]),  # movement id
                    int(row[1]),  # match id
                    (movement_group_identifier := row[2]),
                    (match_group_identifier := row[3]),
                    int(row[4]),  # movement entry type
                    int(row[5]),  # match entry type
                ))
                group_ids_to_count.add(movement_group_identifier)
                group_ids_to_count.add(match_group_identifier)

        if len(matched_rows) == 0:
            return (
                events_result,
                joined_group_ids,
                entries_found,
                entries_with_limit,
                entries_total,
                ignored_group_identifiers,
            )

        group_counts: dict[str, int] = {}
        for chunk, placeholders in get_query_chunks(list(group_ids_to_count)):
            for row in cursor.execute(
                f'SELECT group_identifier, COUNT(*) FROM history_events '
                f'WHERE group_identifier IN ({placeholders}) GROUP BY group_identifier',
                tuple(chunk),
            ):
                group_counts[row[0]] = row[1]

        asset_movement_entry_type = HistoryBaseEntryType.ASSET_MOVEMENT_EVENT.serialize_for_db()
        for (
            movement_id,
            match_id,
            movement_group_identifier,
            match_group_identifier,
            movement_entry_type,
            match_entry_type,
        ) in matched_rows:
            movement_group_count = group_counts.get(movement_group_identifier, 0)
            match_group_count = group_counts.get(match_group_identifier, 0)
            if (
                movement_entry_type == asset_movement_entry_type and
                match_entry_type == asset_movement_entry_type
            ):
                canonical_group_identifier = (
                    movement_group_identifier
                    if movement_id < match_id else
                    match_group_identifier
                )
                joined_group_ids[movement_group_identifier] = canonical_group_identifier
                joined_group_ids[match_group_identifier] = canonical_group_identifier
            else:
                joined_group_ids[movement_group_identifier] = movement_group_identifier
                joined_group_ids[match_group_identifier] = movement_group_identifier

            movement_group_to_match_info[movement_group_identifier].append((
                match_id,
                match_group_identifier,
                match_group_count,
            ))
            match_group_to_movement_info[match_group_identifier] = (
                movement_group_identifier,
                movement_group_count,
            )
            if match_group_identifier not in movement_group_to_match_info:
                # Skip decrementing the total only in the case where a movement is matched with
                # another movement, and this logic will run twice for one joined group.
                entries_total -= 1

        processed_events_result: list[tuple[int, HistoryBaseEntry]] | list[HistoryBaseEntry] = []
        if aggregate_by_group_ids:
            # Aggregating by group. Need to ensure that for each movement/match group there is
            # only one event present. Process the events and for each event that is part of a
            # movement/match group do one of the following:
            # - adjust grouped_events_num to include the events from the other side of the movement
            # - skip the event if we have already processed an event from that movement/match group
            already_processed_matches: set[str] = set()
            for grouped_events_num, event in cast('list[tuple[int, HistoryBaseEntry]]', events_result):  # noqa: E501
                should_skip, matched_joined_group_count = False, 0
                if (
                    (match_info_list := movement_group_to_match_info.get(event.group_identifier)) is not None and  # noqa: E501
                    event.group_identifier in match_group_to_movement_info
                ):  # This is a movement matched with a movement.
                    for _, matched_group_identifier, joined_count in match_info_list:
                        matched_joined_group_count += joined_count
                        if len({matched_group_identifier, event.group_identifier} & already_processed_matches) != 0:  # noqa: E501
                            should_skip = True
                        already_processed_matches.add(matched_group_identifier)
                    already_processed_matches.add(event.group_identifier)
                elif match_info_list is not None:
                    for _, matched_group_identifier, joined_count in match_info_list:
                        matched_joined_group_count += joined_count
                        if matched_group_identifier in already_processed_matches:
                            should_skip = True
                        else:
                            already_processed_matches.add(matched_group_identifier)
                elif (movement_info := match_group_to_movement_info.get(event.group_identifier)) is not None:  # noqa: E501
                    movement_group_identifier, matched_joined_group_count = movement_info
                    should_skip = event.group_identifier in already_processed_matches
                    already_processed_matches.add(event.group_identifier)
                    # also load any other matched events associated with this movement.
                    if (
                        not should_skip and
                        (match_info_list := movement_group_to_match_info.get(movement_group_identifier)) is not None  # noqa: E501
                    ):
                        for _, matched_group_id, joined_count in match_info_list:
                            if matched_group_id == event.group_identifier:
                                continue

                            matched_joined_group_count += joined_count
                            already_processed_matches.add(matched_group_id)

                if should_skip:  # already processed the other side of this pair, so skip.
                    entries_found -= 1
                    entries_with_limit -= 1
                    continue

                processed_events_result.append(
                    (grouped_events_num + matched_joined_group_count, event),   # type: ignore[arg-type]  # will be a list of tuple[int, HistoryBaseEntry]
                )

        else:  # Not aggregating. Need to include all associated events in the movement groups.
            events_by_group: dict[str, list[HistoryBaseEntry]] = defaultdict(list)
            for event in cast('list[HistoryBaseEntry]', events_result):
                events_by_group[event.group_identifier].append(event)

            # Collect any group ids that are associated with some of the current events, but that
            # are not already present in the current event list.
            needed_group_ids: set[str] = set()
            for group_identifier in events_by_group:
                if (match_info_list := movement_group_to_match_info.get(group_identifier)) is not None:  # noqa: E501
                    needed_group_ids.update(
                        group_id for _, group_id, _ in match_info_list
                        if group_id not in events_by_group
                    )
                if (movement_info := match_group_to_movement_info.get(group_identifier)) is not None:  # noqa: E501
                    if (movement_group_id := movement_info[0]) not in events_by_group:
                        needed_group_ids.add(movement_group_id)

                    # also include group ids of any other events matched with this movement.
                    if (match_info_list := movement_group_to_match_info.get(movement_group_id)) is not None:  # noqa: E501
                        needed_group_ids.update(
                            group_id for _, group_id, _ in match_info_list
                            if group_id not in events_by_group
                        )

            # Load the actual events for these associated groups
            joined_events_by_group: dict[str, list[HistoryBaseEntry]] = defaultdict(list)
            if len(needed_group_ids) > 0:
                joined_events_result = self._get_history_events_with_ignored_groups(
                    cursor=cursor,
                    filter_query=HistoryEventFilterQuery.make(
                        group_identifiers=list(needed_group_ids),
                    ),
                    entries_limit=None,
                )
                for joined_event in joined_events_result.events:
                    joined_events_by_group[joined_event.group_identifier].append(joined_event)  # type: ignore  # will be a list of HistoryBaseEntry
                ignored_group_identifiers.update(
                    joined_events_result.ignored_group_identifiers,
                )

            # Include the newly loaded events with their associated groups.
            for group_identifier, events in events_by_group.items():
                if (match_info_list := movement_group_to_match_info.get(group_identifier)) is not None:  # noqa: E501
                    for _, matched_group_id, _ in match_info_list:
                        events.extend(joined_events_by_group[matched_group_id])
                elif (movement_info := match_group_to_movement_info.get(group_identifier)) is not None:  # noqa: E501
                    events.extend(joined_events_by_group[movement_group_id := movement_info[0]])
                    # also include all events from the groups of any other events that are
                    # matched with this movement.
                    if (match_info_list := movement_group_to_match_info.get(movement_group_id)) is not None:  # noqa: E501
                        for _, group_id, _ in match_info_list:
                            events.extend(joined_events_by_group[group_id])

                processed_events_result.extend(sorted(events, key=lambda event: event.timestamp))  # type: ignore  # will be a list of HistoryBaseEntry

        return (
            processed_events_result,
            joined_group_ids,
            entries_found,
            entries_with_limit,
            entries_total,
            ignored_group_identifiers,
        )
