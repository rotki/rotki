import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI, A_SAI
from rotkehlchen.data_import.utils import BaseExchangeImporter
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, Fee, Location, Price, TradeType

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SAI_TIMESTAMP = 1574035200


class ShapeshiftTradesImporter(BaseExchangeImporter):

    def __init__(self, db: 'DBHandler'):
        super().__init__(db=db)
        self.sai = A_SAI.resolve_to_evm_token()

    def _consume_shapeshift_trade(
            self,
            cursor: DBCursor,
            csv_row: Dict[str, Any],
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
        buy_asset = symbol_to_asset_or_token(csv_row['outputCurrency'])
        buy_amount = deserialize_asset_amount(csv_row['outputAmount'])
        sold_asset = symbol_to_asset_or_token(csv_row['inputCurrency'])
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
            log.debug(f'Ignoring ShapeShift trade with sold_amount equal to zero. {csv_row}')
            return
        if in_addr == '' or out_addr == '':
            log.debug(f'Ignoring ShapeShift trade which was performed on DEX. {csv_row}')
            return
        # Assuming that before launch of multi collateral dai everything was SAI.
        # Converting DAI to SAI in buy_asset and sell_asset.
        if buy_asset == A_DAI and timestamp <= SAI_TIMESTAMP:
            buy_asset = self.sai
        if sold_asset == A_DAI and timestamp <= SAI_TIMESTAMP:
            sold_asset = self.sai
        if rate <= ZERO:
            log.warning(f'shapeshift csv entry has negative or zero rate. Ignoring. {csv_row}')
            return

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
        self.add_trade(cursor, trade)

    def _import_csv(self, cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Information for the values that the columns can have has been obtained from sample CSVs
        May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_shapeshift_trade(cursor, row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During ShapeShift CSV import found action with unknown '
                        f'asset {e.asset_name}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during ShapeShift CSV import. '
                        f'{str(e)}. Ignoring entry',
                    )
                    continue
                except KeyError as e:
                    raise InputError(f'Could not find key {str(e)} in csv row {str(row)}') from e
