import csv
from decimal import DivisionByZero
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
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.serialization.deserialize import deserialize_asset_amount
from rotkehlchen.types import Price, TradeType
from rotkehlchen.utils.misc import ts_ms_to_sec

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
        - DivisionByZero if `amount_bought` is ZERO
        """
        amount_sold = deserialize_asset_amount(csv_row['Sell Amount'])
        amount_bought = deserialize_asset_amount(csv_row['Buy Amount'])
        asset, fee, fee_currency, location, timestamp = process_rotki_generic_import_csv_fields(csv_row, 'Base Currency')  # noqa: E501
        if (trade_type := TradeType.deserialize(csv_row['Type'])) == TradeType.BUY:
            rate = amount_sold / amount_bought
            amount = amount_bought
        else:  # sell
            rate = amount_bought / amount_sold
            amount = amount_sold
        trade = Trade(
            timestamp=ts_ms_to_sec(timestamp),
            location=location,
            fee=fee,
            fee_currency=fee_currency,
            rate=Price(rate),
            base_asset=asset,
            quote_asset=symbol_to_asset_or_token(csv_row['Quote Currency']),
            trade_type=trade_type,
            amount=amount,
            notes=csv_row['Description'],
        )
        self.add_trade(write_cursor, trade)

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
                except DivisionByZero:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg='Entry has zero amount bought.',
                        is_error=True,
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
