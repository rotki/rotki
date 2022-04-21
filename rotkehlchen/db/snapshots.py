import logging
from pathlib import Path
from tempfile import mkdtemp
from typing import List, Optional, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from rotkehlchen.accounting.export.csv import CSVWriteError, _dict_to_csv_file
from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

BALANCES_FILENAME = 'balances_snapshot.csv'
LOCATION_DATA_FILENAME = 'location_data_snapshot.csv'

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DBSnapshot:
    def __init__(self, db_handler: DBHandler) -> None:
        self.db = db_handler

    def get_timed_balances(
        self,
        timestamp: Timestamp,
        main_currency_price: FVal,
    ) -> List[DBAssetBalance]:
        """Retrieves the timed_balances from the db for a given timestamp
           Sets the usd_value to the value in the main currency
        """
        balances_data = []
        cursor = self.db.conn.cursor()
        timed_balances_result = cursor.execute(
            'SELECT category, time, amount, currency, usd_value FROM timed_balances '
            'WHERE time=?', (timestamp,),
        )

        for data in timed_balances_result:
            balances_data.append(
                DBAssetBalance(
                    category=BalanceType.deserialize_from_db(data[0]),
                    time=data[1],
                    amount=data[2],
                    asset=Asset(data[3]),
                    usd_value=str(FVal(data[4]) * main_currency_price),
                ),
            )
        return balances_data

    def get_timed_location_data(
        self,
        timestamp: Timestamp,
        main_currency_price: FVal,
    ) -> List[LocationData]:
        """Retrieves the timed_location_data from the db for a given timestamp
           Sets the usd_value to the value in the main currency
        """
        location_data = []
        cursor = self.db.conn.cursor()
        timed_location_data = cursor.execute(
            'SELECT time, location, usd_value FROM timed_location_data '
            'WHERE time=?',
            (timestamp,),
        )
        for data in timed_location_data:
            location_data.append(
                LocationData(
                    time=data[0],
                    location=data[1],
                    usd_value=str(FVal(data[2]) * main_currency_price),
                ),
            )
        return location_data

    def create_zip(
        self,
        timed_balances: List[DBAssetBalance],
        timed_location_data: List[LocationData],
        main_currency: Asset,
    ) -> Tuple[bool, str]:
        """Creates a zip file of csv files containing timed_balances and timed_location_data."""
        dirpath = Path(mkdtemp())
        success, msg = self._export(
            timed_balances=timed_balances,
            timed_location_data=timed_location_data,
            directory=dirpath,
            main_currency=main_currency,
        )
        if not success:
            return False, msg

        files: List[Tuple[Path, str]] = [
            (dirpath / BALANCES_FILENAME, BALANCES_FILENAME),
            (dirpath / LOCATION_DATA_FILENAME, LOCATION_DATA_FILENAME),
        ]
        with ZipFile(file=dirpath / 'snapshot.zip', mode='w', compression=ZIP_DEFLATED) as archive:
            for path, filename in files:
                if not path.exists():
                    continue

                archive.write(path, filename)
                path.unlink()

        success = False
        filename = ''
        if archive.filename is not None:
            success = True
            filename = archive.filename

        return success, filename

    def export(self, timestamp: Timestamp, directory_path: Optional[Path]) -> Tuple[bool, str]:
        """Export the database's snapshot for specified timestamp.

        If `directory_path` is provided, the snapshot generated is written to directory.
        Otherwise, a zip file is created and the snapshot generated is written to the file
        and a path to the zip file is returned.
        """
        main_currency = self.db.get_settings().main_currency
        try:
            main_currency_price = PriceHistorian.query_historical_price(
                from_asset=A_USD,
                to_asset=main_currency,
                timestamp=timestamp,
            )
        except NoPriceForGivenTimestamp:
            manual_prices = GlobalDBHandler.get_manual_prices(
                from_asset=A_USD,
                to_asset=main_currency,
            )
            if len(manual_prices) == 0:
                main_currency_price = Price(ONE)
                MessagesAggregator().add_error(
                    f'Could not find price for timestamp {timestamp}. Using USD for export. '
                    f'Please add manual price from USD to your main currency {main_currency}',
                )
            else:
                best_price = min(manual_prices, key=lambda x: abs(Timestamp(int(x['timestamp'])) - timestamp))  # noqa: E501
                log.info(f'Used manual price {best_price} for {main_currency} - {timestamp}')
                main_currency_price = Price(FVal(best_price['price']))

        timed_balances = self.get_timed_balances(
            timestamp=timestamp,
            main_currency_price=main_currency_price,
        )
        timed_location_data = self.get_timed_location_data(
            timestamp=timestamp,
            main_currency_price=main_currency_price,
        )

        if len(timed_balances) == 0 or len(timed_location_data) == 0:
            return False, 'No snapshot data found for the given timestamp.'

        if directory_path is None:
            return self.create_zip(
                timed_balances=timed_balances,
                timed_location_data=timed_location_data,
                main_currency=main_currency,
            )

        return self._export(
            timed_balances=timed_balances,
            timed_location_data=timed_location_data,
            directory=directory_path,
            main_currency=main_currency,
        )

    @staticmethod
    def _export(
        timed_balances: List[DBAssetBalance],
        timed_location_data: List[LocationData],
        directory: Path,
        main_currency: Asset,
    ) -> Tuple[bool, str]:
        """Serializes the balances and location_data snapshots into a dictionary.
        It then writes the serialized data to a csv file.
        """
        serialized_timed_balances = [balance.serialize(currency=main_currency) for balance in timed_balances]  # noqa: E501
        serialized_timed_location_data = [loc_data.serialize(currency=main_currency) for loc_data in timed_location_data]  # noqa: E501

        try:
            directory.mkdir(parents=True, exist_ok=True)
            _dict_to_csv_file(
                directory / BALANCES_FILENAME,
                serialized_timed_balances,
            )
            _dict_to_csv_file(
                directory / LOCATION_DATA_FILENAME,
                serialized_timed_location_data,
            )
        except (CSVWriteError, PermissionError) as e:
            return False, str(e)

        return True, ''
