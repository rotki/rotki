import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants.assets import A_BSQ, A_BTC
from rotkehlchen.data_import.utils import BaseExchangeImporter
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
from rotkehlchen.types import Location, Price, TradeType

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class BisqTradesImporter(BaseExchangeImporter):
    """Bisq CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Bisq')

    def _consume_bisq_trade(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            timestamp_format: str = '%d %b %Y %H:%M:%S',
    ) -> None:
        """
        Consume the file containing only trades from Bisq.
        - UnknownAsset
        - DeserializationError
        """
        if csv_row['Status'] == 'Canceled':
            return
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Date/Time'],
            formatstr=timestamp_format,
            location='Bisq',
        )
        # Get assets and amounts sold
        offer = csv_row['Offer type'].split()
        assets1_symbol, assets2_symbol = csv_row['Market'].split('/')
        if offer[0] == 'Sell':
            trade_type = TradeType.SELL
            if offer[1] == assets1_symbol:
                base_asset = symbol_to_asset_or_token(assets1_symbol)
                quote_asset = symbol_to_asset_or_token(assets2_symbol)
            else:
                base_asset = symbol_to_asset_or_token(assets2_symbol)
                quote_asset = symbol_to_asset_or_token(assets1_symbol)
        else:
            trade_type = TradeType.BUY
            if offer[1] == assets1_symbol:
                base_asset = symbol_to_asset_or_token(assets1_symbol)
                quote_asset = symbol_to_asset_or_token(assets2_symbol)
            else:
                base_asset = symbol_to_asset_or_token(assets2_symbol)
                quote_asset = symbol_to_asset_or_token(assets1_symbol)

        if base_asset == A_BTC:
            buy_amount = deserialize_asset_amount(csv_row['Amount in BTC'])
        else:
            buy_amount = deserialize_asset_amount(csv_row['Amount'])

        rate = Price(deserialize_asset_amount(csv_row['Price']))
        # Get trade fee
        if len(csv_row['Trade Fee BSQ']) != 0:
            fee_amount = deserialize_fee(csv_row['Trade Fee BSQ'])
            fee_currency = A_BSQ
        else:
            fee_amount = deserialize_fee(csv_row['Trade Fee BTC'])
            fee_currency = A_BTC

        trade = Trade(
            timestamp=timestamp,
            location=Location.BISQ,
            base_asset=base_asset,
            quote_asset=quote_asset,
            trade_type=trade_type,
            amount=buy_amount,
            rate=rate,
            fee=fee_amount,
            fee_currency=fee_currency,
            link='',
            notes=f'ID: {csv_row["Trade ID"]}',
        )
        self.add_trade(write_cursor, trade)

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Import trades from bisq. The information and comments about this importer were addressed
        at the issue https://github.com/rotki/rotki/issues/824
        May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            for index, row in enumerate(csv.DictReader(csvfile), start=1):
                try:
                    self.total_entries += 1
                    self._consume_bisq_trade(write_cursor, row, **kwargs)
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
