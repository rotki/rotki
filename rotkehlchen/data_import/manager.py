from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.data_import.importers.binance import BinanceImporter
from rotkehlchen.data_import.importers.bisq_trades import BisqTradesImporter
from rotkehlchen.data_import.importers.bitcoin_tax import BitcoinTaxImporter
from rotkehlchen.data_import.importers.bitmex import BitMEXImporter
from rotkehlchen.data_import.importers.bitstamp import BitstampTransactionsImporter
from rotkehlchen.data_import.importers.bittrex import BittrexImporter
from rotkehlchen.data_import.importers.blockfi_trades import BlockfiTradesImporter
from rotkehlchen.data_import.importers.blockfi_transactions import BlockfiTransactionsImporter
from rotkehlchen.data_import.importers.blockpit import BlockpitImporter
from rotkehlchen.data_import.importers.cointracking import CointrackingImporter
from rotkehlchen.data_import.importers.cryptocom import CryptocomImporter
from rotkehlchen.data_import.importers.kucoin import KucoinImporter
from rotkehlchen.data_import.importers.nexo import NexoImporter
from rotkehlchen.data_import.importers.rotki_events import RotkiGenericEventsImporter
from rotkehlchen.data_import.importers.rotki_trades import RotkiGenericTradesImporter
from rotkehlchen.data_import.importers.shapeshift_trades import ShapeshiftTradesImporter
from rotkehlchen.data_import.importers.uphold_transactions import UpholdTransactionsImporter
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin

if TYPE_CHECKING:
    from rotkehlchen.data_import.utils import BaseExchangeImporter


class DataImportSource(SerializableEnumNameMixin):
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
    BITCOIN_TAX = 12
    BITMEX_WALLET_HISTORY = 13
    BITSTAMP = 14
    BITTREX = 15
    KUCOIN = 16
    BLOCKPIT = 17


class CSVDataImporter:
    """This class is responsible for importation of csv files."""
    def __init__(self, db: DBHandler):
        self.db = db

    def import_csv(
            self,
            source: DataImportSource,
            filepath: Path,
            **kwargs: Any,
    ) -> tuple[bool, str]:
        """Imports csv data from `filepath`.`source` determines the format of the file.
        Returns (True, '') if imported successfully and (False, message) otherwise."""
        importer: BaseExchangeImporter

        if source == DataImportSource.COINTRACKING:
            importer = CointrackingImporter(db=self.db)
        elif source == DataImportSource.CRYPTOCOM:
            importer = CryptocomImporter(db=self.db)
        elif source == DataImportSource.BLOCKFI_TRANSACTIONS:
            importer = BlockfiTransactionsImporter(db=self.db)
        elif source == DataImportSource.BLOCKFI_TRADES:
            importer = BlockfiTradesImporter(db=self.db)
        elif source == DataImportSource.NEXO:
            importer = NexoImporter(db=self.db)
        elif source == DataImportSource.SHAPESHIFT_TRADES:
            importer = ShapeshiftTradesImporter(db=self.db)
        elif source == DataImportSource.UPHOLD_TRANSACTIONS:
            importer = UpholdTransactionsImporter(db=self.db)
        elif source == DataImportSource.BISQ_TRADES:
            importer = BisqTradesImporter(db=self.db)
        elif source == DataImportSource.BINANCE:
            importer = BinanceImporter(db=self.db)
        elif source == DataImportSource.ROTKI_TRADES:
            importer = RotkiGenericTradesImporter(db=self.db)
        elif source == DataImportSource.ROTKI_EVENTS:
            importer = RotkiGenericEventsImporter(db=self.db)
        elif source == DataImportSource.BITCOIN_TAX:
            importer = BitcoinTaxImporter(db=self.db)
        elif source == DataImportSource.BITMEX_WALLET_HISTORY:
            importer = BitMEXImporter(db=self.db)
        elif source == DataImportSource.BITSTAMP:
            importer = BitstampTransactionsImporter(db=self.db)
        elif source == DataImportSource.BITTREX:
            importer = BittrexImporter(db=self.db)
        elif source == DataImportSource.KUCOIN:
            importer = KucoinImporter(db=self.db)
        elif source == DataImportSource.BLOCKPIT:
            importer = BlockpitImporter(db=self.db)
        else:
            raise AssertionError(f'Unknown DataImportSource value {source}')

        success, msg = importer.import_csv(filepath=filepath, **kwargs)
        return success, msg
