import abc
import csv
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.data_import.utils import BaseExchangeImporter, UnsupportedCSVEntry, hash_csv_row
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.swap import SwapEvent, create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import (
    AssetAmount,
    Location,
    Price,
    Timestamp,
    TradeType,
)
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BinanceCsvRow = dict[str, Any]
BINANCE_TRADE_OPERATIONS = {'Buy', 'Sell', 'Fee'}
EVENT_IDENTIFIER_PREFIX = 'BNC_'
INDEX = '_index'


def hash_binance_csv_row(csv_row: BinanceCsvRow) -> str:
    """Hash the CSV row excluding the INDEX"""
    return hash_csv_row({k: v for k, v in csv_row.items() if k != INDEX})


class BinanceEntry(abc.ABC):  # noqa: B024
    """This is a base BinanceEntry class
    All row combinations in the Binance csv have to be inherited from this base class
    """


class BinanceSingleEntry(BinanceEntry, abc.ABC):
    """Children of this class represent single-row entries
    It means that all required data to create an internal representation
    is contained in one csv row

    Children should have a Final class-variable "AVAILABLE_OPERATIONS" that
    describes which "Operation" types can be processed by a class
    """
    AVAILABLE_OPERATIONS: tuple[str, ...]

    def is_entry(self, requested_operation: str, account: str, change: FVal) -> bool:  # pylint: disable=unused-argument
        """This method checks whether row with "requested_operation" could be processed
        by a class on which this method has been called.
        Some subclasses require combined checks with the "account" and "change" to
        check if a row can be processed.
        - "account" maps to the "Account" field on the csv
        - "change" maps to the "Change" field on the csv
        The default implementation can also be used in a subclass"""
        return requested_operation in self.AVAILABLE_OPERATIONS

    @abc.abstractmethod
    def process_entry(
            self,
            write_cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: BinanceCsvRow,
    ) -> None:
        """This method receives a csv row and processes it into internal rotki's representation
        Should be implemented by subclass."""


class BinanceMultipleEntry(BinanceEntry, abc.ABC):
    @abc.abstractmethod
    def are_entries(self, requested_operations: list) -> bool:
        """The subclass's method checks whether requested operations can be processed
        Not implemented here because the logic can differ for each subclass"""

    @abc.abstractmethod
    def process_entries(
            self,
            write_cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: list[BinanceCsvRow],
    ) -> int:
        """Turns given csv rows into internal rotki's representation"""


class BinanceTransferEntry(BinanceMultipleEntry):
    def are_entries(self, requested_operations: list[str]) -> bool:
        """
        This class supports several formats of Transfers from the csv.
        Supports the following combinations of "Operation" column's values:
            - Transfer Between Spot Account and UM Futures Account
            - Transfer Between Spot Account and CM Futures Account
            - Transfer Between Main and Funding Wallet
        """
        return len(requested_operations) == 2 and requested_operations[0].startswith('Transfer Between ')  # noqa: E501

    @staticmethod
    def process_transfers(
            timestamp: Timestamp,
            data: list[BinanceCsvRow],
    ) -> list[HistoryBaseEntry]:
        """
        Processes transfer events
        May raise:
        - KeyError
        """
        row = data[0]
        return [
            HistoryEvent(
                event_identifier=f'{EVENT_IDENTIFIER_PREFIX}{hash_binance_csv_row(row)}',
                sequence_index=0,
                timestamp=ts_sec_to_ms(timestamp),
                location=Location.BINANCE,
                event_type=HistoryEventType.TRANSFER,
                event_subtype=HistoryEventSubType.NONE,
                asset=row['Coin'],
                amount=abs(row['Change']),
                location_label='CSV import',
                notes=row['Operation'],
            ),
        ]

    def process_entries(
            self,
            write_cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: list[BinanceCsvRow],
    ) -> int:
        """
        Processes and adds the transfer history event to db
        May raise:
        - KeyError
        - DeserializationError: if the event is malformed when being stored in the db
        """
        history_events = self.process_transfers(timestamp=timestamp, data=data)
        importer.add_history_events(write_cursor=write_cursor, history_events=history_events)
        return len(history_events)


