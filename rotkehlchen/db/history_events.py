import logging
from typing import TYPE_CHECKING, List, Optional

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.limits import FREE_HISTORY_EVENTS_LIMIT
from rotkehlchen.db.constants import HISTORY_MAPPING_CUSTOMIZED
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import EVMTxHash, Timestamp, TimestampMS, Tuple
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

HISTORY_INSERT = """INSERT INTO history_events(event_identifier, sequence_index,
timestamp, location, location_label, asset, amount, usd_value, notes,
type, subtype, counterparty, extra_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""


class DBHistoryEvents():

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def add_history_event(
            self,
            event: HistoryBaseEntry,
            mapping_value: Optional[str] = None,
    ) -> int:
        """Insert a single history entry to the DB. Returns its identifier.

        Optionally map it to a specific value used to map attributes
        to some events

        May raise:
        - DeserializationError if the event could not be serialized for the DB
        - sqlcipher.DatabaseError: If anything went wrong at insertion
        """
        cursor = self.db.conn.cursor()
        cursor.execute(HISTORY_INSERT, event.serialize_for_db())
        identifier = cursor.lastrowid

        if mapping_value is not None:
            cursor.execute(
                'INSERT OR IGNORE INTO history_events_mappings(parent_identifier, value) '
                'VALUES(?, ?)',
                (identifier, mapping_value),
            )

        self.db.update_last_write()
        return identifier

    def add_history_events(self, history: List[HistoryBaseEntry]) -> None:
        """Insert a list of history events in database.

        May raise:
        - InputError if the events couldn't be stored in database
        """
        events = []
        for event in history:
            events.append(event.serialize_for_db())
        self.db.write_tuples(
            tuple_type='history_event',
            query=HISTORY_INSERT,
            tuples=events,
        )
        self.db.update_last_write()

    def edit_history_event(self, event: HistoryBaseEntry) -> Tuple[bool, str]:
        """Edit a history entry to the DB. Returns the edited entry"""
        cursor = self.db.conn.cursor()
        try:
            cursor.execute(
                'UPDATE history_events SET event_identifier=?, sequence_index=?, timestamp=?, '
                'location=?, location_label=?, asset=?, amount=?, usd_value=?, notes=?, '
                'type=?, subtype=?, counterparty=?, extra_data=? WHERE identifier=?',
                (*event.serialize_for_db(), event.identifier),
            )
        except sqlcipher.IntegrityError:  # pylint: disable=no-member
            msg = (
                f'Tried to edit event to have event_identifier {event.event_identifier} and '
                f'sequence_index {event.sequence_index} but it already exists'
            )
            return False, msg

        if cursor.rowcount != 1:
            msg = f'Tried to edit event with id {event.identifier} but could not find it in the DB'
            return False, msg
        cursor.execute(
            'INSERT OR IGNORE INTO history_events_mappings(parent_identifier, value) '
            'VALUES(?, ?)',
            (event.identifier, HISTORY_MAPPING_CUSTOMIZED),
        )

        self.db.update_last_write()
        return True, ''

    def delete_history_events_by_identifier(self, identifiers: List[int]) -> Optional[str]:
        """
        Delete the history events with the given identifiers. If deleting an event
        makes it the last event of a transaction hash then do not allow deletion.

        If any identifier is missing the entire call fails and an error message
        is returned. Otherwise None is returned.
        """
        cursor = self.db.conn.cursor()
        for identifier in identifiers:
            result = cursor.execute(
                'SELECT COUNT(*) FROM history_events WHERE event_identifier=('
                'SELECT event_identifier FROM history_events WHERE identifier=?)',
                (identifier,),
            )
            if result.fetchone()[0] == 1:
                self.db.conn.rollback()
                return (
                    f'Tried to remove history event with id {identifier} '
                    f'which was the last event of a transaction'
                )

            cursor.execute(
                'DELETE FROM history_events WHERE identifier=?', (identifier,),
            )
            affected_rows = cursor.rowcount
            if affected_rows != 1:
                self.db.conn.rollback()
                return (
                    f'Tried to remove history event with id {identifier} which does not exist'
                )

        self.db.update_last_write()
        return None

    def delete_events_by_tx_hash(self, tx_hashes: List[EVMTxHash]) -> None:
        """Delete all relevant (by event_identifier) history events except those that
        are customized"""
        cursor = self.db.conn.cursor()
        customized_event_ids = self.get_customized_event_identifiers()
        length = len(customized_event_ids)
        querystr = 'DELETE FROM history_events WHERE event_identifier=?'
        if length != 0:
            querystr += f' AND identifier NOT IN ({", ".join(["?"] * length)})'
            bindings = [(x.hex(), *customized_event_ids) for x in tx_hashes]
        else:
            bindings = [(x.hex(),) for x in tx_hashes]

        cursor.executemany(querystr, bindings)

    def get_customized_event_identifiers(self) -> List[int]:
        """Returns the identifiers of all the events in the database that have been customized"""
        cursor = self.db.conn.cursor()
        result = cursor.execute(
            'SELECT parent_identifier FROM history_events_mappings WHERE value=?',
            (HISTORY_MAPPING_CUSTOMIZED,),
        )
        return [x[0] for x in result]

    def get_history_events(
        self,
        filter_query: HistoryEventFilterQuery,
        has_premium: bool,
    ) -> List[HistoryBaseEntry]:
        """
        Get history events using the provided query filter
        """
        query, bindings = filter_query.prepare()
        cursor = self.db.conn.cursor()

        if has_premium:
            query = 'SELECT * from history_events ' + query
            results = cursor.execute(query, bindings)
        else:
            query = 'SELECT * FROM (SELECT * from history_events ORDER BY timestamp DESC, sequence_index ASC LIMIT ?) ' + query  # noqa: E501
            results = cursor.execute(query, [FREE_HISTORY_EVENTS_LIMIT] + bindings)

        output = []
        for entry in results:
            try:
                output.append(HistoryBaseEntry.deserialize_from_db(entry))
            except (DeserializationError, UnknownAsset) as e:
                log.debug(f'Failed to deserialize history event {entry} due to {str(e)}')

        return output

    def get_history_events_and_limit_info(
        self,
        filter_query: HistoryEventFilterQuery,
        has_premium: bool,
    ) -> Tuple[List[HistoryBaseEntry], int]:
        """Gets all history events for the query from the DB

        Also returns how many are the total found for the filter
        """
        events = self.get_history_events(
            filter_query=filter_query,
            has_premium=has_premium,
        )
        cursor = self.db.conn.cursor()
        query, bindings = filter_query.prepare(with_pagination=False)
        query = 'SELECT COUNT(*) from history_events ' + query
        total_found_result = cursor.execute(query, bindings)
        return events, total_found_result.fetchone()[0]

    def rows_missing_prices_in_base_entries(
        self,
        filter_query: HistoryEventFilterQuery,
    ) -> List[Tuple[str, FVal, Asset, Timestamp]]:
        """
        Get missing prices for history base entries based on filter query
        """
        query, bindings = filter_query.prepare()
        query = 'SELECT identifier, amount, asset, timestamp FROM history_events ' + query
        result = []
        cursor = self.db.conn.cursor()
        cursor.execute(query, bindings)
        for identifier, amount_raw, asset_name, timestamp in cursor:
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
                        Asset(asset_name),
                        ts_ms_to_sec(TimestampMS(timestamp)),
                    ),
                )
            except DeserializationError as e:
                log.error(
                    f'Failed to read value from historic base entry {identifier} '
                    f'with amount. {str(e)}',
                )
            except UnknownAsset as e:
                log.error(
                    f'Failed to read asset from historic base entry {identifier} '
                    f'with asset identifier {asset_name}. {str(e)}',
                )
        return result

    def get_entries_assets_history_events(
        self,
        query_filter: HistoryEventFilterQuery,
    ) -> List[Asset]:
        """Returns asset from base entry events using the desired filter"""
        cursor = self.db.conn.cursor()
        query, bindings = query_filter.prepare(with_pagination=False)
        query = 'SELECT DISTINCT asset from history_events ' + query
        result = cursor.execute(query, bindings)
        assets = []
        for asset_id in result:
            try:
                assets.append(Asset(asset_id[0]))
            except (UnknownAsset, DeserializationError) as e:
                self.db.msg_aggregator.add_error(
                    f'Found asset {asset_id} in the base history events table and '
                    f'is not in the assets database. {str(e)}',
                )
        return assets

    def get_history_events_count(self, query_filter: HistoryEventFilterQuery) -> int:
        """Returns how many of certain base entry events are in the database"""
        cursor = self.db.conn.cursor()
        query, bindings = query_filter.prepare(with_pagination=False)
        query = 'SELECT COUNT(*) from history_events ' + query
        result = cursor.execute(query, bindings)
        return result.fetchone()[0]

    def get_value_stats(
        self,
        query_filter: HistoryEventFilterQuery,
    ) -> Tuple[FVal, List[Tuple[Asset, FVal, FVal]]]:
        """Returns the sum of the USD value at the time of acquisition and the amount received
        by asset"""
        cursor = self.db.conn.cursor()
        usd_value = ZERO
        query_filters, bindings = query_filter.prepare(with_pagination=False, with_order=False)
        try:
            query = 'SELECT SUM(CAST(usd_value AS REAL)) FROM history_events ' + query_filters
            result = cursor.execute(query, bindings).fetchone()[0]
            if result is not None:
                usd_value = deserialize_fval(
                    value=result,
                    name='usd value in history events stats',
                    location='get_value_stats',
                )
        except DeserializationError as e:
            log.error(f'Didnt get correct valid usd_value for history_events query. {str(e)}')

        query = (
            'SELECT asset, SUM(CAST(amount AS REAL)), SUM(CAST(usd_value AS REAL)) ' +
            'FROM history_events ' +
            query_filters +
            ' GROUP BY asset;'
        )
        result = cursor.execute(query, bindings)
        assets_amounts = []
        for row in result:
            try:
                asset = Asset(row[0])
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
            except UnknownAsset as e:
                log.debug(f'Found unknown asset {row[0]} in staking event. {str(e)}')
            except DeserializationError as e:
                log.debug(f'Failed to deserialize amount {row[1]}. {str(e)}')
        return usd_value, assets_amounts
