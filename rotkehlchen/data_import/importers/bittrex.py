import csv
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.assets.converters import asset_from_bittrex
from rotkehlchen.data_import.utils import BaseExchangeImporter, maybe_set_transaction_extra_data
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address, get_key_if_has_val
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_force_positive,
    deserialize_fval_or_zero,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, Location
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.db.dbhandler import DBHandler


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
    """Bittrex CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Bittrex')

    @staticmethod
    def _consume_trades(
            csv_row: dict[str, Any],
            file_type: BittrexFileType,
            timestamp_format: str = '%Y-%m-%dT%H:%M:%S',
    ) -> list[SwapEvent]:
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
            trade_type = 'buy' if csv_row['Transaction'] == 'Bought' else 'sell'
            amount = csv_row['Quantity (Base)']
            rate = csv_row['Price']
            order_id = csv_row['TXID']
        elif file_type == BittrexFileType.TRADES_OLD:
            date = csv_row['Closed']
            quote, base = csv_row['Exchange'].split('-')
            trade_type = 'buy' if csv_row['Type'] == 'LIMIT_BUY' else 'sell'
            amount = csv_row['Quantity']
            rate = csv_row['Price']
            order_id = csv_row['OrderUuid']
        else:
            date = csv_row['CLOSED']
            base = csv_row['MARKET']
            quote = csv_row['QUOTE']
            trade_type = 'buy' if csv_row['ORDERTYPE'] == 'LIMIT_BUY' else 'sell'
            amount = csv_row['FILLED']
            rate = csv_row['LIMIT']
            order_id = csv_row['UUID']

        spend, receive = get_swap_spend_receive(
            raw_trade_type=trade_type,
            base_asset=asset_from_bittrex(base),
            quote_asset=(quote_asset := asset_from_bittrex(quote)),
            amount=deserialize_fval(amount),
            rate=deserialize_price(rate),
        )
        return create_swap_events(
            timestamp=ts_sec_to_ms(deserialize_timestamp_from_date(
                date=date,
                formatstr=timestamp_format,
                location='Bittrex order history import',
            )),
            location=Location.BITTREX,
            spend=spend,
            receive=receive,
            fee=AssetAmount(
                asset=quote_asset,
                amount=deserialize_fval_or_zero(fee),
            ),
            unique_id=order_id,
            spend_notes=notes,
        )

    @staticmethod
    def _consume_deposits_or_withdrawals(
            csv_row: dict[str, Any],
            file_type: BittrexFileType,
            timestamp_format: str = '%Y-%m-%d %H:%M:%S.%f',
    ) -> list[AssetMovement]:
        """
        Use Deposit and Withdrawal entries to generate an AssetMovement object.
        May raise:
        - KeyError
        - DeserializationError
        """
        event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL]
        if file_type == BittrexFileType.DEPOSITS_AND_WITHDRAWALS:
            asset = csv_row['Currency']
            event_type = HistoryEventType.DEPOSIT if csv_row['Type'] == 'DEPOSIT' else HistoryEventType.WITHDRAWAL  # noqa: E501
            address_key = 'Address'
            tx_id_key = 'TxId'
            date = csv_row['Date']
            amount = csv_row['Amount']
        elif file_type == BittrexFileType.DEPOSITS:
            asset = csv_row['Currency']
            event_type = HistoryEventType.DEPOSIT
            address_key = 'CryptoAddress'
            tx_id_key = 'TxId'
            date = csv_row['LastUpdated']
            amount = csv_row['Amount']
        elif file_type == BittrexFileType.DEPOSITS_OLD:
            asset = csv_row['CURRENCY']
            event_type = HistoryEventType.DEPOSIT
            address_key = 'CRYPTOADDRESS'
            tx_id_key = 'TXID'
            date = csv_row['LASTUPDATED']
            amount = csv_row['AMOUNT']
        elif file_type == BittrexFileType.WITHDRAWALS:
            asset = csv_row['Currency']
            event_type = HistoryEventType.WITHDRAWAL
            address_key = 'Address'
            tx_id_key = 'TxId'
            date = csv_row['Opened']
            amount = csv_row['Amount']
        else:
            asset = csv_row['CURRENCY']
            event_type = HistoryEventType.WITHDRAWAL
            address_key = 'ADDRESS'
            tx_id_key = 'TXID'
            date = csv_row['CLOSED']
            amount = csv_row['AMOUNT']
        asset = asset_from_bittrex(asset)
        return [AssetMovement(
            location=Location.BITTREX,
            event_type=event_type,
            timestamp=ts_sec_to_ms(deserialize_timestamp_from_date(
                date=date,
                formatstr=timestamp_format,
                location='Bittrex tx history import',
            )),
            asset=asset,
            amount=deserialize_fval_force_positive(amount),
            unique_id=(transaction_id := get_key_if_has_val(csv_row, tx_id_key)),
            extra_data=maybe_set_transaction_extra_data(
                address=deserialize_asset_movement_address(csv_row, address_key, asset),
                transaction_id=transaction_id,
            ),
        )]

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Import deposits, withdrawals and trades from Bittrex. Find out which file
        we are parsing depending on its format.

        May raise:
        - UnsupportedCSVEntry if operation not supported
        - InputError if a column we need is missing
        """
        consumer_fn: Callable[[dict[str, Any], BittrexFileType, str], list[AssetMovement]] | Callable[[dict[str, Any], BittrexFileType, str], list[SwapEvent]]  # noqa: E501
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
            elif 'Id,Amount,Currency,Confirmations,LastUpdated,TxId,CryptoAddress' in line:
                file_type = BittrexFileType.DEPOSITS
                consumer_fn = self._consume_deposits_or_withdrawals
            elif 'UUID,AMOUNT,CURRENCY,CRYPTOADDRESS,TXID,LASTUPDATED,CONFIRMATIONS,SOURCE,STATE' in line:  # noqa: E501
                file_type = BittrexFileType.DEPOSITS_OLD
                consumer_fn = self._consume_deposits_or_withdrawals
            elif 'PaymentUuid,Currency,Amount,Address,Opened,Authorized,PendingPayment,TxCost,TxId,Canceled,InvalidAddress' in line:  # noqa: E501
                file_type = BittrexFileType.WITHDRAWALS
                consumer_fn = self._consume_deposits_or_withdrawals
            elif 'UUID,AMOUNT,CURRENCY,ADDRESS,TXID,OPENED,LASTUPDATED,CLOSED,TXCOST,STATE' in line:  # noqa: E501
                file_type = BittrexFileType.WITHDRAWALS_OLD
                consumer_fn = self._consume_deposits_or_withdrawals
            elif 'TXID,Time (UTC),Transaction,Order Type,Market,Base,Quote,Price,Quantity (Base),Fees (Quote),Total (Quote),Approx Value (USD),Time In Force,Notes' in line:  # noqa: E501
                file_type = BittrexFileType.TRADES
                consumer_fn = self._consume_trades
            elif 'OrderUuid,Exchange,Type,Quantity,Limit,CommissionPaid,Price,Opened,Closed' in line:  # noqa: E501
                file_type = BittrexFileType.TRADES_OLD
                consumer_fn = self._consume_trades
            elif 'UUID,QUOTE,MARKET,ORDERTYPE,LIMIT,CEILING,QUANTITY,FILLED,PROCEEDS,COMISSIONPAID,OPENED,CLOSED,TIMEINFORCETYPE,ISCONDITIONAL,CONDITION,CONDITIONTARGET' in line:  # noqa: E501
                file_type = BittrexFileType.TRADES_OLDER
                consumer_fn = self._consume_trades
            else:
                raise InputError('The given bittrex CSV file format can not be recognized')

            csvfile.seek(saved_pos)  # go back to start of theline
            for index, row in enumerate(csv.DictReader(csvfile), start=1):
                try:
                    self.total_entries += 1
                    events = consumer_fn(row, file_type, **kwargs)
                    self.add_history_events(write_cursor=write_cursor, history_events=events)
                    self.imported_entries += 1
                except DeserializationError as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=f'Deserialization error: {e!s}.',
                        is_error=True,
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in bittrex csv row {row!s}') from e