class BinanceTradeEntry(BinanceMultipleEntry):
    def are_entries(self, requested_operations: list) -> bool:
        """This class supports several formats of Trade entries from the csv.
        Supports the following combinations of "Operation" column's values:
            - Buy + Buy
            - Sell + Sell
            - Mixed data of (Buy + Buy) * N + (Sell + Sell) * M
            - Buy + Buy + Fee
            - Sell + Sell + Fee
            - Mixed data of (Buy + Buy) * N + (Sell + Sell) * M + Fee * (N + M)
            - DOESN'T support mixed Fee and Non-fee Trades
            - (Transaction Related + Transaction Related) * N
            - (Small assets exchange BNB + Small assets exchange BNB) * N
            - (Asset Conversion Transfer + Asset Conversion Transfer) * N
            - (Binance Convert + Binance Convert) * N
            - (Buy + Transaction Related) * N
        """
        counted = Counter(requested_operations)
        counted.pop('Fee', None)
        counted.pop('Transaction Fee', None)  # popped both fees to validate main trade components
        keys = set(counted.keys())
        return (
            (keys == {'Transaction Buy', 'Transaction Spend'} and counted['Transaction Buy'] - counted['Transaction Spend'] == 0) or  # noqa: E501
            (keys == {'Transaction Revenue', 'Transaction Sold'} and counted['Transaction Revenue'] - counted['Transaction Sold'] == 0) or  # noqa: E501
            (keys == {'Buy', 'Sell'} and counted['Buy'] % 2 == 0 and counted['Sell'] % 2 == 0) or
            (keys == {'Buy'} and counted['Buy'] % 2 == 0) or  # deprecated, new CSVs use Buy/Sell
            (keys == {'Sell'} and counted['Sell'] % 2 == 0) or  # deprecated, new CSVs use Buy/Sell
            (keys == {'Buy', 'Sell'} and counted['Buy'] - counted['Sell'] == 0) or
            (keys == {'Transaction Related'} and counted['Transaction Related'] % 2 == 0) or
            (keys == {'Small assets exchange BNB'} and counted['Small assets exchange BNB'] % 2 == 0) or  # noqa: E501
            (keys == {'Small Assets Exchange BNB'} and counted['Small Assets Exchange BNB'] % 2 == 0) or  # noqa: E501
            (keys == {'ETH 2.0 Staking'} and counted['ETH 2.0 Staking'] % 2 == 0) or
            (keys == {'Buy', 'Transaction Related'} and counted['Buy'] - counted['Transaction Related'] == 0) or  # noqa: E501
            (keys == {'Binance Convert'} and counted['Binance Convert'] % 2 == 0) or
            (keys == {'Asset Conversion Transfer'} and counted['Asset Conversion Transfer'] % 2 == 0)  # noqa: E501
        )

    @staticmethod
    def process_trades(
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: list[BinanceCsvRow],
    ) -> list[SwapEvent]:
        """Processes multiple rows of data and convert them into SwapEvents.
        Each row has format: {'Operation': ..., 'Change': ..., 'Coin': ...}
        Change is amount, Coin is asset
        If amount is negative then this asset is sold, otherwise it's bought
        """
        # Because we can get mixed data (e.g. multiple Buys or Sells on a single timestamp) we need
        # to group it somehow. We are doing it by grouping the highest bought with the highest
        # sold value. We query usd equivalent for each amount because different Sells / Buys
        # may use different assets.

        # If we query price for the first time it can take long, so we would like to avoid it,
        # and therefore we check if all Buys / Sells use the same asset.
        # If so, we can group by original amount.

        # Checking assets
        same_assets = True
        assets: dict[str, AssetWithOracles | None] = defaultdict(lambda: None)
        for row in data:
            if row['Operation'] in {'Fee', 'Transaction Fee'}:
                cur_operation = 'Fee'
            elif row['Change'] < 0:
                cur_operation = 'Sold'
            else:
                cur_operation = 'Bought'
            assets[cur_operation] = assets[cur_operation] or row['Coin']
            if assets[cur_operation] != row['Coin']:
                same_assets = False
                break

        price_at_timestamp: dict[AssetWithOracles, Price] = {}
        # Querying usd value if needed
        if same_assets is False:
            for row in data:
                try:
                    price_at_timestamp[row['Coin']] = PriceHistorian.query_historical_price(
                        from_asset=row['Coin'],
                        to_asset=A_USD,
                        timestamp=timestamp,
                    )
                except NoPriceForGivenTimestamp:
                    # If we can't find price we can't group, so we quit the method
                    importer.send_message(
                        row_index=row[INDEX],
                        csv_row=row,
                        msg=f'Couldn\'t find price of {row["Coin"]} on {timestamp}',
                        is_error=True,
                    )
                    return []

        # Group rows depending on whether they are fee or not and then sort them by amount
        rows_grouped_by_fee: dict[bool, list[BinanceCsvRow]] = defaultdict(list)
        for row in data:
            is_fee = row['Operation'] in {'Fee', 'Transaction Fee'}
            rows_grouped_by_fee[is_fee].append(row)

        for rows_group in rows_grouped_by_fee.values():
            rows_group.sort(key=lambda x: x['Change'] if same_assets else x['Change'] * price_at_timestamp[x['Coin']], reverse=True)  # noqa: E501

        # Grouping by combining the highest sold with the highest bought and the highest fee
        # Using fee only we were provided with fee (checking by "True in rows_by_operation")
        grouped_trade_rows = []
        while len(rows_grouped_by_fee[False]) > 0:
            cur_batch = [rows_grouped_by_fee[False].pop(), rows_grouped_by_fee[False].pop(0)]
            if True in rows_grouped_by_fee and len(rows_grouped_by_fee[True]) > 0:
                cur_batch.append(rows_grouped_by_fee[True].pop())
            grouped_trade_rows.append(cur_batch)

        swap_events = []
        for trade_rows in grouped_trade_rows:
            to_asset: AssetWithOracles | None = None
            to_amount: FVal | None = None
            from_asset: AssetWithOracles | None = None
            from_amount: FVal | None = None
            fee = None
            trade_type: TradeType | None = None

            for row in trade_rows:
                cur_asset = row['Coin']
                amount = row['Change']
                if row['Operation'] in {'Fee', 'Transaction Fee'}:
                    fee = AssetAmount(asset=cur_asset, amount=abs(amount))
                else:
                    trade_type = TradeType.SELL if row['Operation'] == 'Sell' else TradeType.BUY
                    if amount < 0:
                        from_asset = cur_asset
                        from_amount = FVal(-amount)
                    else:
                        to_asset = cur_asset
                        to_amount = amount

            # Validate that we have received proper assets and amounts.
            # There can be no fee, so we don't validate it
            if (
                to_asset is None or from_asset is None or trade_type is None or
                to_amount is None or to_amount == ZERO or
                from_amount is None or from_amount == ZERO
            ):
                for row in trade_rows:
                    importer.send_message(
                        row_index=row[INDEX],
                        csv_row=row,
                        msg='Trade associated with row is missing required assets or amounts.',
                        is_error=True,
                    )
                continue

            swap_events.extend(create_swap_events(
                timestamp=ts_sec_to_ms(timestamp),
                location=Location.BINANCE,
                spend=AssetAmount(asset=from_asset, amount=from_amount),
                receive=AssetAmount(asset=to_asset, amount=to_amount),
                fee=fee,
                event_identifier=f'{EVENT_IDENTIFIER_PREFIX}{hash_binance_csv_row(trade_rows[0])}',  # any row works, just using the first to create the event identifier  # noqa: E501
                spend_notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            ))

        return swap_events

    def process_entries(
            self,
            write_cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: list[BinanceCsvRow],
    ) -> int:
        swap_events = self.process_trades(importer=importer, timestamp=timestamp, data=data)
        importer.add_history_events(write_cursor=write_cursor, history_events=swap_events)
        return len(swap_events)


