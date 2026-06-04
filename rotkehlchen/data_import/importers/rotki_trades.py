import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.data_import.utils import (
    BaseExchangeImporter,
    process_rotki_generic_import_csv_fields,
)
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.utils import create_group_identifier_from_swap
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import AssetAmount

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class RotkiGenericTradesImporter(BaseExchangeImporter):
    """Rotki generic trades CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Rotki generic trades')

    def _consume_rotki_trades(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
    ) -> None:
        """Consume rotki generic trades import CSV file.
        May raise:
        - DeserializationError
        - UnknownAsset
        - KeyError
        """
        spend_amount = deserialize_fval(csv_row['Spend Amount'])
        receive_amount = deserialize_fval(csv_row['Receive Amount'])
        spend_asset, fee, fee_currency, location, timestamp = process_rotki_generic_import_csv_fields(csv_row, 'Spend Currency')  # noqa: E501
        receive_asset = symbol_to_asset_or_token(csv_row['Receive Currency'])
        self.add_history_events(
            write_cursor=write_cursor,
            history_events=create_swap_events(
                timestamp=timestamp,
                location=location,
                spend=(spend := AssetAmount(asset=spend_asset, amount=spend_amount)),
                receive=(receive := AssetAmount(asset=receive_asset, amount=receive_amount)),
                spend_notes=csv_row['Description'],
                fee=AssetAmount(asset=fee_currency, amount=fee) if fee_currency is not None and fee is not None else None,  # noqa: E501
                group_identifier=create_group_identifier_from_swap(
                    location=location,
                    timestamp=timestamp,
                    spend=spend,
                    receive=receive,
                ),
            ),
        )

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            for index, row in enumerate(csv.DictReader(csvfile), start=1):
                try:
                    self.total_entries += 1
                    self._consume_rotki_trades(write_cursor, row)
                    self.imported_entries += 1
                except UnknownAsset as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=f'Unknown asset {e.identifier}.',
                        is_error=True,
                    )
                except DeserializationError as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=f'Deserialization error: {e!s}.',
                        is_error=True,
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
