import logging
from collections import Counter, defaultdict
from itertools import groupby
from typing import Any, Dict, List, Optional

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
)

BinanceCsvRow = Dict[str, Any]
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BinanceEntry:
    """This is a base BinanceEntry class
    All row combinations in the Binance csv have to be inherited from this base class
    """

    db: DBHandler
    db_ledger: DBLedgerActions


class BinanceSingleEntry(BinanceEntry):
    """Children of this class represent a single-row entries
    It means that all required data to create an internal representation
    is contained in one csv row

    Children should have a class-variable "available_operations" which describes
    which "Operation" types can be processed by a class
    """
    available_operations: List[str]

    @classmethod
    def is_entry(cls, requested_operation: str) -> bool:
        """This method checks whether row with "requested_operation" could be processed
        by a class on which this method has been called
        The default implementation can also be used in a subclass"""
        return requested_operation in cls.available_operations

    @classmethod
    def process_entry(cls, timestamp: Timestamp, data: BinanceCsvRow) -> None:
        """This method receives csv row and processes it into internal Rotki's representation
        Should be implemented by subclass."""
        raise NotImplementedError('Should be implemented by subclass')


class BinanceMultipleEntry(BinanceEntry):
    @classmethod
    def are_entries(cls, requested_operations: List) -> bool:
        """The subclass's method checks whether requested operations can be processed
        Not implemented here because the logic can differ for each subclass"""
        raise NotImplementedError('Should be implemented by subclass')

    @classmethod
    def process_entries(cls, timestamp: Timestamp, data: List[BinanceCsvRow]) -> int:
        """Turns given csv rows into internal Rotki's representation"""
        raise NotImplementedError('Should be implemented by subclass')


class BinanceTradeEntry(BinanceMultipleEntry):
    @classmethod
    def are_entries(cls, requested_operations: List) -> bool:
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
            (keys == {'Small assets exchange BNB'} and counted['Small assets exchange BNB'] % 2 == 0)  # noqa: E501
        )

    @staticmethod
    def is_fee_key(x: BinanceCsvRow) -> bool:
        return x['Operation'] == 'Fee'

    @staticmethod
    def unique_trades_key(t_dict: Dict) -> str:
        # Because we list and dict are unhashable, we need this function to sort and group them
        return ';'.join(sorted([f'{x[0]}: {x[1]}' for x in t_dict.items()]))

    @classmethod
    def process_trades(cls, timestamp: Timestamp, data: List[BinanceCsvRow]) -> List[Trade]:
        """Processes multirows data and stores it into Rotki's Trades"""

        # Each row has format: {'Operation': ..., 'Change': ..., 'Coin': ...}
        # Change is amount, Coin is asset
        # If amount is negative then this asset is sold, otherwise it's bought

        # Because we can get mixed data (e.g. multiple Buys or Sells on a single timestamp) we need
        # to group it somehow. We are doing it by grouping the highest bought with the highest
        # sold value. We query usd equivalent for each amount because different Sells / Buys
        # may use different assets.

        # Querying price takes a long time, so we would like to avoid it,
        # and therefore we check if all Buys / Sells use the same asset.
        # If so, we can group by original amount.

        # Checking assets
        same_assets = True
        assets: Dict[str, Optional[Asset]] = defaultdict(lambda: None)
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
        if not same_assets:
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

        # Soring by amount
        rows_by_operation = {}
        for is_fee, rows in groupby(sorted(data, key=cls.is_fee_key), key=cls.is_fee_key):
            rows_by_operation[is_fee] = sorted(
                rows, key=lambda x: x['Change'] if same_assets else x['usd_value'],
            )

        # Grouping by combining the highest sold with the highest bought and the highest fee
        # Using fee only we were provided with fee (checking by "True in rows_by_operation")
        grouped_trade_rows = []
        while len(rows_by_operation[False]) > 0:
            cur_batch = [rows_by_operation[False].pop(0), rows_by_operation[False].pop(-1)]
            if True in rows_by_operation:
                cur_batch.append(rows_by_operation[True].pop(0))
            grouped_trade_rows.append(cur_batch)

        # Sometimes we can get absolutely identical trades, so we prepare data
        # by creating dictionaries with values
        # We don't create Trade classes there because Trade classes are immutable
        # so working with dictionaries is nicer here
        prepared_trade_dicts = []
        for trade_rows in grouped_trade_rows:
            cur_data: BinanceCsvRow = defaultdict(lambda: None)
            for row in trade_rows:
                cur_asset = row['Coin']
                amount = row['Change']
                if row['Operation'] == 'Fee':
                    cur_data['fee_asset'] = cur_asset
                    cur_data['fee_amount'] = Fee(amount)
                else:
                    cur_data['trade_type'] = TradeType.SELL if row['Operation'] == 'Sell' else TradeType.BUY  # noqa:  E501
                    if amount < 0:
                        cur_data['from_asset'] = cur_asset
                        cur_data['from_amount'] = AssetAmount(-amount)
                    else:
                        cur_data['to_asset'] = cur_asset
                        cur_data['to_amount'] = amount
            prepared_trade_dicts.append(cur_data)

        # Validating that all trades have required properties
        # Assets are validated in the grouping method, so we don't need to do it there
        for dict_trade in prepared_trade_dicts:
            if (
                dict_trade['to_amount'] is None or dict_trade['to_amount'] == ZERO or
                dict_trade['from_amount'] is None or dict_trade['from_amount'] == ZERO
            ):
                log.warning(
                    f'Skipped binance rows {data} because '
                    f'trade {dict_trade} didn\'t have enough amounts data',
                )
                cls.db.msg_aggregator.add_warning(
                    'Skipped some rows because couldn\'t find amounts or it was zero',
                )
                return []

        # Grouping identical trades
        grouped_trades_dicts = []
        for _, grouped_trades in groupby(sorted(prepared_trade_dicts, key=cls.unique_trades_key), key=cls.unique_trades_key):  # noqa: E501
            grouped_trades_dicts.append(list(grouped_trades))

        # Combining identical trades
        unique_trade_dicts = []
        for trades_dict_group in grouped_trades_dicts:
            result_trade_dict = trades_dict_group[0]
            for trade_dict in trades_dict_group[1:]:
                result_trade_dict['to_amount'] += trade_dict['to_amount']
                result_trade_dict['from_amount'] += trade_dict['from_amount']
                if result_trade_dict['fee_amount'] is not None:
                    result_trade_dict['fee_amount'] += trade_dict['fee_amount']
            unique_trade_dicts.append(result_trade_dict)

        # Creating Trade classes.
        trades = []
        for trade_dict in unique_trade_dicts:
            rate = FVal(trade_dict['to_amount']) / FVal(trade_dict['from_amount'])
            trades.append(Trade(
                timestamp=timestamp,
                location=Location.BINANCE,
                base_asset=trade_dict['to_asset'],
                quote_asset=trade_dict['from_asset'],
                trade_type=trade_dict['trade_type'],
                amount=trade_dict['to_amount'],
                rate=Price(rate),
                fee=trade_dict['fee_amount'],
                fee_currency=trade_dict['fee_asset'],
                link='',
            ))
        return trades

    @classmethod
    def process_entries(cls, timestamp: Timestamp, data: List[BinanceCsvRow]) -> int:
        trades = cls.process_trades(timestamp=timestamp, data=data)
        cls.db.add_trades(trades)
        return len(trades)


