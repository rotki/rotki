from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.constants import A_EUR, A_XMR
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
        timestamp=Timestamp(1566687719),
        location=Location.COINBASE,
        pair=TradePair('ETH_EUR'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.05772716')),
        rate=Price(FVal('190.3783245183029963712055123')),
        fee=Fee(FVal("0.02")),
        fee_currency=A_EUR,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1567418410),
        location=Location.EXTERNAL,
        pair=TradePair('BTC_USD'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.00100000')),
        rate=Price(ZERO),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='Just a small gift from someone',
    ), Trade(
        timestamp=Timestamp(1567504805),
        location=Location.EXTERNAL,
        pair=TradePair('ETH_USD'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('2')),
        rate=Price(ZERO),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='Sign up bonus',
    )]
    assert expected_trades == trades

    expected_movements = [AssetMovement(
        location=Location.POLONIEX,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=Timestamp(1565848624),
        address=None,
        transaction_id=None,
        asset=A_XMR,
        amount=AssetAmount(FVal('5')),
        fee_asset=A_USD,
        fee=Fee(ZERO),
        link='',
    ), AssetMovement(
        location=Location.COINBASE,
        category=AssetMovementCategory.WITHDRAWAL,
        address=None,
        transaction_id=None,
        timestamp=Timestamp(1566726155),
        asset=A_ETH,
        amount=AssetAmount(FVal('0.05770427')),
        fee_asset=A_ETH,
        fee=Fee(FVal("0.0001")),
        link='',
    )]
    assert expected_movements == asset_movements


def assert_cryptocom_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from crypto.com"""
    trades = rotki.data.db.get_trades()
    asset_movements = rotki.data.db.get_asset_movements()
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0

    def get_trade_note(desc: str):
        return f'{desc}\nSource: crypto.com (CSV import)'

    expected_trades = [Trade(
        timestamp=Timestamp(1595833195),
        location=Location.CRYPTOCOM,
        pair=TradePair('ETH_EUR'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1.0')),
        rate=Price(FVal('281.14')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_trade_note('Buy ETH'),
    ), Trade(
        timestamp=Timestamp(1596014214),
        location=Location.CRYPTOCOM,
        pair=TradePair('MCO_EUR'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('50.0')),
        rate=Price(FVal('3.521')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_trade_note('Buy MCO'),
    ), Trade(
        timestamp=Timestamp(1596014223),
        location=Location.CRYPTOCOM,
        pair=TradePair('MCO_USD'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('12.32402069')),
        rate=Price(FVal('4.057117499045678736198226879')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_trade_note('Sign-up Bonus Unlocked'),
    ), Trade(
        timestamp=Timestamp(1596209827),
        location=Location.CRYPTOCOM,
        pair=TradePair('ETH_MCO'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.14445954600007045')),
        rate=Price(FVal('85.28339137929999991192917299')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_trade_note('MCO -> ETH'),
    ), Trade(
        timestamp=Timestamp(1596429934),
        location=Location.CRYPTOCOM,
        pair=TradePair('ETH_EUR'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.00061475')),
        rate=Price(FVal('309.0687271248474989833265555')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_trade_note('Crypto Earn'),
    ), Trade(
        timestamp=Timestamp(1596465565),
        location=Location.CRYPTOCOM,
        pair=TradePair('CRO_MCO'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1382.306147552291')),
        rate=Price(FVal('27.6439')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_trade_note('MCO/CRO Overall Swap'),
    ), Trade(
        timestamp=Timestamp(1596730165),
        location=Location.CRYPTOCOM,
        pair=TradePair('CRO_MCO'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1301.64')),
        rate=Price(FVal('26.0328')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_trade_note('MCO/CRO Overall Swap'),
    ), Trade(
        timestamp=Timestamp(1599934176),
        location=Location.CRYPTOCOM,
        pair=TradePair('CRO_EUR'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('138.256')),
        rate=Price(FVal('0.1429232727693553986807082514')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_trade_note('Card Rebate: Deliveries'),
    ), Trade(
        timestamp=Timestamp(1602515376),
        location=Location.CRYPTOCOM,
        pair=TradePair('CRO_EUR'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('52.151')),
        rate=Price(FVal('0.06692105616383194953116910510')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_trade_note('Card Cashback'),
    ), Trade(
        timestamp=Timestamp(1602526176),
        location=Location.CRYPTOCOM,
        pair=TradePair('CRO_EUR'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('482.2566417')),
        rate=Price(FVal('0.08756748243245604635910191136')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_trade_note('Referral Bonus Reward'),
    ), Trade(
        timestamp=Timestamp(1606833565),
        location=Location.CRYPTOCOM,
        pair=TradePair('CRO_DAI'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.007231228760408149')),
        rate=Price(FVal('14.26830000900286970270179629')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_trade_note('Convert Dust'),
    ), Trade(
        timestamp=Timestamp(1608024314),
        location=Location.CRYPTOCOM,
        pair=TradePair('CRO_UNI'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('105.9475889306405164438345865')),
        rate=Price(FVal('144.1809293808791657040427665')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_trade_note('Convert Dust'),
    ), Trade(
        timestamp=Timestamp(1608024314),
        location=Location.CRYPTOCOM,
        pair=TradePair('CRO_DOT'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('87.08021007997850666616541352')),
        rate=Price(FVal('306.6322128582378511862892551')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_trade_note('Convert Dust'),
    )]
    assert expected_trades == trades

    expected_movements = [AssetMovement(
        location=Location.CRYPTOCOM,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=Timestamp(1596992965),
        address=None,
        transaction_id=None,
        asset=A_DAI,
        amount=AssetAmount(FVal('115')),
        fee_asset=A_DAI,
        fee=Fee(ZERO),
        link='',
    ), AssetMovement(
        location=Location.CRYPTOCOM,
        category=AssetMovementCategory.WITHDRAWAL,
        address=None,
        transaction_id=None,
        timestamp=Timestamp(1596993025),
        asset=A_DAI,
        amount=AssetAmount(FVal('115')),
        fee_asset=A_DAI,
        fee=Fee(ZERO),
        link='',
    )]
    assert expected_movements == asset_movements
