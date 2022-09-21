import abc
import csv
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.data_import.utils import BaseExchangeImporter
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import (
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeID,
    TradeType,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BinanceCsvRow = Dict[str, Any]
BINANCE_TRADE_OPERATIONS = {'Buy', 'Sell', 'Fee'}


class BinanceEntry(metaclass=abc.ABCMeta):
    """This is a base BinanceEntry class
    All row combinations in the Binance csv have to be inherited from this base class
    """


class BinanceSingleEntry(BinanceEntry, metaclass=abc.ABCMeta):
    """Children of this class represent single-row entries
    It means that all required data to create an internal representation
    is contained in one csv row

    Children should have a class-variable "available_operations" which describes
    which "Operation" types can be processed by a class
    """
    available_operations: List[str]

    def is_entry(self, requested_operation: str) -> bool:
        """This method checks whether row with "requested_operation" could be processed
        by a class on which this method has been called
        The default implementation can also be used in a subclass"""
        return requested_operation in self.available_operations

    @abc.abstractmethod
    def process_entry(
            self,
            cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: BinanceCsvRow,
    ) -> None:
        """This method receives a csv row and processes it into internal Rotki's representation
        Should be implemented by subclass."""
        ...


class BinanceMultipleEntry(BinanceEntry, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def are_entries(self, requested_operations: List) -> bool:
        """The subclass's method checks whether requested operations can be processed
        Not implemented here because the logic can differ for each subclass"""
        ...

    @abc.abstractmethod
    def process_entries(
            self,
            cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: List[BinanceCsvRow],
    ) -> int:
        """Turns given csv rows into internal Rotki's representation"""
        ...


class BinanceTradeEntry(BinanceMultipleEntry):
    def are_entries(self, requested_operations: List) -> bool:
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
        """
        counted = Counter(requested_operations)
        fee = counted.pop('Fee', None)
        keys = set(counted.keys())
        return (
            (
                keys == {'Buy', 'Sell'} and counted['Buy'] % 2 == 0 and counted['Sell'] % 2 == 0 and  # noqa: E501
                (not fee or counted['Sell'] + counted['Buy'] == fee * 2)
            ) or
            (keys == {'Buy'} and counted['Buy'] % 2 == 0 and (not fee or counted['Buy'] == fee * 2)) or  # noqa: E501
            (keys == {'Sell'} and counted['Sell'] % 2 == 0 and (not fee or counted['Sell'] == fee * 2)) or  # noqa: E501
            (keys == {'Transaction Related'} and counted['Transaction Related'] % 2 == 0) or
            (keys == {'Small assets exchange BNB'} and counted['Small assets exchange BNB'] % 2 == 0) or  # noqa: E501
            (keys == {'ETH 2.0 Staking'} and counted['ETH 2.0 Staking'] % 2 == 0)
        )

    @staticmethod
    def process_trades(
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: List[BinanceCsvRow],
    ) -> List[Trade]:
        """Processes multiple rows data and stores it into rotki's trades
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
        assets: Dict[str, Optional[AssetWithOracles]] = defaultdict(lambda: None)
        for row in data:
            if row['Operation'] == 'Fee':
                cur_operation = 'Fee'
            elif row['Change'] < 0:
                cur_operation = 'Sold'
            else:
                cur_operation = 'Bought'
            assets[cur_operation] = assets[cur_operation] or row['Coin']
            if assets[cur_operation] != row['Coin']:
                same_assets = False
                break

        # Querying usd value if needed
        if same_assets is False:
            for row in data:
                try:
                    price = PriceHistorian.query_historical_price(
                        from_asset=row['Coin'],
                        to_asset=A_USD,
                        timestamp=timestamp,
                    )
                except NoPriceForGivenTimestamp:
                    # If we can't find price we can't group, so we quit the method
                    log.warning(f'Couldn\'t find price of {row["Coin"]} on {timestamp}')
                    return []
                row['usd_value'] = row['Change'] * price

        # Group rows depending on whether they are fee or not and then sort them by amount
        rows_grouped_by_fee: Dict[bool, List[BinanceCsvRow]] = defaultdict(list)
        for row in data:
            is_fee = row['Operation'] == 'Fee'
            rows_grouped_by_fee[is_fee].append(row)

        for rows_group in rows_grouped_by_fee.values():
            rows_group.sort(key=lambda x: x['Change'] if same_assets else x['usd_value'], reverse=True)  # noqa: E501

        # Grouping by combining the highest sold with the highest bought and the highest fee
        # Using fee only we were provided with fee (checking by "True in rows_by_operation")
        grouped_trade_rows = []
        while len(rows_grouped_by_fee[False]) > 0:
            cur_batch = [rows_grouped_by_fee[False].pop(), rows_grouped_by_fee[False].pop(0)]
            if True in rows_grouped_by_fee:
                cur_batch.append(rows_grouped_by_fee[True].pop())
            grouped_trade_rows.append(cur_batch)

        # Creating trades structures based on grouped rows data
        raw_trades: List[Trade] = []
        for trade_rows in grouped_trade_rows:
            to_asset: Optional[AssetWithOracles] = None
            to_amount: Optional[AssetAmount] = None
            from_asset: Optional[AssetWithOracles] = None
            from_amount: Optional[AssetAmount] = None
            fee_asset: Optional[AssetWithOracles] = None
            fee_amount: Optional[Fee] = None
            trade_type: Optional[TradeType] = None

            for row in trade_rows:
                cur_asset = row['Coin']
                amount = row['Change']
                if row['Operation'] == 'Fee':
                    fee_asset = cur_asset
                    fee_amount = Fee(amount)
                else:
                    trade_type = TradeType.SELL if row['Operation'] == 'Sell' else TradeType.BUY  # noqa:  E501
                    if amount < 0:
                        from_asset = cur_asset
                        from_amount = AssetAmount(-amount)
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
                log.warning(
                    f'Skipped binance rows {data} because '
                    f'it didn\'t have enough data',
                )
                importer.db.msg_aggregator.add_warning('Skipped some rows because couldn\'t find amounts or it was zero')  # noqa: E501
                continue

            rate = to_amount / from_amount
            trade = Trade(
                timestamp=timestamp,
                location=Location.BINANCE,
                trade_type=trade_type,
                base_asset=to_asset,
                quote_asset=from_asset,
                amount=to_amount,
                rate=Price(rate),
                fee_currency=fee_asset,
                fee=fee_amount,
                link='',
                notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            )
            raw_trades.append(trade)

        # Sometimes we can get absolutely identical trades (including timestamp) but the database
        # allows us to add only one of them. So we combine these trades into a huge single trade
        # First step: group trades
        grouped_trades: Dict[TradeID, List[Trade]] = defaultdict(list)
        for trade in raw_trades:
            grouped_trades[trade.identifier].append(trade)

        # Second step: combine them
        unique_trades = []
        for trades_group in grouped_trades.values():
            result_trade = trades_group[0]
            for trade in trades_group[1:]:
                result_trade.amount = AssetAmount(result_trade.amount + trade.amount)  # noqa: E501
                if result_trade.fee is not None and trade.fee is not None:
                    result_trade.fee = Fee(result_trade.fee + trade.fee)
            unique_trades.append(result_trade)

        return unique_trades

    def process_entries(
            self,
            cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: List[BinanceCsvRow],
    ) -> int:
        trades = self.process_trades(importer=importer, timestamp=timestamp, data=data)
        for trade in trades:
            importer.add_trade(cursor, trade)
        return len(trades)


class BinanceDepositWithdrawEntry(BinanceSingleEntry):
    """This class processes Deposit and Withdraw actions
        which are AssetMovements in the internal representation"""

    available_operations = ['Deposit', 'Withdraw']

    def process_entry(
            self,
            cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: BinanceCsvRow,
    ) -> None:
        amount = data['Change']
        asset = data['Coin']
        category = AssetMovementCategory.DEPOSIT if data['Operation'] == 'Deposit' else AssetMovementCategory.WITHDRAWAL  # noqa: E501
        if category == AssetMovementCategory.WITHDRAWAL:
            amount = -amount

        asset_movement = AssetMovement(
            location=Location.BINANCE,
            category=category,
            address=None,
            transaction_id=None,
            timestamp=timestamp,
            asset=asset,
            amount=AssetAmount(amount),
            fee=Fee(ZERO),
            fee_asset=A_USD,
            link=f'Imported from binance CSV file. Binance operation: {data["Operation"]}',
        )
        importer.add_asset_movement(cursor, asset_movement)


class BinanceStakingRewardsEntry(BinanceSingleEntry):
    """Processing ETH 2.0 Staking Rewards and Launchpool Interest
        which are LedgerActions in the internal representation"""

    available_operations = ['ETH 2.0 Staking Rewards', 'Launchpool Interest']

    def process_entry(
            self,
            cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: BinanceCsvRow,
    ) -> None:
        asset = data['Coin']
        amount = data['Change']
        ledger_action = LedgerAction(
            identifier=0,
            timestamp=timestamp,
            action_type=LedgerActionType.INCOME,
            location=Location.BINANCE,
            amount=amount,
            asset=asset,
            rate=None,
            rate_asset=None,
            link=None,
            notes=f'Imported from binance CSV file. Binance operation: {data["Operation"]}',
        )
        importer.add_ledger_action(cursor, ledger_action)


class BinancePOSEntry(BinanceSingleEntry):
    """Processing POS related actions
        which are LedgerActions in the internal representation"""

    available_operations = [
        'POS savings interest',
        'POS savings purchase',
        'POS savings redemption',
    ]

    def process_entry(
            self,
            cursor: DBCursor,
            importer: BaseExchangeImporter,
            timestamp: Timestamp,
            data: BinanceCsvRow,
    ) -> None:
        asset = data['Coin']
        amount = data['Change']
        action_type = LedgerActionType.INCOME if amount > 0 else LedgerActionType.EXPENSE
        amount = abs(amount)
        ledger_action = LedgerAction(
            identifier=0,
            timestamp=timestamp,
            action_type=action_type,
            location=Location.BINANCE,
            amount=amount,
            asset=asset,
            rate=None,
            rate_asset=None,
            link=None,
            notes=f'Imported from binance CSV file. Binance operation: {data["Operation"]}',
        )
        importer.add_ledger_action(cursor, ledger_action)


SINGLE_BINANCE_ENTRIES = [
    BinanceDepositWithdrawEntry(),
    BinanceStakingRewardsEntry(),
    BinancePOSEntry(),
]

MULTIPLE_BINANCE_ENTRIES = [
    BinanceTradeEntry(),
]


def _group_binance_rows(
        rows: List[BinanceCsvRow],
        timestamp_format: str = '%Y-%m-%d %H:%M:%S',
) -> Tuple[int, Dict[Timestamp, List[BinanceCsvRow]]]:
    """Groups Binance rows by timestamp and deletes unused columns"""
    multirows: Dict[Timestamp, List[BinanceCsvRow]] = defaultdict(list)
    skipped_count = 0
    for csv_row in rows:
        try:
            timestamp = deserialize_timestamp_from_date(
                date=csv_row['UTC_Time'],
                formatstr=timestamp_format,
                location='binance',
            )
            csv_row['Coin'] = asset_from_binance(csv_row['Coin'])
            csv_row['Change'] = deserialize_asset_amount(csv_row['Change'])
            multirows[timestamp].append(csv_row)
        except (DeserializationError, UnknownAsset) as e:
            log.warning(f'Skipped binance csv row {csv_row} because of {str(e)}')
            skipped_count += 1
        except KeyError as e:
            log.error(f'Malformed binance csv columns! Broke on row {csv_row}. {str(e)}')
            return len(rows), {}

    return skipped_count, multirows


class BinanceImporter(BaseExchangeImporter):

    def _process_single_binance_entries(
            self,
            cursor: DBCursor,
            timestamp: Timestamp,
            rows: List[BinanceCsvRow],
    ) -> Tuple[Dict[BinanceSingleEntry, int], List[BinanceCsvRow]]:
        """Processes binance entries that are represented with a single row in a csv file"""
        processed: Dict[BinanceSingleEntry, int] = defaultdict(int)
        ignored: List[BinanceCsvRow] = []
        for row in rows:
            for single_entry_class in SINGLE_BINANCE_ENTRIES:
                if single_entry_class.is_entry(row['Operation']):
                    single_entry_class.process_entry(
                        cursor=cursor,
                        importer=self,
                        timestamp=timestamp,
                        data=row,
                    )
                    processed[single_entry_class] += 1
                    break
            else:  # there was no break in the for loop above
                ignored.append(row)
        return processed, ignored

    def _process_multiple_binance_entries(
            self,
            cursor: DBCursor,
            timestamp: Timestamp,
            rows: List[BinanceCsvRow],
    ) -> Tuple[Optional[BinanceEntry], int]:
        """Processes binance entries that are represented with 2+ rows in a csv file.
        Returns Entry type and entries count if any entries were processed. Otherwise, None and 0.
        """
        for multiple_entry_class in MULTIPLE_BINANCE_ENTRIES:
            if multiple_entry_class.are_entries([row['Operation'] for row in rows]):
                processed_count = multiple_entry_class.process_entries(
                    cursor=cursor,
                    importer=self,
                    timestamp=timestamp,
                    data=rows,
                )
                return multiple_entry_class, processed_count
        return None, 0

    def _process_binance_rows(
            self,
            cursor: DBCursor,
            multi: Dict[Timestamp, List[BinanceCsvRow]],
    ) -> None:
        stats: Dict[BinanceEntry, int] = defaultdict(int)
        skipped_rows: List[Any] = []
        for timestamp, rows in multi.items():
            single_processed, rows_without_single = self._process_single_binance_entries(
                cursor=cursor,
                timestamp=timestamp,
                rows=rows,
            )
            for entry_type, amount in single_processed.items():
                stats[entry_type] += amount

            multiple_type, multiple_count = self._process_multiple_binance_entries(
                cursor=cursor,
                timestamp=timestamp,
                rows=rows_without_single,
            )
            if multiple_type is not None and multiple_count > 0:
                stats[multiple_type] += multiple_count
                rows_without_multiple = []
            else:
                rows_without_multiple = rows_without_single

            if len(rows_without_multiple) > 0:
                skipped_rows.append([timestamp, rows_without_multiple])

        skipped_nontrade_rows = []
        skipped_trade_rows = []
        for skipped_rows_group in skipped_rows:
            cur_operations = {el['Operation'] for el in skipped_rows_group[1]}
            if cur_operations.issubset(BINANCE_TRADE_OPERATIONS):
                skipped_trade_rows.append(skipped_rows_group)
            else:
                skipped_nontrade_rows.append(skipped_trade_rows)
        total_found = sum(stats.values())
        skipped_count = 0
        for _, rows in skipped_rows:
            skipped_count += len(rows)
        log.debug(f'Skipped Binance trade rows: {skipped_trade_rows}')
        log.debug(f'Skipped Binance non-trade rows {skipped_nontrade_rows}')
        log.debug(f'Total found Binance entries: {total_found}')
        log.debug(f'Total skipped Binance csv rows: {skipped_count}')
        log.debug('Binance import stats: {}'.format(
            [{type(entry_class).__name__: amount} for entry_class, amount in stats.items()],
        ))
        if skipped_count > 0:
            self.db.msg_aggregator.add_warning(
                f'Skipped {skipped_count} rows during processing binance csv file. '
                f'Check logs for details',
            )

    def _import_csv(self, cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            input_rows = list(csv.DictReader(csvfile))
            skipped_count, multirows = _group_binance_rows(rows=input_rows, **kwargs)
            if skipped_count > 0:
                self.db.msg_aggregator.add_warning(
                    f'{skipped_count} Binance rows have bad format. Check logs for details.',
                )
            self._process_binance_rows(cursor, multirows)
