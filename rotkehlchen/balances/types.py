from dataclasses import dataclass

from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.filtering import (
    HistoryEventFilterQuery,
    HistoryEventWithCounterpartyFilterQuery,
)
from rotkehlchen.types import Location, Timestamp


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class HistoricalBalancesParams:
    from_timestamp: Timestamp | None = None
    to_timestamp: Timestamp | None = None
    assets: tuple[Asset, ...] | None = None
    location: Location | None = None
    location_label: str | None = None
    protocol: str | None = None

    def make_history_event_filter_query(
            self,
    ) -> HistoryEventFilterQuery | HistoryEventWithCounterpartyFilterQuery:
        if self.protocol is None:
            return HistoryEventFilterQuery.make(
                from_ts=self.from_timestamp,
                to_ts=self.to_timestamp,
                order_by_rules=[('timestamp', True), ('sequence_index', True)],
                exclude_ignored_assets=True,
                assets=self.assets,
                location=self.location,
                location_labels=[self.location_label] if self.location_label is not None else None,
            )

        return HistoryEventWithCounterpartyFilterQuery.make(
            from_ts=self.from_timestamp,
            to_ts=self.to_timestamp,
            order_by_rules=[('timestamp', True), ('sequence_index', True)],
            exclude_ignored_assets=True,
            assets=self.assets,
            location=self.location,
            location_labels=[self.location_label] if self.location_label is not None else None,
            counterparties=[self.protocol],
        )
