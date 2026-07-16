from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.constants.assets import A_1INCH, A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.cache import IGNORED_CUSTOMIZED_EVENT_DUPLICATE_PREFIX
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.drivers.sqlite import DBCursor
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.tasks.events import find_customized_event_duplicate_groups
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import Location, TimestampMS

if TYPE_CHECKING:
    from collections.abc import Sequence

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
        mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED},
    )
    assert base_event_id is not None
    return base_event.group_identifier, base_event_id


def test_find_customized_event_duplicate_groups_filters_group_ids_in_sql(
        database: DBHandler,
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


def test_customized_event_deposit(database: DBHandler) -> None:
    """Regression test for customized event depositing in pool

    tx in ethreum 0x1fc371c505230e0a57de8f60100b6e8ebeb64ee73910ed791900f9f719b349b5"""
    with database.conn.write_ctx() as write_cursor:
        database.add_asset_identifiers(
            write_cursor=write_cursor,
            asset_identifiers=[lp_token_identifier := 'eip155:1/erc20:0x812b40c2cA7fAbBAc756475593fC8B1c313434FA'],  # noqa: E501
        )
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[event := EvmEvent(
                tx_ref=(tx_hash := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=(timestamp := TimestampMS(1710000000000)),
                location=Location.ETHEREUM,
                location_label=(location_label := '0x8b878Ee3B32b0dFeA6142F5ca1EfebA8c5dFEc7e'),
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.0217413358'),
                counterparty=CPT_GAS,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=1,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                location_label=location_label,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('0.000048715914954301'),
                address=(contract_address := deserialize_evm_address('0x812b40c2cA7fAbBAc756475593fC8B1c313434FA')),  # noqa: E501
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=2,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                location_label=location_label,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_ETH,
                amount=FVal('0.015198031483172276'),
                address=contract_address,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=261,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                location_label=location_label,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_1INCH,
                amount=FVal('4.013222500944484486'),
                address=contract_address,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=262,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                location_label=location_label,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.APPROVE,
                asset=A_1INCH,
                amount=FVal('999999994.981920004851581951'),
                address=contract_address,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=266,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                location_label=location_label,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=Asset(lp_token_identifier),
                amount=FVal('2.783195823498258841'),
                address=ZERO_ADDRESS,
            ),
        ])
        customized_id = write_cursor.execute(
            'SELECT identifier FROM history_events WHERE group_identifier=? AND sequence_index=?',
            (event.group_identifier, 2),
        ).fetchone()[0]
        write_cursor.execute(
            'INSERT INTO history_events_mappings(parent_identifier, name, value) '
            'VALUES(?, ?, ?)',
            (
                customized_id,
                HISTORY_MAPPING_KEY_STATE,
                HistoryMappingState.CUSTOMIZED.serialize_for_db(),
            ),
        )

    auto_fix_group_ids, manual_review_group_ids, _ = find_customized_event_duplicate_groups(
        database=database,
        group_identifiers=[event.group_identifier],
    )
    assert event.group_identifier not in auto_fix_group_ids
    assert event.group_identifier not in manual_review_group_ids


def test_ignored_groups_excluded_from_detection(database: DBHandler) -> None:
    """Verify that groups marked as ignored in key_value_cache are excluded by the SQL query."""
    with database.conn.write_ctx() as write_cursor:
        group_id_1, _ = _insert_duplicate_group(
            events_db=(events_db := DBHistoryEvents(database)),
            write_cursor=write_cursor,
            timestamp=(timestamp := TimestampMS(1710000000000)),
        )
        group_id_2, _ = _insert_duplicate_group(
            events_db=events_db,
            write_cursor=write_cursor,
            timestamp=timestamp,
        )

    # both groups detected before ignoring
    auto_fix, _, _ = find_customized_event_duplicate_groups(database=database)
    assert group_id_1 in auto_fix
    assert group_id_2 in auto_fix

    # ignore group 1
    with database.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT INTO key_value_cache(name, value) VALUES(?, ?)',
            (f'{IGNORED_CUSTOMIZED_EVENT_DUPLICATE_PREFIX}{group_id_1}', group_id_1),
        )

    auto_fix, _, _ = find_customized_event_duplicate_groups(database=database)
    assert group_id_1 not in auto_fix
    assert group_id_2 in auto_fix

    # un-ignore group 1
    with database.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name=?',
            (f'{IGNORED_CUSTOMIZED_EVENT_DUPLICATE_PREFIX}{group_id_1}',),
        )

    auto_fix, _, _ = find_customized_event_duplicate_groups(database=database)
    assert group_id_1 in auto_fix
    assert group_id_2 in auto_fix
