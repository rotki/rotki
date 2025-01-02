from typing import Literal

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, CryptoAsset, EvmToken
from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import (
    A_BAT,
    A_BCH,
    A_BNB,
    A_BTC,
    A_BUSD,
    A_DAI,
    A_DOGE,
    A_DOT,
    A_ETC,
    A_ETH,
    A_ETH2,
    A_ETH_MATIC,
    A_EUR,
    A_KNC,
    A_LTC,
    A_SAI,
    A_SOL,
    A_UNI,
    A_USD,
    A_USDC,
    A_USDT,
    A_XRP,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.data_import.importers.constants import COINTRACKING_EVENT_PREFIX
from rotkehlchen.db.filtering import (
    HistoryEventFilterQuery,
    TradesFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.exchanges.data_structures import MarginPosition, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.fixtures.websockets import WebsocketReader
from rotkehlchen.tests.utils.constants import A_AXS, A_CRO, A_GBP, A_KCS, A_MCO, A_XMR, A_XTZ
from rotkehlchen.types import (
    AssetAmount,
    Fee,
    Location,
    Price,
    Timestamp,
    TimestampMS,
    TradeType,
)
from rotkehlchen.utils.misc import ts_sec_to_ms


def get_cryptocom_note(desc: str):
    return f'{desc}\nSource: crypto.com (CSV import)'


def assert_cointracking_import_results(rotki: Rotkehlchen, websocket_connection: WebsocketReader):
    """A utility function to help assert on correctness of importing data from cointracking.info"""
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.read_ctx() as cursor:
        trades = rotki.data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501
        events = dbevents.get_history_events(cursor, filter_query=HistoryEventFilterQuery.make(), has_premium=True)  # noqa: E501

    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0
    websocket_connection.wait_until_messages_num(num=1, timeout=10)
    assert websocket_connection.pop_message() == {
        'type': 'csv_import_result',
        'data': {
            'source_name': 'Cointracking',
            'total_entries': 12,
            'imported_entries': 7,
            'messages': [
                {'msg': 'Not importing ETH Transactions from Cointracking. Cointracking does not export enough data for them. Simply enter your ethereum accounts and all your transactions will be auto imported directly from the chain', 'rows': [1, 2], 'is_error': True},  # noqa: E501
                {'msg': 'Not importing BTC Transactions from Cointracking. Cointracking does not export enough data for them. Simply enter your BTC accounts and all your transactions will be auto imported directly from the chain', 'rows': [5], 'is_error': True},  # noqa: E501
                {'msg': 'Unknown asset ADS.', 'rows': [9], 'is_error': True},
                {'msg': 'Staking event for eip155:1/erc20:0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b(Axie Infinity Shard) at 1641386280 already exists in the DB', 'rows': [12]},  # noqa: E501
            ],
        },
    }
    assert websocket_connection.messages_num() == 0

    expected_trades = [Trade(
        timestamp=Timestamp(1566687719),
        location=Location.COINBASE,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.05772716')),
        rate=Price(FVal('190.378324518302996371205512275331057339387560378858062651964863679418838550173')),
        fee=Fee(FVal('0.02')),
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
        rate=ZERO_PRICE,
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='Just a small gift from someone. Data from -no exchange- not known by rotki.',
    ), Trade(
        timestamp=Timestamp(1567504805),
        location=Location.EXTERNAL,
        base_asset=A_ETH,
        quote_asset=A_USD,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('2')),
        rate=ZERO_PRICE,
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='Sign up bonus. Data from -no exchange- not known by rotki.',
    )]
    assert expected_trades == trades

    for movement in [AssetMovement(
        identifier=1,
        event_identifier='7626b5d52eb9c67f2c9d83a0c1a97f38c8d2e0466d055fd23c48a30afe2aa972',
        location=Location.POLONIEX,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1565848624000),
        asset=A_XMR,
        balance=Balance(FVal('5.00000000')),
    ), AssetMovement(
        identifier=2,
        event_identifier='5dfd720e8b362491a663f4440477592a4e5c48bef0166bc42dd138c6e4ff0054',
        location=Location.COINBASE,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1566726155000),
        asset=A_ETH,
        balance=Balance(FVal('0.05770427')),
    ), AssetMovement(
        identifier=3,
        event_identifier='5dfd720e8b362491a663f4440477592a4e5c48bef0166bc42dd138c6e4ff0054',
        location=Location.COINBASE,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1566726155000),
        asset=A_ETH,
        balance=Balance(FVal('0.0001')),
        is_fee=True,
    )]:
        assert movement in events
        events.remove(movement)  # remove for simpler checking below.

    assert len(events) == 2, 'Duplicated event was not ignored'
    for event in events:
        assert event.event_identifier.startswith(COINTRACKING_EVENT_PREFIX)
        assert event.event_type == HistoryEventType.STAKING
        assert event.event_subtype == HistoryEventSubType.REWARD
        assert event.location == Location.BINANCE
        assert event.location_label is None
        if event.asset == A_AXS:
            assert event.timestamp == 1641386280000
            assert event.balance.amount == FVal(1)
            assert event.notes == 'Stake reward of 1.00000000 AXS in binance'
        else:
            assert event.asset == A_ETH
            assert event.timestamp == 1644319740000
            assert event.balance.amount == FVal('2.12')
            assert event.notes == 'Stake reward of 2.12000000 ETH in binance'


