import csv
import logging
from pathlib import Path
from typing import Any, Dict

from rotkehlchen.assets.converters import asset_from_blockfi
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import BaseExchangeImporter
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


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BlockfiTradesImporter(BaseExchangeImporter):
    def _consume_blockfi_trade(
            self,
            cursor: DBCursor,
            csv_row: Dict[str, Any],
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
            log.debug(f'Ignoring BlockFi trade with sold_amount equal to zero. {csv_row}')
            return
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
        self.add_trade(cursor, trade)

    def _import_csv(self, cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Information for the values that the columns can have has been obtained from
        the issue in github #1674
        May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_blockfi_trade(cursor, row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During BlockFi CSV import found action with unknown '
                        f'asset {e.identifier}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during BlockFi CSV import. '
                        f'{str(e)}. Ignoring entry',
                    )
                    continue
                except KeyError as e:
                    raise InputError(f'Could not find key {str(e)} in csv row {str(row)}') from e
