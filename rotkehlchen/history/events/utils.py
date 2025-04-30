from typing import TYPE_CHECKING, Any

from rotkehlchen.exchanges.data_structures import hash_id
from rotkehlchen.history.events.structures.base import HistoryBaseEntry
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import timestamp_to_date, ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.db.filtering import HistoryBaseEntryFilterQuery
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import Asset, TimestampMS


def history_event_to_staking_for_api(event: HistoryBaseEntry) -> dict[str, Any]:
    """This is a utility function to be used by kraken staking and binance savings
    rotki api endpoints. It just serves to reduce the returned data by the api
    for those endpoints.

    TODO: Think if we need these and if instead the frontend could just consume normal
    history events through the rotki API
    """
    data = {
        'asset': event.asset.identifier,
        'timestamp': ts_ms_to_sec(event.timestamp),
        'location': str(event.location),
        'amount': abs(event.amount),
    }
    if not (
            event.location == Location.BINANCE and
            event.event_type == HistoryEventSubType.REWARD
    ):
        data['event_type'] = event.event_subtype.serialize()

    return data


def create_event_identifier(
        location: Location,
        timestamp: 'TimestampMS',
        asset: 'Asset',
        amount: 'FVal',
        unique_id: str | None,
) -> str:
    """Create a unique event identifier from the given parameters.
    `unique_id` is a transaction id from an exchange, which in combination with the
    location makes a unique event identifier. If this is not available, the location,
    timestamp, asset, and balance must all be combined to ensure a unique identifier.
    """
    if unique_id is not None:
        return hash_id(str(location) + unique_id)

    return hash_id(
        str(location) +
        str(timestamp) +
        asset.identifier +
        str(amount),
    )


def generate_events_export_filename(filter_query: 'HistoryBaseEntryFilterQuery') -> str:
    """Generate a filename for CSV export based on filter properties."""
    parts = [f'{filter_query.__class__.__name__.replace("FilterQuery", "").lower()}s']
    if filter_query.timestamp_filter:
        if filter_query.timestamp_filter.from_ts and filter_query.timestamp_filter.to_ts:
            from_date = timestamp_to_date(filter_query.timestamp_filter.from_ts, formatstr='%Y%m%d')  # noqa: E501
            to_date = timestamp_to_date(filter_query.timestamp_filter.to_ts, formatstr='%Y%m%d')
            parts.append(f'{from_date}_to_{to_date}')
        elif filter_query.timestamp_filter.to_ts:
            parts.append(f'till_{timestamp_to_date(filter_query.timestamp_filter.to_ts, formatstr="%Y%m%d")}')  # noqa: E501
        elif filter_query.timestamp_filter.from_ts:
            parts.append(f'from_{timestamp_to_date(filter_query.timestamp_filter.from_ts, formatstr="%Y%m%d")}')  # noqa: E501

    if filter_query.location_filter and filter_query.location_filter.location:
        parts.append(filter_query.location_filter.location.name.lower())

    return f'{"_".join(parts)}.csv'
