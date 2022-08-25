from pathlib import Path
from typing import Any, Tuple, Type

from rotkehlchen.data_import.importers.binance import BinanceImporter
from rotkehlchen.data_import.importers.bisq_trades import BisqTradesImporter
from rotkehlchen.data_import.importers.blockfi_trades import BlockfiTradesImporter
from rotkehlchen.data_import.importers.blockfi_transactions import BlockfiTransactionsImporter
from rotkehlchen.data_import.importers.cointracking import CointrackingImporter
from rotkehlchen.data_import.importers.cryptocom import CryptocomImporter
from rotkehlchen.data_import.importers.nexo import NexoImporter
from rotkehlchen.data_import.importers.rotki_events import RotkiGenericEventsImporter
from rotkehlchen.data_import.importers.rotki_trades import RotkiGenericTradesImporter
from rotkehlchen.data_import.importers.shapeshift_trades import ShapeshiftTradesImporter
from rotkehlchen.data_import.importers.uphold_transactions import UpholdTransactionsImporter
from rotkehlchen.data_import.utils import BaseExchangeImporter
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin


class DataImportSource(SerializableEnumMixin):
    COINTRACKING = 1
    CRYPTOCOM = 2
    BLOCKFI_TRANSACTIONS = 3
    BLOCKFI_TRADES = 4
    NEXO = 5
    SHAPESHIFT_TRADES = 6
    UPHOLD_TRANSACTIONS = 7
    BISQ_TRADES = 8
    BINANCE = 9
    ROTKI_TRADES = 10
    ROTKI_EVENTS = 11

    def get_importer_type(self) -> Type[BaseExchangeImporter]:
        if self == DataImportSource.COINTRACKING:
            return CointrackingImporter
        if self == DataImportSource.CRYPTOCOM:
            return CryptocomImporter
        if self == DataImportSource.BLOCKFI_TRANSACTIONS:
            return BlockfiTransactionsImporter
        if self == DataImportSource.BLOCKFI_TRADES:
            return BlockfiTradesImporter
        if self == DataImportSource.NEXO:
            return NexoImporter
        if self == DataImportSource.SHAPESHIFT_TRADES:
            return ShapeshiftTradesImporter
        if self == DataImportSource.UPHOLD_TRANSACTIONS:
            return UpholdTransactionsImporter
        if self == DataImportSource.BISQ_TRADES:
            return BisqTradesImporter
        if self == DataImportSource.BINANCE:
            return BinanceImporter
        if self == DataImportSource.ROTKI_TRADES:
            return RotkiGenericTradesImporter
        if self == DataImportSource.ROTKI_EVENTS:
            return RotkiGenericEventsImporter
        raise AssertionError(f'Unknown DataImportSource value {self}')


class CSVDataImporter:
    """This class is responsible for importation of csv files."""
    def __init__(self, db: DBHandler):
        self.db = db

    def import_csv(
            self,
            source: DataImportSource,
            filepath: Path,
            **kwargs: Any,
    ) -> Tuple[bool, str]:
        """Imports csv data from `filepath`.`source` determines the format of the file.
        Returns (True, '') if imported successfully and (False, message) otherwise."""
        importer_type = source.get_importer_type()
        importer = importer_type(db=self.db)
        success, msg = importer.import_csv(filepath=filepath, **kwargs)
        return success, msg
