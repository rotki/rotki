import logging
from typing import TYPE_CHECKING, List

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures import HistoryBaseEntry
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.limits import FREE_HISTORY_EVENTS_LIMIT
from rotkehlchen.constants.timing import KRAKEN_TS_MULTIPLIER
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_timestamp
from rotkehlchen.typing import Location, Timestamp, Tuple

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DBHistoryEvents():

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def add_history_events(self, history: List[HistoryBaseEntry]) -> None:
        """Insert a list of history events in database. May raise:
        - InputError if the events couldn't be stored in database
        """
        query_str = """INSERT INTO history_events(identifier, event_identifier, sequence_index,
        timestamp, location, location_label, asset, amount, usd_value, notes,
        type, subtype) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
        events = []
        for event in history:
            try:
                events.append(event.serialize_for_db())
            except DeserializationError as e:
                self.db.msg_aggregator.add_error(
                    f'Failed to process kraken event for database. {str(e)}',
                )
        self.db.write_tuples(
            tuple_type='history_event',
            query=query_str,
            tuples=events,
        )
        self.db.update_last_write()

    def delete_history_events(self, location: Location) -> None:
        """
        Deletes history entries following the criteria of the filter_query. May raise:
        - DeserializationError if the location is not valid
        """
        # TODO: In the future this method should allow for more granularity in the delete query
        cursor = self.db.conn.cursor()
        cursor.execute(
            'DELETE FROM history_events WHERE location=?',
            (location.serialize_for_db(),),
        )
        cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ?',
            (f'{location}_history_events_%',),
        )
        self.db.update_last_write()

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
            query = 'SELECT * FROM (SELECT * from history_events ORDER BY timestamp DESC LIMIT ?) ' + query  # noqa: E501
            results = cursor.execute(query, [FREE_HISTORY_EVENTS_LIMIT] + bindings)

        output = []
        for entry in results:
            try:
                output.append(HistoryBaseEntry.deserialize_from_db(entry))
            except DeserializationError as e:
                log.debug(f'Failed to deserialize history event {entry}')
                self.db.msg_aggregator.add_error(
                    f'Failed to read history event from database. {str(e)}',
                )

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
                high_precision_timestamp = deserialize_timestamp(timestamp)
                result.append(
                    (
                        identifier,
                        amount,
                        Asset(asset_name),
                        Timestamp(int(high_precision_timestamp / KRAKEN_TS_MULTIPLIER)),
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
    ) -> Tuple[FVal, List[Tuple[Asset, FVal]]]:
        """Returns the sum of the USD value at the time of acquisition and the amount reveived
        by asset"""
        cursor = self.db.conn.cursor()
        usd_value = FVal(0)
        query_filters, bindings = query_filter.prepare(with_pagination=False)
        try:
            query = 'SELECT SUM(CAST(usd_value AS REAL)) FROM history_events ' + query_filters
            result = cursor.execute(query, bindings)
            usd_value = deserialize_fval(
                value=result.fetchone()[0],
                name='usd value in history events stats',
                location='get_value_stats',
            )
        except (DeserializationError, sqlcipher.DatabaseError) as e:  # pylint: disable=no-member)
            log.error(f'Didnt get correct valid usd_value for history_events query. {str(e)}')

        query = (
            'SELECT asset, SUM(CAST(amount AS REAL)) FROM history_events ' +
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
                assets_amounts.append((asset, amount))
            except UnknownAsset as e:
                log.debug(f'Found unknown asset {row[0]} in staking event. {str(e)}')
            except DeserializationError as e:
                log.debug(f'Failed to deserialize amount {row[1]}. {str(e)}')
        return usd_value, assets_amounts
