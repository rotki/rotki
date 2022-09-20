import pytest as pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.data_import.importers._import_helpers import (
    TransactionType,
    classify_transaction,
    is_deposit,
    is_on_exchange,
    is_same_asset,
    is_trade,
    is_withdrawal,
)
from rotkehlchen.fval import FVal
from rotkehlchen.types import AssetAmount


@pytest.mark.parametrize(
    'origin,destination,expected',
    [
        ('uphold', 'uphold', True),
        ('uphold', 'blockfi', False),
    ],
)
def test_is_onexchange(origin, destination, expected):
    assert is_on_exchange(origin, destination) == expected


@pytest.mark.parametrize(
    'origin_asset,destination_asset,expected',
    [
        ('BTC', 'BTC', True),
        ('BTC', 'ETH', False),
    ],
)
def test_is_same_asset(origin_asset, destination_asset, expected):
    assert is_same_asset(Asset(origin_asset), Asset(destination_asset)) == expected


@pytest.mark.parametrize(
    'transaction_type,origin_asset,destination_asset,expected',
    [
        ('in', 'BTC', 'BTC', False),
        ('out', 'BTC', 'BTC', True),
    ],
)
def test_is_withdrawal(transaction_type, origin_asset, destination_asset, expected):
    assert (
        is_withdrawal(
            transaction_type,
            Asset(origin_asset),
            Asset(destination_asset),
        ) == expected
    )


@pytest.mark.parametrize(
    'transaction_type,origin_asset,destination_asset,expected',
    [
        ('in', 'BTC', 'BTC', True),
        ('out', 'BTC', 'BTC', False),
    ],
)
def test_is_deposit(transaction_type, origin_asset, destination_asset, expected):
    assert (
        is_deposit(transaction_type, Asset(origin_asset), Asset(destination_asset)) == expected
    )


@pytest.mark.parametrize(
    'origin_asset,destination_asset,expected',
    [
        ('BTC', 'BTC', False),
        ('BTC', 'ETH', True),
    ],
)
def test_is_trade(origin_asset, destination_asset, expected):
    assert is_trade(Asset(origin_asset), Asset(destination_asset)) == expected


@pytest.mark.parametrize(
    'origin,origin_asset,origin_amount,destination,'
    'destination_asset,destination_amount,transaction_type,expected',
    [
        ('uphold', 'BTC', 2, 'uphold', 'BTC', 2, 'in', TransactionType.LedgerAction),
        ('uphold', 'BTC', 2, 'uphold', 'BTC', 2, 'out', TransactionType.LedgerAction),
        ('uphold', 'BTC', 2, 'uphold', 'ETH', 3, 'in', TransactionType.Trade),
        ('uphold', 'BTC', 2, 'uphold', 'ETH', 3, 'out', TransactionType.Trade),
        ('uphold', 'BTC', 2, 'uphold', 'BTC', 3, 'in', ValueError),
        ('uphold', 'BTC', 2, 'blockfi', 'BTC', 3, 'in', TransactionType.AssetMovement),
        (
            'uphold',
            'BTC',
            2,
            'blockfi',
            'BTC',
            3,
            'out',
            TransactionType.AssetMovement,
        ),
        ('uphold', 'BTC', 2, 'blockfi', 'ETH', 3, 'in', ValueError),
        ('uphold', 'BTC', 2, 'blockfi', 'ETH', 3, 'out', ValueError),
        ('uphold', 'BTC', 0, 'blockfi', 'ETH', 0, 'out', ValueError),
    ],
)
def test_classify_transaction(
    origin,
    origin_asset,
    origin_amount,
    destination,
    destination_asset,
    destination_amount,
    transaction_type,
    expected,
):
    if expected in [
        TransactionType.AssetMovement,
        TransactionType.Trade,
        TransactionType.LedgerAction,
        None,
    ]:
        assert (
            classify_transaction(
                transaction_type=transaction_type,
                origin=origin,
                origin_asset=Asset(origin_asset),
                origin_amount=AssetAmount(FVal(origin_amount)),
                destination=destination,
                destination_asset=Asset(destination_asset),
                destination_amount=AssetAmount(FVal(destination_amount)),
            )
            is expected
        )
    else:
        with pytest.raises(expected):
            classify_transaction(
                transaction_type=transaction_type,
                origin=origin,
                origin_asset=Asset(origin_asset),
                origin_amount=AssetAmount(FVal(origin_amount)),
                destination=destination,
                destination_asset=Asset(destination_asset),
                destination_amount=AssetAmount(FVal(destination_amount)),
            )