def assert_cryptocom_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from crypto.com"""
    with rotki.data.db.conn.read_ctx() as cursor:
        trades = rotki.data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501
        events_db = DBHistoryEvents(rotki.data.db)
        events = events_db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

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
        notes=get_cryptocom_note('Buy ETH'),
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
        notes=get_cryptocom_note('Buy MCO'),
    ), Trade(
        timestamp=Timestamp(1596209827),
        location=Location.CRYPTOCOM,
        base_asset=A_ETH,
        quote_asset=A_MCO,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.14445954600007045')),
        rate=Price(FVal('85.2833913792999999119291729949518503246750176145827472350567448513045323590123')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_cryptocom_note('MCO -> ETH'),
    ), Trade(
        timestamp=Timestamp(1596465565),
        location=Location.CRYPTOCOM,
        base_asset=A_CRO,
        quote_asset=A_MCO,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1382.306147552291')),
        rate=Price(FVal('0.0361743458773906720831720560412966332536291912501492191767442365223430847311703')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_cryptocom_note('MCO/CRO Overall Swap'),
    ), Trade(
        timestamp=Timestamp(1596730165),
        location=Location.CRYPTOCOM,
        base_asset=A_CRO,
        quote_asset=A_MCO,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1301.64')),
        rate=Price(FVal('0.0384130788850987984388924741095848314434098521864724501398236071417596263175686')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_cryptocom_note('MCO/CRO Overall Swap'),
    ), Trade(
        timestamp=Timestamp(1606833565),
        location=Location.CRYPTOCOM,
        base_asset=A_CRO,
        quote_asset=A_DAI,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.007231228760408149')),
        rate=Price(FVal('0.0700854340999999978091578312748869585371803619665889773958276318539354780260676')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_cryptocom_note('Convert Dust'),
    ), Trade(
        timestamp=Timestamp(1608024314),
        location=Location.CRYPTOCOM,
        base_asset=A_CRO,
        quote_asset=A_UNI,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('105.947588930640516443834586466165413533834586466165413533834586466165413533835')),
        rate=Price(FVal('0.00693573001848479514937114955719518855874680530297017002120554259080677365630703')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_cryptocom_note('Convert Dust'),
    ), Trade(
        timestamp=Timestamp(1608024314),
        location=Location.CRYPTOCOM,
        base_asset=A_CRO,
        quote_asset=A_DOT,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('87.0802100799785066661654135338345864661654135338345864661654135338345864661654')),
        rate=Price(FVal('0.00326123596304058183837711870501319393677721839811503439931415924850926769770534')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_cryptocom_note('Convert Dust'),
    ), Trade(
        timestamp=Timestamp(1620192867),
        location=Location.CRYPTOCOM,
        base_asset=A_EUR,
        quote_asset=A_DOGE,
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal('406.22')),
        rate=Price(FVal('1.84629018758308305844123873762985574319334350844370045787996652060459849342721')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_cryptocom_note('DOGE -> EUR'),
    ), Trade(
        timestamp=Timestamp(1626720960),
        location=Location.CRYPTOCOM,
        base_asset=A_BTC,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.003')),
        rate=Price(FVal('26003.3333333333333333333333333333333333333333333333333333333333333333333333333')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes=get_cryptocom_note('EUR -> BTC'),
    )]
    assert expected_trades == trades

    expected_events = [HistoryEvent(
        identifier=7,
        event_identifier='CCM_8742d989ca51cb724a6de9492cab6a647074635ea1fb5cad8c9db5596ec4cf46',
        sequence_index=0,
        timestamp=TimestampMS(1596014223000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('12.32402069')),
        asset=A_MCO,
        notes=get_cryptocom_note('Sign-up Bonus Unlocked'),
    ), HistoryEvent(
        identifier=6,
        event_identifier='CCM_983789e023405101a67cc9bb77faba8819e49e78de4ad4fda5281d2ecffd8052',
        sequence_index=0,
        timestamp=TimestampMS(1596429934000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.00061475')),
        asset=A_ETH,
        notes=get_cryptocom_note('Crypto Earn'),
    ), AssetMovement(
        identifier=5,
        event_identifier='20b719f712a8951eeaa518e6976950c8410028dc974c2b6e72b62e6e8745d355',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1596992965000),
        asset=A_DAI,
        balance=Balance(FVal('115')),
    ), AssetMovement(
        identifier=4,
        event_identifier='2e2bba27c61cf9d71b8c60e1fce061a59b01d150b294badbb060c940d603594b',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1596993025000),
        asset=A_DAI,
        balance=Balance(FVal('115')),
    ), HistoryEvent(
        identifier=3,
        event_identifier='CCM_f24eb95216e362d79bb4a9cec0743fbb5bfd387c743e98ce51a97c6b3c430987',
        sequence_index=0,
        timestamp=TimestampMS(1599934176000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('138.256')),
        asset=A_CRO,
        notes=get_cryptocom_note('Card Rebate: Deliveries'),
    ), HistoryEvent(
        identifier=2,
        event_identifier='CCM_eadaa0af72f57a3a987faa9da84b149a14af47c94a5cf37f3dc0d3a6b795af95',
        sequence_index=0,
        timestamp=TimestampMS(1602515376000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('52.151')),
        asset=A_CRO,
        notes=get_cryptocom_note('Card Cashback'),
    ), HistoryEvent(
        identifier=1,
        event_identifier='CCM_10f2e57d3ff770148095e4b1f8407858dacb5b0f738679a5e30a61a9e65abd2c',
        sequence_index=0,
        timestamp=TimestampMS(1602526176000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('482.2566417')),
        asset=A_CRO,
        notes=get_cryptocom_note('Referral Bonus Reward'),
    ), HistoryEvent(
        identifier=15,
        event_identifier='CCM_da60cedfc97c1df9319d7c2102e0269cbca97d4abac374d2d96a385ab02d072c',
        sequence_index=0,
        timestamp=TimestampMS(1614989135000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('7.76792828')),
        asset=A_CRO,
        notes=get_cryptocom_note('Card Rebate: Netflix'),
    ), HistoryEvent(
        identifier=14,
        event_identifier='CCM_0bcbe9abf2d75f68eecebc2c99611efb56e6f8795fbaa2e2c33db348864e6f4c',
        sequence_index=0,
        timestamp=TimestampMS(1615097829000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('7.76792828')),
        asset=A_CRO,
        notes=get_cryptocom_note('Card Rebate Reversal: Netflix'),
    ), HistoryEvent(
        identifier=12,
        event_identifier='CCM_a5051400dab1a0736302f3d80c969067f60def2e01f00fe5088d46016c351121',
        sequence_index=0,
        timestamp=TimestampMS(1616237351000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('10')),
        asset=A_CRO,
        notes=get_cryptocom_note('Pay Rewards'),
    ), HistoryEvent(
        identifier=13,
        event_identifier='CCM_f1b8ad8d5c58fbdc361faa8e2747ac6dd3d7ddc85025dc965f6324149ffe2b08',
        sequence_index=0,
        timestamp=TimestampMS(1616237351000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('100')),
        asset=A_CRO,
        notes=get_cryptocom_note('To +49XXXXXXXXXX'),
    ), HistoryEvent(
        identifier=11,
        event_identifier='CCM_29fe97c4aa05263dfccd478c2f90177f0006fea259bd71e22d3813b6602d9692',
        sequence_index=0,
        timestamp=TimestampMS(1616266740000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('100')),
        asset=symbol_to_asset_or_token('CRO'),
        notes=get_cryptocom_note('From +49XXXXXXXXXX'),
    ), HistoryEvent(
        identifier=10,
        event_identifier='CCM_5450de111ff9e242523f011a42f2b1ed9684110bf2cb1b3c893ea3c5957bc3db',
        sequence_index=0,
        timestamp=TimestampMS(1616669547000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('15.38')),
        asset=A_CRO,
        notes=get_cryptocom_note('Merchant XXX'),
    ), HistoryEvent(
        identifier=9,
        event_identifier='CCM_61d0b5ca125f051c7a3b04be7d94ee450d86d6777b0ef9cd334689883138bf5e',
        sequence_index=0,
        timestamp=TimestampMS(1616669548000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.3076')),
        asset=A_CRO,
        notes=get_cryptocom_note('Pay Rewards'),
    ), HistoryEvent(
        identifier=8,
        event_identifier='CCM_68a055044785832276c423a6acc538b7118ce2e04021859a687c9655c47c16d9',
        sequence_index=0,
        timestamp=TimestampMS(1616670041000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('15.31')),
        asset=A_CRO,
        notes=get_cryptocom_note('Refund from Merchant XXX'),
    )]
    assert expected_events == events


def assert_cryptocom_special_events_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from crypto.com"""
    with rotki.data.db.conn.read_ctx() as cursor:
        trades = rotki.data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501
        events_db = DBHistoryEvents(rotki.data.db)
        events = events_db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    expected_events = [AssetMovement(
        identifier=12,
        event_identifier='5d81565035faf4f9e3ec74685a4a5c275f6cd3b10a194e9a12e446042910dbcb',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1609534800000),
        asset=A_ETC,
        balance=Balance(FVal('1.0')),
    ), AssetMovement(
        identifier=11,
        event_identifier='e973b9453f750c8286fdb718b8211abbd8b9027fea582a4e9365f3d0b5c371dc',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1609534860000),
        asset=A_ETC,
        balance=Balance(FVal('0.24')),
    ), AssetMovement(
        identifier=10,
        event_identifier='6e7b476f5880af1cea17c22fd8781fc7aa75a67fc7808200f18d20b181589c34',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1609538400000),
        asset=A_BTC,
        balance=Balance(FVal('0.01')),
    ), AssetMovement(
        identifier=9,
        event_identifier='edfb38684bb8ddfa0cd961a3a1fe0f90bda823f45a2095859b2d0e3c43401e4d',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1609542000000),
        asset=A_BTC,
        balance=Balance(FVal('0.01')),
    ), HistoryEvent(
        identifier=1,
        event_identifier='CCM_26556241ec9e68acba8cd0d6a6e7b5c010f344b7c763d4b45fa1b6d2abfaf2af',
        sequence_index=0,
        timestamp=TimestampMS(1609624800000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.00005')),
        asset=A_BTC,
        notes='Staking profit for BTC',
    ), AssetMovement(
        identifier=8,
        event_identifier='dd3b3db7df9d05e2a725bfb2edfd15f55a4d8cd473941735ab863a321ad38d92',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1609624800000),
        asset=A_BTC,
        balance=Balance(FVal('0.02005')),
    ), AssetMovement(
        identifier=7,
        event_identifier='4944f654c206336187e8df89b7ef8201fe7fdda65133a362166770de9283b6b6',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1609714800000),
        asset=A_BTC,
        balance=Balance(FVal('1.0')),
    ), AssetMovement(
        identifier=6,
        event_identifier='99e05dba03cbcd7337e453049be2bdaa88814aec73cdcce26f40a0bc98d79f2e',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1609797600000),
        asset=A_BTC,
        balance=Balance(FVal('1.02005')),
    ), HistoryEvent(
        identifier=2,
        event_identifier='CCM_680977437f573e30752041fb8971be234a8fdb4d72f707d56eb5643d40908d82',
        sequence_index=0,
        timestamp=TimestampMS(1609797600000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.02005')),
        asset=A_BTC,
        notes='Staking profit for BTC',
    ), HistoryEvent(
        identifier=3,
        event_identifier='CCM_4edba1d54872a176b913a3a1afc476f4b7d9565d665b86d7fb0c8b1f56ca8cbf',
        sequence_index=0,
        timestamp=TimestampMS(1609884000000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(ONE),
        asset=A_CRO,
        notes=get_cryptocom_note('CRO Stake Rewards'),
    ), HistoryEvent(
        identifier=5,
        event_identifier='CCM_afb12f3eac3e93695a1ac1b09b4708f678d7cf395a3f364390376510ec801059',
        sequence_index=0,
        timestamp=TimestampMS(1609884000000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(ONE),
        asset=A_CRO,
        notes=get_cryptocom_note('CRO Airdrop to Exchange'),
    ), HistoryEvent(
        identifier=4,
        event_identifier='CCM_b0bb99d65ac111caec2d5d9b6a2b69bae1a13de50f89358a2a25dfc0992c51c4',
        sequence_index=0,
        timestamp=TimestampMS(1609884000000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.5')),
        asset=A_MCO,
        notes=get_cryptocom_note('MCO Stake Rewards'),
    ), HistoryEvent(
        identifier=13,
        event_identifier='CCM_64288070ac60947e3fcaaf150f76c5768122a08538c8efdec806d689d4c49d62',
        sequence_index=0,
        timestamp=TimestampMS(1635390997000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.00356292')),
        asset=A_AXS,
        notes=get_cryptocom_note('Supercharger Reward'),
    ), HistoryEvent(
        identifier=14,
        event_identifier='CCM_e66810bd6561fbe1d31aec4ad7942d854d63115808c2d1a7b2cd0df8bb110e49',
        sequence_index=0,
        timestamp=TimestampMS(1635477398000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.5678')),
        asset=A_CRO,
        notes=get_cryptocom_note('Card Cashback Reversal'),
    )]
    assert expected_events == events

    expected_trades = [Trade(
        timestamp=Timestamp(1609884000),
        location=Location.CRYPTOCOM,
        base_asset=symbol_to_asset_or_token('CRO'),
        quote_asset=symbol_to_asset_or_token('MCO'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(ONE),
        rate=Price(FVal('0.1')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='MCO Earnings/Rewards Swap\nSource: crypto.com (CSV import)',
    ), Trade(
        timestamp=Timestamp(1635390998),
        location=Location.CRYPTOCOM,
        base_asset=symbol_to_asset_or_token('EUR'),
        quote_asset=A_USDC.resolve_to_evm_token(),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('11.3')),
        rate=Price(FVal('1.14513274336283185840707964601769911504424778761061946902654867256637168141593')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='USDC -> EUR\nSource: crypto.com (CSV import)',
    )]
    assert trades == expected_trades


def assert_blockfi_transactions_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from blockfi"""
    with rotki.data.db.conn.read_ctx() as cursor:
        events_db = DBHistoryEvents(rotki.data.db)
        events = events_db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    expected_events = [AssetMovement(
        identifier=5,
        event_identifier='f62fb2e0ee8695192ae332e25c4afc3682466ae2d1ef019ed51bc08cfd3aa296',
        location=Location.BLOCKFI,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1595247055000),
        asset=A_BTC,
        balance=Balance(FVal('1.11415058')),
    ), HistoryEvent(
        identifier=4,
        event_identifier='BLF_a8ef6e164b0130b0df9b4d1e877d1c0a601bbc66f244682b6d4f3fe3aadd66e9',
        sequence_index=0,
        timestamp=TimestampMS(1600293599000),
        location=Location.BLOCKFI,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.48385358')),
        asset=A_ETH,
        notes='Bonus Payment from BlockFi',
    ), AssetMovement(
        identifier=3,
        event_identifier='677c77a20f78f19f2dcc5333e260b16b15b511dbb4e42afab67d02ff907e161a',
        location=Location.BLOCKFI,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1605977971000),
        asset=A_ETH,
        balance=Balance(FVal('3')),
    ), HistoryEvent(
        identifier=2,
        event_identifier='BLF_e027e251abadf0f748d49341c94f0a9bdaff50a2e4f735bb410dd5b594a3b1ec',
        sequence_index=0,
        timestamp=TimestampMS(1606953599000),
        location=Location.BLOCKFI,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.00052383')),
        asset=A_BTC,
        notes='Referral Bonus from BlockFi',
    ), AssetMovement(
        identifier=6,
        event_identifier='7549573fba3392466dbd36b1f7a7e8bac06a276caa615008645d646f025f0b00',
        location=Location.BLOCKFI,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1611734258000),
        asset=A_USDC,
        balance=Balance(FVal('3597.48627700')),
    ), AssetMovement(
        identifier=7,
        event_identifier='731be1787656d4aa1e5bdc20f733f288728081884e2a607ccd3dafaca37c8e91',
        location=Location.BLOCKFI,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1611820658000),
        asset=A_BTC,
        balance=Balance(FVal('2.11415058')),
    ), HistoryEvent(
        identifier=1,
        event_identifier='BLF_d6e38784f89609668f70a37dd67f67e57fb926a74fc9c1cd1ea4e557317c0b9d',
        sequence_index=0,
        timestamp=TimestampMS(1612051199000),
        location=Location.BLOCKFI,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.56469042')),
        asset=A_ETH,
        notes='Interest Payment from BlockFi',
    )]
    assert expected_events == events


def assert_blockfi_trades_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing trades data from blockfi"""
    with rotki.data.db.conn.read_ctx() as cursor:
        trades = rotki.data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    expected_trades = [Trade(
        timestamp=Timestamp(1612051199),
        location=Location.BLOCKFI,
        base_asset=symbol_to_asset_or_token('LTC'),
        quote_asset=A_USDC.resolve_to_evm_token(),
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal('42.23878904')),
        rate=Price(FVal('151.628399998277980935222379661289645722286549718755857589803668291907073101071')),
        fee=None,
        fee_currency=None,
        link='',
        notes='One Time',
    )]
    assert trades == expected_trades


def assert_nexo_results(rotki: Rotkehlchen, websocket_connection: WebsocketReader):
    """A utility function to help assert on correctness of importing data from nexo"""
    with rotki.data.db.conn.read_ctx() as cursor:
        events_db = DBHistoryEvents(rotki.data.db)
        events = events_db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0
    websocket_connection.wait_until_messages_num(num=1, timeout=10)
    assert websocket_connection.pop_message() == {
        'type': 'csv_import_result',
        'data': {
            'source_name': 'Nexo',
            'total_entries': 31,
            'imported_entries': 27,
            'messages': [
                {'msg': 'Ignoring rejected entry.', 'rows': [2, 8]},
                {'msg': 'Found exchange/credit card status transaction in nexo csv import but the entry will be ignored since not enough information is provided about the trade.', 'rows': [7, 15], 'is_error': True},  # noqa: E501
            ],
        },
    }
    assert websocket_connection.messages_num() == 0

    expected_events = [AssetMovement(
        identifier=12,
        event_identifier='30270894f93665bb104b59a693ccd2f1c3e19dbe559b8c86c5f1efbe47e2cf5b',
        location=Location.NEXO,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1621940400000),
        asset=A_GBP,
        balance=Balance(FVal('5000')),
    ), HistoryEvent(
        identifier=1,
        event_identifier='NEXO_df0cd4ec1cfef6d56ecdc864d71e41f6629074b6453b78cadd67cef214ad3997',
        sequence_index=0,
        timestamp=TimestampMS(1643698860000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('127.5520683')),
        asset=A_GBP,
        location_label='NXTZOvzs3be6e',
        notes='Fixed Term Interest from Nexo',
    ), HistoryEvent(
        identifier=4,
        event_identifier='NEXO_3c65434b92f9e41a5274160c861ebb51890a3bb9246982d18cb0500b3babb4f9',
        sequence_index=0,
        timestamp=TimestampMS(1646092800000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.10000001')),
        asset=symbol_to_asset_or_token('NEXO'),
        location_label='NXTabcdefghij',
        notes='Cashback from Nexo',
    ), AssetMovement(
        identifier=3,
        event_identifier='46383f05d585bd112c7d8a3a03258569ab1cabe7a3834a13f516964a533b5f6c',
        location=Location.NEXO,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1647963925000),
        asset=A_ETH_MATIC,
        balance=Balance(FVal('5.00000000')),
    ), AssetMovement(
        identifier=2,
        event_identifier='a5f62498f9cc39ac8d99455fe9db0abdf26c9ce5d92b30f0bc9ecce9937c9189',
        location=Location.NEXO,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1647964353000),
        asset=A_ETH_MATIC,
        balance=Balance(FVal('3050.00000000')),
    ), HistoryEvent(
        identifier=5,
        event_identifier='NEXO_f5c25b7009473f1ed6fb48c0ed42c3febf0703883740ba2a1862953d71b1e8db',
        sequence_index=0,
        timestamp=TimestampMS(1649462400000),
        location=Location.NEXO,
        event_type=HistoryEventType.LOSS,
        event_subtype=HistoryEventSubType.LIQUIDATE,
        balance=Balance(FVal('710.82000000')),
        asset=A_GBP,
        location_label='NXTabcdefghij',
        notes='Liquidation from Nexo',
    ), HistoryEvent(
        identifier=6,
        event_identifier='NEXO_178eb80900dce91bc7230e95d86bf63d5a16451edfde20336915209e0cf66244',
        sequence_index=0,
        timestamp=TimestampMS(1649548800000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.00999999')),
        asset=A_BTC,
        location_label='NXTabcdefghij',
        notes='Referral Bonus from Nexo',
    ), AssetMovement(
        identifier=7,
        event_identifier='44082c1422aea2a9e03665529115684e81d37f04cf5ed4c112efc956c22a3aea',
        location=Location.NEXO,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1649877300000),
        asset=A_USDC,
        balance=Balance(FVal('595.92')),
    ), AssetMovement(
        identifier=8,
        event_identifier='fd3b3af4503ed66ab961365e9ae94cd4d301a1db2e944889c0ba00c43e3bcf9b',
        location=Location.NEXO,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1650192060000),
        asset=A_GBP,
        balance=Balance(FVal('54')),
    ), AssetMovement(
        identifier=11,
        event_identifier='22d48c31b52037480e31c626d6d38c34fc2ee501819cfea78b2e512e2900f140',
        location=Location.NEXO,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1650192180000),
        asset=A_BTC,
        balance=Balance(FVal('0.0017316')),
    ), HistoryEvent(
        identifier=9,
        event_identifier='NEXO_d31d7ee1cab8bcda90e3021abd70b578209414ac7d36d078072d8cbd052fa287',
        sequence_index=0,
        timestamp=TimestampMS(1650438000000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('1.09246793')),
        asset=A_USDC,
        location_label='NXTGWynyMmm5K',
        notes='Interest from Nexo',
    ), HistoryEvent(
        identifier=10,
        event_identifier='NEXO_e8137e27e69bc848578349c0dece234fd4af50487ecfdf42518de3246f900b23',
        sequence_index=0,
        timestamp=TimestampMS(1657782007000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.00178799')),
        asset=A_ETH,
        location_label='NXT1isX0Refua',
        notes='Interest from Nexo',
    ), AssetMovement(
        identifier=16,
        event_identifier='c64cd362e062eba2958f2656ebb63ebb22107650e88c7a04c401687d81220056',
        location=Location.NEXO,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1707003036000),
        asset=A_EUR,
        balance=Balance(FVal('47.99000000')),
    ), HistoryEvent(
        identifier=15,
        event_identifier='NEXO_05be9cf28e8f09148ffb0d1f7280419118aa19803dd13c6bdcdf71e7bc8e3e9d',
        sequence_index=0,
        timestamp=TimestampMS(1734971539000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('1.28539200')),
        asset=A_USDC,
        location_label='NXT44OjpCjxegVqhfHj3ZmeAa',
        notes='Exchange Cashback from Nexo',
    ), HistoryEvent(
        identifier=13,
        event_identifier='NEXO_4cf8625c0bd44e83aab18c3f380f0de765ce52174806f71a232fd16492adcba8',
        sequence_index=0,
        timestamp=TimestampMS(1735365600000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('5.37250072')),
        asset=Asset('eip155:1/erc20:0xB62132e35a6c13ee1EE0f84dC5d40bad8d815206'),
        location_label='NXT5Gz0cNLEHLbYtc3xDkZ8eR',
        notes='Fixed Term Interest from Nexo',
    ), HistoryEvent(
        identifier=14,
        event_identifier='NEXO_a1ef61959184d70ed118df337ddae6c1c63538989cd3438ab663b7ca9dc29538',
        sequence_index=0,
        timestamp=TimestampMS(1735365600000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        balance=Balance(FVal('0.12179800')),
        asset=A_USDC,
        location_label='NXT4OTjYHHRW6xseMpUarHKKT',
        notes='Interest from Nexo',
    )]
    assert events == expected_events


def assert_shapeshift_trades_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing trades data from shapeshift"""
    with rotki.data.db.conn.read_ctx() as cursor:
        trades = rotki.data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501
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
            amount=AssetAmount(FVal('0.59420343') + FVal('0.002')),
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
            amount=AssetAmount(FVal('0.06198721') + FVal('0.0042')),
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
    with rotki.data.db.conn.read_ctx() as cursor:
        trades = rotki.data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501
        history_db = DBHistoryEvents(rotki.data.db)
        events = history_db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )

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
        rate=Price(FVal('7531.00514819511930618355770708004855992119556212928627158009525215311437186898')),
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
        rate=Price(FVal('0.000170791075050709939148073022312373225152129817444219066937119675456389452332657')),
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
        rate=Price(FVal('0.00945963318697030358017570852003256519799395333012472323263413517142611581370832')),
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
        rate=Price(FVal('44054.1938293177414115617684285986312264076973912653875018201776493385754449634')),
        fee=Fee(FVal('0.0000021')),
        fee_currency=A_BTC,
        link='',
        notes=notes4,
    )]
    expected_events = [HistoryEvent(
        identifier=2,
        event_identifier='UPH_55d4d58869d96ad9adf18929bf89caaae87e657482ea20ae4c8c66b8ab34f4e2',
        sequence_index=0,
        timestamp=TimestampMS(1576780809000),
        location=Location.UPHOLD,
        asset=A_BAT,
        balance=Balance(amount=FVal('5.15')),
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        notes=notes5,
    ), AssetMovement(
        identifier=1,
        event_identifier='c85215d66a23ae39cbf232dd931dafa40006acb065d5314382f623b7bb8ce707',
        location=Location.UPHOLD,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1589376604000),
        asset=symbol_to_asset_or_token('GBP'),
        balance=Balance(FVal('24.65')),
    )]
    assert len(trades) == 4
    assert trades == expected_trades
    assert events == expected_events


def assert_custom_cointracking(rotki: Rotkehlchen):
    """
    A utility function to help assert on correctness of importing data from cointracking.info
    when using custom formats for dates
    """
    with rotki.data.db.conn.read_ctx() as cursor:
        events = DBHistoryEvents(rotki.data.db).get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )
    assert events == [AssetMovement(
        identifier=2,
        event_identifier='2bb82301ad9d4b4251e404c11026f53f9f1c5190a943a26aa654e4fa0969ccbd',
        location=Location.COINBASE,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1504646040000),
        asset=A_ETH,
        balance=Balance(FVal('0.05770427')),
    ), AssetMovement(
        identifier=1,
        event_identifier='55220a50d1f1af04042410f6c0223518cd14e1a5ad250dfb65be6404c7b6a01e',
        location=Location.POLONIEX,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1504646040000),
        asset=A_XMR,
        balance=Balance(FVal('5.00000000')),
    ), AssetMovement(
        identifier=3,
        event_identifier='2bb82301ad9d4b4251e404c11026f53f9f1c5190a943a26aa654e4fa0969ccbd',
        location=Location.COINBASE,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1504646040000),
        asset=A_ETH,
        balance=Balance(FVal('0.0001')),
        is_fee=True,
    )]


def assert_bisq_trades_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing trades data from bisq"""
    with rotki.data.db.conn.read_ctx() as cursor:
        trades = rotki.data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    expected_trades = [Trade(
        timestamp=Timestamp(1517195493),
        location=Location.BISQ,
        base_asset=symbol_to_asset_or_token('SC'),
        quote_asset=symbol_to_asset_or_token('BTC'),
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal(9811.32075471)),
        rate=Price(FVal(0.00000371)),
        fee=Fee(FVal(0.0002)),
        fee_currency=symbol_to_asset_or_token('BTC'),
        link='',
        notes='ID: exxXE',
    ), Trade(
        timestamp=Timestamp(1545136553),
        location=Location.BISQ,
        base_asset=symbol_to_asset_or_token('BTC'),
        quote_asset=symbol_to_asset_or_token('EUR'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal(0.25)),
        rate=Price(FVal(3394.8800)),
        fee=Fee(FVal(0.0005)),
        fee_currency=symbol_to_asset_or_token('BTC'),
        link='',
        notes='ID: IxxWl',
    ), Trade(
        timestamp=Timestamp(1545416958),
        location=Location.BISQ,
        base_asset=symbol_to_asset_or_token('BTC'),
        quote_asset=symbol_to_asset_or_token('EUR'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal(0.1850)),
        rate=Price(FVal(3376.9400)),
        fee=Fee(FVal(0.000370)),
        fee_currency=symbol_to_asset_or_token('BTC'),
        link='',
        notes='ID: VxxABMN',
    ), Trade(
        timestamp=Timestamp(1560284504),
        location=Location.BISQ,
        base_asset=symbol_to_asset_or_token('DASH'),
        quote_asset=symbol_to_asset_or_token('BTC'),
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal(19.45685539)),
        rate=Price(FVal(0.01541873)),
        fee=Fee(FVal(0.0009)),
        fee_currency=symbol_to_asset_or_token('BTC'),
        link='',
        notes='ID: LxxAob',
    ), Trade(
        timestamp=Timestamp(1577082782),
        location=Location.BISQ,
        base_asset=symbol_to_asset_or_token('BTC'),
        quote_asset=symbol_to_asset_or_token('EUR'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal(0.01)),
        rate=Price(FVal(6785.6724)),
        fee=Fee(FVal(0.00109140)),
        fee_currency=symbol_to_asset_or_token('BTC'),
        link='',
        notes='ID: GxxL',
    ), Trade(
        timestamp=Timestamp(1577898084),
        location=Location.BISQ,
        base_asset=symbol_to_asset_or_token('BSQ'),
        quote_asset=symbol_to_asset_or_token('BTC'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal(116.65)),
        rate=Price(FVal(0.00008487)),
        fee=Fee(FVal(0.00005940)),
        fee_currency=symbol_to_asset_or_token('BTC'),
        link='',
        notes='ID: 552',
    ), Trade(
        timestamp=Timestamp(1607706820),
        location=Location.BISQ,
        base_asset=symbol_to_asset_or_token('BTC'),
        quote_asset=symbol_to_asset_or_token('EUR'),
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal(0.05)),
        rate=Price(FVal(15883.3283)),
        fee=Fee(FVal(2.01)),
        fee_currency=symbol_to_asset_or_token('BSQ'),
        link='',
        notes='ID: xxYARFU',
    ), Trade(
        timestamp=Timestamp(1615371360),
        location=Location.BISQ,
        base_asset=symbol_to_asset_or_token('BTC'),
        quote_asset=symbol_to_asset_or_token('EUR'),
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal(0.01)),
        rate=Price(FVal(50500.0000)),
        fee=Fee(FVal(0.40)),
        fee_currency=symbol_to_asset_or_token('BSQ'),
        link='',
        notes='ID: xxcz',
    ), Trade(
        timestamp=Timestamp(1615372820),
        location=Location.BISQ,
        base_asset=symbol_to_asset_or_token('BTC'),
        quote_asset=symbol_to_asset_or_token('EUR'),
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal(0.01)),
        rate=Price(FVal(49000.0000)),
        fee=Fee(FVal(0.29)),
        fee_currency=symbol_to_asset_or_token('BSQ'),
        link='',
        notes='ID: xxhee',
    )]
    assert trades == expected_trades


