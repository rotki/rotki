import json
import logging
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from rotkehlchen.accounting.export.csv import (
    FILENAME_SKIPPED_EXTERNAL_EVENTS_CSV,
    dict_to_csv_file,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location

if TYPE_CHECKING:
    from rotkehlchen.exchanges.kraken import Kraken
    from rotkehlchen.rotkehlchen import Rotkehlchen


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def get_skipped_external_events_summary(rotki: 'Rotkehlchen') -> dict[str, Any]:
    """Get a summary of skipped external events by location"""
    summary: dict[str, Any] = {'locations': {}}
    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*), location FROM skipped_external_events GROUP BY location')

        total = 0
        for count, location in cursor:
            serialized_location = Location.deserialize_from_db(location).serialize()
            summary['locations'][serialized_location] = count
            total += count

    summary['total'] = total
    return summary


def export_skipped_external_events(rotki: 'Rotkehlchen', directory: Path | None) -> Path:
    """
    Export the skipped events in a CSV file.

    If `directory` is provided, the export generated is written to that directory.
    Otherwise a file is created, the data are written to this file and the path
    is returned for download

    May raise:
    - CSVWriteError is CSV can't be written
    """
    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute('SELECT location, data, extra_data FROM skipped_external_events')
        data = [{'location': Location.deserialize_from_db(x).serialize(), 'data': y, 'extra_data': z} for x, y, z in cursor]  # noqa: E501

    if directory is None:
        _, newfilename = tempfile.mkstemp()
        newfilepath = Path(newfilename)
    else:
        filepath = directory / FILENAME_SKIPPED_EXTERNAL_EVENTS_CSV
        filepath.touch(exist_ok=True)
        newfilepath = filepath

    dict_to_csv_file(
        path=newfilepath,
        dictionary_list=data,
        csv_delimiter=CachedSettings().get_settings().csv_export_delimiter,
    )
    return Path(newfilepath)


def reprocess_skipped_external_events(rotki: 'Rotkehlchen') -> tuple[int, int]:
    """Go through the skipped external events, try to re-process them and if any
    are successfully reprocessed them remove them from the table

    This is effectively containing only the kraken exchange logic right now

    Returns number of current skipped events processed, and how many were
    reprocessed successfully.
    """
    raw_kraken_events = defaultdict(list)
    total_num, processed_num = 0, 0
    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute('SELECT identifier, data, location, extra_data FROM skipped_external_events')  # noqa: E501
        for identifier, data, raw_location, extra_data in cursor:
            location = Location.deserialize_from_db(raw_location)  # should not raise
            if location != Location.KRAKEN:
                continue
            extra_json = None
            if extra_data is not None:
                try:
                    extra_json = json.loads(extra_data)
                except json.JSONDecodeError as e:  # should not happen
                    log.error(f"Could not decode json from DB's skipped event extra data due to: {e}")  # noqa: E501
                    continue

            if extra_json is None or (location_label := extra_json.get('location_label')) is None:
                continue  # kraken skipped events should be saved with name as location label

            raw_kraken_events[location_label].append((identifier, json.loads(data)))

    identifiers_to_delete = set()
    # Now that we got the skipped kraken events from the DB, find the kraken instances
    for kraken_name, raw_events in raw_kraken_events.items():
        exchange = rotki.exchange_manager.get_exchange(name=kraken_name, location=Location.KRAKEN)
        if exchange is None:  # we have deleted the exchange, so the skipped events can also go
            identifiers_to_delete.update({x[0] for x in raw_events})
            continue

        total_num += len(raw_events)
        exchange = cast('Kraken', exchange)
        new_events, processed_refids = exchange.process_kraken_raw_events(
            events=[x[1] for x in raw_events],
            events_source='processing skipped events',
            save_skipped_events=False,
        )
        if len(new_events) != 0:
            with rotki.data.db.user_write() as write_cursor:
                DBHistoryEvents(rotki.data.db).add_history_events(write_cursor=write_cursor, history=new_events)  # noqa: E501

        processed_num = 0
        for identifier, raw_data in raw_events:
            try:
                if raw_data['refid'] in processed_refids:
                    identifiers_to_delete.add(identifier)
                    processed_num += 1
            except KeyError:  # should never really happen
                log.error(f'Processing skipped kraken event could not find refid in {raw_data}')
                continue

    if len(identifiers_to_delete) != 0:  # delete some skipped events if needed
        with rotki.data.db.user_write() as write_cursor:
            write_cursor.executemany('DELETE FROM skipped_external_events WHERE identifier=?', [(x,) for x in identifiers_to_delete])  # noqa: E501

    return total_num, processed_num
