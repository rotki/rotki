from rotkehlchen.data_import.importers.binance import BinanceImporter
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
