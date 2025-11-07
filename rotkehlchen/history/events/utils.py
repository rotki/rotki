from typing import TYPE_CHECKING, Any

from rotkehlchen.db.filtering import DBMultiStringFilter
from rotkehlchen.exchanges.data_structures import hash_id
from rotkehlchen.history.events.structures.base import HistoryBaseEntry
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.types import AssetAmount, Location
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


def create_group_identifier_from_unique_id(
        location: Location,
        unique_id: str,
) -> str:
    return hash_id(str(location) + unique_id)


def create_group_identifier(
        location: Location,
        timestamp: 'TimestampMS',
        asset: 'Asset',
        amount: 'FVal',
        unique_id: str | None,
) -> str:
    """Create a unique group identifier from the given parameters.
    `unique_id` is a transaction id from an exchange, which in combination with the
    location makes a unique group identifier. If this is not available, the location,
    timestamp, asset, and balance must all be combined to ensure a unique identifier.
    """
    if unique_id:
        return create_group_identifier_from_unique_id(location, unique_id)

    return hash_id(
        str(location) +
        str(timestamp) +
        asset.identifier +
        str(amount),
    )


def create_group_identifier_from_swap(
        location: Location,
        timestamp: 'TimestampMS',
        spend: AssetAmount,
        receive: AssetAmount,
        unique_id: str | None = None,
) -> str:
    if unique_id:
        return create_group_identifier_from_unique_id(location, unique_id)

    return hash_id(
        str(location)
        + str(timestamp)
        + spend.asset.identifier
        + str(spend.amount)
        + receive.asset.identifier
        + str(receive.amount),
    )


def generate_events_export_filename(filter_query: 'HistoryBaseEntryFilterQuery', use_localtime: bool) -> str:  # noqa: E501
    """Generate a filename for CSV export based on filter properties."""
    parts = [f'{filter_query.__class__.__name__.replace("FilterQuery", "").lower()}s']
    date_format = '%Y%m%d'
    if filter_query.location_filter and filter_query.location_filter.location:
        parts.append(f'on_{filter_query.location_filter.location.name.lower()}')

    if filter_query.timestamp_filter:
        if filter_query.timestamp_filter.from_ts and filter_query.timestamp_filter.to_ts:
            from_date = timestamp_to_date(ts=filter_query.timestamp_filter.from_ts, formatstr=date_format, treat_as_local=use_localtime)  # noqa: E501
            to_date = timestamp_to_date(ts=filter_query.timestamp_filter.to_ts, formatstr=date_format, treat_as_local=use_localtime)  # noqa: E501
            parts.append(f'{from_date}_to_{to_date}')
        elif filter_query.timestamp_filter.to_ts:
            parts.append(f'until_{timestamp_to_date(ts=filter_query.timestamp_filter.to_ts, formatstr=date_format, treat_as_local=use_localtime)}')  # noqa: E501
        elif filter_query.timestamp_filter.from_ts:
            parts.append(f'from_{timestamp_to_date(ts=filter_query.timestamp_filter.from_ts, formatstr=date_format, treat_as_local=use_localtime)}')  # noqa: E501

    for filter_ in filter_query.filters:
        if isinstance(filter_, DBMultiStringFilter):
            if filter_.column == 'type':
                parts.append(f'types_{"-".join(filter_.values)}')
            elif filter_.column == 'subtype':
                parts.append(f'subtypes_{"-".join(filter_.values)}')

    return f'{"_".join(parts)}.csv'