def assert_bitmex_import_wallet_history(rotki: Rotkehlchen):
    expected_events = [
        AssetMovement(
            identifier=3,
            event_identifier='016035ad3c5a14f733b11d39f19f82cefa1000d0db62d5377548d2e6456a16fc',
            location=Location.BITMEX,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1574825791000),
            asset=A_BTC,
            balance=Balance(FVal('0.05000000')),
        ),
        AssetMovement(
            identifier=1,
            event_identifier='c7ee1cfaa00878d7079cdc2ebf0f15477e9116fc1284f0ebf298db26405e5897',
            location=Location.BITMEX,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1577252845000),
            asset=A_BTC,
            balance=Balance(FVal('0.05746216')),
            extra_data={'address': '3Qsy5NGSnGA1vd1cmcNgeMjLrKPsKNhfCe'},
        ),
        AssetMovement(
            identifier=2,
            event_identifier='415ec13a5c2e79c101ede3f4178cfb3dd576c96ed3037fd96d56e1ea89ba039d',
            location=Location.BITMEX,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1577252845000),
            asset=A_BTC,
            balance=Balance(FVal('0.00100000')),
            is_fee=True,
        ),
    ]
    expected_margin_positions = [
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1576738800),
            profit_loss=AssetAmount(FVal(0.00000373)),
            pl_currency=A_BTC,
            fee=Fee(FVal(0)),
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1576825200),
            profit_loss=AssetAmount(FVal(0.00000016)),
            pl_currency=A_BTC,
            fee=Fee(FVal(0)),
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1576911600),
            profit_loss=AssetAmount(FVal(-0.00000123)),
            pl_currency=A_BTC,
            fee=Fee(FVal(0)),
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1576998000),
            profit_loss=AssetAmount(FVal(-0.00000075)),
            pl_currency=A_BTC,
            fee=Fee(FVal(0)),
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1577084400),
            profit_loss=AssetAmount(FVal(-0.00000203)),
            pl_currency=A_BTC,
            fee=Fee(FVal(0)),
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1577170800),
            profit_loss=AssetAmount(FVal(-0.00000201)),
            pl_currency=A_BTC,
            fee=Fee(FVal(0)),
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1577257200),
            profit_loss=AssetAmount(FVal(0.00085517)),
            pl_currency=A_BTC,
            fee=Fee(FVal(0)),
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
    ]
    with rotki.data.db.conn.read_ctx() as cursor:
        margin_positions = rotki.data.db.get_margin_positions(cursor)
        warnings = rotki.msg_aggregator.consume_warnings()
        errors = rotki.msg_aggregator.consume_errors()
        events = DBHistoryEvents(rotki.data.db).get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )
    assert events == expected_events
    assert margin_positions == expected_margin_positions
    assert len(warnings) == 0
    assert len(errors) == 0


