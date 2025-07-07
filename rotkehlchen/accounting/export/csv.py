"""
CSV Export functionality for accounting events

This module has been temporarily removed as part of the ProcessedAccountingEvent removal.
The CSV export needs to be completely rethought to work with the new system where
history events are decorated with accounting information rather than creating
separate ProcessedAccountingEvent objects.

TODO: Reimplement CSV export to work with HistoryEventWithAccounting
"""
import csv
import json
import logging
import os
from collections.abc import Collection
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.pnl import PnlTotals
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Constants for compatibility
FILENAME_ALL_CSV = 'all_events.csv'
FILENAME_SKIPPED_EXTERNAL_EVENTS_CSV = 'skipped_external_events.csv'


class CSVWriteError(Exception):
    pass


def dict_to_csv_file(
        path: Path,
        dictionary_list: list,
        csv_delimiter: str,
        headers: Collection | None = None,
) -> None:
    """Takes a filepath and a list of dictionaries representing the rows and writes them
    into the file as a CSV

    May raise:
    - CSVWriteError if DictWriter.writerow() tried to write a dict contains
    fields not in fieldnames
    """
    if len(dictionary_list) == 0:
        log.debug(f'Skipping writing empty CSV for {path}')
        return

    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=dictionary_list[0].keys() if headers is None else headers, delimiter=csv_delimiter)  # noqa: E501
        w.writeheader()
        try:
            for dic in dictionary_list:
                w.writerow(dic)
        except ValueError as e:
            raise CSVWriteError(f'Failed to write {path} CSV due to {e!s}') from e

    os.utime(path)


class CSVExporter:
    """Placeholder CSV exporter - functionality removed pending redesign"""

    def __init__(self, database: 'DBHandler'):
        self.database = database
        # Initialize transaction explorers from settings for compatibility
        self.transaction_explorers = self._init_transaction_explorers()
        log.warning('CSV export functionality has been temporarily removed')

    def reset(self, start_ts: Any, end_ts: Any) -> None:
        """Placeholder reset method"""

    def create_zip(self, events: Any, pnls: PnlTotals) -> tuple[bool, str]:
        """Placeholder create_zip method"""
        return False, 'CSV export functionality has been removed and needs to be redesigned'

    def export(self, events: Any, pnls: PnlTotals, directory: Path) -> tuple[bool, str]:
        """Placeholder export method"""
        return False, 'CSV export functionality has been removed and needs to be redesigned'

    def _init_transaction_explorers(self) -> dict[Any, str]:
        """Initialize transaction explorers from frontend settings for compatibility"""
        explorers = {}
        with self.database.conn.read_ctx() as cursor:
            settings = self.database.get_settings(cursor)
            if settings.frontend_settings:
                try:
                    frontend_data = json.loads(settings.frontend_settings)
                    if 'explorers' in frontend_data:
                        for chain_str, chain_data in frontend_data['explorers'].items():
                            try:
                                if chain_str == 'eth':
                                    chain = SupportedBlockchain.ETHEREUM
                                elif chain_str == 'polygon_pos':
                                    chain = SupportedBlockchain.POLYGON_POS
                                else:
                                    # Skip other chains for now
                                    continue

                                if isinstance(chain_data, dict) and 'transaction' in chain_data:
                                    explorers[chain] = chain_data['transaction']
                            except (KeyError, ValueError, TypeError):
                                continue  # Skip problematic chain configs
                except json.JSONDecodeError:
                    pass

        return explorers
