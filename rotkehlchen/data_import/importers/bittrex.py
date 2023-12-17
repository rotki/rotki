import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.converters import asset_from_bittrex
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import BaseExchangeImporter
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address, get_key_if_has_val
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetMovementCategory, Fee, Location, TradeType

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BittrexImporter(BaseExchangeImporter):
    @staticmethod
    def _consume_trades(
            csv_row: dict[str, Any], timestamp_format: str = '%Y-%m-%dT%H:%M:%S',
    ) -> Trade:
        """
        Consume entries of bittrex order history csv

        May raise:
        - KeyError
        - DeserializationError
        """
        quote_asset = asset_from_bittrex(csv_row['Quote'])
        return Trade(
            timestamp=deserialize_timestamp_from_date(
                date=csv_row['Time (UTC)'],
                formatstr=timestamp_format,
                location='Bittrex order history import',
            ),
            location=Location.BITTREX,
            base_asset=asset_from_bittrex(csv_row['Base']),
            quote_asset=quote_asset,
            trade_type=TradeType.BUY if csv_row['Transaction'] == 'Bought' else TradeType.SELL,
            amount=deserialize_asset_amount(csv_row['Quantity (Base)']),
            rate=deserialize_price(csv_row['Price']),
            fee=deserialize_fee(csv_row['Fees (Quote)']),
            fee_currency=quote_asset,
            link=f'Imported bittrex trade {csv_row["TXID"]} from csv',
            notes=csv_row['Notes'],
        )

    @staticmethod
    def _consume_deposits_or_withdrawals(
            csv_row: dict[str, Any], timestamp_format: str = '%Y-%m-%d %H:%M:%S.%f',
    ) -> AssetMovement:
        """
        Use Deposit and Withdrawal entries to generate an AssetMovement object.
        May raise:
        - KeyError
        - DeserializationError
        """
        asset = asset_from_bittrex(csv_row['Currency'])
        return AssetMovement(
            location=Location.BITTREX,
            category=AssetMovementCategory.DEPOSIT if csv_row['Type'] == 'DEPOSIT' else AssetMovementCategory.WITHDRAWAL,  # noqa: E501
            address=deserialize_asset_movement_address(csv_row, 'Address', asset),
            transaction_id=get_key_if_has_val(csv_row, 'TxId'),
            timestamp=deserialize_timestamp_from_date(
                date=csv_row['Date'],
                formatstr=timestamp_format,
                location='Bittrex tx history import',
            ),
            asset=asset,
            amount=deserialize_asset_amount_force_positive(csv_row['Amount']),
            fee_asset=asset,
            fee=Fee(ZERO),
            link='Imported from bittrex CSV file',
        )

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Import deposits, withdrawals and trades from Bittrex. Find out which file
        we are parsing depending on its format.

        May raise:
        - UnsupportedCSVEntry if operation not supported
        - InputError if a column we need is missing
        """
        consumer_fn: 'Callable[[dict[str, Any], str], AssetMovement] | Callable[[dict[str, Any], str], Trade]'  # noqa: E501
        save_fn: 'Callable[[DBCursor, Trade], None] | Callable[[DBCursor, AssetMovement], None]'
        with open(filepath, encoding='utf-8-sig') as csvfile:
            while True:
                saved_pos = csvfile.tell()
                line = csvfile.readline()
                if not (line.startswith(('Name: ', 'UserID: ', 'Date Generated: ')) or line.strip() == ''):  # noqa: E501
                    break

            # by now in both files we should have reached the header
            if 'Date,Currency,Type,Address,Memo/Tag,TxId,Amount' in line:
                consumer_fn = self._consume_deposits_or_withdrawals
                save_fn = self.add_asset_movement
            elif 'TXID,Time (UTC),Transaction,Order Type,Market,Base,Quote,Price,Quantity (Base),Fees (Quote),Total (Quote),Approx Value (USD),Time In Force,Notes' in line:  # noqa: E501
                consumer_fn = self._consume_trades
                save_fn = self.add_trade
            else:
                raise InputError('The given bittrex CSV file format can not be recognized')

            csvfile.seek(saved_pos)  # go back to start of theline
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    event = consumer_fn(row, **kwargs)
                    save_fn(write_cursor, event)  # type: ignore  # checked by if above
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during Bittrex CSV import. '
                        f'{e!s}. Ignoring entry',
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in bittrex csv row {row!s}') from e