def assert_binance_import_results(rotki: Rotkehlchen, websocket_connection: WebsocketReader):
    expected_trades = [
        Trade(
            timestamp=Timestamp(1603922583),
            location=Location.BINANCE,
            base_asset=asset_from_binance('BNB'),
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.576474665')),
            rate=Price(FVal('0.00235055928644240570846075433231396534148827726809378185524974515800203873598369')),
            fee=None,
            fee_currency=None,
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1604042198),
            location=Location.BINANCE,
            base_asset=A_AXS,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('1.19592356')),
            rate=Price(FVal('0.00797282373333333333333333333333333333333333333333333333333333333333333333333333')),
            fee=None,
            fee_currency=None,
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1604067680),
            location=Location.BINANCE,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.03605')),
            rate=Price(FVal('0.000268085733817674892430599305657949412222028604747798345911022344945913703202284')),
            fee=Fee(FVal('0.00003605')),
            fee_currency=A_ETH,
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1604070545),
            location=Location.BINANCE,
            base_asset=A_ETH2,
            quote_asset=A_ETH,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(0.036)),
            rate=Price(ONE),
            fee=None,
            fee_currency=None,
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1604437979),
            location=Location.BINANCE,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.08345')),
            rate=Price(FVal('0.000250443284613766366468649509632048726245454454384260140448594011400178315618645')),
            fee=Fee(FVal('0.00008345')),
            fee_currency=A_ETH,
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1604437979),
            location=Location.BINANCE,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.0148')),
            rate=Price(FVal('0.000250465866511711783918087643016009778187428617228044162141583345021740437213217')),
            fee=Fee(FVal('0.00009009')),
            fee_currency=asset_from_binance('BNB'),
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1605169314),
            location=Location.BINANCE,
            base_asset=A_BTC,
            quote_asset=CryptoAsset('IOTA'),
            trade_type=TradeType.SELL,
            amount=AssetAmount(FVal('0.001366875')),
            rate=Price(FVal('0.00002025')),
            fee=Fee(FVal('0.0001057')),
            fee_currency=asset_from_binance('BNB'),
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1605903740),
            location=Location.BINANCE,
            base_asset=asset_from_binance('BNB'),
            quote_asset=CryptoAsset('SOL-2'),
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.00072724')),
            rate=Price(FVal('0.353790806907103399795190130207509857387141734754191669930165185727525035695782')),
            fee=None,
            fee_currency=None,
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1605903740),
            location=Location.BINANCE,
            base_asset=asset_from_binance('BNB'),
            quote_asset=CryptoAsset('SOL-2'),
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.000237955')),
            rate=Price(FVal('1.64367617600331560406161497547834496097257719140705947364785521862264281273745')),
            fee=None,
            fee_currency=None,
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1605910681),
            location=Location.BINANCE,
            base_asset=A_USDT,
            quote_asset=EvmToken('eip155:56/erc20:0x23CE9e926048273eF83be0A3A8Ba9Cb6D45cd978'),
            trade_type=TradeType.SELL,
            amount=AssetAmount(FVal('1157.56')),
            rate=Price(FVal('3.44')),
            fee=Fee(FVal('1.15756')),
            fee_currency=A_USDT,
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1605911401),
            location=Location.BINANCE,
            base_asset=CryptoAsset('IOTA'),
            quote_asset=A_USDT,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('882')),
            rate=Price(FVal('0.769408324998076479187504808802031237977994921905055012695237362468261906593829')),
            fee=Fee(FVal('0.882')),
            fee_currency=CryptoAsset('IOTA'),
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1606837907),
            location=Location.BINANCE,
            base_asset=A_BTC,
            quote_asset=A_ETH,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.10680859385')),
            rate=Price(FVal('0.105682989690721649484536082474226804123711340206185567010309278350515463917526')),
            fee=Fee(FVal('0.0462623227152')),
            fee_currency=EvmToken('eip155:1/erc20:0xB8c77482e45F1F44dE1745F52C74426C631bDD52'),
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1606837907),
            location=Location.BINANCE,
            base_asset=A_BTC,
            quote_asset=A_ETH,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.09564009919439999')),
            rate=Price(FVal('0.105682993421052632206922204695749122240024160732607611786961067306030999402176')),
            fee=Fee(FVal('0.041427214681599996')),
            fee_currency=EvmToken('eip155:1/erc20:0xB8c77482e45F1F44dE1745F52C74426C631bDD52'),
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1606948201),
            location=Location.BINANCE,
            base_asset=CryptoAsset('IOTA'),
            quote_asset=A_USDT,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('882')),
            rate=Price(FVal('0.769408324998076479187504808802031237977994921905055012695237362468261906593829')),
            fee=None,
            fee_currency=None,
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1685994420),
            location=Location.BINANCE,
            base_asset=EvmToken('eip155:1/erc20:0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'),
            quote_asset=EvmToken('eip155:1/erc20:0x4Fabb145d64652a948d72533023f6E7A623C7C53'),
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('140.1195285')),
            rate=Price(FVal('1.11536230236898751269214452908890115413004082453093372870932008377376574660536')),
            fee=None,
            fee_currency=None,
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1690262284),
            location=Location.BINANCE,
            base_asset=A_USDT,
            quote_asset=A_USDC,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('2641.26410000')),
            rate=Price(FVal('1.0001')),
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1690570138),
            location=Location.BINANCE,
            base_asset=A_USDT,
            quote_asset=A_SOL,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('26.82490000')),
            rate=Price(FVal('25.07')),
            fee=Fee(FVal(0.00008316)),
            fee_currency=A_BNB,
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1695981386),
            location=Location.BINANCE,
            base_asset=A_ETH,
            quote_asset=A_USDT,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.01700000')),
            rate=Price(FVal('0.000597307338517961031669235088222293899102844377546022530432808897490114563547528')),
            fee=Fee(FVal('0.00009883')),
            fee_currency=A_BNB,
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
        Trade(
            timestamp=Timestamp(1704118880),
            location=Location.BINANCE,
            base_asset=A_ETH,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.03605')),
            rate=Price(FVal('0.000268085733817674892430599305657949412222028604747798345911022344945913703202284')),
            fee=Fee(FVal('0.00003605')),
            fee_currency=A_ETH,
            link='',
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ),
    ]

    expected_events = [
        AssetMovement(
            identifier=1,
            event_identifier='3f9a750608754c8361951f87f0e21ea71bf98221d52a69c809c27307c65fff13',
            location=Location.BINANCE,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1603922583000),
            asset=A_EUR,
            balance=Balance(FVal(245.25)),
        ), HistoryEvent(
            identifier=2,
            event_identifier='BNC_1a75acacbf626a04e8be50cb3f79ec8abd1f573e2cb9d9650df576626e437ddf',
            sequence_index=0,
            timestamp=TimestampMS(1603926662000),
            location=Location.BINANCE,
            asset=A_BNB,
            balance=Balance(amount=FVal('0.577257355')),
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            notes='Imported from binance CSV file. Binance operation: POS savings purchase',
        ), HistoryEvent(
            identifier=3,
            event_identifier='BNC_14e2f3956bf5c9506a460c8bf35ff199139555118a0ef40ea6f732248fcac5a0',
            sequence_index=0,
            timestamp=TimestampMS(1604223373000),
            location=Location.BINANCE,
            asset=A_ETH2,
            balance=Balance(amount=FVal('0.000004615')),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            notes='Imported from binance CSV file. Binance operation: ETH 2.0 Staking Rewards',
        ), HistoryEvent(
            identifier=4,
            event_identifier='BNC_d5dc6cca7342e668707b496d951a317156146eee348073cbb55ba852fb8f7a72',
            sequence_index=0,
            timestamp=TimestampMS(1604274610000),
            location=Location.BINANCE,
            asset=EvmToken('eip155:56/erc20:0x23CE9e926048273eF83be0A3A8Ba9Cb6D45cd978'),
            balance=Balance(amount=FVal('0.115147055')),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            notes='Imported from binance CSV file. Binance operation: Launchpool Interest',
        ), HistoryEvent(
            identifier=5,
            event_identifier='BNC_2d10e01a5946dac7ff1904203810cb6a6bafd1ab92e387fc6850384b17d1eae9',
            sequence_index=0,
            timestamp=TimestampMS(1604450188000),
            location=Location.BINANCE,
            asset=A_AXS,
            balance=Balance(amount=FVal('1.18837124')),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            notes='Imported from binance CSV file. Binance operation: POS savings redemption',
        ), HistoryEvent(
            identifier=6,
            event_identifier='BNC_9a2793560cc940557e51500ca876e0a0d11324666eae644f3145cf7038cbc9bd',
            sequence_index=0,
            timestamp=TimestampMS(1604456888000),
            location=Location.BINANCE,
            asset=A_BNB,
            balance=Balance(amount=FVal('0.000092675')),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            notes='Imported from binance CSV file. Binance operation: POS savings interest',
        ), AssetMovement(
            identifier=7,
            event_identifier='da21894e86cb5aea08db8cf0fad34836b96c380ebc401e46922864533f306e46',
            location=Location.BINANCE,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1606853204000),
            asset=A_KNC,
            balance=Balance(FVal(0.16)),
        ), HistoryEvent(
            identifier=8,
            event_identifier='BNC_ac8a1a8ccd32547766f312428a59ac8ea667f72c33c0c4695b3fc82a7896645f',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1640910825)),
            location=Location.BINANCE,
            asset=A_USDT,
            balance=Balance(amount=FVal(500.00000000)),
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            location_label='CSV import',
            notes='Transfer Between Main and Funding Wallet',
        ), HistoryEvent(
            identifier=9,
            event_identifier='BNC_29a2d52a91b9bbb7213d4710ad190d587c4febc197373291289d85ae275ec7a5',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1640912422)),
            location=Location.BINANCE,
            asset=A_USDT,
            balance=Balance(amount=FVal(100.00000000)),
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            location_label='CSV import',
            notes='Transfer Between Spot Account and UM Futures Account',
        ), HistoryEvent(
            identifier=10,
            event_identifier='BNC_33a197c8698d3de4db57bb5d8a43e48addb28538587f73cd624792036b69a870',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1640912706)),
            location=Location.BINANCE,
            asset=A_USDT,
            balance=Balance(amount=FVal(60.00000000)),
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            location_label='CSV import',
            notes='Transfer Between Spot Account and CM Futures Account',
        ), HistoryEvent(
            identifier=11,
            event_identifier='BNC_a5e6e8af4008679025ce68ac818ee4ae3f8b9f461d70eeb3d30f20f3c9a8d92f',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1640913498)),
            location=Location.BINANCE,
            asset=A_USDT,
            balance=Balance(amount=FVal(40.00000000)),
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            location_label='CSV import',
            notes='Transfer Between Spot Account and UM Futures Account',
        ), HistoryEvent(
            identifier=12,
            event_identifier='BNC_5d651c8364e0b853f3f4c4b3812b2d370607fc008bedb30291137fabae0d93ef',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1673587740)),
            location=Location.BINANCE,
            asset=EvmToken('eip155:1/erc20:0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'),
            balance=Balance(amount=FVal('0.00001605')),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            location_label='CSV import',
            notes='Reward from Simple Earn Locked Rewards',
        ), HistoryEvent(
            identifier=13,
            event_identifier='BNC_e2433b7eddb388759cbab8d440dda8447a0d1d6733889000f2bd3145454cae59',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1673589660)),
            location=Location.BINANCE,
            asset=EvmToken('eip155:1/erc20:0x4Fabb145d64652a948d72533023f6E7A623C7C53'),
            balance=Balance(amount=FVal('0.00003634')),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            location_label='CSV import',
            notes='Reward from Simple Earn Flexible Interest',
        ), HistoryEvent(
            identifier=15,
            event_identifier='BNC_f5b62b836a4f520729099765bd12f49bce839ae53aef5c53f6e2b12cd4a5d2e2',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1673590320)),
            location=Location.BINANCE,
            asset=EvmToken('eip155:1/erc20:0x4Fabb145d64652a948d72533023f6E7A623C7C53'),
            balance=Balance(amount=FVal('0.00003634')),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            location_label='CSV import',
            notes='Reward from Simple Earn Flexible Interest',
        ), HistoryEvent(
            identifier=14,
            event_identifier='BNC_8ee2c667b24dc991ccaf81050b48cf33d9ccdd45471e1517efcb64c0bbfcb318',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1673593020)),
            location=Location.BINANCE,
            asset=EvmToken('eip155:1/erc20:0x4Fabb145d64652a948d72533023f6E7A623C7C53'),
            balance=Balance(amount=FVal('0.00003634')),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            location_label='CSV import',
            notes='Deposit in Simple Earn Flexible Subscription',
        ), HistoryEvent(
            identifier=16,
            event_identifier='BNC_6f2a1947e66d9d38c1d07ade18706be20fbbddf48cdbfbd345e6976a85333e35',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1673593560)),
            location=Location.BINANCE,
            asset=EvmToken('eip155:1/erc20:0x4Fabb145d64652a948d72533023f6E7A623C7C53'),
            balance=Balance(amount=FVal('0.00003634')),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            location_label='CSV import',
            notes='Deposit in Simple Earn Flexible Subscription',
        ), HistoryEvent(
            identifier=17,
            event_identifier='BNC_93ffcc0bba0a90bddb72dd100479e6c784e5dd5ea68e2bf4c5a0a9c3432a24b9',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1686389700)),
            location=Location.BINANCE,
            asset=CryptoAsset('SUI'),
            balance=Balance(amount=FVal('0.0080696')),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            location_label='CSV import',
            notes='Reward from BNB Vault Rewards',
        ), HistoryEvent(
            identifier=18,
            event_identifier='BNC_2d4a94bee000e141e2f5b63195fc805d28757e6f2b7cc8f7af9488e9c3ea3f1b',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1686538886)),
            location=Location.BINANCE, event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_BNB,
            balance=Balance(amount=FVal('0.95901726')),
            location_label='CSV import',
            notes='Unstake eip155:1/erc20:0xB8c77482e45F1F44dE1745F52C74426C631bDD52(Binance Coin) in Staking Redemption',  # noqa: E501
        ), HistoryEvent(
            identifier=19,
            event_identifier='BNC_60fcc311b4f38019dde25c9c55b28058faf57f602ecf3d775004515ff934a152',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1686539468)),
            location=Location.BINANCE, event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_BNB,
            balance=Balance(amount=FVal(0.96455172)),
            location_label='CSV import',
            notes='Deposit in Staking Purchase',
        ), HistoryEvent(
            identifier=20,
            event_identifier='BNC_4259a864eeb6e39a046bbd4030a62d63bcaafebb36c4a5f55b00d1e78a90569e',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1686543089)),
            location=Location.BINANCE, event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH_MATIC,
            balance=Balance(amount=FVal(602.5193197)),
            location_label='CSV import',
            notes='Deposit in Simple Earn Locked Subscription',
        ), AssetMovement(
            identifier=21,
            event_identifier='504972a5e897bc3324adc5635514fcf1a2e8c8adae380ebdc60cec9d52227176',
            location=Location.BINANCE,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1686571601000),
            asset=A_BUSD,
            balance=Balance(FVal('479.6780028')),
        ), AssetMovement(
            identifier=22,
            event_identifier='805fdb95ec899ebd25a799fa8aa9a8735ee3cd423d804b874a3319f42ddb98e5',
            location=Location.BINANCE,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1686571762000),
            asset=A_EUR,
            balance=Balance(FVal('2435.34')),
        ), HistoryEvent(
            identifier=23,
            event_identifier='BNC_4b706868b7c8906507b66b1b35017dcaa9eec3c27e63563603e8aa7475243f81',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1686824951)),
            location=Location.BINANCE, event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_BUSD,
            balance=Balance(amount=FVal(0.35628294)),
            location_label='CSV import',
            notes='Reward from Cash Voucher Distribution',
        ), HistoryEvent(
            identifier=24,
            event_identifier='BNC_6b282ed5ab3de42a924f008ed20e35ebcbbe1618b60c0a120c7c76278240f725',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1686825000)),
            location=Location.BINANCE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_BUSD,
            balance=Balance(amount=FVal(4.87068)),
            location_label='CSV import',
            notes='Reward from Mission Reward Distribution',
        ), HistoryEvent(
            identifier=25,
            event_identifier='BNC_d6a38298147f2c10d888205893ac2baeccad83d1dbed1477a3e2f4ddd943761f',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1694505602)),
            location=Location.BINANCE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDT,
            balance=Balance(amount=FVal(0.07779065)),
            location_label='CSV import',
            notes='0.07779065 USDT fee paid on binance USD-MFutures',
        ), HistoryEvent(
            identifier=26,
            event_identifier='BNC_982287169e9675e5c799ca2f9d2b7f345eb6be73dbe6cfdb60a161949fdf8c01',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1694623421)),
            location=Location.BINANCE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_USDT,
            balance=Balance(amount=FVal(0.05576000)),
            location_label='CSV import',
            notes='0.05576000 USDT realized loss on binance USD-MFutures',
        ), HistoryEvent(
            identifier=27,
            event_identifier='BNC_cd4e771cb6692df31c11743419800b4ccd73c3ac2b4b3f948f731cf663c7db0a',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1694623421)),
            location=Location.BINANCE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_USDT,
            balance=Balance(amount=FVal('1.29642000')),
            location_label='CSV import',
            notes='1.29642000 USDT realized profit on binance USD-MFutures',
        ),
    ]

    with rotki.data.db.conn.read_ctx() as cursor:
        trades = rotki.data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501
        history_db = DBHistoryEvents(rotki.data.db)
        events = history_db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )
    assert trades == expected_trades
    assert expected_events == events
    websocket_connection.wait_until_messages_num(num=1, timeout=10)
    assert websocket_connection.pop_message() == {
        'type': 'csv_import_result',
        'data': {
            'source_name': 'Binance',
            'total_entries': 87,
            'imported_entries': 81,
            'messages': [
                {'msg': 'Failed to deserialize a timestamp from a null entry in binance', 'rows': [4], 'is_error': True},  # noqa: E501
                {'msg': 'Unknown asset "" provided.', 'rows': [5], 'is_error': True},
                {'msg': 'Could not process row in multi-line entry. Expected a valid combination of operations but got "Small assets exchange BNB, Small assets exchange BNB, Small assets exchange BNB" instead', 'rows': [31, 32, 33], 'is_error': True},  # noqa: E501
                {'msg': 'Could not process row in multi-line entry. Expected a valid combination of operations but got "ABC" instead', 'rows': [41], 'is_error': True},  # noqa: E501
            ],
        },
    }
    assert websocket_connection.messages_num() == 0