class BinanceDepositWithdrawEntry(BinanceSingleEntry):
    """This class processes Deposit and Withdraw actions
        which are AssetMovements in the internal representation"""

    AVAILABLE_OPERATIONS: Final[tuple[str, ...]] = (  # type: ignore[misc]  # figure out how to mark final only in this class
        'Deposit',
        'Buy Crypto',  # it's a direct buy where you deposit fiat and get credited with crypto
        'Fiat Deposit',
        'Withdraw',
    )

    def process_entry(
            self,
            write_cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: BinanceCsvRow,
    ) -> None:
        asset = data['Coin']
        importer.add_history_events(write_cursor, [AssetMovement(
            location=Location.BINANCE,
            event_type=HistoryEventType.WITHDRAWAL if data['Operation'] == 'Withdraw' else HistoryEventType.DEPOSIT,  # else clause also covers 'Buy Crypto' & 'Fiat Deposit'  # noqa: E501
            timestamp=ts_sec_to_ms(timestamp),
            asset=asset,
            amount=abs(data['Change']),
        )])


class BinanceDistributionEntry(BinanceSingleEntry):
    """Used to handle the distributions on Binance"""
    AVAILABLE_OPERATIONS = (
        'Cash Voucher Distribution',
        'Mission Reward Distribution',
    )

    def process_entry(
            self,
            write_cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: BinanceCsvRow,
    ) -> None:
        """
        Process distributions from binance. It includes
        Cash Voucher Distribution and Mission Reward Distribution. May raise:
        - KeyError
        - DeserializationError: if the event is malformed when being stored in the db
        """
        importer.add_history_events(write_cursor, history_events=[
            HistoryEvent(
                event_identifier=f'{EVENT_IDENTIFIER_PREFIX}{hash_binance_csv_row(data)}',
                sequence_index=0,
                timestamp=ts_sec_to_ms(timestamp),
                location=Location.BINANCE,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.REWARD,
                asset=data['Coin'],
                amount=data['Change'],
                location_label='CSV import',
                notes=f'Reward from {data["Operation"]}',
            ),
        ])


