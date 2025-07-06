from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import BCH_BSV_FORK_TS, BTC_BCH_FORK_TS, ETH_DAO_FORK_TS
from rotkehlchen.constants.assets import A_BCH, A_BSV, A_BTC, A_ETC, A_ETH
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import Location, Price, Timestamp, TimestampMS

if TYPE_CHECKING:
    from .base import CostBasisCalculator


def handle_prefork_asset_acquisitions(
        cost_basis: 'CostBasisCalculator',
        location: Location,
        timestamp: Timestamp,
        asset: Asset,
        amount: FVal,
        price: Price,
        ignored_asset_ids: set[str],
        event_count: int,
        database: Any,
) -> list[HistoryEvent]:
    """
        Calculate the prefork asset acquisitions, meaning how is the acquisition
        of ETC pre ETH fork handled etc.

        TODO: This should change for https://github.com/rotki/rotki/issues/1610

        Returns the acquisition events to append to the pot
    """
    acquisitions = []
    if asset == A_ETH and timestamp < ETH_DAO_FORK_TS:
        acquisitions = [(A_ETC, 'Prefork acquisition for ETC')]
    elif asset == A_BTC and timestamp < BTC_BCH_FORK_TS:
        # Acquiring BTC before the BCH fork provides equal amount of BCH and BSV
        acquisitions = [
            (A_BCH, 'Prefork acquisition for BCH'),
            (A_BSV, 'Prefork acquisition for BSV'),
        ]
    elif asset == A_BCH and timestamp < BCH_BSV_FORK_TS:
        # Acquiring BCH before the BSV fork provides equal amount of BSV
        acquisitions = [(A_BSV, 'Prefork acquisition for BSV')]

    events = []
    for acquisition in acquisitions:
        if acquisition[0].identifier in ignored_asset_ids:
            continue

        # Create a history event for the prefork acquisition
        history_event = HistoryEvent(
            event_identifier=f'prefork_{event_count}',
            sequence_index=0,
            timestamp=TimestampMS(timestamp * 1000),  # Convert to milliseconds
            location=location,
            location_label=f'{AccountingEventType.PREFORK_ACQUISITION.serialize()}',
            asset=acquisition[0],
            amount=amount,
            notes=acquisition[1],
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            extra_data={'prefork_acquisition': True},
        )

        # Add to database
        with database.user_write() as write_cursor:
            dbevents = DBHistoryEvents(database)
            history_event.identifier = dbevents.add_history_event(write_cursor, history_event)

        # TODO: Update cost basis to work with HistoryEvent instead of ProcessedAccountingEvent

        events.append(history_event)
        event_count += 1

    return events


def handle_prefork_asset_spends(
        originating_event_id: int | None,
        cost_basis: 'CostBasisCalculator',
        asset: Asset,
        amount: FVal,
        timestamp: Timestamp,
) -> None:
    """
    Calculate the prefork asset spends, meaning the opposite of
    handle_prefork_asset_acquisitions

    TODO: This should change for https://github.com/rotki/rotki/issues/1610
    """
    # For now for those don't use inform_user_missing_acquisition since if those hit
    # the preforked asset acquisition data is what's missing so user would getLogger
    # two messages. So as an example one for missing ETH data and one for ETC data
    if asset == A_ETH and timestamp < ETH_DAO_FORK_TS:
        cost_basis.reduce_asset_amount(
            originating_event_id=originating_event_id,
            asset=A_ETC,
            amount=amount,
            timestamp=timestamp,
        )

    if asset == A_BTC and timestamp < BTC_BCH_FORK_TS:
        cost_basis.reduce_asset_amount(
            originating_event_id=originating_event_id,
            asset=A_BCH,
            amount=amount,
            timestamp=timestamp,
        )
        cost_basis.reduce_asset_amount(
            originating_event_id=originating_event_id,
            asset=A_BSV,
            amount=amount,
            timestamp=timestamp,
        )

    if asset == A_BCH and timestamp < BCH_BSV_FORK_TS:
        cost_basis.reduce_asset_amount(
            originating_event_id=originating_event_id,
            asset=A_BSV,
            amount=amount,
            timestamp=timestamp,
        )