def assert_rotki_generic_trades_import_results(rotki: Rotkehlchen, websocket_connection: WebsocketReader):  # noqa: E501
    expected_trades = [
        Trade(  # Sell 1875.64 USDC for 1 ETH
            timestamp=Timestamp(1659085200),
            location=Location.BINANCE,
            base_asset=A_USDC,
            quote_asset=A_ETH,
            trade_type=TradeType.SELL,
            amount=AssetAmount(FVal('1875.64')),
            rate=Price(FVal('0.000533151351005523447996417222921242882429464076261969247830074001407519566654582')),
            fee=None,
            fee_currency=None,
            notes='Trade USDC for ETH',
        ), Trade(  # Buy 4.3241 BTC with 392.8870 LTC
            timestamp=Timestamp(1659171600),
            location=Location.KRAKEN,
            base_asset=A_BTC,
            quote_asset=A_LTC,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('4.3241')),
            rate=Price(FVal('90.8598321037903841261765454082930552022386161282116509793945560925973034851183')),
            fee=None,
            fee_currency=None,
            notes='Trade LTC for BTC',
        ), Trade(  # Sell 20 UNI for 880 DAI
            timestamp=Timestamp(1659344400),
            location=Location.KUCOIN,
            base_asset=A_UNI,
            quote_asset=A_DAI,
            trade_type=TradeType.SELL,
            amount=AssetAmount(FVal('20')),
            rate=Price(FVal('44')),
            fee=Fee(FVal('0.1040')),
            fee_currency=A_USD,
            notes='Trade UNI for DAI',
        ),
    ]
    with rotki.data.db.conn.read_ctx() as cursor:
        trades = rotki.data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501

    assert trades == expected_trades
    websocket_connection.wait_until_messages_num(num=1, timeout=10)
    assert websocket_connection.pop_message() == {
        'type': 'csv_import_result',
        'data': {
            'source_name': 'Rotki generic trades',
            'total_entries': 5,
            'imported_entries': 3,
            'messages': [
                {'msg': 'Deserialization error: Failed to deserialize Location value luno.', 'rows': [4], 'is_error': True},  # noqa: E501
                {'msg': 'Entry has zero amount bought.', 'rows': [5], 'is_error': True},
            ],
        },
    }
    assert websocket_connection.messages_num() == 0


