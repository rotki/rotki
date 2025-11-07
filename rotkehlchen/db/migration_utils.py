from typing import TYPE_CHECKING

from rotkehlchen.constants import ZERO
from rotkehlchen.exchanges.data_structures import hash_id
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.types import AssetAmount, Location, Price, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.fval import FVal


def create_swap_events_v47_v48(
        timestamp: TimestampMS,
        location: Location,
        spend: AssetAmount,
        receive: AssetAmount,
        unique_id: str | None = None,
        fee: AssetAmount | None = None,
        location_label: str | None = None,
        spend_notes: str | None = None,
) -> list[SwapEvent]:
    """Create group identifier and SwapEvents using exact v47->v48 upgrade logic.

    FROZEN: Do not modify. Used for v47->v48 upgrade and data migration 20.
    """
    if unique_id:
        group_identifier = hash_id(str(location) + unique_id)
    else:
        group_identifier = hash_id(
            str(location)
            + str(timestamp)
            + spend.asset.identifier
            + str(spend.amount)
            + receive.asset.identifier
            + str(receive.amount),
        )

    events = [
        SwapEvent(
            timestamp=timestamp,
            location=location,
            event_subtype=HistoryEventSubType.SPEND,
            asset=spend.asset,
            amount=spend.amount,
            location_label=location_label,
            notes=spend_notes,
            group_identifier=group_identifier,
        ),
        SwapEvent(
            timestamp=timestamp,
            location=location,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=receive.asset,
            amount=receive.amount,
            location_label=location_label,
            notes=None,
            group_identifier=group_identifier,
        ),
    ]

    if fee is not None and fee.amount != ZERO:
        events.append(SwapEvent(
            timestamp=timestamp,
            location=location,
            event_subtype=HistoryEventSubType.FEE,
            asset=fee.asset,
            amount=fee.amount,
            location_label=location_label,
            notes=None,
            group_identifier=group_identifier,
        ))

    return events


def get_swap_spend_receive_v47_48(
        is_buy: bool,
        base_asset: 'Asset',
        quote_asset: 'Asset',
        amount: 'FVal',
        rate: 'Price',
) -> tuple[AssetAmount, AssetAmount]:
    """Calculates amounts and assets spent and received depending on the is_buy flag.
    Returns the spend asset amount and receive asset amount in a tuple.

    FROZEN: Do not modify. Used for v47->v48 upgrade and data migration 20.
    """
    base = AssetAmount(asset=base_asset, amount=amount)
    quote = AssetAmount(asset=quote_asset, amount=amount * rate)
    return (quote, base) if is_buy else (base, quote)