class BinanceStakingEntry(BinanceMultipleEntry):
    """This class processes ETH 2.0 Staking events"""

    @classmethod
    def are_entries(cls, requested_operations: List) -> bool:
        """Processing only pairs of ETH 2.0 Staking"""
        return (
            requested_operations == ['ETH 2.0 Staking', 'ETH 2.0 Staking']
        )

    @classmethod
    def process_entries(cls, timestamp: Timestamp, data: List[BinanceCsvRow]) -> int:
        # Both rows have identical values except amount with is positive / negative
        # So we can use data from only one row"""
        amount = abs(data[0]['Change'])
        asset = data[0]['Coin']

        ledger_action = LedgerAction(
            identifier=0,
            timestamp=timestamp,
            action_type=LedgerActionType.EXPENSE,
            location=Location.BINANCE,
            amount=amount,
            asset=asset,
            rate=None,
            rate_asset=None,
            link=None,
            notes='ETH 2.0 Staking',
        )
        cls.db_ledger.add_ledger_action(ledger_action)
        return 1


class BinanceDepositWithdrawEntry(BinanceSingleEntry):
    """This class processes Deposit and Withdraw actions
        which are AssetMovements in the internal representation"""

    available_operations = ['Deposit', 'Withdraw']

    @classmethod
    def process_entry(cls, timestamp: Timestamp, data: BinanceCsvRow) -> None:
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
            link='',
        )
        cls.db.add_asset_movements([asset_movement])


class BinanceStakingRewardsEntry(BinanceSingleEntry):
    """Processing ETH 2.0 Staking Rewards and Launchpool Interest
        which are LedgerActions in the internal representation"""

    available_operations = ['ETH 2.0 Staking Rewards', 'Launchpool Interest']

    @classmethod
    def process_entry(cls, timestamp: Timestamp, data: BinanceCsvRow) -> None:
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
            notes=data['Operation'],
        )
        cls.db_ledger.add_ledger_action(ledger_action)


class BinancePOSEntry(BinanceSingleEntry):
    """Processing POS related actions
        which are LedgerActions in the internal representation"""

    available_operations = [
        'POS savings interest',
        'POS savings purchase',
        'POS savings redemption',
    ]

    @classmethod
    def process_entry(cls, timestamp: Timestamp, data: BinanceCsvRow) -> None:
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
            notes=data['Operation'],
        )
        cls.db_ledger.add_ledger_action(ledger_action)