class BinanceStakingRewardsEntry(BinanceSingleEntry):
    """
    Processing ETH 2.0 Staking Rewards and Launchpool Interests. Also processes
    other staking rewards in the Binance program.
    """

    AVAILABLE_OPERATIONS: Final[tuple[str, ...]] = (  # type: ignore[misc]  # figure out how to mark final only in this class
        'ETH 2.0 Staking Rewards',
        'Launchpool Interest',
        'Staking Rewards',
    )

    def process_entry(
            self,
            write_cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: BinanceCsvRow,
    ) -> None:
        event = HistoryEvent(
            event_identifier=f'{EVENT_IDENTIFIER_PREFIX}{hash_binance_csv_row(data)}',
            sequence_index=0,
            timestamp=ts_sec_to_ms(timestamp),
            location=Location.BINANCE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            amount=data['Change'],
            asset=data['Coin'],
            notes=f'Imported from binance CSV file. Binance operation: {data["Operation"]}',
        )
        importer.add_history_events(write_cursor=write_cursor, history_events=[event])


class BinanceEarnProgram(BinanceSingleEntry):
    AVAILABLE_OPERATIONS = (
        'Simple Earn Flexible Interest',
        'Simple Earn Flexible Subscription',
        'Simple Earn Locked Subscription',
        'Simple Earn Locked Rewards',
        'Simple Earn Locked Redemption',
        'Simple Earn Flexible Redemption',
        'Staking Redemption',
        'BNB Vault Rewards',
        'Swap Farming Rewards',
        'Staking Purchase',
    )

    def process_entry(
            self,
            write_cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: BinanceCsvRow,
    ) -> None:
        """
        Process rewards, deposit and withdrawals from the binance earn program. It includes
        the flexible deposit, locking and staking. May raise:
        - KeyError
        - DeserializationError: if the event is malformed when being stored in the db
        """
        asset = data['Coin']
        amount = abs(data['Change'])
        event_identifier = f'{EVENT_IDENTIFIER_PREFIX}{hash_binance_csv_row(data)}'
        timestamp_ms = ts_sec_to_ms(timestamp)
        staking_event = None
        if data['Operation'] in {
            'Simple Earn Flexible Interest',
            'Simple Earn Locked Rewards',
            'BNB Vault Rewards',
            'Swap Farming Rewards',
        }:
            staking_event = HistoryEvent(
                event_identifier=event_identifier,
                sequence_index=0,
                timestamp=timestamp_ms,
                location=Location.BINANCE,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.REWARD,
                asset=asset,
                amount=amount,
                location_label='CSV import',
                notes=f'Reward from {data["Operation"]}',
            )
        elif data['Operation'] in {
            'Simple Earn Flexible Subscription',
            'Simple Earn Locked Subscription',
            'Staking Purchase',
        }:
            staking_event = HistoryEvent(
                event_identifier=event_identifier,
                sequence_index=0,
                timestamp=timestamp_ms,
                location=Location.BINANCE,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=asset,
                amount=amount,
                location_label='CSV import',
                notes=f'Deposit in {data["Operation"]}',
            )
        elif data['Operation'] in {
            'Simple Earn Locked Redemption',
            'Simple Earn Flexible Redemption',
            'Staking Redemption',
        }:
            staking_event = HistoryEvent(
                event_identifier=event_identifier,
                sequence_index=0,
                timestamp=timestamp_ms,
                location=Location.BINANCE,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.REMOVE_ASSET,
                asset=asset,
                amount=amount,
                location_label='CSV import',
                notes=f'Unstake {asset} in {data["Operation"]}',
            )
        if staking_event is None:
            raise UnsupportedCSVEntry(f'Unknown staking event operation: {data["Operation"]}.')
        importer.add_history_events(write_cursor=write_cursor, history_events=[staking_event])


