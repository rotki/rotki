from typing import Dict, NamedTuple, Optional

from rotkehlchen.accounting.structures import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal


class ActionItem(NamedTuple):
    """Action items to propagate to other decoders during decoding"""
    action: str
    sequence_index: int
    from_event_type: HistoryEventType
    from_event_subtype: HistoryEventSubType
    asset: Asset
    amount: FVal
    to_event_type: Optional[HistoryEventType] = None
    to_event_subtype: Optional[HistoryEventSubType] = None
    to_notes: Optional[str] = None
    to_counterparty: Optional[str] = None
    extras: Optional[Dict] = None
