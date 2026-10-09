"""Test for data migration 29 - repair of the Hyperliquid Core history."""
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.evm.constants import ZERO_32_BYTES_HEX
from rotkehlchen.constants.assets import A_USDC
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.tests.utils.data_migrations import run_single_migration
from rotkehlchen.types import Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.mark.parametrize('data_migration_version', [28])
def test_migration_29_resets_hyperliquid_core_history_ranges(database: DBHandler) -> None:
    """Only the Hyperliquid Core history ranges are removed, so it is all queried again."""
    with database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO used_query_ranges(name, start_ts, end_ts) VALUES(?, ?, ?)',
            [
                ('hyperliquid_core_history_0x000000000000000000000000000000000000dEaD', 0, 10),
                ('hyperliquid_core_history_0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c', 5, 20),
                ('hyperliquidXcoreXhistory_0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c', 5, 20),
                ('kraken_history_events_kraken', 0, 10),
            ],
        )

    run_single_migration(database=database, migration=29)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT name FROM used_query_ranges ORDER BY name').fetchall() == [
            ('hyperliquidXcoreXhistory_0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c',),
            ('kraken_history_events_kraken',),
        ]


@pytest.mark.parametrize('data_migration_version', [28])
def test_migration_29_removes_the_zero_hash_funding_event(database: DBHandler) -> None:
    """The funding event saved under the zero hash group is removed unless customized.
    Other Hyperliquid events are kept."""
    zero_hash_group = create_group_identifier_from_unique_id(
        location=Location.HYPERLIQUID,
        unique_id=ZERO_32_BYTES_HEX,
    )
    history_db = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        for group_identifier, sequence_index in ((zero_hash_group, 0), (zero_hash_group, 1), ('other', 0)):  # noqa: E501
            history_db.add_history_event(write_cursor=write_cursor, event=HistoryEvent(
                group_identifier=group_identifier,
                sequence_index=sequence_index,
                timestamp=TimestampMS(1762300800000),
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.INTEREST,
                asset=A_USDC,
                amount=ONE,
                notes='Hyperliquid funding payment',
            ), mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED} if sequence_index == 1 else None)  # noqa: E501

    run_single_migration(database=database, migration=29)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT group_identifier, sequence_index FROM history_events ORDER BY sequence_index, group_identifier',  # noqa: E501
        ).fetchall() == [('other', 0), (zero_hash_group, 1)]