class BinanceUSDMProgram(BinanceSingleEntry):
    """All Binance USDM Program Single Events are processed here"""
    ACCOUNT = 'USD-MFutures'  # specifying account because fee is ambiguous
    AVAILABLE_OPERATIONS = (
        'Fee',
        'Funding Fee',
        'Realized Profit and Loss',
    )

    def is_entry(self, requested_operation: str, account: str, change: FVal) -> bool:
        if requested_operation in {'Fee', 'Funding Fee'} and change == abs(change):
            return False
        return requested_operation in self.AVAILABLE_OPERATIONS and account == self.ACCOUNT

    def _get_event(self, timestamp: Timestamp, data: BinanceCsvRow) -> HistoryEvent:
        """
        Process USDM Program Events. It includes
        Fee, Funding Fee, and Realized Profit and Loss. May raise:
        - KeyError
        """
        amount = abs(data['Change'])
        if data['Operation'] in {'Fee', 'Funding Fee'}:
            event_type = HistoryEventType.SPEND
            event_subtype = HistoryEventSubType.FEE
            notes = f'{amount} {data["Coin"].symbol} fee paid on binance USD-MFutures'
        else:  # is Realized Profit and Loss
            is_profit = data['Change'] == amount
            event_type = HistoryEventType.RECEIVE if is_profit else HistoryEventType.SPEND
            event_subtype = HistoryEventSubType.REWARD if is_profit else HistoryEventSubType.PAYBACK_DEBT  # noqa: E501
            action = 'profit' if is_profit else 'loss'
            notes = f'{amount} {data["Coin"].symbol} realized {action} on binance USD-MFutures'
        return HistoryEvent(
            event_identifier=f'{EVENT_IDENTIFIER_PREFIX}{hash_binance_csv_row(data)}',
            sequence_index=0,
            timestamp=ts_sec_to_ms(timestamp),
            location=Location.BINANCE,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=data['Coin'],
            amount=amount,
            location_label='CSV import',
            notes=notes,
        )

    def process_entry(
            self,
            write_cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: BinanceCsvRow,
    ) -> None:
        """
        Processes and adds the history event to db
        May raise:
        - KeyError
        - DeserializationError: if the event is malformed when being stored in the db
        """
        history_event = self._get_event(timestamp, data)
        importer.add_history_events(write_cursor=write_cursor, history_events=[history_event])


