from unittest.mock import Mock

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ONE
from rotkehlchen.data_import.importers.binance import (
    INDEX,
    BinanceDistributionEntry,
    BinanceImporter,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import Timestamp, Timezone


def _binance_row(timestamp: str) -> dict[str, str]:
    return {
        'UTC_Time': timestamp,
        'Account': 'Spot',
        'Operation': 'Deposit',
        'Coin': 'BTC',
        'Change': '1',
        'Remark': '',
    }


def test_binance_import_groups_rows_with_default_timezone() -> None:
    """Test Binance import keeps interpreting timestamps as UTC by default."""
    _, grouped_rows = BinanceImporter._group_binance_rows(
        self=object.__new__(BinanceImporter),
        rows=[_binance_row('2024-01-01 12:00:00')],
    )
    assert list(grouped_rows.keys()) == [Timestamp(1704110400)]


def test_binance_import_groups_rows_with_timezone() -> None:
    """Test Binance import interprets naive timestamps with the provided timezone."""
    _, grouped_rows = BinanceImporter._group_binance_rows(
        self=object.__new__(BinanceImporter),
        rows=[_binance_row('2024-07-01 12:00:00')],
        timezone=Timezone('Europe/Madrid'),
    )
    assert list(grouped_rows.keys()) == [Timestamp(1719828000)]


@pytest.mark.parametrize(('operation', 'change', 'remark', 'event_type', 'event_subtype'), [
    (
        'Asset - Transfer',
        '0.00004601',
        'NEO GAS 分发',
        HistoryEventType.RECEIVE,
        HistoryEventSubType.REWARD,
    ), (
        'Asset - Transfer',
        '0.000087',
        'NEO空投ONT第一批 (比例1:0.1)',
        HistoryEventType.RECEIVE,
        HistoryEventSubType.AIRDROP,
    ),
    ('Distribution', '0.00000606', '', HistoryEventType.RECEIVE, HistoryEventSubType.REWARD),
    ('Airdrop Assets', '0.00009144', '', HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP),
    ('Asset Recovery', '-0.000973', '', HistoryEventType.SPEND, HistoryEventSubType.NONE),
    (
        'Token Swap - Distribution',
        '0.14144501',
        '',
        HistoryEventType.RECEIVE,
        HistoryEventSubType.NONE,
    ),
])
def test_binance_import_single_row_distributions_and_adjustments(
        operation: str,
        change: str,
        remark: str,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
) -> None:
    """Test standalone Binance distributions and balance adjustments are imported."""
    importer = Mock(spec=BinanceImporter)
    skipped_count, processed, ignored = BinanceImporter._process_single_binance_entries(
        self=importer,
        write_cursor=Mock(),
        timestamp=Timestamp(1700000000),
        rows=[{
            'UTC_Time': '2023-11-14 22:13:20',
            'Account': 'Spot',
            'Operation': operation,
            'Coin': Asset('GAS'),
            'Change': FVal(change),
            'Remark': remark,
            INDEX: 1,
        }],
    )

    assert skipped_count == 0
    assert sum(processed.values()) == 1
    assert ignored == []
    event = importer.add_history_events.call_args.kwargs['history_events'][0]
    assert event.event_type == event_type
    assert event.event_subtype == event_subtype
    assert event.amount == abs(FVal(change))


def test_binance_import_does_not_treat_generic_asset_transfer_as_reward() -> None:
    """Test only explicitly identified legacy distributions are treated as rewards."""
    assert BinanceDistributionEntry().is_entry(
        requested_operation='Asset - Transfer',
        account='Spot',
        change=ONE,
        remark='',
    ) is False
