from rotkehlchen.accounting.constants import EVENT_CATEGORY_MAPPINGS
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import (
    HistoryEvent,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.types import Location, TimestampMS


def test_serialize_with_invalid_type_subtype():
    """Test that serialize an event with invalid type/subtype does not raise exception"""
    event_type = HistoryEventType.TRANSFER
    event_subtype = HistoryEventSubType.SPEND
    assert event_subtype not in EVENT_CATEGORY_MAPPINGS[event_type]
    event = HistoryEvent(
        event_identifier='1',
        sequence_index=1,
        timestamp=TimestampMS(1),
        location=Location.KRAKEN,
        event_type=event_type,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        balance=Balance(amount=FVal(1)),
    )
    event.event_subtype = event_subtype  # do here cause ctor will raise for invalid subtype
    assert event.serialize_for_api(
        customized_event_ids=[],
        ignored_ids_mapping={},
        hidden_event_ids=[],
        missing_accounting_rule=True,  # needed to recreate the error thistestsfor
        grouped_events_num=None,
    ) == {
        'entry': {
            'asset': 'ETH',
            'balance': {'amount': '1', 'usd_value': '0'},
            'entry_type': 'history event',
            'event_identifier': '1',
            'event_subtype': 'spend',
            'event_type': 'transfer',
            'identifier': None,
            'location': 'kraken',
            'location_label': None,
            'notes': None,
            'sequence_index': 1,
            'timestamp': 1,
        },
        'missing_accounting_rule': True,
    }
