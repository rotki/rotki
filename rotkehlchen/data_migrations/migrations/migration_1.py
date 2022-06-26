import logging
import re
from typing import TYPE_CHECKING

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.rotkehlchen import Rotkehlchen


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def data_migration_1(write_cursor: 'DBCursor', rotki: 'Rotkehlchen') -> None:
    """
    Purge data for exchanges where there is more than one instance. Also purge information
    from kraken as requested for https://github.com/rotki/rotki/pull/3755
    """
    exchange_re = re.compile(r'(.*?)_(trades|margins|asset_movements|ledger_actions).*')
    db = rotki.data.db
    used_ranges = write_cursor.execute('SELECT * from used_query_ranges').fetchall()
    credentials_result = write_cursor.execute('SELECT * from user_credentials')
    location_to_name = {}
    multiple_locations = set()
    for result in credentials_result:
        try:
            location = Location.deserialize_from_db(result[1])
        except DeserializationError as e:
            log.error(
                f'During data migration 1 found location {result[1]} '
                f'that could not be deserialized due to {str(e)}',
            )
            continue

        if location in location_to_name:
            multiple_locations.add(location)
        else:
            location_to_name[location] = result[0]

    for used_range in used_ranges:
        range_name = used_range[0]
        match = exchange_re.search(range_name)
        if match is None:
            continue

        location_str = match.group(1)
        entry_type = match.group(2)
        try:
            location = Location.deserialize(location_str)
        except DeserializationError as e:
            log.error(
                f'During data migration 1 could not deserialize location '
                f'string {location_str} to location due to {str(e)}',
            )
            continue

        if location not in location_to_name:
            if location in SUPPORTED_EXCHANGES:
                # Can happen if there is a stray used_query_range from a non-connected exchange
                write_cursor.execute('DELETE FROM used_query_ranges WHERE name=?', (range_name,))
            # in any case continue. Can also be non CEX location such as uniswap/balancer
            continue

        if location in multiple_locations or location == Location.KRAKEN:
            db.purge_exchange_data(write_cursor, location)
            db.delete_used_query_range_for_exchange(write_cursor=write_cursor, location=location)
        else:
            write_cursor.execute(
                'UPDATE used_query_ranges SET name=? WHERE name=?',
                (f'{location_str}_{entry_type}_{location_to_name[location]}', range_name),
            )
