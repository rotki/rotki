from rotkehlchen.db.filtering import EthDepositEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.eth2 import EthDepositEvent
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import TimestampMS


def make_deposit_event():
    tx_hash = make_evm_tx_hash()
    depositor = make_evm_address()
    return EthDepositEvent(
        identifier=1,
        tx_ref=tx_hash,
        validator_index=42,
        sequence_index=1,
        timestamp=TimestampMS(69000),
        amount=FVal(32),
        depositor=depositor,
    )


def test_db_read_write(database):
    dbevents = DBHistoryEvents(database)
    event = make_deposit_event()

    with database.user_write() as write_cursor:
        dbevents.add_history_event(write_cursor, event)

    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EthDepositEventFilterQuery.make(),
        )
    assert event == events[0]


def test_serialization():
    event = make_deposit_event()
    serialized_event_data = event.serialize()
    assert event == EthDepositEvent.deserialize(serialized_event_data)
