import csv
import logging
from pathlib import Path
from typing import Any, Dict

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.assets.converters import asset_from_uphold
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import BaseExchangeImporter
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, AssetMovementCategory, Fee, Location, Price, TradeType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class UpholdTransactionsImporter(BaseExchangeImporter):
    def _consume_uphold_transaction(
            self,
            cursor: DBCursor,
            csv_row: Dict[str, Any],
            timestamp_format: str = '%a %b %d %Y %H:%M:%S %Z%z',
    ) -> None:
        """
        Consume the file containing both trades and transactions from uphold.
        This method can raise:
        - UnknownAsset
        - DeserializationError
        - KeyError
        """
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Date'],
            formatstr=timestamp_format,
            location='uphold',
        )
        destination = csv_row['Destination']
        destination_asset = asset_from_uphold(csv_row['Destination Currency'])
        destination_amount = deserialize_asset_amount(csv_row['Destination Amount'])
        origin = csv_row['Origin']
        origin_asset = asset_from_uphold(csv_row['Origin Currency'])
        origin_amount = deserialize_asset_amount(csv_row['Origin Amount'])
        if csv_row['Fee Amount'] == '':
            fee = FVal(ZERO)
        else:
            fee = deserialize_fee(csv_row['Fee Amount'])
        fee_asset = asset_from_uphold(csv_row['Fee Currency'] or csv_row['Origin Currency'])
        transaction_type = csv_row['Type']
        notes = f"""
Activity from uphold with uphold transaction id:
 {csv_row['Id']}, origin: {csv_row['Origin']},
 and destination: {csv_row['Destination']}.
  Type: {csv_row['Type']}.
  Status: {csv_row['Status']}.
"""
        if origin == destination == 'uphold':  # On exchange Transfers / Trades
            if origin_asset == destination_asset and origin_amount == destination_amount:
                if transaction_type == 'in':
                    action_type = LedgerActionType.INCOME
                elif transaction_type == 'out':
                    action_type = LedgerActionType.EXPENSE
                else:
                    log.debug(f'Ignoring uncaught transaction type of {transaction_type}.')
                    return
                action = LedgerAction(
                    identifier=0,
                    timestamp=timestamp,
                    action_type=action_type,
                    location=Location.UPHOLD,
                    amount=destination_amount,
                    asset=destination_asset,
                    rate=None,
                    rate_asset=None,
                    link='',
                    notes=notes,
                )
                self.add_ledger_action(cursor, action)
            else:  # Assets or amounts differ (Trades)
                # in uphold UI the exchanged amount includes the fee.
                if fee_asset == destination_asset:
                    destination_amount = AssetAmount(destination_amount + fee)
                if destination_amount > 0:
                    trade = Trade(
                        timestamp=timestamp,
                        location=Location.UPHOLD,
                        base_asset=destination_asset,
                        quote_asset=origin_asset,
                        trade_type=TradeType.BUY,
                        amount=destination_amount,
                        rate=Price(origin_amount / destination_amount),
                        fee=Fee(fee),
                        fee_currency=fee_asset,
                        link='',
                        notes=notes,
                    )
                    self.add_trade(cursor, trade)
                else:
                    log.debug(f'Ignoring trade with Destination Amount: {destination_amount}.')
        elif origin == 'uphold':
            if transaction_type == 'out':
                if origin_asset == destination_asset:  # Withdrawals
                    asset_movement = AssetMovement(
                        location=Location.UPHOLD,
                        category=AssetMovementCategory.WITHDRAWAL,
                        address=None,
                        transaction_id=None,
                        timestamp=timestamp,
                        asset=origin_asset,
                        amount=origin_amount,
                        fee=Fee(fee),
                        fee_asset=fee_asset,
                        link='',
                    )
                    self.add_asset_movement(cursor, asset_movement)
                else:  # Trades (sell)
                    if origin_amount > 0:
                        trade = Trade(
                            timestamp=timestamp,
                            location=Location.UPHOLD,
                            base_asset=origin_asset,
                            quote_asset=destination_asset,
                            trade_type=TradeType.SELL,
                            amount=origin_amount,
                            rate=Price(destination_amount / origin_amount),
                            fee=Fee(fee),
                            fee_currency=fee_asset,
                            link='',
                            notes=notes,
                        )
                        self.add_trade(cursor, trade)
                    else:
                        log.debug(f'Ignoring trade with Origin Amount: {origin_amount}.')
        elif destination == 'uphold':
            if transaction_type == 'in':
                if origin_asset == destination_asset:  # Deposits
                    asset_movement = AssetMovement(
                        location=Location.UPHOLD,
                        category=AssetMovementCategory.DEPOSIT,
                        address=None,
                        transaction_id=None,
                        timestamp=timestamp,
                        asset=origin_asset,
                        amount=origin_amount,
                        fee=Fee(fee),
                        fee_asset=fee_asset,
                        link='',
                    )
                    self.add_asset_movement(cursor, asset_movement)
                else:  # Trades (buy)
                    if destination_amount > 0:
                        trade = Trade(
                            timestamp=timestamp,
                            location=Location.UPHOLD,
                            base_asset=destination_asset,
                            quote_asset=origin_asset,
                            trade_type=TradeType.BUY,
                            amount=destination_amount,
                            rate=Price(origin_amount / destination_amount),
                            fee=Fee(fee),
                            fee_currency=fee_asset,
                            link='',
                            notes=notes,
                        )
                        self.add_trade(cursor, trade)
                    else:
                        log.debug(f'Ignoring trade with Destination Amount: {destination_amount}.')

    def _import_csv(self, cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Information for the values that the columns can have has been obtained from sample CSVs
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_uphold_transaction(cursor, row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During uphold CSV import found action with unknown '
                        f'asset {e.identifier}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during uphold CSV import. '
                        f'{str(e)}. Ignoring entry',
                    )
                    continue
                except KeyError as e:
                    raise InputError(f'Could not find key {str(e)} in csv row {str(row)}') from e
