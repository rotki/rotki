from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants.assets import (
    A_BTC,
    A_DAI,
    A_SAI,
    A_USDC,
    A_DOT,
    A_ETH,
    A_LTC,
    A_EUR,
    A_UNI,
    A_USD,
    A_XRP,
    A_BAT,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.constants import A_CRO, A_MCO, A_XMR
from rotkehlchen.typing import (
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
)


def assert_cointracking_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from cointracking.info"""
    trades = rotki.data.db.get_trades()
    asset_movements = rotki.data.db.get_asset_movements()
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 3

    expected_trades = [Trade(
        timestamp=Timestamp(1566687719),
        location=Location.COINBASE,
        base_asset=A_ETH,
        quote_asset=A_EUR,
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
        base_asset=A_BTC,
        quote_asset=A_USD,
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
        base_asset=A_ETH,
        quote_asset=A_USD,
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
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    def get_trade_note(desc: str):
        return f'{desc}\nSource: crypto.com (CSV import)'

    expected_trades = [Trade(
        timestamp=Timestamp(1595833195),
        location=Location.CRYPTOCOM,
        base_asset=A_ETH,
        quote_asset=A_EUR,
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
        base_asset=A_MCO,
        quote_asset=A_EUR,
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
        base_asset=A_MCO,
        quote_asset=A_USD,
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
        base_asset=A_ETH,
        quote_asset=A_MCO,
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
        base_asset=A_ETH,
        quote_asset=A_EUR,
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
        base_asset=A_CRO,
        quote_asset=A_MCO,
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
        base_asset=A_CRO,
        quote_asset=A_MCO,
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
        base_asset=A_CRO,
        quote_asset=A_EUR,
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
        base_asset=A_CRO,
        quote_asset=A_EUR,
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
        base_asset=A_CRO,
        quote_asset=A_EUR,
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
        base_asset=A_CRO,
        quote_asset=A_DAI,
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
        base_asset=A_CRO,
        quote_asset=A_UNI,
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
        base_asset=A_CRO,
        quote_asset=A_DOT,
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


def assert_cryptocom_special_events_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from crypto.com"""
    trades = rotki.data.db.get_trades()
    ledger_db = DBLedgerActions(rotki.data.db, rotki.msg_aggregator)
    ledger_actions = ledger_db.get_ledger_actions(None, None, None)
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    expected_actions = [LedgerAction(
        identifier=5,
        timestamp=Timestamp(1609884000),
        action_type=LedgerActionType.INCOME,
        location=Location.CRYPTOCOM,
        amount=AssetAmount(FVal('1')),
        asset=symbol_to_asset_or_token('CRO'),
        rate=None,
        rate_asset=None,
        link=None,
        notes=None,
    ), LedgerAction(
        identifier=4,
        timestamp=Timestamp(1609884000),
        action_type=LedgerActionType.INCOME,
        location=Location.CRYPTOCOM,
        amount=AssetAmount(FVal('0.5')),
        asset=symbol_to_asset_or_token('MCO'),
        rate=None,
        rate_asset=None,
        link=None,
        notes=None,
    ), LedgerAction(
        identifier=3,
        timestamp=Timestamp(1609884000),
        action_type=LedgerActionType.INCOME,
        location=Location.CRYPTOCOM,
        amount=AssetAmount(FVal('1')),
        asset=symbol_to_asset_or_token('CRO'),
        rate=None,
        rate_asset=None,
        link=None,
        notes=None,
    ), LedgerAction(
        identifier=2,
        timestamp=Timestamp(1609797600),
        action_type=LedgerActionType.INCOME,
        location=Location.CRYPTOCOM,
        amount=AssetAmount(FVal('0.02005')),
        asset=A_BTC,
        rate=None,
        rate_asset=None,
        link=None,
        notes='Stake profit for asset BTC',
    ), LedgerAction(
        identifier=1,
        timestamp=Timestamp(1609624800),
        action_type=LedgerActionType.INCOME,
        location=Location.CRYPTOCOM,
        amount=AssetAmount(FVal('0.00005')),
        asset=A_BTC,
        rate=None,
        rate_asset=None,
        link=None,
        notes='Stake profit for asset BTC',
    )]
    assert list(reversed(expected_actions)) == ledger_actions

    expected_trades = [Trade(
        timestamp=Timestamp(1609884000),
        location=Location.CRYPTOCOM,
        base_asset=symbol_to_asset_or_token('CRO'),
        quote_asset=symbol_to_asset_or_token('MCO'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1')),
        rate=Price(FVal('10')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='MCO Earnings/Rewards Swap\nSource: crypto.com (CSV import)',
    )]
    assert trades == expected_trades


def assert_blockfi_transactions_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from blockfi"""
    ledger_db = DBLedgerActions(rotki.data.db, rotki.msg_aggregator)
    ledger_actions = ledger_db.get_ledger_actions(None, None, None)
    asset_movements = rotki.data.db.get_asset_movements()
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    expected_actions = [LedgerAction(
        identifier=3,
        timestamp=Timestamp(1600293599),
        action_type=LedgerActionType.INCOME,
        location=Location.BLOCKFI,
        amount=AssetAmount(FVal('0.48385358')),
        asset=A_ETH,
        rate=None,
        rate_asset=None,
        link=None,
        notes='Bonus Payment from BlockFi',
    ), LedgerAction(
        identifier=2,
        timestamp=Timestamp(1606953599),
        action_type=LedgerActionType.INCOME,
        location=Location.BLOCKFI,
        amount=AssetAmount(FVal('0.00052383')),
        asset=A_BTC,
        rate=None,
        rate_asset=None,
        link=None,
        notes='Referral Bonus from BlockFi',
    ), LedgerAction(
        identifier=1,
        timestamp=Timestamp(1612051199),
        action_type=LedgerActionType.INCOME,
        location=Location.BLOCKFI,
        amount=AssetAmount(FVal('0.56469042')),
        asset=A_ETH,
        rate=None,
        rate_asset=None,
        link=None,
        notes='Interest Payment from BlockFi',
    )]
    assert expected_actions == ledger_actions

    expected_movements = [AssetMovement(
        location=Location.BLOCKFI,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=Timestamp(1595247055),
        address=None,
        transaction_id=None,
        asset=A_BTC,
        amount=AssetAmount(FVal('1.11415058')),
        fee_asset=A_USD,
        fee=Fee(ZERO),
        link='',
    ), AssetMovement(
        location=Location.BLOCKFI,
        category=AssetMovementCategory.WITHDRAWAL,
        address=None,
        transaction_id=None,
        timestamp=Timestamp(1605977971),
        asset=A_ETH,
        amount=AssetAmount(FVal('3')),
        fee_asset=A_USD,
        fee=Fee(ZERO),
        link='',
    )]
    assert expected_movements == asset_movements


def assert_blockfi_trades_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing trades data from blockfi"""
    trades = rotki.data.db.get_trades()
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    expected_trades = [Trade(
        timestamp=Timestamp(1612051199),
        location=Location.BLOCKFI,
        base_asset=symbol_to_asset_or_token('USDC'),
        quote_asset=symbol_to_asset_or_token('LTC'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('6404.6')),
        rate=Price(FVal('151.6283999982779809352223797')),
        fee=None,
        fee_currency=None,
        link='',
        notes='One Time',
    )]
    assert trades == expected_trades


def assert_nexo_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from nexo"""
    ledger_db = DBLedgerActions(rotki.data.db, rotki.msg_aggregator)
    ledger_actions = ledger_db.get_ledger_actions(None, None, None)
    asset_movements = rotki.data.db.get_asset_movements()
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    expected_actions = [LedgerAction(
        identifier=3,
        timestamp=Timestamp(1565888464),
        action_type=LedgerActionType.INCOME,
        location=Location.NEXO,
        amount=AssetAmount(FVal('22.5653042')),
        asset=symbol_to_asset_or_token('NEXO'),
        rate=None,
        rate_asset=None,
        link='NXT0000000009',
        notes='Dividend from Nexo',
    ), LedgerAction(
        identifier=4,
        timestamp=Timestamp(1587739424),
        action_type=LedgerActionType.INCOME,
        location=Location.NEXO,
        amount=AssetAmount(FVal('10')),
        asset=symbol_to_asset_or_token('NEXO'),
        rate=None,
        rate_asset=None,
        link='NXT0000000015',
        notes='Interest from Nexo',
    ), LedgerAction(
        identifier=5,
        timestamp=Timestamp(1587825824),
        action_type=LedgerActionType.INCOME,
        location=Location.NEXO,
        amount=AssetAmount(FVal('10')),
        asset=symbol_to_asset_or_token('ETH'),
        rate=None,
        rate_asset=None,
        link='NXT0000000016',
        notes='FixedTermInterest from Nexo',
    ), LedgerAction(
        identifier=2,
        timestamp=Timestamp(1597492915),
        action_type=LedgerActionType.INCOME,
        location=Location.NEXO,
        amount=AssetAmount(FVal('10.3585507')),
        asset=symbol_to_asset_or_token('NEXO'),
        rate=None,
        rate_asset=None,
        link='NXT0000000007',
        notes='Dividend from Nexo',
    ), LedgerAction(
        identifier=1,
        timestamp=Timestamp(1614993620),
        action_type=LedgerActionType.INCOME,
        location=Location.NEXO,
        amount=AssetAmount(FVal('1')),
        asset=symbol_to_asset_or_token('USDC'),
        rate=None,
        rate_asset=None,
        link='NXT0000000002',
        notes='Interest from Nexo',
    )]

    expected_movements = [AssetMovement(
        location=Location.NEXO,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=Timestamp(1556116964),
        address=None,
        transaction_id=None,
        asset=A_BTC,
        amount=AssetAmount(FVal('1')),
        fee_asset=A_USD,
        fee=Fee(ZERO),
        link='NXT0000000013',
    ), AssetMovement(
        location=Location.NEXO,
        category=AssetMovementCategory.WITHDRAWAL,
        timestamp=Timestamp(1556122699),
        address=None,
        transaction_id=None,
        asset=A_BTC,
        amount=AssetAmount(FVal('0.9995')),
        fee_asset=A_USD,
        fee=Fee(ZERO),
        link='NXT0000000012',
    ), AssetMovement(
        location=Location.NEXO,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=Timestamp(1558720210),
        address=None,
        transaction_id=None,
        asset=symbol_to_asset_or_token('NEXO'),
        amount=AssetAmount(FVal('1.00001')),
        fee_asset=A_USD,
        fee=Fee(ZERO),
        link='NXT0000000011',
    ), AssetMovement(
        location=Location.NEXO,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=Timestamp(1565912821),
        address=None,
        transaction_id=None,
        asset=A_EUR,
        amount=AssetAmount(FVal('10000')),
        fee_asset=A_USD,
        fee=Fee(ZERO),
        link='NXT0000000010',
    ), AssetMovement(
        location=Location.NEXO,
        category=AssetMovementCategory.WITHDRAWAL,
        timestamp=Timestamp(1608131364),
        address=None,
        transaction_id=None,
        asset=A_EUR,
        amount=AssetAmount(FVal('2000.79')),
        fee_asset=A_USD,
        fee=Fee(ZERO),
        link='NXT0000000005',
    ), AssetMovement(
        location=Location.NEXO,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=Timestamp(1614366540),
        address=None,
        transaction_id=None,
        asset=A_EUR,
        amount=AssetAmount(FVal('10')),
        fee_asset=A_USD,
        fee=Fee(ZERO),
        link='NXT0000000003',
    ), AssetMovement(
        location=Location.NEXO,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=Timestamp(1615024314),
        address=None,
        transaction_id=None,
        asset=symbol_to_asset_or_token('USDC'),
        amount=AssetAmount(FVal('1')),
        fee_asset=A_USD,
        fee=Fee(ZERO),
        link='NXT0000000001',
    )]

    assert ledger_actions == expected_actions
    assert asset_movements == expected_movements


def assert_shapeshift_trades_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing trades data from shapeshift"""
    trades = rotki.data.db.get_trades()
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    notes1 = """
Trade from ShapeShift with ShapeShift Deposit Address:
 0xc181da8187a37f8c518a2d12733c763a491a873c, and
 Transaction ID: 0xcd4b53bd1991c387558e4274fc49604487708c3878abc1a419b6120d1f489881.
  Refund Address: , and
 Transaction ID: .
  Destination Address: JWPKHH2j5YubGNpexkRrElg7D0yuCusu0Q, and
 Transaction ID: 9f9d6bb29d896080202f9f51ee1c767527bf88c468bd5e40cd568ecbad3cde61.
"""
    notes2 = """
Trade from ShapeShift with ShapeShift Deposit Address:
 0xbc7b968df007c6b4d7507763e17971c7c8cb4812, and
 Transaction ID: 0xaf026f6f53521563bb5d16e781f26f8ecd885010e5a731c6059902e01a8500a3.
  Refund Address: , and
 Transaction ID: 0x59383b5c0834d76118f7d4e3d283e512d05cbfa7d0127084642f0eb4e0188f70.
  Destination Address: 0xf7ee0f8a9a1c67558c7fce768ab40cd0771c882a2, and
 Transaction ID: 0x5395176bf37a198b7df9e7ace0f45f4cdcad0cf78a593912eae1a2fd6c40f7b9.
"""
    assert len(errors) == 0
    assert len(warnings) == 0
    expected_trades = [
        Trade(
            timestamp=Timestamp(1561551116),
            location=Location.SHAPESHIFT,
            base_asset=symbol_to_asset_or_token('DASH'),
            quote_asset=A_SAI,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.59420343')),
            rate=Price(1 / FVal('0.00578758')),
            fee=Fee(FVal('0.002')),
            fee_currency=symbol_to_asset_or_token('DASH'),
            link='',
            notes=notes1,
        ),
        Trade(
            timestamp=Timestamp(1630856301),
            location=Location.SHAPESHIFT,
            base_asset=A_ETH,
            quote_asset=A_USDC,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.06198721')),
            rate=Price(1 / FVal('0.00065004')),
            fee=Fee(FVal('0.0042')),
            fee_currency=A_ETH,
            link='',
            notes=notes2,
        )]
    assert trades[0].timestamp == expected_trades[0].timestamp
    assert len(trades) == 2
    assert trades == expected_trades


def assert_uphold_transactions_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing trades data from uphold"""
    trades = rotki.data.db.get_trades()
    asset_movements = rotki.data.db.get_asset_movements()
    ledger_db = DBLedgerActions(rotki.data.db, rotki.msg_aggregator)
    ledger_actions = ledger_db.get_ledger_actions(None, None, None)
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    notes1 = """
Activity from uphold with uphold transaction id:
 1a2b3c4d-5e6f-1a2b-3c4d-5e6f1a2b3c4d, origin: credit-card,
 and destination: uphold.
  Type: in.
  Status: completed.
"""
    notes2 = """
Activity from uphold with uphold transaction id:
 1a2b3c4d-5e6f-1a2b-3c4d-5e6f1a2b3c4d, origin: uphold,
 and destination: uphold.
  Type: transfer.
  Status: completed.
"""
    notes3 = """
Activity from uphold with uphold transaction id:
 1a2b3c4d-5e6f-1a2b-3c4d-5e6f1a2b3c4d, origin: uphold,
 and destination: litecoin.
  Type: out.
  Status: completed.
"""
    notes4 = """
Activity from uphold with uphold transaction id:
 1a2b3c4d-5e6f-1a2b-3c4d-5e6f1a2b3c4d, origin: uphold,
 and destination: xrp-ledger.
  Type: out.
  Status: completed.
"""
    notes5 = """
Activity from uphold with uphold transaction id:
 1a2b3c4d-5e6f-1a2b-3c4d-5e6f1a2b3c4d, origin: uphold,
 and destination: uphold.
  Type: in.
  Status: completed.
"""
    assert len(errors) == 0
    assert len(warnings) == 0
    expected_trades = [Trade(
        timestamp=Timestamp(1581426837),
        location=Location.UPHOLD,
        base_asset=A_BTC,
        quote_asset=symbol_to_asset_or_token('GBP'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.00331961')),
        rate=Price(FVal('7531.005148195119306183557707')),
        fee=Fee(ZERO),
        fee_currency=symbol_to_asset_or_token('GBP'),
        link='',
        notes=notes1,
    ), Trade(
        timestamp=Timestamp(1585484504),
        location=Location.UPHOLD,
        base_asset=symbol_to_asset_or_token('GBP'),
        quote_asset=A_BTC,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('24.65')),
        rate=Price(FVal('0.0001707910750507099391480730223')),
        fee=Fee(ZERO),
        fee_currency=A_BTC,
        link='',
        notes=notes2,
    ), Trade(
        timestamp=Timestamp(1589940026),
        location=Location.UPHOLD,
        base_asset=symbol_to_asset_or_token('NANO'),
        quote_asset=A_LTC,
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal('133.362002	')),
        rate=Price(FVal('0.009459633186970303580175708520')),
        fee=Fee(FVal('0.111123')),
        fee_currency=symbol_to_asset_or_token('NANO'),
        link='',
        notes=notes3,
    ), Trade(
        timestamp=Timestamp(1590516388),
        location=Location.UPHOLD,
        base_asset=A_BTC,
        quote_asset=A_XRP,
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal('0.00714216')),
        rate=Price(FVal('44054.19382931774141156176843')),
        fee=Fee(FVal('0.0000021')),
        fee_currency=A_BTC,
        link='',
        notes=notes4,
    )]
    expected_movements = [AssetMovement(
        location=Location.UPHOLD,
        category=AssetMovementCategory.WITHDRAWAL,
        timestamp=Timestamp(1589376604),
        address=None,
        transaction_id=None,
        asset=symbol_to_asset_or_token('GBP'),
        amount=AssetAmount(FVal('24.65')),
        fee_asset=symbol_to_asset_or_token('GBP'),
        fee=Fee(ZERO),
        link='',
    )]
    expected_ledger_actions = [LedgerAction(
        identifier=ledger_actions[0].identifier,
        location=Location.UPHOLD,
        action_type=LedgerActionType.INCOME,
        timestamp=Timestamp(1576780809),
        asset=A_BAT,
        amount=AssetAmount(FVal('5.15')),
        rate=None,
        rate_asset=None,
        link='',
        notes=notes5,
    )]
    assert len(trades) == 4
    assert trades == expected_trades
    assert len(asset_movements) == 1
    assert asset_movements == expected_movements
    assert len(ledger_actions) == 1
    assert ledger_actions == expected_ledger_actions


def assert_custom_cointracking(rotki: Rotkehlchen):
    """
    A utility function to help assert on correctness of importing data from cointracking.info
    when using custom formats for dates
    """
    asset_movements = rotki.data.db.get_asset_movements()
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    expected_movements = [AssetMovement(
        location=Location.POLONIEX,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=Timestamp(1504646040),
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
        timestamp=Timestamp(1504646040),
        asset=A_ETH,
        amount=AssetAmount(FVal('0.05770427')),
        fee_asset=A_ETH,
        fee=Fee(FVal("0.0001")),
        link='',
    )]
    assert expected_movements == asset_movements
