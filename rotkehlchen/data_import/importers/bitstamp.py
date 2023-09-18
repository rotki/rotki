import csv
from pathlib import Path
from typing import Any

from rotkehlchen.assets.converters import asset_from_bitstamp
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.data_import.utils import BaseExchangeImporter
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, AssetMovementCategory, Trade
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import Location, Price, TradeType


class BitstampTransactionsImporter(BaseExchangeImporter):
    def _consume_bitstamp_trade(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            timestamp_format: str = '%b. %d, %Y, %I:%M %p',
    ) -> None:
        """
        Consume the file containing only trades from Bitstamp.
        - UnknownAsset
        - DeserializationError
        """
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Datetime'],
            formatstr=timestamp_format,
            location='Bitstamp',
        )

        amount, amount_symbol = csv_row['Amount'].split(' ')

        if csv_row['Type'] == 'Market':
            value_amount, value_symbol = csv_row['Value'].split(' ')
            rate = Price(csv_row['Rate'].split(' ')[0])
            fee_amount, fee_symbol = csv_row['Fee'].split(' ')
            trade_type = TradeType.deserialize(csv_row['Sub Type'])

            # if trade_type buy
            bought_amount = deserialize_asset_amount(amount)
            sold_amount = deserialize_asset_amount(value_amount)
            bought_symbol = asset_from_bitstamp(amount_symbol)
            sold_symbol = asset_from_bitstamp(value_symbol)

            if trade_type == TradeType.SELL:
                bought_amount, sold_amount = sold_amount, bought_amount
                sold_symbol, bought_symbol = bought_symbol, sold_symbol

            trade = Trade(
                timestamp=timestamp,
                location=Location.BITSTAMP,
                base_asset=bought_symbol,
                quote_asset=sold_symbol,
                trade_type=trade_type,
                amount=bought_amount,
                rate=rate,
                fee=deserialize_fee(fee_amount),
                fee_currency=asset_from_bitstamp(fee_symbol),
                link='',
                notes='',
            )
            self.add_trade(write_cursor, trade)
        elif csv_row['Type'] == 'Deposit' or csv_row['Type'] == 'Withdrawal':
            asset_movement = AssetMovement(
                location=Location.BITSTAMP,
                category=AssetMovementCategory.DEPOSIT
                if csv_row['Type'] == 'Deposit'
                else AssetMovementCategory.WITHDRAWAL,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset_from_bitstamp(amount_symbol),
                amount=amount,
                fee=deserialize_fee(None),
                fee_asset=A_USD,
                link='',
            )
            self.add_asset_movement(write_cursor, asset_movement)

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Import trades from bitstamp.
        May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_bitstamp_trade(write_cursor, row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During Bitstamp CSV import found action with unknown '
                        f'asset {e.identifier}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during Bitstamp CSV import. '
                        f'{e!s}. Ignoring entry',
                    )
                    continue
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
