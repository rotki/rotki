import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.converters import asset_from_blockfi
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import BaseExchangeImporter, SkippedCSVEntry
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import Location, Price, TradeType

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BlockfiTradesImporter(BaseExchangeImporter):
    """Blockfi trades CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Blockfi trades')

    def _consume_blockfi_trade(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            timestamp_format: str = '%Y-%m-%d %H:%M:%S',
    ) -> None:
        """
        Consume the file containing only trades from BlockFi. As per my investigations
        (@yabirgb) this file can only contain confirmed trades.
        - UnknownAsset
        - DeserializationError
        """
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Date'],
            formatstr=timestamp_format,
            location='BlockFi',
        )

        buy_asset = asset_from_blockfi(csv_row['Buy Currency'])
        buy_amount = deserialize_asset_amount(csv_row['Buy Quantity'])
        sold_asset = asset_from_blockfi(csv_row['Sold Currency'])
        sold_amount = deserialize_asset_amount(csv_row['Sold Quantity'])
        if sold_amount == ZERO:
            raise SkippedCSVEntry('Trade has sold_amount equal to zero.')
        rate = Price(buy_amount / sold_amount)
        trade = Trade(
            timestamp=timestamp,
            location=Location.BLOCKFI,
            base_asset=sold_asset,
            quote_asset=buy_asset,
            trade_type=TradeType.SELL,
            amount=sold_amount,
            rate=rate,
            fee=None,  # BlockFI doesn't provide this information
            fee_currency=None,
            link='',
            notes=csv_row['Type'],
        )
        self.add_trade(write_cursor, trade)

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Information for the values that the columns can have has been obtained from
        the issue in github #1674
        May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            for index, row in enumerate(csv.DictReader(csvfile), start=1):
                try:
                    self.total_entries += 1
                    self._consume_blockfi_trade(write_cursor, row, **kwargs)
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
                except SkippedCSVEntry as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=str(e),
                        is_error=False,
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
