import json
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, cast

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location

if TYPE_CHECKING:
    from rotkehlchen.exchanges.kraken import Kraken
    from rotkehlchen.rotkehlchen import Rotkehlchen


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def reprocess_skipped_external_events(rotki: 'Rotkehlchen') -> None:
    """Go through the skipped external events, try to re-process them and if any
    are succesfully reprocessed them remove them from the table

    This is effectively containing only the kraken exchange logic right now
    """
    raw_kraken_events = defaultdict(list)
    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute('SELECT identifier, data, location, location_label FROM skipped_external_events')  # noqa: E501
        for identifier, data, raw_location, location_label in cursor:
            location = Location.deserialize_from_db(raw_location)  # should not raise
            if location != Location.KRAKEN:
                continue
            if location_label is None:
                continue  # kraken skipped events should be saved with name as location label

            raw_kraken_events[location_label].append((identifier, json.loads(data)))

    identifiers_to_delete = set()
    # Now that we got the skipped kraken events from the DB, find the kraken instances
    for kraken_name, raw_events in raw_kraken_events.items():
        exchange = rotki.exchange_manager.get_exchange(name=kraken_name, location=Location.KRAKEN)
        if exchange is None:  # we have deleted the exchange, so the skipped events can also go
            identifiers_to_delete.update({x[0] for x in raw_events})
            continue

        exchange = cast('Kraken', exchange)
        processed_events = exchange.process_kraken_raw_events(
            events=[x[1] for x in raw_events],
            events_source='processing skipped events',
            save_skipped_events=False,
        )

        for processed_event in processed_events:
            for identifier, raw_data in raw_events:
                try:
                    if identifier == processed_event.event_identifier:
                        identifiers_to_delete.add(identifier)
                except KeyError:
                    log.error(f'Processing skipped kraken event could not find refid in {raw_data}')  # noqa: E501
                    continue

    if len(identifiers_to_delete) != 0:  # delete some skipped events if needed
        with rotki.data.db.user_write() as write_cursor:
            write_cursor.executemany('DELETE FROM skipped_external_events WHERE identifier=?', list(identifiers_to_delete))  # noqa: E501
