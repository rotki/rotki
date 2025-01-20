import logging
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED, ZipFile

from rotkehlchen.accounting.export.csv import CSVWriteError, dict_to_csv_file
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.snapshots import get_main_currency_price

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.client import DBCursor, DBWriterClient

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
            cursor: 'DBCursor',
            timestamp: Timestamp,
    ) -> list[DBAssetBalance]:
        """Retrieves the timed_balances from the db for a given timestamp."""
        balances_data = []
        cursor.execute(
            'SELECT category, timestamp, currency, amount, usd_value FROM timed_balances '
            'WHERE timestamp=?', (timestamp,),
        )

        for data in cursor:
            try:
                balances_data.append(DBAssetBalance.deserialize_from_db(data))
            except UnknownAsset as e:
                self.msg_aggregator.add_error(
                    f'Failed to include balance for asset {data[2]}. Verify that the '
                    f'asset is in your list of known assets. Skipping this entry. {e!s}',
                )
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Failed to read location {data[0]} during balances retrieval.'
                    f'Skipping. {e!s}',
                )
        return balances_data

    @staticmethod
    def get_timed_location_data(
            cursor: 'DBCursor',
            timestamp: Timestamp,
    ) -> list[LocationData]:
        """Retrieves the timed_location_data from the db for a given timestamp."""
        cursor.execute(
            'SELECT timestamp, location, usd_value FROM timed_location_data '
            'WHERE timestamp=?',
            (timestamp,),
        )
        return [LocationData(
            time=data[0],
            location=data[1],
            usd_value=str(FVal(data[2])),
        ) for data in cursor]

    def create_zip(
            self,
            timed_balances: list[DBAssetBalance],
            timed_location_data: list[LocationData],
            main_currency: AssetWithOracles,
            main_currency_price: Price,
    ) -> tuple[bool, str]:
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

        files: list[tuple[Path, str]] = [
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
            directory_path: Path | None,
    ) -> tuple[bool, str]:
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

    def _export(
            self,
            timed_balances: list[DBAssetBalance],
            timed_location_data: list[LocationData],
            directory: Path,
            main_currency: AssetWithOracles,
            main_currency_price: Price,
    ) -> tuple[bool, str]:
        """Serializes the balances and location_data snapshots into a dictionary.
        It then writes the serialized data to a csv file.
        """
        settings = CachedSettings().get_settings()

        serialized_timed_balances = []
        for balance in timed_balances:
            serialized_timed_balance = balance.serialize(
                currency_and_price=(main_currency, main_currency_price),
                display_date_in_localtime=settings.display_date_in_localtime,
            )
            serialized_timed_balances.append(serialized_timed_balance)

        serialized_timed_balances_for_import = [balance.serialize() for balance in timed_balances]
        serialized_timed_location_data = [
            loc_data.serialize(
                currency_and_price=(main_currency, main_currency_price),
                display_date_in_localtime=settings.display_date_in_localtime,
            )
            for loc_data in timed_location_data
        ]
        serialized_timed_location_data_for_import = [loc_data.serialize() for loc_data in timed_location_data]  # noqa: E501

        try:
            directory.mkdir(parents=True, exist_ok=True)
            dict_to_csv_file(
                path=directory / BALANCES_FILENAME,
                dictionary_list=serialized_timed_balances,
                csv_delimiter=settings.csv_export_delimiter,
            )
            dict_to_csv_file(
                path=directory / BALANCES_FOR_IMPORT_FILENAME,
                dictionary_list=serialized_timed_balances_for_import,
                csv_delimiter=settings.csv_export_delimiter,
            )
            dict_to_csv_file(
                path=directory / LOCATION_DATA_FILENAME,
                dictionary_list=serialized_timed_location_data,
                csv_delimiter=settings.csv_export_delimiter,
            )
            dict_to_csv_file(
                path=directory / LOCATION_DATA_IMPORT_FILENAME,
                dictionary_list=serialized_timed_location_data_for_import,
                csv_delimiter=settings.csv_export_delimiter,
            )
        except (CSVWriteError, PermissionError) as e:
            return False, str(e)

        return True, ''

    def import_snapshot(
            self,
            write_cursor: 'DBWriterClient',
            processed_balances_list: list[DBAssetBalance],
            processed_location_data_list: list[LocationData],
    ) -> None:
        """Import the validated snapshot data to the database.
        May raise:
        - InputError if any timed location data is already present in the database, or any timed
          balance is already present in the database or contains an unknown asset.
        """
        self.add_nft_asset_ids(
            write_cursor=write_cursor,
            entries=[entry.asset.identifier for entry in processed_balances_list],
        )
        self.db.add_multiple_balances(write_cursor, processed_balances_list)
        self.db.add_multiple_location_data(write_cursor, processed_location_data_list)

    def update(
            self,
            write_cursor: 'DBWriterClient',
            timestamp: Timestamp,
            balances_snapshot: list[DBAssetBalance],
            location_data_snapshot: list[LocationData],
    ) -> None:
        """Updates a DB Balance snapshot at a given timestamp.
        May raise:
        - InputError
        """
        # delete the existing snapshot of that timestamp
        self.delete(
            write_cursor=write_cursor,
            timestamp=timestamp,
        )

        # update the snapshot with the provided data.
        self.import_snapshot(
            write_cursor=write_cursor,
            processed_balances_list=balances_snapshot,
            processed_location_data_list=location_data_snapshot,
        )

    def delete(self, write_cursor: 'DBWriterClient', timestamp: Timestamp) -> None:
        """Deletes a snapshot of the database at a given timestamp
        May raise:
        - InputError
        """
        write_cursor.execute('DELETE FROM timed_balances WHERE timestamp=?', (timestamp,))
        if write_cursor.rowcount == 0:
            raise InputError('No snapshot found for the specified timestamp')
        write_cursor.execute('DELETE FROM timed_location_data WHERE timestamp=?', (timestamp,))
        if write_cursor.rowcount == 0:
            raise InputError('No snapshot found for the specified timestamp')

    def add_nft_asset_ids(self, write_cursor: 'DBWriterClient', entries: list[str]) -> None:
        """Add NFT identifiers to the DB to prevent unknown asset error."""
        nft_ids = [x for x in entries if x.startswith(NFT_DIRECTIVE)]
        self.db.add_asset_identifiers(write_cursor, nft_ids)
