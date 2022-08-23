from typing import TYPE_CHECKING, List, Optional, Sequence

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.utils import form_query_to_filter_timestamps
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

from .types import BalancerEvent

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


def add_balancer_events(
        write_cursor: 'DBCursor',
        events: Sequence[BalancerEvent],
        msg_aggregator: MessagesAggregator,
) -> None:
    query = (
        """
        INSERT INTO balancer_events (
            tx_hash,
            log_index,
            address,
            timestamp,
            type,
            pool_address_token,
            lp_amount,
            usd_value,
            amount0,
            amount1,
            amount2,
            amount3,
            amount4,
            amount5,
            amount6,
            amount7
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """
    )
    for event in events:
        event_tuple = event.to_db_tuple()
        try:
            write_cursor.execute(query, event_tuple)
        except sqlcipher.IntegrityError:  # pylint: disable=no-member
            msg_aggregator.add_warning(
                f'Tried to add a Balancer event that already exists in the DB. '
                f'Event data: {event_tuple}. Skipping event.',
            )
            continue


def get_balancer_events(
        cursor: 'DBCursor',
        msg_aggregator: MessagesAggregator,
        from_timestamp: Optional[Timestamp] = None,
        to_timestamp: Optional[Timestamp] = None,
        address: Optional[ChecksumEvmAddress] = None,
) -> List[BalancerEvent]:
    """Returns a list of Balancer events optionally filtered by time and address"""
    query = 'SELECT * FROM balancer_events '
    # Timestamp filters are omitted, done via `form_query_to_filter_timestamps`
    filters = []
    if address is not None:
        filters.append(f'address="{address}" ')

    if filters:
        query += 'WHERE '
        query += 'AND '.join(filters)

    query, bindings = form_query_to_filter_timestamps(
        query=query,
        timestamp_attribute='timestamp',
        from_ts=from_timestamp,
        to_ts=to_timestamp,
    )

    events = []
    cursor.execute(query, bindings)
    for event_tuple in cursor:
        try:
            event = BalancerEvent.deserialize_from_db(event_tuple)
        except DeserializationError as e:
            msg_aggregator.add_error(
                f'Error deserializing Balancer event from the DB. Skipping event. '
                f'Error was: {str(e)}',
            )
            continue
        events.append(event)

    return events
