import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.converters import asset_from_kraken
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI, A_SAI
from rotkehlchen.data_import.utils import BaseExchangeImporter, SkippedCSVEntry
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, Fee, Location, Price, TradeType

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

SAI_TIMESTAMP = 1574035200


class ShapeshiftTradesImporter(BaseExchangeImporter):
    """Shapeshift CSV importer"""

    def __init__(self, db: 'DBHandler'):
        super().__init__(db=db, name='ShapeShift')
        self.sai = A_SAI.resolve_to_evm_token()

    def _consume_shapeshift_trade(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            timestamp_format: str = 'iso8601',
    ) -> None:
        """
        Consume the file containing only trades from ShapeShift.
        May raise:
        - DeserializationError if failed to deserialize timestamp or amount
        - UnknownAsset if unknown asset in the csv row was found
        - KeyError if csv_row does not have expected cells
        """
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['timestamp'],
            formatstr=timestamp_format,
            location='ShapeShift',
        )
        # Use asset_from_kraken since the mapping is the same as in kraken
        buy_asset = asset_from_kraken(csv_row['outputCurrency'])
        buy_amount = deserialize_asset_amount(csv_row['outputAmount'])
        sold_asset = asset_from_kraken(csv_row['inputCurrency'])
        sold_amount = deserialize_asset_amount(csv_row['inputAmount'])
        rate = deserialize_asset_amount(csv_row['rate'])
        fee = deserialize_fee(csv_row['minerFee'])
        gross_amount = AssetAmount(buy_amount + fee)
        in_addr = csv_row['inputAddress']
        out_addr = csv_row['outputAddress']
        notes = f"""
Trade from ShapeShift with ShapeShift Deposit Address:
 {csv_row['inputAddress']}, and
 Transaction ID: {csv_row['inputTxid']}.
  Refund Address: {csv_row['refundAddress']}, and
 Transaction ID: {csv_row['refundTxid']}.
  Destination Address: {csv_row['outputAddress']}, and
 Transaction ID: {csv_row['outputTxid']}.
"""
        if sold_amount == ZERO:
            raise SkippedCSVEntry('Trade has sold_amount of zero.')
        if in_addr == '' or out_addr == '':
            raise SkippedCSVEntry('Trade was preformed on a DEX.')
        # Assuming that before launch of multi collateral dai everything was SAI.
        # Converting DAI to SAI in buy_asset and sell_asset.
        if buy_asset == A_DAI and timestamp <= SAI_TIMESTAMP:
            buy_asset = self.sai
        if sold_asset == A_DAI and timestamp <= SAI_TIMESTAMP:
            sold_asset = self.sai
        if rate <= ZERO:
            raise SkippedCSVEntry('Entry has negative or zero rate.')

        # Fix the rate correctly (1 / rate) * (fee + buy_amount) = sell_amount
        trade = Trade(
            timestamp=timestamp,
            location=Location.SHAPESHIFT,
            base_asset=buy_asset,
            quote_asset=sold_asset,
            trade_type=TradeType.BUY,
            amount=gross_amount,
            rate=Price(1 / rate),
            fee=Fee(fee),
            fee_currency=buy_asset,  # Assumption that minerFee is denominated in outputCurrency
            link='',
            notes=notes,
        )
        self.add_trade(write_cursor, trade)

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Information for the values that the columns can have has been obtained from sample CSVs
        May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            for index, row in enumerate(csv.DictReader(csvfile), start=1):
                try:
                    self.total_entries += 1
                    self._consume_shapeshift_trade(write_cursor, row, **kwargs)
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
