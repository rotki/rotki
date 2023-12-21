import csv
from enum import Enum, auto
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
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetMovementCategory, Fee, Location, TradeType

if TYPE_CHECKING:
    from collections.abc import Callable


class BittrexFileType(Enum):
    """The type of the file we are parsing"""
    TRADES = auto()  # default header format
    TRADES_OLD = auto()  # old header format
    TRADES_OLDER = auto()  # header format with uppercase
    DEPOSITS = auto()  # old format having only deposits
    DEPOSITS_OLD = auto()  # old format having only deposits with uppercase
    WITHDRAWALS = auto()  # old format having only withdrawals
    WITHDRAWALS_OLD = auto()  # old format having only withdrawals with uppercase
    DEPOSITS_AND_WITHDRAWALS = auto()  # default header format having both deposits/withdrawals


class BittrexImporter(BaseExchangeImporter):
    @staticmethod
    def _consume_trades(
            csv_row: dict[str, Any],
            file_type: BittrexFileType,
            timestamp_format: str = '%Y-%m-%dT%H:%M:%S',
    ) -> Trade:
        """
        Consume entries of bittrex order history csv

        May raise:
        - KeyError
        - DeserializationError
        """
        fee = get_key_if_has_val(csv_row, 'Fees (Quote)')
        notes = get_key_if_has_val(csv_row, 'Notes')
        if file_type == BittrexFileType.TRADES:
            date = csv_row['Time (UTC)']
            base = csv_row['Base']
            quote = csv_row['Quote']
            trade_type = TradeType.BUY if csv_row['Transaction'] == 'Bought' else TradeType.SELL
            amount = csv_row['Quantity (Base)']
            rate = csv_row['Price']
            order_id = csv_row['TXID']
        elif file_type == BittrexFileType.TRADES_OLD:
            date = csv_row['Closed']
            quote, base = csv_row['Exchange'].split('-')
            trade_type = TradeType.BUY if csv_row['Type'] == 'LIMIT_BUY' else TradeType.SELL
            amount = csv_row['Quantity']
            rate = csv_row['Price']
            order_id = csv_row['OrderUuid']
        else:
            date = csv_row['CLOSED']
            base = csv_row['MARKET']
            quote = csv_row['QUOTE']
            trade_type = TradeType.BUY if csv_row['ORDERTYPE'] == 'LIMIT_BUY' else TradeType.SELL
            amount = csv_row['FILLED']
            rate = csv_row['LIMIT']
            order_id = csv_row['UUID']
        return Trade(
            timestamp=deserialize_timestamp_from_date(
                date=date,
                formatstr=timestamp_format,
                location='Bittrex order history import',
            ),
            location=Location.BITTREX,
            base_asset=asset_from_bittrex(base),
            quote_asset=asset_from_bittrex(quote),
            trade_type=trade_type,
            amount=deserialize_asset_amount(amount),
            rate=deserialize_price(rate),
            fee=deserialize_fee(fee),
            fee_currency=asset_from_bittrex(quote),
            link=f'Imported bittrex trade {order_id} from csv',
            notes=notes,
        )

    @staticmethod
    def _consume_deposits_or_withdrawals(
            csv_row: dict[str, Any],
            file_type: BittrexFileType,
            timestamp_format: str = '%Y-%m-%d %H:%M:%S.%f',
    ) -> AssetMovement:
        """
        Use Deposit and Withdrawal entries to generate an AssetMovement object.
        May raise:
        - KeyError
        - DeserializationError
        """
        if file_type == BittrexFileType.DEPOSITS_AND_WITHDRAWALS:
            asset = csv_row['Currency']
            category = AssetMovementCategory.DEPOSIT if csv_row['Type'] == 'DEPOSIT' else AssetMovementCategory.WITHDRAWAL  # noqa: E501
            address_key = 'Address'
            tx_id_key = 'TxId'
            date = csv_row['Date']
            amount = csv_row['Amount']
        elif file_type == BittrexFileType.DEPOSITS:
            asset = csv_row['Currency']
            category = AssetMovementCategory.DEPOSIT
            address_key = 'CryptoAddress'
            tx_id_key = 'TxId'
            date = csv_row['LastUpdated']
            amount = csv_row['Amount']
        elif file_type == BittrexFileType.DEPOSITS_OLD:
            asset = csv_row['CURRENCY']
            category = AssetMovementCategory.DEPOSIT
            address_key = 'CRYPTOADDRESS'
            tx_id_key = 'TXID'
            date = csv_row['LASTUPDATED']
            amount = csv_row['AMOUNT']
        elif file_type == BittrexFileType.WITHDRAWALS:
            asset = csv_row['Currency']
            category = AssetMovementCategory.WITHDRAWAL
            address_key = 'Address'
            tx_id_key = 'TxId'
            date = csv_row['Opened']
            amount = csv_row['Amount']
        else:
            asset = csv_row['CURRENCY']
            category = AssetMovementCategory.WITHDRAWAL
            address_key = 'ADDRESS'
            tx_id_key = 'TXID'
            date = csv_row['CLOSED']
            amount = csv_row['AMOUNT']
        asset = asset_from_bittrex(asset)
        return AssetMovement(
            location=Location.BITTREX,
            category=category,
            address=deserialize_asset_movement_address(csv_row, address_key, asset),
            transaction_id=get_key_if_has_val(csv_row, tx_id_key),
            timestamp=deserialize_timestamp_from_date(
                date=date,
                formatstr=timestamp_format,
                location='Bittrex tx history import',
            ),
            asset=asset,
            amount=deserialize_asset_amount_force_positive(amount),
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
        consumer_fn: 'Callable[[dict[str, Any], BittrexFileType, str], AssetMovement] | Callable[[dict[str, Any], BittrexFileType, str], Trade]'  # noqa: E501
        save_fn: 'Callable[[DBCursor, Trade], None] | Callable[[DBCursor, AssetMovement], None]'
        with open(filepath, encoding='utf-8-sig') as csvfile:
            while True:
                saved_pos = csvfile.tell()
                line = csvfile.readline()
                if not (line.startswith(('Name: ', 'UserID: ', 'Date Generated: ')) or line.strip() == ''):  # noqa: E501
                    break

            # by now in both files we should have reached the header
            if 'Date,Currency,Type,Address,Memo/Tag,TxId,Amount' in line:
                file_type = BittrexFileType.DEPOSITS_AND_WITHDRAWALS
                consumer_fn = self._consume_deposits_or_withdrawals
                save_fn = self.add_asset_movement
            elif 'Id,Amount,Currency,Confirmations,LastUpdated,TxId,CryptoAddress' in line:
                file_type = BittrexFileType.DEPOSITS
                consumer_fn = self._consume_deposits_or_withdrawals
                save_fn = self.add_asset_movement
            elif 'UUID,AMOUNT,CURRENCY,CRYPTOADDRESS,TXID,LASTUPDATED,CONFIRMATIONS,SOURCE,STATE' in line:  # noqa: E501
                file_type = BittrexFileType.DEPOSITS_OLD
                consumer_fn = self._consume_deposits_or_withdrawals
                save_fn = self.add_asset_movement
            elif 'PaymentUuid,Currency,Amount,Address,Opened,Authorized,PendingPayment,TxCost,TxId,Canceled,InvalidAddress' in line:  # noqa: E501
                file_type = BittrexFileType.WITHDRAWALS
                consumer_fn = self._consume_deposits_or_withdrawals
                save_fn = self.add_asset_movement
            elif 'UUID,AMOUNT,CURRENCY,ADDRESS,TXID,OPENED,LASTUPDATED,CLOSED,TXCOST,STATE' in line:  # noqa: E501
                file_type = BittrexFileType.WITHDRAWALS_OLD
                consumer_fn = self._consume_deposits_or_withdrawals
                save_fn = self.add_asset_movement
            elif 'TXID,Time (UTC),Transaction,Order Type,Market,Base,Quote,Price,Quantity (Base),Fees (Quote),Total (Quote),Approx Value (USD),Time In Force,Notes' in line:  # noqa: E501
                file_type = BittrexFileType.TRADES
                consumer_fn = self._consume_trades
                save_fn = self.add_trade
            elif 'OrderUuid,Exchange,Type,Quantity,Limit,CommissionPaid,Price,Opened,Closed' in line:  # noqa: E501
                file_type = BittrexFileType.TRADES_OLD
                consumer_fn = self._consume_trades
                save_fn = self.add_trade
            elif 'UUID,QUOTE,MARKET,ORDERTYPE,LIMIT,CEILING,QUANTITY,FILLED,PROCEEDS,COMISSIONPAID,OPENED,CLOSED,TIMEINFORCETYPE,ISCONDITIONAL,CONDITION,CONDITIONTARGET' in line:  # noqa: E501
                file_type = BittrexFileType.TRADES_OLDER
                consumer_fn = self._consume_trades
                save_fn = self.add_trade
            else:
                raise InputError('The given bittrex CSV file format can not be recognized')

            csvfile.seek(saved_pos)  # go back to start of theline
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    event = consumer_fn(row, file_type, **kwargs)
                    save_fn(write_cursor, event)  # type: ignore  # checked by if above
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during Bittrex CSV import. '
                        f'{e!s}. Ignoring entry',
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in bittrex csv row {row!s}') from e
