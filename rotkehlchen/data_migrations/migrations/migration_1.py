import logging
import re
from typing import TYPE_CHECKING

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.locations.constants import (
    LOCATION_KRAKEN,
)
from rotkehlchen.locations.legacy_chars import location_from_v53_char, location_to_v53_char
from rotkehlchen.locations.types import deserialize_location_identifier
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def data_migration_1(rotki: Rotkehlchen, progress_handler: MigrationProgressHandler) -> None:  # pylint: disable=unused-argument
    """
    Purge data for exchanges where there is more than one instance. Also purge information
    from kraken as requested for https://github.com/rotki/rotki/pull/3755

    Migration was introduced at least before 1.22.3
    """
    exchange_re = re.compile(r'(.*?)_(trades|margins|asset_movements).*')
    db = rotki.data.db
    with db.conn.read_ctx() as cursor:
        used_ranges = cursor.execute('SELECT * from used_query_ranges').fetchall()
        credentials_result = cursor.execute('SELECT * from user_credentials')
        location_to_name = {}
        multiple_locations = set()
        for result in credentials_result:
            try:  # this migration only runs against the pre-v54 schema
                location = location_from_v53_char(result[1])
            except (KeyError, DeserializationError) as e:
                log.error(
                    f'During data migration 1 found location {result[1]} '
                    f'that could not be deserialized due to {e!s}',
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
            location = deserialize_location_identifier(location_str)
        except DeserializationError as e:
            log.error(
                f'During data migration 1 could not deserialize location '
                f'string {location_str} to location due to {e!s}',
            )
            continue

        if location not in location_to_name:
            if location in SUPPORTED_EXCHANGES:
                with db.user_write() as write_cursor:
                    # Can happen if there is a stray used_query_range from a non-connected exchange
                    write_cursor.execute('DELETE FROM used_query_ranges WHERE name=?', (range_name,))  # noqa: E501
            # in any case continue. Can also be non CEX location such as uniswap/balancer
            continue

        with db.user_write() as write_cursor:
            if location in multiple_locations or location == LOCATION_KRAKEN:
                write_cursor.execute(
                    'DELETE FROM trades WHERE location = ?;',
                    (location_to_v53_char(location),),
                )
                write_cursor.execute(
                    'DELETE FROM asset_movements WHERE location = ?;',
                    (location_to_v53_char(location),),
                )
                write_cursor.execute(
                    'DELETE FROM asset_movements WHERE location = ?;',
                    (location_to_v53_char(location),),
                )
                db.delete_used_query_range_for_exchange(write_cursor=write_cursor, location=location)  # noqa: E501
            else:
                write_cursor.execute(
                    'UPDATE OR IGNORE used_query_ranges SET name=? WHERE name=?',
                    (f'{location_str}_{entry_type}_{location_to_name[location]}', range_name),
                )
