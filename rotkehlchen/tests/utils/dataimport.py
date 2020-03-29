from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.constants import A_XMR
from rotkehlchen.typing import (
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradePair,
    TradeType,
)


def assert_cointracking_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from cointracking.info"""
    trades = rotki.data.db.get_trades()
    asset_movements = rotki.data.db.get_asset_movements()
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 3

    expected_trades = [Trade(
        timestamp=Timestamp(1566687660),
        location=Location.COINBASE,
        pair=TradePair('ETH_EUR'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.05772716')),
        rate=Price(FVal('190.3783245183029963712055123')),
        fee=Fee(ZERO),
        fee_currency=A_ETH,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1567418400),
        location=Location.EXTERNAL,
        pair=TradePair('BTC_USD'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.00100000')),
        rate=Price(ZERO),
        fee=Fee(ZERO),
        fee_currency=A_BTC,
        link='',
        notes='Just a small gift from someone',
    )]
    assert expected_trades == trades

    expected_movements = [AssetMovement(
        location=Location.POLONIEX,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=Timestamp(1565848620),
        asset=A_XMR,
        amount=AssetAmount(FVal('5')),
        fee_asset=A_XMR,
        fee=Fee(ZERO),
        link='',
    ), AssetMovement(
        location=Location.COINBASE,
        category=AssetMovementCategory.WITHDRAWAL,
        timestamp=Timestamp(1566726120),
        asset=A_ETH,
        amount=AssetAmount(FVal('0.05770427')),
        fee_asset=A_ETH,
        fee=Fee(ZERO),
        link='',
    )]
    assert expected_movements == asset_movements
