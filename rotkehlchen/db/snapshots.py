import logging
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING, List, Optional, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from rotkehlchen.accounting.export.csv import CSVWriteError, _dict_to_csv_file
from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.snapshots import get_main_currency_price

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor

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

    @staticmethod
    def get_timed_balances(
            cursor: 'DBCursor',
            timestamp: Timestamp,
    ) -> List[DBAssetBalance]:
        """Retrieves the timed_balances from the db for a given timestamp."""
        balances_data = []
        cursor.execute(
            'SELECT category, time, amount, currency, usd_value FROM timed_balances '
            'WHERE time=?', (timestamp,),
        )

        for data in cursor:
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

    @staticmethod
    def get_timed_location_data(
            cursor: 'DBCursor',
            timestamp: Timestamp,
    ) -> List[LocationData]:
        """Retrieves the timed_location_data from the db for a given timestamp."""
        location_data = []
        cursor.execute(
            'SELECT time, location, usd_value FROM timed_location_data '
            'WHERE time=?',
            (timestamp,),
        )
        for data in cursor:
            location_data.append(
                LocationData(
                    time=data[0],
                    location=data[1],
                    usd_value=str(FVal(data[2])),
                ),
            )
        return location_data

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
        with self.db.conn.read_ctx() as cursor:
            main_currency, main_currency_price = get_main_currency_price(
                cursor=cursor,
                db=self.db,
                timestamp=timestamp,
                msg_aggregator=self.msg_aggregator,
            )
            timed_balances = self.get_timed_balances(cursor=cursor, timestamp=timestamp)
            timed_location_data = self.get_timed_location_data(cursor=cursor, timestamp=timestamp)

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
            processed_balances_list: List[DBAssetBalance],
            processed_location_data_list: List[LocationData],
    ) -> Tuple[bool, str]:
        """Import the validated snapshot data to the database."""
        with self.db.user_write() as cursor:
            self.add_nft_asset_ids(cursor, [entry.asset.identifier for entry in processed_balances_list])  # noqa: E501
            try:
                self.db.add_multiple_balances(cursor, processed_balances_list)
                self.db.add_multiple_location_data(cursor, processed_location_data_list)
            except InputError as err:
                return False, str(err)

        return True, ''

    def update(
            self,
            timestamp: Timestamp,
            balances_snapshot: List[DBAssetBalance],
            location_data_snapshot: List[LocationData],
    ) -> Tuple[bool, str]:
        """Updates a DB Balance snapshot at a given timestamp."""
        # delete the existing snapshot of that timestamp
        is_success, message = self.delete(timestamp)
        if is_success is False:
            return is_success, message

        # update the snapshot with the provided data.
        is_success, msg = self.import_snapshot(
            processed_balances_list=balances_snapshot,
            processed_location_data_list=location_data_snapshot,
        )
        return is_success, msg

    def delete(self, timestamp: Timestamp) -> Tuple[bool, str]:
        """Deletes a snapshot of the database at a given timestamp"""
        with self.db.user_write() as cursor:
            cursor.execute('DELETE FROM timed_balances WHERE time=?', (timestamp,))
            if cursor.rowcount == 0:
                return False, 'No snapshot found for the specified timestamp'
            cursor.execute('DELETE FROM timed_location_data WHERE time=?', (timestamp,))
            if cursor.rowcount == 0:
                return False, 'No snapshot found for the specified timestamp'

        return True, ''

    def add_nft_asset_ids(self, write_cursor: 'DBCursor', entries: List[str]) -> None:
        """Add NFT identifiers to the DB to prevent unknown asset error."""
        nft_ids = []
        for entry in entries:
            if entry.startswith(NFT_DIRECTIVE):
                nft_ids.append(entry)
        self.db.add_asset_identifiers(write_cursor, nft_ids)
