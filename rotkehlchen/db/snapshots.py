import logging
from csv import DictReader
from pathlib import Path
from tempfile import mkdtemp
from typing import Dict, List, Optional, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from rotkehlchen.accounting.export.csv import CSVWriteError, _dict_to_csv_file
from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import Location, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

BALANCES_FILENAME = 'balances_snapshot.csv'
BALANCES_FOR_IMPORT_FILENAME = 'balances_snapshot_import.csv'
LOCATION_DATA_FILENAME = 'location_data_snapshot.csv'
LOCATION_DATA_IMPORT_FILENAME = 'location_data_snapshot_import.csv'

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DBSnapshot:
    def __init__(self, db_handler: DBHandler, msg_aggregator: MessagesAggregator) -> None:
        self.db = db_handler
        self.msg_aggregator = msg_aggregator

    def get_timed_balances(
        self,
        timestamp: Timestamp,
    ) -> List[DBAssetBalance]:
        """Retrieves the timed_balances from the db for a given timestamp."""
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
                    usd_value=str(FVal(data[4])),
                ),
            )
        return balances_data

    def get_timed_location_data(
        self,
        timestamp: Timestamp,
    ) -> List[LocationData]:
        """Retrieves the timed_location_data from the db for a given timestamp."""
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
                    usd_value=str(FVal(data[2])),
                ),
            )
        return location_data

    def get_main_currency_price(self, timestamp: Timestamp) -> Tuple[Asset, Price]:
        """Gets the main currency and its equivalent price at a particular timestamp."""
        main_currency = self.db.get_main_currency()
        main_currency_price = None
        try:
            main_currency_price = PriceHistorian.query_historical_price(
                from_asset=A_USD,
                to_asset=main_currency,
                timestamp=timestamp,
            )
        except NoPriceForGivenTimestamp:
            main_currency_price = Price(ONE)
            self.msg_aggregator.add_error(
                f'Could not find price for timestamp {timestamp}. Using USD for export. '
                f'Please add manual price from USD to your main currency {main_currency}',
            )
        return main_currency, main_currency_price

    @staticmethod
    def _csv_to_dict(file: Path) -> List[Dict[str, str]]:
        """Converts a csv file to a list of dictionary."""
        with open(file, mode='r') as csv_file:
            csv_reader = DictReader(csv_file)
            return list(csv_reader)

    def create_zip(
        self,
        timed_balances: List[DBAssetBalance],
        timed_location_data: List[LocationData],
        main_currency: Asset,
        main_currency_price: Price,
    ) -> Tuple[bool, str]:
        """Creates a zip file of csv files containing timed_balances and timed_location_data."""
        dirpath = Path(mkdtemp())
        success, msg = self._export(
            timed_balances=timed_balances,
            timed_location_data=timed_location_data,
            directory=dirpath,
            main_currency=main_currency,
            main_currency_price=main_currency_price,
        )
        if not success:
            return False, msg

        files: List[Tuple[Path, str]] = [
            (dirpath / BALANCES_FILENAME, BALANCES_FILENAME),
            (dirpath / BALANCES_FOR_IMPORT_FILENAME, BALANCES_FOR_IMPORT_FILENAME),
            (dirpath / LOCATION_DATA_FILENAME, LOCATION_DATA_FILENAME),
            (dirpath / LOCATION_DATA_IMPORT_FILENAME, LOCATION_DATA_IMPORT_FILENAME),
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

    def export(
        self,
        timestamp: Timestamp,
        directory_path: Optional[Path],
    ) -> Tuple[bool, str]:
        """Export the database's snapshot for specified timestamp.

        If `directory_path` is provided, the snapshot generated is written to directory.
        Otherwise, a zip file is created and the snapshot generated is written to the file
        and a path to the zip file is returned.
        """
        main_currency, main_currency_price = self.get_main_currency_price(timestamp)
        timed_balances = self.get_timed_balances(timestamp=timestamp)
        timed_location_data = self.get_timed_location_data(timestamp=timestamp)

        if len(timed_balances) == 0 or len(timed_location_data) == 0:
            return False, 'No snapshot data found for the given timestamp.'

        if directory_path is None:
            return self.create_zip(
                timed_balances=timed_balances,
                timed_location_data=timed_location_data,
                main_currency=main_currency,
                main_currency_price=main_currency_price,
            )

        return self._export(
            timed_balances=timed_balances,
            timed_location_data=timed_location_data,
            directory=directory_path,
            main_currency=main_currency,
            main_currency_price=main_currency_price,
        )

    @staticmethod
    def _export(
        timed_balances: List[DBAssetBalance],
        timed_location_data: List[LocationData],
        directory: Path,
        main_currency: Asset,
        main_currency_price: Price,
    ) -> Tuple[bool, str]:
        """Serializes the balances and location_data snapshots into a dictionary.
        It then writes the serialized data to a csv file.
        """
        serialized_timed_balances = [balance.serialize(export_data=(main_currency, main_currency_price)) for balance in timed_balances]  # noqa: E501
        serialized_timed_balances_for_import = [balance.serialize() for balance in timed_balances]
        serialized_timed_location_data = [loc_data.serialize(export_data=(main_currency, main_currency_price)) for loc_data in timed_location_data]  # noqa: E501
        serialized_timed_location_data_for_import = [loc_data.serialize() for loc_data in timed_location_data]  # noqa: E501

        try:
            directory.mkdir(parents=True, exist_ok=True)
            _dict_to_csv_file(
                directory / BALANCES_FILENAME,
                serialized_timed_balances,
            )
            _dict_to_csv_file(
                directory / BALANCES_FOR_IMPORT_FILENAME,
                serialized_timed_balances_for_import,
            )
            _dict_to_csv_file(
                directory / LOCATION_DATA_FILENAME,
                serialized_timed_location_data,
            )
            _dict_to_csv_file(
                directory / LOCATION_DATA_IMPORT_FILENAME,
                serialized_timed_location_data_for_import,
            )
        except (CSVWriteError, PermissionError) as e:
            return False, str(e)

        return True, ''

    def import_snapshot(
        self,
        balances_snapshot_file: Path,
        location_data_snapshot_file: Path,
    ) -> Tuple[bool, str]:
        """
        Converts the snapshot files to list to dictionaries.
        Performs a series of validation checks on the list before importing.
        """
        balances_list = self._csv_to_dict(balances_snapshot_file)
        location_data_list = self._csv_to_dict(location_data_snapshot_file)
        # check if the headers match the type stored in the db
        has_invalid_headers = (
            tuple(balances_list[0].keys()) != ('timestamp', 'category', 'asset_identifier', 'amount', 'usd_value') or  # noqa: E501
            tuple(location_data_list[0].keys()) != ('timestamp', 'location', 'usd_value')  # noqa: E501
        )
        if has_invalid_headers:
            return False, 'csv file has invalid headers'

        # check if all timestamps are the same.
        balances_timestamps = [int(entry['timestamp']) for entry in balances_list]
        location_data_timestamps = [int(entry['timestamp']) for entry in location_data_list]
        has_different_timestamps = (
            balances_timestamps.count(balances_timestamps[0]) != len(balances_timestamps) or
            location_data_timestamps.count(location_data_timestamps[0]) != len(location_data_timestamps) or  # noqa: E501
            balances_timestamps[0] != location_data_timestamps[0]
        )
        if has_different_timestamps:
            return False, 'csv file has different timestamps'

        # check if the timestamp can be converted to int
        try:
            _ = deserialize_timestamp(balances_list[0]['timestamp'])
        except DeserializationError:
            return False, 'csv file contains invalid timestamp format'

        return self._import_snapshot(
            balances_list=balances_list,
            location_data_list=location_data_list,
        )

    def _import_snapshot(
        self,
        balances_list: List[Dict[str, str]],
        location_data_list: List[Dict[str, str]],
    ) -> Tuple[bool, str]:
        """Import the validated snapshot data to the database."""
        processed_balances_list = []
        processed_location_data_list = []
        try:
            for entry in balances_list:
                if entry['asset_identifier'].startswith(NFT_DIRECTIVE):
                    self.db.add_asset_identifiers([entry['asset_identifier']])

                processed_balances_list.append(
                    DBAssetBalance(
                        category=BalanceType.deserialize(entry['category']),
                        time=Timestamp(int(entry['timestamp'])),
                        asset=Asset(identifier=entry['asset_identifier']),
                        amount=entry['amount'],
                        usd_value=str(FVal(entry['usd_value'])),
                    ),
                )
        except UnknownAsset as err:
            return False, f'snapshot contains an unknown asset ({err.asset_name}). Try adding this asset manually.'  # noqa: 501

        for entry in location_data_list:
            processed_location_data_list.append(
                LocationData(
                    time=Timestamp(int(entry['timestamp'])),
                    location=Location.deserialize(entry['location']).serialize_for_db(),
                    usd_value=str(FVal(entry['usd_value'])),
                ),
            )
        try:
            self.db.add_multiple_balances(processed_balances_list)
            self.db.add_multiple_location_data(processed_location_data_list)
        except InputError as err:
            return False, str(err)
        return True, ''

    def delete(self, timestamp: Timestamp) -> Tuple[bool, str]:
        """Deletes a snapshot of the database at a given timestamp"""
        cursor = self.db.conn.cursor()
        cursor.execute('DELETE FROM timed_balances WHERE time=?', (timestamp,))
        if cursor.rowcount == 0:
            return False, 'No snapshot found for the specified timestamp'
        cursor.execute('DELETE FROM timed_location_data WHERE time=?', (timestamp,))
        if cursor.rowcount == 0:
            self.db.conn.rollback()
            return False, 'No snapshot found for the specified timestamp'
        self.db.update_last_write()
        return True, ''
