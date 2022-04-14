from pathlib import Path
from tempfile import mkdtemp
from typing import List, Optional, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from rotkehlchen.accounting.export.csv import CSVWriteError, _dict_to_csv_file
from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.types import Timestamp

BALANCES_FILENAME = 'balances_snapshot.csv'
LOCATION_DATA_FILENAME = 'location_data_snapshot.csv'


class DBSnapshot:
    def __init__(self, db_handler: DBHandler) -> None:
        self.db = db_handler

    def get_timed_balances(self, timestamp: Timestamp) -> List[DBAssetBalance]:
        """Retrieves the timed_balances from the db for a given timestamp"""
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
                    usd_value=data[4],
                ),
            )
        return balances_data

    def get_timed_location_data(self, timestamp: Timestamp) -> List[LocationData]:
        """Retrieves the timed_location_data from the db for a given timestamp"""
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
                    usd_value=data[2],
                ),
            )
        return location_data

    def create_zip(
        self,
        timed_balances: List[DBAssetBalance],
        timed_location_data: List[LocationData],
    ) -> Tuple[bool, str]:
        """Creates a zip file of csv files containing timed_balances and timed_location_data."""
        dirpath = Path(mkdtemp())
        success, msg = self._export(
            timed_balances=timed_balances,
            timed_location_data=timed_location_data,
            directory=dirpath,
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
        """Export the database's snapshot for specified timestamp."""
        timed_balances = self.get_timed_balances(timestamp)
        timed_location_data = self.get_timed_location_data(timestamp)

        if len(timed_balances) == 0 or len(timed_location_data) == 0:
            return False, 'No snapshot data found for the given timestamp.'

        if directory_path is None:
            return self.create_zip(
                timed_balances=timed_balances,
                timed_location_data=timed_location_data,
            )

        return self._export(
            timed_balances=timed_balances,
            timed_location_data=timed_location_data,
            directory=directory_path,
        )

    @staticmethod
    def _export(
        timed_balances: List[DBAssetBalance],
        timed_location_data: List[LocationData],
        directory: Path,
    ) -> Tuple[bool, str]:
        """Serializes the balances and location_data snapshots into a dictionary.
        It then writes the serialized data to a csv file.
        """
        serialized_timed_balances = [balance.serialize() for balance in timed_balances]
        serialized_timed_location_data = [loc_data.serialize() for loc_data in timed_location_data]

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