def assert_rotki_generic_events_import_results(rotki: Rotkehlchen, websocket_connection: WebsocketReader):  # noqa: E501
    expected_history_events = [
        HistoryEvent(
            identifier=1,
            event_identifier='1xyz',  # placeholder as this field is randomly generated on import
            sequence_index=0,
            timestamp=TimestampMS(1658912400000),
            location=Location.KUCOIN,
            asset=A_EUR,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            balance=Balance(
                amount=FVal('1000.00'),
                usd_value=ZERO,
            ),
            notes='Deposit EUR to Kucoin',
        ), HistoryEvent(
            identifier=2,
            event_identifier='2xyz',  # placeholder as this field is randomly generated on import
            sequence_index=1,
            timestamp=TimestampMS(1658998800000),
            location=Location.BINANCE,
            asset=A_USDT,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            balance=Balance(
                amount=FVal('99.00'),
                usd_value=ZERO,
            ),
            notes='',
        ), HistoryEvent(
            identifier=3,
            event_identifier='2xyz',  # placeholder as this field is randomly generated on import
            sequence_index=2,
            timestamp=TimestampMS(1658998800000),
            location=Location.BINANCE,
            asset=A_USDT,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            balance=Balance(
                amount=FVal('1.00'),
                usd_value=ZERO,
            ),
            notes='',
        ), HistoryEvent(
            identifier=4,
            event_identifier='3xyz',  # placeholder as this field is randomly generated on import
            sequence_index=2,
            timestamp=TimestampMS(1659085200000),
            location=Location.KRAKEN,
            asset=A_BNB,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            balance=Balance(
                amount=FVal('1.01'),
                usd_value=ZERO,
            ),
            notes='',
        ), HistoryEvent(
            identifier=5,
            event_identifier='5xyz',  # placeholder as this field is randomly generated on import
            sequence_index=4,
            timestamp=TimestampMS(1659430800000),
            location=Location.COINBASE,
            asset=A_BTC,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            balance=Balance(
                amount=FVal('0.0910'),
                usd_value=ZERO,
            ),
            notes='',
        ),
    ]
    with rotki.data.db.conn.read_ctx() as cursor:
        history_db = DBHistoryEvents(rotki.data.db)
        history_events = history_db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )
        warnings = rotki.msg_aggregator.consume_warnings()

    assert len(history_events) == 5
    assert len(expected_history_events) == 5
    assert len(warnings) == 0
    websocket_connection.wait_until_messages_num(num=1, timeout=10)
    assert websocket_connection.pop_message() == {
        'type': 'csv_import_result',
        'data': {
            'source_name': 'Rotki generic events',
            'total_entries': 7,
            'imported_entries': 4,
            'messages': [
                {'msg': 'Deserialization error: Failed to deserialize Location value luno.', 'rows': [4], 'is_error': True},  # noqa: E501
                {'msg': 'Deserialization error: Failed to deserialize Location value cex.', 'rows': [6], 'is_error': True},   # noqa: E501
                {'msg': "Unsupported entry Invalid. Data: {'Type': 'Invalid', 'Location': 'bisq', 'Currency': 'BCH', 'Amount': '0.3456', 'Fee': '', 'Fee Currency': '', 'Description': '', 'Timestamp': '1659686400000'}", 'rows': [7], 'is_error': True},  # noqa: E501
            ],
        },
    }
    assert websocket_connection.messages_num() == 0
    for actual, expected in zip(history_events, expected_history_events, strict=True):
        assert_is_equal_history_event(actual=actual, expected=expected)


