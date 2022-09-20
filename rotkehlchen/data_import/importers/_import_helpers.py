from __future__ import annotations  # isort:skip

import logging

import typing

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
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

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def classify_transaction(
    origin: str,
    destination: str,
    origin_asset: Asset,
    destination_asset: Asset,
    origin_amount: AssetAmount,
    destination_amount: AssetAmount,
    transaction_type: str,
) -> typing.Callable:
    if is_on_exchange(origin, destination):
        if is_ledger_action(
            origin_asset,
            destination_asset,
            origin_amount,
            destination_amount,
        ):
            return TransactionType.LedgerAction
        if is_trade(origin_asset, destination_asset):
            return TransactionType.Trade
        raise ValueError(
            f'Could not classify transaction between {origin} and {destination} '
            f'with type {transaction_type}',
        )
    if is_withdrawal(
        transaction_type=transaction_type,
        origin_asset=origin_asset,
        destination_asset=destination_asset,
    ) or is_deposit(
        transaction_type=transaction_type,
        origin_asset=origin_asset,
        destination_asset=destination_asset,
    ):
        return TransactionType.AssetMovement
    if is_trade(origin_asset=origin_asset, destination_asset=destination_asset):
        return TransactionType.Trade
    raise ValueError(
        f'Could not classify transaction between {origin} and {destination} '
        f'with type {transaction_type}',
    )


def check_transaction_type(
    transaction_type: str,
    origin: str,
    destination: str,
    target_platform: str,
) -> None:
    """Check if the transaction type is valid."""
    if is_on_exchange(origin, destination):
        return
    if transaction_type == 'in' and origin != target_platform:
        raise ValueError(
            'Transaction Type and origin don\'t match. '
            f'Transaction Type is {transaction_type} but origin is {origin}',
        )
    if transaction_type == "out" and destination != target_platform:
        raise ValueError(
            'Transaction Type and destination don\'t match. '
            f'Transaction Type is {transaction_type} but destination is {destination}',
        )


def is_on_exchange(origin: str, destination: str) -> bool:
    """Check if the transaction is on exchange."""
    return origin == destination


def is_same_asset(origin_asset: Asset, destination_asset: Asset) -> bool:
    """Check if the transaction has the same origin and destination assets."""
    return origin_asset == destination_asset


def is_withdrawal(
    transaction_type: str,
    origin_asset: Asset,
    destination_asset: Asset,
) -> bool:
    """Check if the transaction is a withdrawal."""
    if not is_same_asset(origin_asset, destination_asset):
        raise ValueError(
            'Transaction Type and origin/destination assets don\'t match. '
            f'Transaction Type is {transaction_type} but origin asset is {origin_asset} '
            f'and destination asset is {destination_asset}',
        )
    # Add negative check to serve for 'is_deposit'
    return transaction_type == 'out' and transaction_type != 'in'


def is_deposit(
    transaction_type: str,
    origin_asset: Asset,
    destination_asset: Asset,
) -> bool:
    """Check if the transaction is a deposit."""
    return not is_withdrawal(transaction_type, origin_asset, destination_asset)


def is_trade(origin_asset: Asset, destination_asset: Asset) -> bool:
    """Check if the transaction is a trade."""
    return not is_same_asset(origin_asset, destination_asset)


def is_ledger_action(
    origin_asset: Asset,
    destination_asset: Asset,
    origin_amount: AssetAmount,
    destination_amount: AssetAmount,
) -> bool:
    """Check if the transaction is a ledger action."""
    return origin_asset == destination_asset and origin_amount == destination_amount


def get_action_type(transaction_type: str) -> LedgerActionType | None:
    if transaction_type == 'in':
        return LedgerActionType.INCOME
    if transaction_type == 'out':
        return LedgerActionType.EXPENSE
    log.debug(f'Ignoring uncaught transaction type of {transaction_type}.')
    return None


class TransactionType:
    class AssetMovement:
        def __call__(
            self,
            location: Location,
            category: AssetMovementCategory,
            timestamp: Timestamp,
            asset: Asset,
            amount: AssetAmount,
            fee: Fee,
            fee_asset: Asset,
            link: str = '',
            address: str = None,
            transaction_id: str = None,
        ) -> AssetMovement:
            return AssetMovement(
                location=location,
                category=category,
                address=address,
                transaction_id=transaction_id,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=fee,
                fee_asset=fee_asset,
                link=link,
            )

    class Trade:
        def __call__(
            self,
            location: Location,
            fee_asset: Asset,
            quote_asset: Asset,
            destination_amount: AssetAmount,
            trade_type: TradeType,
            fee: Fee,
            notes: str,
            origin_amount: AssetAmount,
            base_asset: Asset,
            timestamp: Timestamp,
            link: str = '',
        ) -> Trade | None:
            """
            Returns the trade from the csv row.
            """
            if fee_asset == quote_asset:
                destination_amount = AssetAmount(destination_amount + fee)
            if destination_amount <= 0 and origin_amount <= 0:
                log.debug(
                    f'Ignoring trade with Destination Amount: {destination_amount} '
                    f'and Origin Amount: {origin_amount}.',
                )
                return None
            rate = Price(destination_amount / origin_amount)
            if trade_type == TradeType.BUY:
                rate = Price(origin_amount / destination_amount)
            return Trade(
                timestamp=timestamp,
                location=location,
                base_asset=base_asset,
                quote_asset=quote_asset,
                trade_type=trade_type,
                amount=destination_amount,
                rate=rate,
                fee=fee,
                fee_currency=fee_asset,
                link=link,
                notes=notes,
            )

    class LedgerAction:
        def __call__(
            self,
            action_type: LedgerActionType,
            timestamp: Timestamp,
            destination_amount: AssetAmount,
            destination_asset: Asset,
            notes: str,
            location: Location,
            link: str = '',
            rate: Price = None,
            rate_asset: Asset = None,
        ) -> LedgerAction:
            return LedgerAction(
                identifier=0,
                timestamp=timestamp,
                action_type=action_type,
                location=location,
                amount=destination_amount,
                asset=destination_asset,
                rate=rate,
                rate_asset=rate_asset,
                link=link,
                notes=notes,
            )