class BinancePOSEntry(BinanceSingleEntry):
    """Processing POS related actions"""

    AVAILABLE_OPERATIONS: Final[tuple[str, ...]] = (  # type: ignore[misc]  # figure out how to mark final only in this class
        'POS savings interest',
        'POS savings purchase',
        'POS savings redemption',
    )

    def process_entry(
            self,
            write_cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: BinanceCsvRow,
    ) -> None:
        if data['Change'] >= 0:
            event_type = HistoryEventType.RECEIVE
            event_subtype = HistoryEventSubType.NONE
        else:
            event_type = HistoryEventType.SPEND
            event_subtype = HistoryEventSubType.NONE

        event = HistoryEvent(
            event_identifier=f'{EVENT_IDENTIFIER_PREFIX}{hash_binance_csv_row(data)}',
            sequence_index=0,
            timestamp=ts_sec_to_ms(timestamp),
            location=Location.BINANCE,
            event_type=event_type,
            event_subtype=event_subtype,
            amount=abs(data['Change']),
            asset=data['Coin'],
            notes=f'Imported from binance CSV file. Binance operation: {data["Operation"]}',
        )
        importer.add_history_events(write_cursor=write_cursor, history_events=[event])


SINGLE_BINANCE_ENTRIES: list[BinanceSingleEntry] = [
    BinanceDepositWithdrawEntry(),
    BinanceStakingRewardsEntry(),
    BinancePOSEntry(),
    BinanceEarnProgram(),
    BinanceUSDMProgram(),
    BinanceDistributionEntry(),
]

MULTIPLE_BINANCE_ENTRIES: list[BinanceMultipleEntry] = [
    BinanceTradeEntry(),
    BinanceTransferEntry(),
]