def assert_is_equal_history_event(
        actual: HistoryBaseEntry,
        expected: HistoryBaseEntry,
) -> None:
    """Compares two `HistoryEvent` objects omitting the `event_identifier` as its
    generated randomly upon import."""
    actual_dict = actual.serialize()
    actual_dict.pop('event_identifier')
    expected_dict = expected.serialize()
    expected_dict.pop('event_identifier')
    assert actual_dict == expected_dict


def assert_bitcoin_tax_trades_import_results(
        rotki: Rotkehlchen,
        csv_file_name: Literal['bitcoin_tax_trades.csv', 'bitcoin_tax_spending.csv'],
):
    if csv_file_name == 'bitcoin_tax_trades.csv':
        expected_history_events = [
            HistoryEvent(
                identifier=1,
                event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
                sequence_index=0,
                timestamp=TimestampMS(1528060575000),
                location=Location.COINBASEPRO,
                asset=A_EUR,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                balance=Balance(
                    amount=FVal('1008'),
                    usd_value=ZERO,
                ),
                notes='',
            ),
            HistoryEvent(
                identifier=2,
                event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
                sequence_index=1,
                timestamp=TimestampMS(1528060575000),
                location=Location.COINBASEPRO,
                asset=A_BCH,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                balance=Balance(
                    amount=FVal('0.99735527'),
                    usd_value=ZERO,
                ),
                notes='',
            ),
            HistoryEvent(
                identifier=3,
                event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
                sequence_index=2,
                timestamp=TimestampMS(1528060575000),
                location=Location.COINBASEPRO,
                asset=A_EUR,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.FEE,
                balance=Balance(
                    amount=FVal('3.01495511'),
                    usd_value=ZERO,
                ),
                notes='',
            ),
            HistoryEvent(
                identifier=4,
                event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
                sequence_index=0,
                timestamp=TimestampMS(1541771471000),
                location=Location.EXTERNAL,
                asset=A_USDT,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                balance=Balance(
                    amount=FVal('713.952'),
                    usd_value=ZERO,
                ),
                notes='',
            ),
            HistoryEvent(
                identifier=5,
                event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
                sequence_index=1,
                timestamp=TimestampMS(1541771471000),
                location=Location.EXTERNAL,
                asset=A_BTC,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                balance=Balance(
                    amount=FVal('0.110778'),
                    usd_value=ZERO,
                ),
                notes='',
            ),
            HistoryEvent(
                identifier=6,
                event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
                sequence_index=2,
                timestamp=TimestampMS(1541771471000),
                location=Location.EXTERNAL,
                asset=A_BTC,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.FEE,
                balance=Balance(
                    amount=FVal('0.000222'),
                    usd_value=ZERO,
                ),
                notes='',
            ),
        ]
        with rotki.data.db.conn.read_ctx() as cursor:
            history_db = DBHistoryEvents(rotki.data.db)
            history_events = history_db.get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(),
                has_premium=False,
            )
        assert len(history_events) == 6
        assert len(expected_history_events) == 6
        for actual, expected in zip(history_events, expected_history_events, strict=True):
            assert_is_equal_history_event(actual=actual, expected=expected)

    elif csv_file_name == 'bitcoin_tax_spending.csv':
        # the spending csv file is imported after the trades csv file
        expected_history_events = [
            HistoryEvent(
                identifier=7,  # last event identifier of trades import + 1
                event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
                sequence_index=0,
                timestamp=TimestampMS(1543701600000),
                location=Location.EXTERNAL,
                asset=A_BTC,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                balance=Balance(
                    amount=FVal('0.05'),
                    usd_value=ZERO,
                ),
                notes='',
            ),
        ]
        with rotki.data.db.conn.read_ctx() as cursor:
            history_db = DBHistoryEvents(rotki.data.db)
            history_events = history_db.get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(),
                has_premium=False,
            )

        assert len(history_events) == 7  # events from trades import + 1
        assert len(expected_history_events) == 1
        history_events = history_events[6:]  # only check the last event
        for actual, expected in zip(history_events, expected_history_events, strict=True):
            assert_is_equal_history_event(actual=actual, expected=expected)

    else:
        raise AssertionError(f'Unexpected csv file name {csv_file_name}')


def assert_bitstamp_trades_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from bitstamp"""
    with rotki.data.db.conn.read_ctx() as cursor:
        history_db = DBHistoryEvents(rotki.data.db)
        history_events = history_db.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=False,
        )

    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0
    assert len(history_events) == 5

    expected_history_events = [
        HistoryEvent(
            identifier=1,
            event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
            sequence_index=0,
            timestamp=TimestampMS(1643328780000),
            location=Location.BITSTAMP,
            asset=A_ETH,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            balance=Balance(
                amount=FVal('2.00000000'),
                usd_value=ZERO,
            ),
            notes='Deposit of 2.00000000 ETH(Ethereum) on Bitstamp',
        ),
        HistoryEvent(
            identifier=2,
            event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
            sequence_index=0,
            timestamp=TimestampMS(1643329860000),
            location=Location.BITSTAMP,
            asset=A_ETH,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            balance=Balance(
                amount=FVal('1.00000000'),
                usd_value=ZERO,
            ),
            notes='Spend 1.00000000 ETH(Ethereum) as the result of a trade on Bitstamp',
        ),
        HistoryEvent(
            identifier=3,
            event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
            sequence_index=1,
            timestamp=TimestampMS(1643329860000),
            location=Location.BITSTAMP,
            asset=A_EUR,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            balance=Balance(
                amount=FVal('2214.01'),
                usd_value=ZERO,
            ),
            notes='Receive 2214.01 EUR(Euro) as the result of a trade on Bitstamp',
        ),
        HistoryEvent(
            identifier=4,
            event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
            sequence_index=2,
            timestamp=TimestampMS(1643329860000),
            location=Location.BITSTAMP,
            asset=A_EUR,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.FEE,
            balance=Balance(
                amount=FVal('10.87005'),
                usd_value=ZERO,
            ),
            notes='Fee of 10.87005 EUR(Euro) as the result of a trade on Bitstamp',
        ),
        HistoryEvent(
            identifier=5,
            event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
            sequence_index=0,
            timestamp=TimestampMS(1643542800000),
            location=Location.BITSTAMP,
            asset=A_EUR,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            balance=Balance(
                amount=FVal('2211.01'),
                usd_value=ZERO,
            ),
            notes='Withdrawal of 2211.01 EUR(Euro) on Bitstamp',
        ),
    ]

    for actual, expected in zip(history_events, expected_history_events, strict=True):
        assert_is_equal_history_event(actual=actual, expected=expected)


def assert_bittrex_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from bittrex"""
    with rotki.data.db.conn.read_ctx() as cursor:
        trades = rotki.data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501
        events = DBHistoryEvents(rotki.data.db).get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )

    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0
    assert trades == [Trade(
        timestamp=Timestamp(1502659923),
        location=Location.BITTREX,
        base_asset=EvmToken('eip155:1/erc20:0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c'),
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal('857.78221905')),
        rate=Price(FVal('0.00018098')),
        fee=Fee(FVal('0.00038812')),
        fee_currency=A_BTC,
        link='Imported bittrex trade a3a27e1a-2b6c-3b82-c275-d61e375d35a2 from csv',
        notes='Sold 857.78221905 EDGELESS for 0.15486188 BTC',
    ), Trade(
        timestamp=Timestamp(1512302656),
        location=Location.BITTREX,
        base_asset=EvmToken('eip155:1/erc20:0xB9e7F8568e08d5659f5D29C4997173d84CdF2607'),
        quote_asset=A_BTC,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('731.28354007')),
        rate=Price(FVal('0.00034100')),
        fee=Fee(FVal('0.00062343')),
        fee_currency=A_BTC,
        link='Imported bittrex trade 28445361-31c6-1ab1-91a9-e196d50ad1a5 from csv',
        notes='Bought 731.28354007 SWT for 0.24999841 BTC',
    ), Trade(
        timestamp=Timestamp(1546269766),
        location=Location.BITTREX,
        base_asset=A_BTC,
        quote_asset=A_USDT,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.01')),
        rate=Price(FVal('10')),
        fee=Fee(ZERO),
        fee_currency=A_USDT,
        link='Imported bittrex trade aaaaaa from csv',
        notes=None,
    ), Trade(
        timestamp=Timestamp(1546269967),
        location=Location.BITTREX,
        base_asset=A_ETH,
        quote_asset=A_USDT,
        trade_type=TradeType.BUY,
        amount=AssetAmount(ONE),
        rate=Price(ONE),
        fee=Fee(ZERO),
        fee_currency=A_USDT,
        link='Imported bittrex trade 0 from csv',
        notes=None,
    )]
    assert events == [AssetMovement(
        identifier=5,
        event_identifier='28c432c0faec444c6c0b3c6da30171260273a05a2f684f67fa5e3184500ee83a',
        location=Location.BITTREX,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1451576024000),
        asset=A_ETH,
        balance=Balance(ONE),
        extra_data={'transaction_id': '0x'},
    ), AssetMovement(
        identifier=4,
        event_identifier='aac9b816a80599e72bd3e68adb9ce6165adddfcecd54ec682defbc57eb1cfe15',
        location=Location.BITTREX,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1483273298000),
        asset=A_BTC,
        balance=Balance(FVal('0.001')),
        extra_data={
            'address': '3m',
            'transaction_id': 'a5577',
        },
    ), AssetMovement(
        identifier=3,
        event_identifier='3fea1671268ba41b048e6a82cc8c2e06ec296a25992b25f887d349e73c140a7a',
        location=Location.BITTREX,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1495373867000),
        asset=A_BTC,
        balance=Balance(ONE),
        extra_data={
            'address': '3bamsmdamsd',
            'transaction_id': 'aaaa',
        },
    ), AssetMovement(
        identifier=2,
        event_identifier='538f61a7ca39a7dc1805121b14fcb5e0ba389f952bad6b3f4b52854d94dd4f70',
        location=Location.BITTREX,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1632868521000),
        asset=Asset('BCHA'),
        balance=Balance(FVal('0.00000001')),
        extra_data={'transaction_id': '1A313456CCEA5AF45B334881513CF472'},
    ), AssetMovement(
        identifier=1,
        event_identifier='082a31a46ebe3e9f89e49c5b24a52c8069c4f42a9a5a1ec1cb34ae21779cd91d',
        location=Location.BITTREX,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1678175503000),
        asset=A_ETH,
        balance=Balance(FVal('0.20084931')),
        extra_data={
            'address': '0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5',
            'transaction_id': '0xecac30357b613f6bcb5bc148fdd1d608bd94021e95a59233003948fde0c7c4d9',
        },
    ), AssetMovement(
        identifier=6,
        event_identifier='0cedd8004a902913273c81448450dba57001176234745e4b43e142760cebe561',
        location=Location.BITTREX,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1698881807000),
        asset=A_BTC,
        balance=Balance(ONE),
        extra_data={'transaction_id': 'Aaaa'},
    )]


