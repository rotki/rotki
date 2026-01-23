from collections.abc import Sequence
from typing import TYPE_CHECKING

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.tasks.events import find_customized_event_duplicate_groups
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _insert_duplicate_group(
        events_db: DBHistoryEvents,
        write_cursor: DBCursor,
        timestamp: TimestampMS,
) -> tuple[str, int]:
    tx_hash = make_evm_tx_hash()
    base_event = EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=ONE,
    )
    customized_event = EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,  # change only the sequence index
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=ONE,
    )
    base_event_id = events_db.add_history_event(write_cursor=write_cursor, event=base_event)
    events_db.add_history_event(
        write_cursor=write_cursor,
        event=customized_event,
        mapping_values={HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED},
    )
    assert base_event_id is not None
    return base_event.group_identifier, base_event_id


def test_find_customized_event_duplicate_groups_filters_group_ids_in_sql(
        database: 'DBHandler',
        monkeypatch,
) -> None:
    """Ensure the group identifier filter is applied in the SQL query."""
    events_db = DBHistoryEvents(database)
    timestamp = TimestampMS(1710000000000)
    with database.conn.write_ctx() as write_cursor:
        group_id_1, _base_id_1 = _insert_duplicate_group(
            events_db=events_db,
            write_cursor=write_cursor,
            timestamp=timestamp,
        )
        _group_id_2, _base_id_2 = _insert_duplicate_group(
            events_db=events_db,
            write_cursor=write_cursor,
            timestamp=timestamp,
        )

    executed: list[tuple[str, tuple[Sequence, ...]]] = []
    original_execute = DBCursor.execute

    def execute_spy(self, statement: str, *bindings: Sequence) -> DBCursor:
        executed.append((statement, bindings))
        return original_execute(self, statement, *bindings)

    monkeypatch.setattr(DBCursor, 'execute', execute_spy)

    find_customized_event_duplicate_groups(
        database=database,
        group_identifiers=[group_id_1],
    )

    matching_statements = [
        (statement, bindings)
        for statement, bindings in executed
        if 'FROM history_events he' in statement
    ]
    assert matching_statements
    assert any(
        'he.group_identifier IN (' in statement
        for statement, _ in matching_statements
    )
    assert any(
        group_id_1 in binding
        for _, bindings in matching_statements
        for binding in bindings
    )