class BinanceImporter(BaseExchangeImporter):
    """Binance CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Binance')

    def _group_binance_rows(
            self,
            rows: list[BinanceCsvRow],
            timestamp_format: str = '%Y-%m-%d %H:%M:%S',
    ) -> tuple[int, dict[Timestamp, list[BinanceCsvRow]]]:
        """Groups Binance rows by timestamp and deletes unused columns"""
        multirows: dict[Timestamp, list[BinanceCsvRow]] = defaultdict(list)
        skipped_count = 0
        for index, csv_row in enumerate(rows, start=1):
            try:
                timestamp = deserialize_timestamp_from_date(
                    date=csv_row['UTC_Time'],
                    formatstr=timestamp_format,
                    location='binance',
                )
                csv_row['Coin'] = asset_from_binance(csv_row['Coin'])
                csv_row['Change'] = deserialize_asset_amount(csv_row['Change'])
                csv_row[INDEX] = index
                multirows[timestamp].append(csv_row)
            except UnknownAsset as e:
                self.send_message(
                    row_index=index,
                    csv_row=csv_row,
                    msg=f'Unknown asset "{e.identifier}" provided.',
                    is_error=True,
                )
                skipped_count += 1
            except (DeserializationError, UnsupportedAsset) as e:
                self.send_message(
                    row_index=index,
                    csv_row=csv_row,
                    msg=str(e),
                    is_error=True,
                )
                skipped_count += 1
            except KeyError as e:
                raise InputError(f'Malformed binance csv columns! {e!s}') from e

        return skipped_count, multirows

    def _process_single_binance_entries(
            self,
            write_cursor: DBCursor,
            timestamp: Timestamp,
            rows: list[BinanceCsvRow],
    ) -> tuple[int, dict[BinanceSingleEntry, int], list[BinanceCsvRow]]:
        """
        Processes binance entries that are represented with a single row in a csv file.
        May raise:
        - InputError
        """
        processed: dict[BinanceSingleEntry, int] = defaultdict(int)
        ignored: list[BinanceCsvRow] = []
        skipped_count: int = 0
        for row in rows:
            for single_entry_class in SINGLE_BINANCE_ENTRIES:
                try:
                    if single_entry_class.is_entry(
                        requested_operation=row['Operation'],
                        account=row['Account'],
                        change=row['Change'],
                    ):
                        single_entry_class.process_entry(
                            write_cursor=write_cursor,
                            importer=self,
                            timestamp=timestamp,
                            data=row,
                        )
                        processed[single_entry_class] += 1
                        break
                except UnsupportedCSVEntry as e:
                    self.send_message(
                        row_index=row[INDEX],
                        csv_row=row,
                        msg=str(e),
                        is_error=True,
                    )
                    skipped_count += 1
                    break
                except KeyError as e:
                    raise InputError(f'Could not read key {e} in binance CSV row {row}') from e
                except DeserializationError as e:
                    raise InputError(
                        f'Could not deserialize object {e} before adding it to the database',
                    ) from e
            else:  # there was no break in the for loop above
                ignored.append(row)
        return skipped_count, processed, ignored

    def _process_multiple_binance_entries(
            self,
            write_cursor: DBCursor,
            timestamp: Timestamp,
            rows: list[BinanceCsvRow],
    ) -> tuple[BinanceEntry | None, int]:
        """Processes binance entries that are represented with 2+ rows in a csv file.
        Returns Entry type and entries count if any entries were processed. Otherwise, None and 0.
        """
        operations = [row['Operation'] for row in rows]
        for multiple_entry_class in MULTIPLE_BINANCE_ENTRIES:
            if multiple_entry_class.are_entries(operations):
                processed_count = multiple_entry_class.process_entries(
                    write_cursor=write_cursor,
                    importer=self,
                    timestamp=timestamp,
                    data=rows,
                )
                return multiple_entry_class, processed_count

        for row in rows:
            self.send_message(
                row_index=row[INDEX],
                csv_row=row,
                msg=f'Could not process row in multi-line entry. Expected a valid combination of operations but got "{", ".join(operations)}" instead',  # noqa: E501
                is_error=True,
            )
        return None, 0

    def _process_binance_rows(
            self,
            write_cursor: DBCursor,
            multi: dict[Timestamp, list[BinanceCsvRow]],
    ) -> int:
        """Process binance entries grouped by timestamp
        Returns a count of how many rows were skipped during import
        """
        stats: dict[BinanceEntry, int] = defaultdict(int)
        ignored_rows: list[Any] = []
        skipped_count: int = 0
        for timestamp, rows in multi.items():
            skipped_count_single, single_processed, rows_without_single = self._process_single_binance_entries(  # noqa: E501
                write_cursor=write_cursor,
                timestamp=timestamp,
                rows=rows,
            )
            skipped_count += skipped_count_single
            for entry_type, amount in single_processed.items():
                stats[entry_type] += amount

            multiple_type, multiple_count = self._process_multiple_binance_entries(
                write_cursor=write_cursor,
                timestamp=timestamp,
                rows=rows_without_single,
            )
            if multiple_type is not None and multiple_count > 0:
                stats[multiple_type] += multiple_count
                rows_without_multiple = []
            else:
                rows_without_multiple = rows_without_single

            skipped_count += len(rows_without_multiple)
            if len(rows_without_multiple) > 0:
                ignored_rows.append([timestamp, rows_without_multiple])

        skipped_nontrade_rows = []
        skipped_trade_rows = []
        for skipped_rows_group in ignored_rows:
            cur_operations = {el['Operation'] for el in skipped_rows_group[1]}
            if cur_operations.issubset(BINANCE_TRADE_OPERATIONS):
                skipped_trade_rows.append(skipped_rows_group)
            else:
                skipped_nontrade_rows.append(skipped_rows_group)
        total_found = sum(stats.values())
        ignored_count = 0
        for _, rows in ignored_rows:
            ignored_count += len(rows)
        log.debug(f'Skipped Binance trade rows: {skipped_trade_rows}')
        log.debug(f'Skipped Binance non-trade rows {skipped_nontrade_rows}')
        log.debug(f'Total found Binance entries: {total_found}')
        log.debug(f'Total skipped Binance csv rows: {ignored_count}')
        log.debug(f'Binance import stats: {[{type(entry_class).__name__: amount} for entry_class, amount in stats.items()]}')  # noqa: E501

        return skipped_count

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Group and process binance CSV entries. May raise:
        - InputError
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            input_rows = list(csv.DictReader(csvfile))
            self.total_entries = len(input_rows)
            skipped_count, multirows = self._group_binance_rows(rows=input_rows, **kwargs)
            skipped_count += self._process_binance_rows(write_cursor=write_cursor, multi=multirows)
            self.imported_entries = self.total_entries - skipped_count