def assert_kucoin_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from kucoin"""
    with rotki.data.db.conn.read_ctx() as cursor:
        trades = rotki.data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0
    expected_trades = [Trade(
        timestamp=Timestamp(1557570437),
        location=Location.KUCOIN,
        base_asset=A_KCS,
        quote_asset=A_BTC,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal(10.01)),
        rate=Price(FVal(0.00015225)),
        fee=Fee(FVal(0.00000152)),
        fee_currency=A_BTC,
    ), Trade(
        timestamp=Timestamp(1557570438),
        location=Location.KUCOIN,
        base_asset=A_KCS,
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal(10.02)),
        rate=Price(FVal(0.00015226)),
        fee=Fee(FVal(0.00000153)),
        fee_currency=A_BTC,
    ), Trade(
        timestamp=Timestamp(1651149360),
        location=Location.KUCOIN,
        base_asset=A_XTZ,
        quote_asset=A_USDT,
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal(36.4479)),
        rate=Price(FVal(0.1025)),
        fee=Fee(FVal(0.00373590975)),
        fee_currency=A_USDT,
    ), Trade(
        timestamp=Timestamp(1651160767),
        location=Location.KUCOIN,
        base_asset=A_XRP,
        quote_asset=A_USDT,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal(432.59183198)),
        rate=Price(FVal(0.64924)),
        fee=Fee(FVal(0.2808559209946952)),
        fee_currency=A_USDT,
    )]
    assert trades == expected_trades


def assert_blockpit_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from blockpit"""
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.read_ctx() as cursor:
        trades = rotki.data.db.get_trades(cursor=cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501
        history_events = dbevents.get_history_events(cursor=cursor, filter_query=HistoryEventFilterQuery.make(), has_premium=True)  # noqa: E501

    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == len(warnings) == 0

    assert trades == [
        Trade(
            timestamp=Timestamp(1673181840),
            location=Location.BINANCE,
            base_asset=A_ETH_MATIC,
            quote_asset=A_EUR,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('223.7')),
            rate=Price(FVal('0.7541')),
            fee=Fee(FVal('0.2237')),
            fee_currency=A_ETH_MATIC,
            notes='spot',
        ), Trade(
            timestamp=Timestamp(1673192880),
            location=Location.BINANCE,
            base_asset=A_EUR,
            quote_asset=A_ETH_MATIC,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('106.1899')),
            rate=Price(FVal('1.32310134956337655464408573696745170680074093675575549087060068801270177295581')),
            fee=Fee(FVal('0.1061899')),
            fee_currency=A_EUR,
            notes='spot',
        ), Trade(
            timestamp=Timestamp(1673195040),
            location=Location.BINANCE,
            base_asset=A_BNB,
            quote_asset=A_USDT,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.00092036')),
            rate=Price(FVal('263.048328914772480333782432961015254900256421400321613281759311573732017906037')),
            fee=Fee(FVal('0.0000184')),
            fee_currency=A_BNB,
            notes='',
        ),
    ]

    expected_history_events = [
        HistoryEvent(
            identifier=1,
            event_identifier='',
            sequence_index=0,
            timestamp=TimestampMS(1673035680000),
            location=Location.EXTERNAL,
            asset=A_ETH_MATIC,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            balance=Balance(amount=FVal('0.001537148341223424')),
            notes='Fee of 0.001537148341223424 MATIC in external',
        ), HistoryEvent(
            identifier=2,
            event_identifier='',
            sequence_index=1,
            timestamp=TimestampMS(1673035680000),
            location=Location.EXTERNAL,
            asset=Asset('META'),
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            balance=Balance(amount=FVal('10')),
            notes='Spend 10 META in external',
        ), HistoryEvent(
            identifier=3,
            event_identifier='',
            sequence_index=1,
            timestamp=TimestampMS(1673139600000),
            location=Location.BINANCE,
            asset=A_EUR,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            balance=Balance(amount=FVal('0.01061899')),
            notes='Receive 0.01061899 EUR in binance',
        ), AssetMovement(
            identifier=4,
            location=Location.BINANCE,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1673194740000),
            asset=A_BNB,
            balance=Balance(FVal('0.0095')),
        ), AssetMovement(
            identifier=6,
            location=Location.EXTERNAL,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1673194740000),
            asset=A_BNB,
            balance=Balance(FVal('0.0095')),
        ), AssetMovement(
            identifier=5,
            location=Location.BINANCE,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1673194740000),
            asset=A_BNB,
            balance=Balance(FVal('0.0005')),
            is_fee=True,
        ), HistoryEvent(
            identifier=7,
            event_identifier='',
            sequence_index=1,
            timestamp=TimestampMS(1673194800000),
            location=Location.EXTERNAL,
            asset=A_BNB,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            balance=Balance(amount=FVal('0.00024391')),
            notes='Fee of 0.00024391 BNB in external',
        ), AssetMovement(
            identifier=8,
            location=Location.EXTERNAL,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1673194920000),
            asset=A_BNB,
            balance=Balance(FVal('0.00915109')),
        ), AssetMovement(
            identifier=10,
            location=Location.BINANCE,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1673194920000),
            asset=A_BNB,
            balance=Balance(FVal('0.00915109')),
        ), AssetMovement(
            identifier=9,
            location=Location.EXTERNAL,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1673194920000),
            asset=A_BNB,
            balance=Balance(FVal('0.000105')),
            is_fee=True,
        ), AssetMovement(
            identifier=11,
            location=Location.EXTERNAL,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1673204160000),
            asset=A_EUR,
            balance=Balance(FVal('150')),
        ), AssetMovement(
            identifier=12,
            location=Location.BITPANDA,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1674759960000),
            asset=A_EUR,
            balance=Balance(FVal('1000')),
        ), AssetMovement(
            identifier=13,
            location=Location.BITPANDA,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1674760200000),
            asset=A_EUR,
            balance=Balance(FVal('1000')),
        ), HistoryEvent(
            identifier=14,
            event_identifier='',
            sequence_index=1,
            timestamp=TimestampMS(1675532220000),
            location=Location.KRAKEN,
            asset=A_EUR,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            balance=Balance(amount=FVal('0.0181')),
            notes='Spend 0.0181 EUR in kraken',
        ), HistoryEvent(
            identifier=15,
            event_identifier='',
            sequence_index=0,
            timestamp=TimestampMS(1675532700000),
            location=Location.KRAKEN,
            asset=A_EUR,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            balance=Balance(amount=FVal('0.0021')),
            notes='Fee of 0.0021 EUR in kraken',
        ), HistoryEvent(
            identifier=16,
            event_identifier='',
            sequence_index=1,
            timestamp=TimestampMS(1675532700000),
            location=Location.KRAKEN,
            asset=A_EUR,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            balance=Balance(amount=FVal('0.0025')),
            notes='Receive 0.0025 EUR in kraken',
        ), HistoryEvent(
            identifier=17,
            event_identifier='',
            sequence_index=1,
            timestamp=TimestampMS(1675913100000),
            location=Location.KRAKEN,
            asset=A_ETH_MATIC,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            balance=Balance(amount=FVal('0.1932938')),
            notes='Staking reward of 0.1932938 MATIC in kraken',
        ), HistoryEvent(
            identifier=18,
            event_identifier='',
            sequence_index=1,
            timestamp=TimestampMS(1675954800000),
            location=Location.KRAKEN,
            asset=A_EUR,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            balance=Balance(amount=FVal('0.06')),
            notes='Receive 0.06 EUR in kraken',
        ),
    ]

    for actual, expected in zip(history_events, expected_history_events, strict=True):
        assert_is_equal_history_event(actual=actual, expected=expected)
