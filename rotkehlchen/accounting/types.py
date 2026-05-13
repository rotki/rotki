from enum import auto
from typing import Any, NamedTuple

from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.mixins.enums import DBCharEnumMixIn, SerializableEnumNameMixin


class SchemaEventType(DBCharEnumMixIn):
    """Supported Event Type schemas

    Keeping it as this for now since we may experiment with a different schemas
    per accounting event type.
    """
    ACCOUNTING_EVENT = 1

    def get_schema(self) -> dict[str, Any]:
        """May raise EncodingError if schema is invalid"""
        schema: dict[str, Any] = {}
        if self == SchemaEventType.ACCOUNTING_EVENT:
            return schema

        raise AssertionError('Should never happen')


class MissingAcquisition(NamedTuple):
    """Data for a missing acquisition

    originating_event_id is the identifier of the history event that originated it.
    Can be missing since at the moment not all events are history events.

    asset is the asset whose acquisition we can't find

    time is the time of the originating event

    found_amount is the amount needed by the originating event that we have found

    missing_amount is the amount needed by the originating event that we have not found
    """
    originating_event_id: int | None
    asset: Asset
    time: Timestamp
    found_amount: FVal
    missing_amount: FVal

    def serialize(self) -> dict[str, str | int]:
        data = {
            'asset': self.asset.identifier,
            'time': self.time,
            'found_amount': str(self.found_amount),
            'missing_amount': str(self.missing_amount),
        }
        if self.originating_event_id:
            data['originating_event_id'] = self.originating_event_id

        return data  # type: ignore


class MissingPrice(NamedTuple):
    from_asset: Asset
    to_asset: Asset
    time: Timestamp
    rate_limited: bool

    def serialize(self) -> dict[str, str | (int | bool)]:
        return {
            'from_asset': self.from_asset.identifier,
            'to_asset': self.to_asset.identifier,
            'time': self.time,
            'rate_limited': self.rate_limited,
        }


class EventAccountingRuleStatus(SerializableEnumNameMixin):
    HAS_RULE = auto()
    PROCESSED = auto()
    NOT_PROCESSED = auto()
