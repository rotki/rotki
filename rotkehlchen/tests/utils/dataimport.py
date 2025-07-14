from typing import Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import (
    A_BAT,
    A_BCH,
    A_BNB,
    A_BSQ,
    A_BTC,
    A_BUSD,
    A_DAI,
    A_DOT,
    A_ETC,
    A_ETH,
    A_ETH2,
    A_ETH_MATIC,
    A_EUR,
    A_KNC,
    A_SAI,
    A_UNI,
    A_USD,
    A_USDC,
    A_USDT,
)
from rotkehlchen.data_import.importers.constants import COINTRACKING_EVENT_PREFIX
from rotkehlchen.db.filtering import (
    HistoryEventFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.fixtures.websockets import WebsocketReader
from rotkehlchen.tests.utils.constants import (
    A_ADA,
    A_AXS,
    A_CRO,
    A_DASH,
    A_DOGE,
    A_GBP,
    A_KCS,
    A_LTC,
    A_MCO,
    A_NANO,
    A_SOL,
    A_XMR,
    A_XRP,
    A_XTZ,
)
from rotkehlchen.types import Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_sec_to_ms


def get_cryptocom_note(desc: str):
    return f'{desc}\nSource: crypto.com (CSV import)'


def assert_cointracking_import_results(rotki: Rotkehlchen, websocket_connection: WebsocketReader):
    """A utility function to help assert on correctness of importing data from cointracking.info"""
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(cursor, filter_query=HistoryEventFilterQuery.make())  # noqa: E501

    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0
    websocket_connection.wait_until_messages_num(num=1, timeout=10)
    assert websocket_connection.pop_message() == {
        'type': 'progress_updates',
        'data': {
            'source_name': 'Cointracking',
            'subtype': 'csv_import_result',
            'total': 12,
            'processed': 7,
            'messages': [
                {'msg': 'Not importing ETH Transactions from Cointracking. Cointracking does not export enough data for them. Simply enter your ethereum accounts and all your transactions will be auto imported directly from the chain', 'rows': [1, 2], 'is_error': True},  # noqa: E501
                {'msg': 'Not importing BTC Transactions from Cointracking. Cointracking does not export enough data for them. Simply enter your BTC accounts and all your transactions will be auto imported directly from the chain', 'rows': [5], 'is_error': True},  # noqa: E501
                {'msg': 'Unknown asset ADS.', 'rows': [9], 'is_error': True},
                {'msg': 'Staking event for eip155:1/erc20:0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b(Axie Infinity Shard) at 1641386280000 already exists in the DB', 'rows': [12]},  # noqa: E501
            ],
        },
    }
    assert websocket_connection.messages_num() == 0

    for entry in [AssetMovement(
        identifier=5,
        event_identifier='7626b5d52eb9c67f2c9d83a0c1a97f38c8d2e0466d055fd23c48a30afe2aa972',
        location=Location.POLONIEX,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1565848624000),
        asset=A_XMR,
        amount=FVal('5.00000000'),
    ), AssetMovement(
        identifier=9,
        event_identifier='5dfd720e8b362491a663f4440477592a4e5c48bef0166bc42dd138c6e4ff0054',
        location=Location.COINBASE,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1566726155000),
        asset=A_ETH,
        amount=FVal('0.05770427'),
    ), AssetMovement(
        identifier=10,
        event_identifier='5dfd720e8b362491a663f4440477592a4e5c48bef0166bc42dd138c6e4ff0054',
        location=Location.COINBASE,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1566726155000),
        asset=A_ETH,
        amount=FVal('0.0001'),
        is_fee=True,
    ), SwapEvent(
        identifier=6,
        event_identifier='COT294e300a1564b1f2822b97c560e9751be451d828c4854051e1ab781542565e0f',
        timestamp=TimestampMS(1566687719000),
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_EUR,
        location=Location.COINBASE,
        amount=FVal('10.99000000'),
    ), SwapEvent(
        identifier=7,
        event_identifier='COT294e300a1564b1f2822b97c560e9751be451d828c4854051e1ab781542565e0f',
        timestamp=TimestampMS(1566687719000),
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        location=Location.COINBASE,
        amount=FVal('0.05772716'),
    ), SwapEvent(
        identifier=8,
        event_identifier='COT294e300a1564b1f2822b97c560e9751be451d828c4854051e1ab781542565e0f',
        timestamp=TimestampMS(1566687719000),
        event_subtype=HistoryEventSubType.FEE,
        asset=A_EUR,
        location=Location.COINBASE,
        amount=FVal('0.02'),
    ), SwapEvent(
        identifier=1,
        event_identifier='COT0f2ce7aff39dcc979efe6e60523d7e4afe2465af2277b7063716d23f6465aafe',
        timestamp=TimestampMS(1567418410000),
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USD,
        location=Location.EXTERNAL,
        amount=ZERO,
        notes='Just a small gift from someone. Data from -no exchange- not known by rotki.',
    ), SwapEvent(
        identifier=2,
        event_identifier='COT0f2ce7aff39dcc979efe6e60523d7e4afe2465af2277b7063716d23f6465aafe',
        timestamp=TimestampMS(1567418410000),
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        location=Location.EXTERNAL,
        amount=FVal('0.00100000'),
    ), SwapEvent(
        identifier=3,
        event_identifier='COTced23da81fd6e1a3276d0a1162686200e2a7aa41527fe8475b676c561a787775',
        timestamp=TimestampMS(1567504805000),
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USD,
        location=Location.EXTERNAL,
        amount=ZERO,
        notes='Sign up bonus. Data from -no exchange- not known by rotki.',
    ), SwapEvent(
        identifier=4,
        event_identifier='COTced23da81fd6e1a3276d0a1162686200e2a7aa41527fe8475b676c561a787775',
        timestamp=TimestampMS(1567504805000),
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        location=Location.EXTERNAL,
        amount=FVal('2'),
    )]:
        assert entry in events
        events.remove(entry)  # remove for simpler checking below.

    assert len(events) == 2, 'Duplicated event was not ignored'
    for event in events:
        assert event.event_identifier.startswith(COINTRACKING_EVENT_PREFIX)
        assert event.event_type == HistoryEventType.STAKING
        assert event.event_subtype == HistoryEventSubType.REWARD
        assert event.location == Location.BINANCE
        assert event.location_label is None
        if event.asset == A_AXS:
            assert event.timestamp == 1641386280000
            assert event.amount == ONE
            assert event.notes == 'Stake reward of 1.00000000 AXS in binance'
        else:
            assert event.asset == A_ETH
            assert event.timestamp == 1644319740000
            assert event.amount == FVal('2.12')
            assert event.notes == 'Stake reward of 2.12000000 ETH in binance'


def assert_cryptocom_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from crypto.com"""
    with rotki.data.db.conn.read_ctx() as cursor:
        events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(order_by_rules=[('timestamp', True)]),
                    )
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    expected_events = [SwapEvent(
        identifier=22,
        event_identifier='CCM_9ae9033697be4060e51746089335fd254528354a7ef522dbb58f455a83204ff6',
        timestamp=TimestampMS(1595833195000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.SPEND,
        amount=FVal('281.14'),
        asset=A_EUR,
        notes=get_cryptocom_note('Buy ETH'),
    ), SwapEvent(
        identifier=23,
        event_identifier='CCM_9ae9033697be4060e51746089335fd254528354a7ef522dbb58f455a83204ff6',
        timestamp=TimestampMS(1595833195000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.RECEIVE,
        amount=ONE,
        asset=A_ETH,
    ), SwapEvent(
        identifier=20,
        event_identifier='CCM_b3b66fbb4bcfcaf6d5ef6f136753f820bdf9150145f04e9c955f75381c38a7d0',
        timestamp=TimestampMS(1596014214000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.SPEND,
        amount=FVal('176.05'),
        asset=A_EUR,
        notes=get_cryptocom_note('Buy MCO'),
    ), SwapEvent(
        identifier=21,
        event_identifier='CCM_b3b66fbb4bcfcaf6d5ef6f136753f820bdf9150145f04e9c955f75381c38a7d0',
        timestamp=TimestampMS(1596014214000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.RECEIVE,
        amount=FVal('50.0'),
        asset=A_MCO,
    ), HistoryEvent(
        identifier=19,
        event_identifier='CCM_8742d989ca51cb724a6de9492cab6a647074635ea1fb5cad8c9db5596ec4cf46',
        sequence_index=0,
        timestamp=TimestampMS(1596014223000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('12.32402069'),
        asset=A_MCO,
        notes=get_cryptocom_note('Sign-up Bonus Unlocked'),
    ), SwapEvent(
        identifier=17,
        event_identifier='CCM_71c9914b9065de357bcba737b8d3ec6a6257647b5b04bbe63b4d56ba9864bdc7',
        timestamp=TimestampMS(1596209827000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.SPEND,
        amount=FVal('12.32'),
        asset=A_MCO,
        notes=get_cryptocom_note('MCO -> ETH'),
    ), SwapEvent(
        identifier=18,
        event_identifier='CCM_71c9914b9065de357bcba737b8d3ec6a6257647b5b04bbe63b4d56ba9864bdc7',
        timestamp=TimestampMS(1596209827000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.RECEIVE,
        amount=FVal('0.14445954600007045'),
        asset=A_ETH,
    ), HistoryEvent(
        identifier=16,
        event_identifier='CCM_983789e023405101a67cc9bb77faba8819e49e78de4ad4fda5281d2ecffd8052',
        sequence_index=0,
        timestamp=TimestampMS(1596429934000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.00061475'),
        asset=A_ETH,
        notes=get_cryptocom_note('Crypto Earn'),
    ), SwapEvent(
        identifier=3,
        event_identifier='CCM_4a542db62c4c1ec73fcc864352a2283c03313001bc8cd4e50ae3e352525acb3b',
        timestamp=TimestampMS(1596465565000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.SPEND,
        amount=FVal('50.00402069'),
        asset=A_MCO,
        notes=get_cryptocom_note('MCO/CRO Overall Swap'),
    ), SwapEvent(
        identifier=4,
        event_identifier='CCM_4a542db62c4c1ec73fcc864352a2283c03313001bc8cd4e50ae3e352525acb3b',
        timestamp=TimestampMS(1596465565000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.RECEIVE,
        amount=FVal('1382.306147552291'),
        asset=A_CRO,
    ), SwapEvent(
        identifier=1,
        event_identifier='CCM_a096438fd902d39af3e2461f7dedc11720df9030de90fec5ffbca2095a454d0e',
        timestamp=TimestampMS(1596730165000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.SPEND,
        amount=FVal('50'),
        asset=A_MCO,
        notes=get_cryptocom_note('MCO/CRO Overall Swap'),
    ), SwapEvent(
        identifier=2,
        event_identifier='CCM_a096438fd902d39af3e2461f7dedc11720df9030de90fec5ffbca2095a454d0e',
        timestamp=TimestampMS(1596730165000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.RECEIVE,
        amount=FVal('1301.64'),
        asset=A_CRO,
    ), AssetMovement(
        identifier=15,
        event_identifier='20b719f712a8951eeaa518e6976950c8410028dc974c2b6e72b62e6e8745d355',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1596992965000),
        asset=A_DAI,
        amount=FVal('115'),
    ), AssetMovement(
        identifier=14,
        event_identifier='2e2bba27c61cf9d71b8c60e1fce061a59b01d150b294badbb060c940d603594b',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1596993025000),
        asset=A_DAI,
        amount=FVal('115'),
    ), HistoryEvent(
        identifier=13,
        event_identifier='CCM_f24eb95216e362d79bb4a9cec0743fbb5bfd387c743e98ce51a97c6b3c430987',
        sequence_index=0,
        timestamp=TimestampMS(1599934176000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('138.256'),
        asset=A_CRO,
        notes=get_cryptocom_note('Card Rebate: Deliveries'),
    ), HistoryEvent(
        identifier=12,
        event_identifier='CCM_eadaa0af72f57a3a987faa9da84b149a14af47c94a5cf37f3dc0d3a6b795af95',
        sequence_index=0,
        timestamp=TimestampMS(1602515376000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('52.151'),
        asset=A_CRO,
        notes=get_cryptocom_note('Card Cashback'),
    ), HistoryEvent(
        identifier=11,
        event_identifier='CCM_10f2e57d3ff770148095e4b1f8407858dacb5b0f738679a5e30a61a9e65abd2c',
        sequence_index=0,
        timestamp=TimestampMS(1602526176000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('482.2566417'),
        asset=A_CRO,
        notes=get_cryptocom_note('Referral Bonus Reward'),
    ), SwapEvent(
        identifier=9,
        event_identifier='CCM_7cd82c9fe61590593f7f8349586b925ad6fb3b7189301a6c4206ed4f80d490cd',
        timestamp=TimestampMS(1606833565000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.SPEND,
        amount=FVal('0.00050680380674961'),
        asset=A_DAI,
        notes=get_cryptocom_note('Convert Dust'),
    ), SwapEvent(
        identifier=10,
        event_identifier='CCM_7cd82c9fe61590593f7f8349586b925ad6fb3b7189301a6c4206ed4f80d490cd',
        timestamp=TimestampMS(1606833565000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.RECEIVE,
        amount=FVal('0.007231228760408149'),
        asset=A_CRO,
    ), SwapEvent(
        identifier=5,
        event_identifier='CCM_21ea7227dc931c362a5530b676c030a0823fa33ab8bd87934116e9407acf6f48',
        timestamp=TimestampMS(1608024314000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.SPEND,
        amount=FVal('0.734823872932330827067669172932330827067669172932330827067669172932330827067669'),
        asset=Asset('eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984'),
        notes=get_cryptocom_note('Convert Dust'),
    ), SwapEvent(
        identifier=6,
        event_identifier='CCM_21ea7227dc931c362a5530b676c030a0823fa33ab8bd87934116e9407acf6f48',
        timestamp=TimestampMS(1608024314000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.RECEIVE,
        amount=FVal('105.947588930640516443834586466165413533834586466165413533834586466165413533835'),
        asset=A_CRO,
    ), SwapEvent(
        identifier=7,
        event_identifier='CCM_73df24989bdcf041e585bf506a903db58eb093a5ad470c8c42b2fdc581619377',
        timestamp=TimestampMS(1608024314000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.SPEND,
        amount=FVal('0.283989112781954887218045112781954887218045112781954887218045112781954887218045'),
        asset=A_DOT,
        notes=get_cryptocom_note('Convert Dust'),
    ), SwapEvent(
        identifier=8,
        event_identifier='CCM_73df24989bdcf041e585bf506a903db58eb093a5ad470c8c42b2fdc581619377',
        timestamp=TimestampMS(1608024314000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.RECEIVE,
        amount=FVal('87.0802100799785066661654135338345864661654135338345864661654135338345864661654'),
        asset=A_CRO,
    ), HistoryEvent(
        identifier=35,
        event_identifier='CCM_da60cedfc97c1df9319d7c2102e0269cbca97d4abac374d2d96a385ab02d072c',
        sequence_index=0,
        timestamp=TimestampMS(1614989135000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('7.76792828'),
        asset=A_CRO,
        notes=get_cryptocom_note('Card Rebate: Netflix'),
    ), HistoryEvent(
        identifier=34,
        event_identifier='CCM_0bcbe9abf2d75f68eecebc2c99611efb56e6f8795fbaa2e2c33db348864e6f4c',
        sequence_index=0,
        timestamp=TimestampMS(1615097829000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('7.76792828'),
        asset=A_CRO,
        notes=get_cryptocom_note('Card Rebate Reversal: Netflix'),
    ), HistoryEvent(
        identifier=32,
        event_identifier='CCM_a5051400dab1a0736302f3d80c969067f60def2e01f00fe5088d46016c351121',
        sequence_index=0,
        timestamp=TimestampMS(1616237351000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('10'),
        asset=A_CRO,
        notes=get_cryptocom_note('Pay Rewards'),
    ), HistoryEvent(
        identifier=33,
        event_identifier='CCM_f1b8ad8d5c58fbdc361faa8e2747ac6dd3d7ddc85025dc965f6324149ffe2b08',
        sequence_index=0,
        timestamp=TimestampMS(1616237351000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('100'),
        asset=A_CRO,
        notes=get_cryptocom_note('To +49XXXXXXXXXX'),
    ), HistoryEvent(
        identifier=31,
        event_identifier='CCM_29fe97c4aa05263dfccd478c2f90177f0006fea259bd71e22d3813b6602d9692',
        sequence_index=0,
        timestamp=TimestampMS(1616266740000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('100'),
        asset=A_CRO,
        notes=get_cryptocom_note('From +49XXXXXXXXXX'),
    ), HistoryEvent(
        identifier=30,
        event_identifier='CCM_5450de111ff9e242523f011a42f2b1ed9684110bf2cb1b3c893ea3c5957bc3db',
        sequence_index=0,
        timestamp=TimestampMS(1616669547000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('15.38'),
        asset=A_CRO,
        notes=get_cryptocom_note('Merchant XXX'),
    ), HistoryEvent(
        identifier=29,
        event_identifier='CCM_61d0b5ca125f051c7a3b04be7d94ee450d86d6777b0ef9cd334689883138bf5e',
        sequence_index=0,
        timestamp=TimestampMS(1616669548000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.3076'),
        asset=A_CRO,
        notes=get_cryptocom_note('Pay Rewards'),
    ), HistoryEvent(
        identifier=28,
        event_identifier='CCM_68a055044785832276c423a6acc538b7118ce2e04021859a687c9655c47c16d9',
        sequence_index=0,
        timestamp=TimestampMS(1616670041000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('15.31'),
        asset=A_CRO,
        notes=get_cryptocom_note('Refund from Merchant XXX'),
    ), SwapEvent(
        identifier=26,
        event_identifier='CCM_5e2b8b92f3bbad193cd19f7b021366b1cb2719f837924acebc8f65cf7e564aed',
        timestamp=TimestampMS(1620192867000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_DOGE,
        amount=FVal('750.0'),
        notes=get_cryptocom_note('DOGE -> EUR'),
    ), SwapEvent(
        identifier=27,
        event_identifier='CCM_5e2b8b92f3bbad193cd19f7b021366b1cb2719f837924acebc8f65cf7e564aed',
        timestamp=TimestampMS(1620192867000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_EUR,
        amount=FVal('406.22'),
    ), SwapEvent(
        identifier=24,
        event_identifier='CCM_26bccacb6107ce9bc436b98edf6262365973a3a398f962ae11f177ce4240066d',
        timestamp=TimestampMS(1626720960000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_EUR,
        amount=FVal('78.01'),
        notes=get_cryptocom_note('EUR -> BTC'),
    ), SwapEvent(
        identifier=25,
        event_identifier='CCM_26bccacb6107ce9bc436b98edf6262365973a3a398f962ae11f177ce4240066d',
        timestamp=TimestampMS(1626720960000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('0.003'),
    )]
    assert expected_events == events


def assert_cryptocom_special_events_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from crypto.com"""
    with rotki.data.db.conn.read_ctx() as cursor:
        events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(order_by_rules=[('timestamp', True)]),
                    )
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    expected_events = [AssetMovement(
        identifier=14,
        event_identifier='5d81565035faf4f9e3ec74685a4a5c275f6cd3b10a194e9a12e446042910dbcb',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1609534800000),
        asset=A_ETC,
        amount=ONE,
    ), AssetMovement(
        identifier=13,
        event_identifier='e973b9453f750c8286fdb718b8211abbd8b9027fea582a4e9365f3d0b5c371dc',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1609534860000),
        asset=A_ETC,
        amount=FVal('0.24'),
    ), AssetMovement(
        identifier=12,
        event_identifier='6e7b476f5880af1cea17c22fd8781fc7aa75a67fc7808200f18d20b181589c34',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1609538400000),
        asset=A_BTC,
        amount=FVal('0.01'),
    ), AssetMovement(
        identifier=11,
        event_identifier='edfb38684bb8ddfa0cd961a3a1fe0f90bda823f45a2095859b2d0e3c43401e4d',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1609542000000),
        asset=A_BTC,
        amount=FVal('0.01'),
    ), HistoryEvent(
        identifier=3,
        event_identifier='CCM_26556241ec9e68acba8cd0d6a6e7b5c010f344b7c763d4b45fa1b6d2abfaf2af',
        sequence_index=0,
        timestamp=TimestampMS(1609624800000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.00005'),
        asset=A_BTC,
        notes='Staking profit for BTC',
    ), AssetMovement(
        identifier=10,
        event_identifier='dd3b3db7df9d05e2a725bfb2edfd15f55a4d8cd473941735ab863a321ad38d92',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1609624800000),
        asset=A_BTC,
        amount=FVal('0.02005'),
    ), AssetMovement(
        identifier=9,
        event_identifier='4944f654c206336187e8df89b7ef8201fe7fdda65133a362166770de9283b6b6',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1609714800000),
        asset=A_BTC,
        amount=ONE,
    ), HistoryEvent(
        identifier=4,
        event_identifier='CCM_680977437f573e30752041fb8971be234a8fdb4d72f707d56eb5643d40908d82',
        sequence_index=0,
        timestamp=TimestampMS(1609797600000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.02005'),
        asset=A_BTC,
        notes='Staking profit for BTC',
    ), AssetMovement(
        identifier=8,
        event_identifier='99e05dba03cbcd7337e453049be2bdaa88814aec73cdcce26f40a0bc98d79f2e',
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1609797600000),
        asset=A_BTC,
        amount=FVal('1.02005'),
    ), SwapEvent(
        identifier=1,
        event_identifier='CCM_ebe2ce31051fc960270785590b349735d10d5cd7b7b972bd1c3017a7e3f83b1c',
        timestamp=TimestampMS(1609884000000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_MCO,
        amount=FVal('0.1'),
        notes=get_cryptocom_note('MCO Earnings/Rewards Swap'),
    ), SwapEvent(
        identifier=2,
        event_identifier='CCM_ebe2ce31051fc960270785590b349735d10d5cd7b7b972bd1c3017a7e3f83b1c',
        timestamp=TimestampMS(1609884000000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_CRO,
        amount=ONE,
    ), HistoryEvent(
        identifier=5,
        event_identifier='CCM_4edba1d54872a176b913a3a1afc476f4b7d9565d665b86d7fb0c8b1f56ca8cbf',
        sequence_index=0,
        timestamp=TimestampMS(1609884000000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=ONE,
        asset=A_CRO,
        notes=get_cryptocom_note('CRO Stake Rewards'),
    ), HistoryEvent(
        identifier=6,
        event_identifier='CCM_b0bb99d65ac111caec2d5d9b6a2b69bae1a13de50f89358a2a25dfc0992c51c4',
        sequence_index=0,
        timestamp=TimestampMS(1609884000000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.5'),
        asset=A_MCO,
        notes=get_cryptocom_note('MCO Stake Rewards'),
    ), HistoryEvent(
        identifier=7,
        event_identifier='CCM_afb12f3eac3e93695a1ac1b09b4708f678d7cf395a3f364390376510ec801059',
        sequence_index=0,
        timestamp=TimestampMS(1609884000000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=ONE,
        asset=A_CRO,
        notes=get_cryptocom_note('CRO Airdrop to Exchange'),
    ), HistoryEvent(
        identifier=15,
        event_identifier='CCM_64288070ac60947e3fcaaf150f76c5768122a08538c8efdec806d689d4c49d62',
        sequence_index=0,
        timestamp=TimestampMS(1635390997000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.00356292'),
        asset=A_AXS,
        notes=get_cryptocom_note('Supercharger Reward'),
    ), SwapEvent(
        identifier=16,
        event_identifier='CCM_060450c1d57f9e2dd52f2ab747b9cdb4c4bbd14b690d5ffa1eada014d2382f40',
        timestamp=TimestampMS(1635390998000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDC,
        amount=FVal('12.94'),
        notes=get_cryptocom_note('USDC -> EUR'),
    ), SwapEvent(
        identifier=17,
        event_identifier='CCM_060450c1d57f9e2dd52f2ab747b9cdb4c4bbd14b690d5ffa1eada014d2382f40',
        timestamp=TimestampMS(1635390998000),
        location=Location.CRYPTOCOM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_EUR,
        amount=FVal('11.3'),
    ), HistoryEvent(
        identifier=18,
        event_identifier='CCM_e66810bd6561fbe1d31aec4ad7942d854d63115808c2d1a7b2cd0df8bb110e49',
        sequence_index=0,
        timestamp=TimestampMS(1635477398000),
        location=Location.CRYPTOCOM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.5678'),
        asset=A_CRO,
        notes=get_cryptocom_note('Card Cashback Reversal'),
    )]
    assert expected_events == events


def assert_blockfi_transactions_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from blockfi"""
    with rotki.data.db.conn.read_ctx() as cursor:
        events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
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
        amount=FVal('1.11415058'),
    ), HistoryEvent(
        identifier=4,
        event_identifier='BLF_a8ef6e164b0130b0df9b4d1e877d1c0a601bbc66f244682b6d4f3fe3aadd66e9',
        sequence_index=0,
        timestamp=TimestampMS(1600293599000),
        location=Location.BLOCKFI,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.48385358'),
        asset=A_ETH,
        notes='Bonus Payment from BlockFi',
    ), AssetMovement(
        identifier=3,
        event_identifier='677c77a20f78f19f2dcc5333e260b16b15b511dbb4e42afab67d02ff907e161a',
        location=Location.BLOCKFI,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1605977971000),
        asset=A_ETH,
        amount=FVal('3'),
    ), HistoryEvent(
        identifier=2,
        event_identifier='BLF_e027e251abadf0f748d49341c94f0a9bdaff50a2e4f735bb410dd5b594a3b1ec',
        sequence_index=0,
        timestamp=TimestampMS(1606953599000),
        location=Location.BLOCKFI,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.00052383'),
        asset=A_BTC,
        notes='Referral Bonus from BlockFi',
    ), AssetMovement(
        identifier=6,
        event_identifier='7549573fba3392466dbd36b1f7a7e8bac06a276caa615008645d646f025f0b00',
        location=Location.BLOCKFI,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1611734258000),
        asset=A_USDC,
        amount=FVal('3597.48627700'),
    ), AssetMovement(
        identifier=7,
        event_identifier='731be1787656d4aa1e5bdc20f733f288728081884e2a607ccd3dafaca37c8e91',
        location=Location.BLOCKFI,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1611820658000),
        asset=A_BTC,
        amount=FVal('2.11415058'),
    ), HistoryEvent(
        identifier=1,
        event_identifier='BLF_d6e38784f89609668f70a37dd67f67e57fb926a74fc9c1cd1ea4e557317c0b9d',
        sequence_index=0,
        timestamp=TimestampMS(1612051199000),
        location=Location.BLOCKFI,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.56469042'),
        asset=A_ETH,
        notes='Interest Payment from BlockFi',
    )]
    assert expected_events == events


def assert_blockfi_trades_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing trades data from blockfi"""
    with rotki.data.db.conn.read_ctx() as cursor:
        events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
                    )
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    expected_events = [SwapEvent(
        timestamp=TimestampMS(1612051199000),
        identifier=1,
        event_identifier='f5fb9bcadcea3f3829282a9f12286f71aecf9dff30cef61e85a4aab8ad1e326a',
        location=Location.BLOCKFI,
        event_subtype=HistoryEventSubType.SPEND,
        notes='One Time',
        amount=FVal('42.23878904'),
        asset=symbol_to_asset_or_token('LTC'),
    ), SwapEvent(
        timestamp=TimestampMS(1612051199000),
        identifier=2,
        event_identifier='f5fb9bcadcea3f3829282a9f12286f71aecf9dff30cef61e85a4aab8ad1e326a',
        location=Location.BLOCKFI,
        event_subtype=HistoryEventSubType.RECEIVE,
        amount=FVal('6404.6'),
        asset=A_USDC,
    )]
    assert events == expected_events


def assert_nexo_results(rotki: Rotkehlchen, websocket_connection: WebsocketReader):
    """A utility function to help assert on correctness of importing data from nexo"""
    with rotki.data.db.conn.read_ctx() as cursor:
        events_db = DBHistoryEvents(rotki.data.db)
        events = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
                    )
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0
    websocket_connection.wait_until_messages_num(num=1, timeout=10)
    assert websocket_connection.pop_message() == {
        'type': 'progress_updates',
        'data': {
            'subtype': 'csv_import_result',
            'source_name': 'Nexo',
            'total': 38,
            'processed': 36,
            'messages': [{'msg': 'Ignoring rejected entry.', 'rows': [2, 8]}],
        },
    }
    assert websocket_connection.messages_num() == 0

    expected_events = [AssetMovement(
        identifier=14,
        event_identifier='30270894f93665bb104b59a693ccd2f1c3e19dbe559b8c86c5f1efbe47e2cf5b',
        location=Location.NEXO,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1621940400000),
        asset=A_GBP,
        amount=FVal('5000'),
    ), HistoryEvent(
        identifier=1,
        event_identifier='NEXO_df0cd4ec1cfef6d56ecdc864d71e41f6629074b6453b78cadd67cef214ad3997',
        sequence_index=0,
        timestamp=TimestampMS(1643698860000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('127.5520683'),
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
        amount=FVal('0.10000001'),
        asset=Asset('eip155:1/erc20:0xB62132e35a6c13ee1EE0f84dC5d40bad8d815206'),
        location_label='NXTabcdefghij',
        notes='Cashback from Nexo',
    ), AssetMovement(
        identifier=3,
        event_identifier='46383f05d585bd112c7d8a3a03258569ab1cabe7a3834a13f516964a533b5f6c',
        location=Location.NEXO,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1647963925000),
        asset=A_ETH_MATIC,
        amount=FVal('5.00000000'),
    ), AssetMovement(
        identifier=2,
        event_identifier='a5f62498f9cc39ac8d99455fe9db0abdf26c9ce5d92b30f0bc9ecce9937c9189',
        location=Location.NEXO,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1647964353000),
        asset=A_ETH_MATIC,
        amount=FVal('3050.00000000'),
    ), HistoryEvent(
        identifier=5,
        event_identifier='NEXO_f5c25b7009473f1ed6fb48c0ed42c3febf0703883740ba2a1862953d71b1e8db',
        sequence_index=0,
        timestamp=TimestampMS(1649462400000),
        location=Location.NEXO,
        event_type=HistoryEventType.LOSS,
        event_subtype=HistoryEventSubType.LIQUIDATE,
        amount=FVal('710.82000000'),
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
        amount=FVal('0.00999999'),
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
        amount=FVal('595.92'),
    ), SwapEvent(
        identifier=8,
        timestamp=TimestampMS(1650192060000),
        event_identifier='NEXO_1b9bf08b0a12bfb57beca6b558d3e38fd4133a6dfaea596df989753e7eef4af4',
        event_subtype=HistoryEventSubType.SPEND,
        location=Location.NEXO,
        asset=A_GBP,
        amount=FVal('54'),
        notes='Exchange from Nexo',
    ), AssetMovement(
        identifier=10,
        event_identifier='fd3b3af4503ed66ab961365e9ae94cd4d301a1db2e944889c0ba00c43e3bcf9b',
        location=Location.NEXO,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1650192060000),
        asset=A_GBP,
        amount=FVal('54'),
    ), SwapEvent(
        identifier=9,
        timestamp=TimestampMS(1650192060000),
        event_identifier='NEXO_1b9bf08b0a12bfb57beca6b558d3e38fd4133a6dfaea596df989753e7eef4af4',
        event_subtype=HistoryEventSubType.RECEIVE,
        location=Location.NEXO,
        asset=A_BTC,
        amount=FVal('0.0017316'),
    ), AssetMovement(
        identifier=13,
        event_identifier='22d48c31b52037480e31c626d6d38c34fc2ee501819cfea78b2e512e2900f140',
        location=Location.NEXO,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1650192180000),
        asset=A_BTC,
        amount=FVal('0.0017316'),
    ), HistoryEvent(
        identifier=11,
        event_identifier='NEXO_d31d7ee1cab8bcda90e3021abd70b578209414ac7d36d078072d8cbd052fa287',
        sequence_index=0,
        timestamp=TimestampMS(1650438000000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('1.09246793'),
        asset=A_USDC,
        location_label='NXTGWynyMmm5K',
        notes='Interest from Nexo',
    ), HistoryEvent(
        identifier=19,
        event_identifier='NEXO_139c6bd4cb1c69ea8bc856c20bebca9b0180fcdd5acd66f2b7d33e8888094c3b',
        sequence_index=0,
        timestamp=TimestampMS(1656626402000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.01000000'),
        asset=A_USD,
        location_label='NXTslZ5J6wqqmKalgCjpDEQd',
        notes='Interest from Nexo',
    ), HistoryEvent(
        identifier=24,
        event_identifier='NEXO_6ca2336b08501cf491bc3a62e8c289f2de0d303fa605ab0eb8c5ff8ed5386dbe',
        sequence_index=0,
        timestamp=TimestampMS(1656702227000),
        location=Location.NEXO,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.PAYBACK_DEBT,
        amount=FVal('0.16962900'),
        asset=A_USDC,
        location_label='NXT53Q6ioNttPkX91sNAWbbnQ',
        notes='Manual Sell Order from Nexo',
    ), HistoryEvent(
        identifier=12,
        event_identifier='NEXO_e8137e27e69bc848578349c0dece234fd4af50487ecfdf42518de3246f900b23',
        sequence_index=0,
        timestamp=TimestampMS(1657782007000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.00178799'),
        asset=A_ETH,
        location_label='NXT1isX0Refua',
        notes='Interest from Nexo',
    ), AssetMovement(
        identifier=18,
        event_identifier='c64cd362e062eba2958f2656ebb63ebb22107650e88c7a04c401687d81220056',
        location=Location.NEXO,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1707003036000),
        asset=A_EUR,
        amount=FVal('47.99000000'),
    ), HistoryEvent(
        identifier=21,
        event_identifier='NEXO_d368377375acf56c2133d1e9d023b6dc17bcffc747f07b108f523228e6ad4663',
        sequence_index=0,
        timestamp=TimestampMS(1719187529000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.00007929'),
        asset=A_BTC,
        location_label='NXT6tSqWCGWiEeOgZrG2ltm27',
        notes='Referral Bonus from Nexo',
    ), HistoryEvent(
        identifier=20,
        event_identifier='NEXO_b2d0ff5b09383635d27453682ac8c5f3a4f6a8b3c3e98edc0e0440c74cda72fe',
        sequence_index=0,
        timestamp=TimestampMS(1724371533000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.00001953'),
        asset=A_BTC,
        location_label='NXT5Xa0rjcaf90s3h3b5j0uZI',
        notes='Referral Bonus from Nexo',
    ), HistoryEvent(
        identifier=17,
        event_identifier='NEXO_05be9cf28e8f09148ffb0d1f7280419118aa19803dd13c6bdcdf71e7bc8e3e9d',
        sequence_index=0,
        timestamp=TimestampMS(1734971539000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('1.28539200'),
        asset=A_USDC,
        location_label='NXT44OjpCjxegVqhfHj3ZmeAa',
        notes='Exchange Cashback from Nexo',
    ), SwapEvent(
        identifier=22,
        timestamp=TimestampMS(1734971539000),
        event_identifier='NEXO_dc19313d088deb51008fe1f8b8255606f33e65e7308412525cbd8187320a2bfe',
        event_subtype=HistoryEventSubType.SPEND,
        location=Location.NEXO,
        asset=Asset('eip155:1/erc20:0x05Ac103f68e05da35E78f6165b9082432FE64B58'),
        amount=FVal('500.00000000'),
        notes='Exchange from Nexo',
    ), SwapEvent(
        identifier=23,
        timestamp=TimestampMS(1734971539000),
        event_identifier='NEXO_dc19313d088deb51008fe1f8b8255606f33e65e7308412525cbd8187320a2bfe',
        event_subtype=HistoryEventSubType.RECEIVE,
        location=Location.NEXO,
        asset=A_USDC,
        amount=FVal('514.15679500'),
    ), HistoryEvent(
        identifier=15,
        event_identifier='NEXO_4cf8625c0bd44e83aab18c3f380f0de765ce52174806f71a232fd16492adcba8',
        sequence_index=0,
        timestamp=TimestampMS(1735365600000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('5.37250072'),
        asset=Asset('eip155:1/erc20:0xB62132e35a6c13ee1EE0f84dC5d40bad8d815206'),
        location_label='NXT5Gz0cNLEHLbYtc3xDkZ8eR',
        notes='Fixed Term Interest from Nexo',
    ), HistoryEvent(
        identifier=16,
        event_identifier='NEXO_a1ef61959184d70ed118df337ddae6c1c63538989cd3438ab663b7ca9dc29538',
        sequence_index=0,
        timestamp=TimestampMS(1735365600000),
        location=Location.NEXO,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        amount=FVal('0.12179800'),
        asset=A_USDC,
        location_label='NXT4OTjYHHRW6xseMpUarHKKT',
        notes='Interest from Nexo',
    )]
    assert events == expected_events


def assert_shapeshift_trades_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing trades data from shapeshift"""
    with rotki.data.db.conn.read_ctx() as cursor:
        events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
                    )
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
    expected_events = [
        SwapEvent(
            identifier=4,
            event_identifier='SHF37751fe6752dc1ee2a37e366c104a17072b8f0d9c3cdf657f1ed4d02621f9e90',
            timestamp=TimestampMS(1561551116000),
            asset=A_SAI,
            amount=FVal('103.0142883'),
            event_subtype=HistoryEventSubType.SPEND,
            notes=notes1,
            location=Location.SHAPESHIFT,
        ), SwapEvent(
            identifier=5,
            event_identifier='SHF37751fe6752dc1ee2a37e366c104a17072b8f0d9c3cdf657f1ed4d02621f9e90',
            timestamp=TimestampMS(1561551116000),
            asset=A_DASH,
            amount=FVal('0.59420343'),
            event_subtype=HistoryEventSubType.RECEIVE,
            location=Location.SHAPESHIFT,
        ), SwapEvent(
            identifier=6,
            event_identifier='SHF37751fe6752dc1ee2a37e366c104a17072b8f0d9c3cdf657f1ed4d02621f9e90',
            timestamp=TimestampMS(1561551116000),
            asset=A_DASH,
            amount=FVal('0.002'),
            event_subtype=HistoryEventSubType.FEE,
            location=Location.SHAPESHIFT,
        ), SwapEvent(
            identifier=1,
            event_identifier='SHF67054c5ad174eccd57b727dea0b77ac78d4bac301f85c378978037f04d6a80ac',
            timestamp=TimestampMS(1630856301000),
            asset=A_USDC,
            amount=FVal('101.82'),
            event_subtype=HistoryEventSubType.SPEND,
            notes=notes2,
            location=Location.SHAPESHIFT,
        ), SwapEvent(
            identifier=2,
            event_identifier='SHF67054c5ad174eccd57b727dea0b77ac78d4bac301f85c378978037f04d6a80ac',
            timestamp=TimestampMS(1630856301000),
            asset=A_ETH,
            amount=FVal('0.06198721'),
            event_subtype=HistoryEventSubType.RECEIVE,
            location=Location.SHAPESHIFT,
        ), SwapEvent(
            identifier=3,
            event_identifier='SHF67054c5ad174eccd57b727dea0b77ac78d4bac301f85c378978037f04d6a80ac',
            timestamp=TimestampMS(1630856301000),
            asset=A_ETH,
            amount=FVal('0.0042'),
            event_subtype=HistoryEventSubType.FEE,
            location=Location.SHAPESHIFT,
        )]
    assert events == expected_events


def assert_uphold_transactions_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing trades data from uphold"""
    with rotki.data.db.conn.read_ctx() as cursor:
        history_db = DBHistoryEvents(rotki.data.db)
        events = history_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
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
    expected_events = [HistoryEvent(
        identifier=12,
        event_identifier='UPH_55d4d58869d96ad9adf18929bf89caaae87e657482ea20ae4c8c66b8ab34f4e2',
        sequence_index=0,
        timestamp=TimestampMS(1576780809000),
        location=Location.UPHOLD,
        asset=A_BAT,
        amount=FVal('5.15'),
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        notes=notes5,
    ), SwapEvent(
        identifier=10,
        event_identifier='UPH_ca138ecb5850b20ada7cbc02916f98c452496bf678f0230f68520f817821658b',
        location=Location.UPHOLD,
        timestamp=TimestampMS(1581426837000),
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_GBP,
        notes=notes1,
        amount=FVal('25'),
    ), SwapEvent(
        identifier=11,
        event_identifier='UPH_ca138ecb5850b20ada7cbc02916f98c452496bf678f0230f68520f817821658b',
        location=Location.UPHOLD,
        timestamp=TimestampMS(1581426837000),
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('0.00331961'),
    ), SwapEvent(
        identifier=8,
        event_identifier='UPH_bfec53b1f8968eed54806c887dbf93da46d17bb31ee8da90b2ca028fbeb6fd64',
        location=Location.UPHOLD,
        timestamp=TimestampMS(1585484504000),
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BTC,
        notes=notes2,
        amount=FVal('0.00421'),
    ), SwapEvent(
        identifier=9,
        event_identifier='UPH_bfec53b1f8968eed54806c887dbf93da46d17bb31ee8da90b2ca028fbeb6fd64',
        location=Location.UPHOLD,
        timestamp=TimestampMS(1585484504000),
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_GBP,
        amount=FVal('24.65'),
    ), AssetMovement(
        identifier=7,
        event_identifier='c85215d66a23ae39cbf232dd931dafa40006acb065d5314382f623b7bb8ce707',
        location=Location.UPHOLD,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1589376604000),
        asset=symbol_to_asset_or_token('GBP'),
        amount=FVal('24.65'),
    ), SwapEvent(
        identifier=4,
        event_identifier='UPH_643f948173b4829e6a933e5102fe8cf9d35fde3da830da488da7d05b2c4e8972',
        location=Location.UPHOLD,
        timestamp=TimestampMS(1589940026000),
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_NANO,
        amount=FVal('133.362002'),
        notes=notes3,
    ), SwapEvent(
        identifier=5,
        event_identifier='UPH_643f948173b4829e6a933e5102fe8cf9d35fde3da830da488da7d05b2c4e8972',
        location=Location.UPHOLD,
        timestamp=TimestampMS(1589940026000),
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_LTC,
        amount=FVal('1.26155562'),
    ), SwapEvent(
        identifier=6,
        event_identifier='UPH_643f948173b4829e6a933e5102fe8cf9d35fde3da830da488da7d05b2c4e8972',
        location=Location.UPHOLD,
        timestamp=TimestampMS(1589940026000),
        event_subtype=HistoryEventSubType.FEE,
        asset=A_NANO,
        amount=FVal('0.111123'),
    ), SwapEvent(
        identifier=1,
        location=Location.UPHOLD,
        event_identifier='UPH_9c817cf738e47cde664fb26290f18c3f3a773c84f6341c2132a3a95bdf4e1e36',
        timestamp=TimestampMS(1590516388000),
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BTC,
        amount=FVal('0.00714216'),
        notes=notes4,
    ), SwapEvent(
        identifier=2,
        event_identifier='UPH_9c817cf738e47cde664fb26290f18c3f3a773c84f6341c2132a3a95bdf4e1e36',
        location=Location.UPHOLD,
        timestamp=TimestampMS(1590516388000),
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_XRP,
        amount=FVal('314.642101'),
    ), SwapEvent(
        identifier=3,
        event_identifier='UPH_9c817cf738e47cde664fb26290f18c3f3a773c84f6341c2132a3a95bdf4e1e36',
        location=Location.UPHOLD,
        timestamp=TimestampMS(1590516388000),
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal('0.0000021'),
    )]
    assert events == expected_events


def assert_custom_cointracking(rotki: Rotkehlchen):
    """
    A utility function to help assert on correctness of importing data from cointracking.info
    when using custom formats for dates
    """
    with rotki.data.db.conn.read_ctx() as cursor:
        events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
                    )
    assert events == [AssetMovement(
        identifier=1,
        event_identifier='55220a50d1f1af04042410f6c0223518cd14e1a5ad250dfb65be6404c7b6a01e',
        location=Location.POLONIEX,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1504646040000),
        asset=A_XMR,
        amount=FVal('5.00000000'),
    ), AssetMovement(
        identifier=2,
        event_identifier='2bb82301ad9d4b4251e404c11026f53f9f1c5190a943a26aa654e4fa0969ccbd',
        location=Location.COINBASE,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1504646040000),
        asset=A_ETH,
        amount=FVal('0.05770427'),
    ), AssetMovement(
        identifier=3,
        event_identifier='2bb82301ad9d4b4251e404c11026f53f9f1c5190a943a26aa654e4fa0969ccbd',
        location=Location.COINBASE,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1504646040000),
        asset=A_ETH,
        amount=FVal('0.0001'),
        is_fee=True,
    )]


def assert_bisq_trades_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing trades data from bisq"""
    with rotki.data.db.conn.read_ctx() as cursor:
        swap_events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
                    )
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0

    expected_swap_events = [SwapEvent(
        identifier=25,
        timestamp=TimestampMS(1517195493000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.SPEND,
        asset=symbol_to_asset_or_token('SC'),
        amount=FVal('9811.32075471'),
        notes='ID: exxXE',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='exxXE',
        ),
    ), SwapEvent(
        identifier=26,
        timestamp=TimestampMS(1517195493000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('0.0363999999999741'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='exxXE',
        ),
    ), SwapEvent(
        identifier=27,
        timestamp=TimestampMS(1517195493000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal('0.0002'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='exxXE',
        ),
    ), SwapEvent(
        identifier=22,
        timestamp=TimestampMS(1545136553000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_EUR,
        amount=FVal('848.720000'),
        notes='ID: IxxWl',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='IxxWl',
        ),
    ), SwapEvent(
        identifier=23,
        timestamp=TimestampMS(1545136553000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('0.25'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='IxxWl',
        ),
    ), SwapEvent(
        identifier=24,
        timestamp=TimestampMS(1545136553000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal('0.0005'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='IxxWl',
        ),
    ), SwapEvent(
        identifier=19,
        timestamp=TimestampMS(1545416958000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_EUR,
        amount=FVal('624.73390000'),
        notes='ID: VxxABMN',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='VxxABMN',
        ),
    ), SwapEvent(
        identifier=20,
        timestamp=TimestampMS(1545416958000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('0.1850'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='VxxABMN',
        ),
    ), SwapEvent(
        identifier=21,
        timestamp=TimestampMS(1545416958000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal('0.000370'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='VxxABMN',
        ),
    ), SwapEvent(
        identifier=16,
        timestamp=TimestampMS(1560284504000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_DASH,
        amount=FVal('19.45685539'),
        notes='ID: LxxAob',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='LxxAob',
        ),
    ), SwapEvent(
        identifier=17,
        timestamp=TimestampMS(1560284504000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('0.2999999999074547'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='LxxAob',
        ),
    ), SwapEvent(
        identifier=18,
        timestamp=TimestampMS(1560284504000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal('0.0009'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='LxxAob',
        ),
    ), SwapEvent(
        identifier=13,
        timestamp=TimestampMS(1577082782000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_EUR,
        amount=FVal('67.856724'),
        notes='ID: GxxL',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='GxxL',
        ),
    ), SwapEvent(
        identifier=14,
        timestamp=TimestampMS(1577082782000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('0.01'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='GxxL',
        ),
    ), SwapEvent(
        identifier=15,
        timestamp=TimestampMS(1577082782000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal('0.00109140'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='GxxL',
        ),
    ), SwapEvent(
        identifier=10,
        timestamp=TimestampMS(1577898084000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BTC,
        amount=FVal('0.0099000855'),
        notes='ID: 552',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='552',
        ),
    ), SwapEvent(
        identifier=11,
        timestamp=TimestampMS(1577898084000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BSQ,
        amount=FVal('116.65'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='552',
        ),
    ), SwapEvent(
        identifier=12,
        timestamp=TimestampMS(1577898084000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal('0.00005940'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='552',
        ),
    ), SwapEvent(
        identifier=7,
        timestamp=TimestampMS(1607706820000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BTC,
        amount=FVal('0.05'),
        notes='ID: xxYARFU',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='xxYARFU',
        ),
    ), SwapEvent(
        identifier=8,
        timestamp=TimestampMS(1607706820000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_EUR,
        amount=FVal('794.166415'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='xxYARFU',
        ),
    ), SwapEvent(
        identifier=9,
        timestamp=TimestampMS(1607706820000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BSQ,
        amount=FVal('2.01'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='xxYARFU',
        ),
    ), SwapEvent(
        identifier=4,
        timestamp=TimestampMS(1615371360000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BTC,
        amount=FVal('0.01'),
        notes='ID: xxcz',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='xxcz',
        ),
    ), SwapEvent(
        identifier=5,
        timestamp=TimestampMS(1615371360000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_EUR,
        amount=FVal('505.000000'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='xxcz',
        ),
    ), SwapEvent(
        identifier=6,
        timestamp=TimestampMS(1615371360000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BSQ,
        amount=FVal('0.40'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='xxcz',
        ),
    ), SwapEvent(
        identifier=1,
        timestamp=TimestampMS(1615372820000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BTC,
        amount=FVal('0.01'),
        notes='ID: xxhee',
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='xxhee',
        ),
    ), SwapEvent(
        identifier=2,
        timestamp=TimestampMS(1615372820000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_EUR,
        amount=FVal('490.000000'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='xxhee',
        ),
    ), SwapEvent(
        identifier=3,
        timestamp=TimestampMS(1615372820000),
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BSQ,
        amount=FVal('0.29'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BISQ,
            unique_id='xxhee',
        ),
    )]
    assert swap_events == expected_swap_events


def assert_bitmex_import_wallet_history(rotki: Rotkehlchen):
    expected_events = [
        AssetMovement(
            identifier=3,
            event_identifier='016035ad3c5a14f733b11d39f19f82cefa1000d0db62d5377548d2e6456a16fc',
            location=Location.BITMEX,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1574825791000),
            asset=A_BTC,
            amount=FVal('0.05000000'),
        ),
        AssetMovement(
            identifier=1,
            event_identifier='c7ee1cfaa00878d7079cdc2ebf0f15477e9116fc1284f0ebf298db26405e5897',
            location=Location.BITMEX,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1577252845000),
            asset=A_BTC,
            amount=FVal('0.05746216'),
            extra_data={'address': '3Qsy5NGSnGA1vd1cmcNgeMjLrKPsKNhfCe'},
        ),
        AssetMovement(
            identifier=2,
            event_identifier='c7ee1cfaa00878d7079cdc2ebf0f15477e9116fc1284f0ebf298db26405e5897',
            location=Location.BITMEX,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1577252845000),
            asset=A_BTC,
            amount=FVal('0.00100000'),
            is_fee=True,
        ),
    ]
    expected_margin_positions = [
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1576738800),
            profit_loss=FVal(0.00000373),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1576825200),
            profit_loss=FVal(0.00000016),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1576911600),
            profit_loss=FVal(-0.00000123),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1576998000),
            profit_loss=FVal(-0.00000075),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1577084400),
            profit_loss=FVal(-0.00000203),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1577170800),
            profit_loss=FVal(-0.00000201),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
        MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=Timestamp(1577257200),
            profit_loss=FVal(0.00085517),
            pl_currency=A_BTC,
            fee=ZERO,
            fee_currency=A_BTC,
            link='Imported from BitMEX CSV file. Transact Type: RealisedPNL',
            notes='PnL from trade on XBTUSD',
        ),
    ]
    with rotki.data.db.conn.read_ctx() as cursor:
        margin_positions = rotki.data.db.get_margin_positions(cursor)
        warnings = rotki.msg_aggregator.consume_warnings()
        errors = rotki.msg_aggregator.consume_errors()
        events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
                    )
    assert events == expected_events
    assert margin_positions == expected_margin_positions
    assert len(warnings) == 0
    assert len(errors) == 0


def assert_binance_import_results(rotki: Rotkehlchen, websocket_connection: WebsocketReader):
    expected_events = [
        AssetMovement(
            identifier=1,
            event_identifier='3f9a750608754c8361951f87f0e21ea71bf98221d52a69c809c27307c65fff13',
            timestamp=TimestampMS(1603922583000),
            location=Location.BINANCE,
            event_type=HistoryEventType.DEPOSIT,
            asset=A_EUR,
            amount=FVal('245.25'),
        ), SwapEvent(
            event_identifier='BNC_6db2cc45205ff1e96053530d82df689e35741f872e65762ded05857f3d3dd544',
            timestamp=TimestampMS(1603922583000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_EUR,
            amount=FVal('245.25'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=2,
        ), SwapEvent(
            event_identifier='BNC_6db2cc45205ff1e96053530d82df689e35741f872e65762ded05857f3d3dd544',
            timestamp=TimestampMS(1603922583000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_BNB,
            amount=FVal('0.576474665'),
            identifier=3,
        ), HistoryEvent(
            identifier=4,
            event_identifier='BNC_1a75acacbf626a04e8be50cb3f79ec8abd1f573e2cb9d9650df576626e437ddf',
            sequence_index=0,
            timestamp=TimestampMS(1603926662000),
            location=Location.BINANCE,
            asset=A_BNB,
            amount=FVal('0.577257355'),
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            notes='Imported from binance CSV file. Binance operation: POS savings purchase',
        ), SwapEvent(
            event_identifier='BNC_554d6b0208711df3f371412ea762204152f64d772621851b5b36869338ce94eb',
            timestamp=TimestampMS(1604042198000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_EUR,
            amount=FVal('150'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=5,
        ), SwapEvent(
            event_identifier='BNC_554d6b0208711df3f371412ea762204152f64d772621851b5b36869338ce94eb',
            timestamp=TimestampMS(1604042198000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_AXS,
            amount=FVal('1.19592356'),
            identifier=6,
        ), SwapEvent(
            event_identifier='BNC_1b3fb45a96e895e98f597b07efe5e052d727ed399bc01abc1128b3e33bb6357c',
            timestamp=TimestampMS(1604067680000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_EUR,
            amount=FVal('134.4719075'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=7,
        ), SwapEvent(
            event_identifier='BNC_1b3fb45a96e895e98f597b07efe5e052d727ed399bc01abc1128b3e33bb6357c',
            timestamp=TimestampMS(1604067680000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.03605'),
            identifier=8,
        ), SwapEvent(
            event_identifier='BNC_1b3fb45a96e895e98f597b07efe5e052d727ed399bc01abc1128b3e33bb6357c',
            timestamp=TimestampMS(1604067680000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00003605'),
            identifier=9,
        ), SwapEvent(
            event_identifier='BNC_f5c3ce5d1d48d96a64a05a2faa152d9770a5d01a15a727f9d577bac001396f73',
            timestamp=TimestampMS(1604070545000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.036'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=10,
        ), SwapEvent(
            event_identifier='BNC_f5c3ce5d1d48d96a64a05a2faa152d9770a5d01a15a727f9d577bac001396f73',
            timestamp=TimestampMS(1604070545000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH2,
            amount=FVal('0.036'),
            identifier=11,
        ), HistoryEvent(
            identifier=12,
            event_identifier='BNC_14e2f3956bf5c9506a460c8bf35ff199139555118a0ef40ea6f732248fcac5a0',
            sequence_index=0,
            timestamp=TimestampMS(1604223373000),
            location=Location.BINANCE,
            asset=A_ETH2,
            amount=FVal('0.000004615'),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            notes='Imported from binance CSV file. Binance operation: ETH 2.0 Staking Rewards',
        ), HistoryEvent(
            identifier=13,
            event_identifier='BNC_d5dc6cca7342e668707b496d951a317156146eee348073cbb55ba852fb8f7a72',
            sequence_index=0,
            timestamp=TimestampMS(1604274610000),
            location=Location.BINANCE,
            asset=Asset('eip155:56/erc20:0x23CE9e926048273eF83be0A3A8Ba9Cb6D45cd978'),
            amount=FVal('0.115147055'),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            notes='Imported from binance CSV file. Binance operation: Launchpool Interest',
        ), SwapEvent(
            event_identifier='BNC_58f951f0038eb9fb60dbe594635004334bb9f4f7e93c29a1cb4cdd575e66c614',
            timestamp=TimestampMS(1604437979000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_EUR,
            amount=FVal('333.209174'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=14,
        ), SwapEvent(
            event_identifier='BNC_58f951f0038eb9fb60dbe594635004334bb9f4f7e93c29a1cb4cdd575e66c614',
            timestamp=TimestampMS(1604437979000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.08345'),
            identifier=15,
        ), SwapEvent(
            event_identifier='BNC_58f951f0038eb9fb60dbe594635004334bb9f4f7e93c29a1cb4cdd575e66c614',
            timestamp=TimestampMS(1604437979000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00008345'),
            identifier=16,
        ), SwapEvent(
            event_identifier='BNC_c10ef72d8b01b389777629b422e6811409635fab6113a7fc420bf23e40c34105',
            timestamp=TimestampMS(1604437979000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_EUR,
            amount=FVal('59.089888'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=17,
        ), SwapEvent(
            event_identifier='BNC_c10ef72d8b01b389777629b422e6811409635fab6113a7fc420bf23e40c34105',
            timestamp=TimestampMS(1604437979000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.0148'),
            identifier=18,
        ), SwapEvent(
            event_identifier='BNC_c10ef72d8b01b389777629b422e6811409635fab6113a7fc420bf23e40c34105',
            timestamp=TimestampMS(1604437979000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BNB,
            amount=FVal('0.00009009'),
            identifier=19,
        ), HistoryEvent(
            identifier=20,
            event_identifier='BNC_2d10e01a5946dac7ff1904203810cb6a6bafd1ab92e387fc6850384b17d1eae9',
            sequence_index=0,
            timestamp=TimestampMS(1604450188000),
            location=Location.BINANCE,
            asset=A_AXS,
            amount=FVal('1.18837124'),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            notes='Imported from binance CSV file. Binance operation: POS savings redemption',
        ), HistoryEvent(
            identifier=21,
            event_identifier='BNC_9a2793560cc940557e51500ca876e0a0d11324666eae644f3145cf7038cbc9bd',
            sequence_index=0,
            timestamp=TimestampMS(1604456888000),
            location=Location.BINANCE,
            asset=A_BNB,
            amount=FVal('0.000092675'),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            notes='Imported from binance CSV file. Binance operation: POS savings interest',
        ), SwapEvent(
            event_identifier='BNC_e0dca22b6b647a5070d8d64c1a407c700acfe7cea9d7f1f9a119e830a5cc2960',
            timestamp=TimestampMS(1605169314000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('IOTA'),
            amount=FVal('67.5'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=22,
        ), SwapEvent(
            event_identifier='BNC_e0dca22b6b647a5070d8d64c1a407c700acfe7cea9d7f1f9a119e830a5cc2960',
            timestamp=TimestampMS(1605169314000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_BTC,
            amount=FVal('0.001366875'),
            identifier=23,
        ), SwapEvent(
            event_identifier='BNC_e0dca22b6b647a5070d8d64c1a407c700acfe7cea9d7f1f9a119e830a5cc2960',
            timestamp=TimestampMS(1605169314000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BNB,
            amount=FVal('0.0001057'),
            identifier=24,
        ), SwapEvent(
            event_identifier='BNC_577fa5ca63cae7f3f33c594f1c3e3c9493415243344a4d2753acdae78d26fd81',
            timestamp=TimestampMS(1605903740000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_SOL,
            amount=FVal('0.002055565'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=25,
        ), SwapEvent(
            event_identifier='BNC_577fa5ca63cae7f3f33c594f1c3e3c9493415243344a4d2753acdae78d26fd81',
            timestamp=TimestampMS(1605903740000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_BNB,
            amount=FVal('0.00072724'),
            identifier=26,
        ), SwapEvent(
            event_identifier='BNC_63058e64402a3caf220ea07c36ae4e77a34f56c41dd7b5ed8cc0968f3910e34d',
            timestamp=TimestampMS(1605903740000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_SOL,
            amount=FVal('0.00014477'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=27,
        ), SwapEvent(
            event_identifier='BNC_63058e64402a3caf220ea07c36ae4e77a34f56c41dd7b5ed8cc0968f3910e34d',
            timestamp=TimestampMS(1605903740000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_BNB,
            amount=FVal('0.000237955'),
            identifier=28,
        ), SwapEvent(
            event_identifier='BNC_9069b19a08dd93da473ecff8ee2a6c2f5728243ac35032911523bcd40d233403',
            timestamp=TimestampMS(1605910681000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:56/erc20:0x23CE9e926048273eF83be0A3A8Ba9Cb6D45cd978'),
            amount=FVal('336.5'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=29,
        ), SwapEvent(
            event_identifier='BNC_9069b19a08dd93da473ecff8ee2a6c2f5728243ac35032911523bcd40d233403',
            timestamp=TimestampMS(1605910681000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('1157.56'),
            identifier=30,
        ), SwapEvent(
            event_identifier='BNC_9069b19a08dd93da473ecff8ee2a6c2f5728243ac35032911523bcd40d233403',
            timestamp=TimestampMS(1605910681000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDT,
            amount=FVal('1.15756'),
            identifier=31,
        ), SwapEvent(
            event_identifier='BNC_673e5f941b998c95f873c53906cbfe8798ee06be7e10cc3f3c0e1619c5176dec',
            timestamp=TimestampMS(1605911401000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal('1146.3354'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=32,
        ), SwapEvent(
            event_identifier='BNC_673e5f941b998c95f873c53906cbfe8798ee06be7e10cc3f3c0e1619c5176dec',
            timestamp=TimestampMS(1605911401000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('IOTA'),
            amount=FVal('882'),
            identifier=33,
        ), SwapEvent(
            event_identifier='BNC_673e5f941b998c95f873c53906cbfe8798ee06be7e10cc3f3c0e1619c5176dec',
            timestamp=TimestampMS(1605911401000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('IOTA'),
            amount=FVal('0.882'),
            identifier=34,
        ), SwapEvent(
            event_identifier='BNC_76ad65290e2bf47337a45a8ed8b3b23944971ff5c2e7188cb6f162da1786340c',
            timestamp=TimestampMS(1606837907000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('1.01065076'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=36,
        ), SwapEvent(
            event_identifier='BNC_76ad65290e2bf47337a45a8ed8b3b23944971ff5c2e7188cb6f162da1786340c',
            timestamp=TimestampMS(1606837907000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_BTC,
            amount=FVal('0.10680859385'),
            identifier=37,
        ), SwapEvent(
            event_identifier='BNC_76ad65290e2bf47337a45a8ed8b3b23944971ff5c2e7188cb6f162da1786340c',
            timestamp=TimestampMS(1606837907000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BNB,
            amount=FVal('0.0462623227152'),
            identifier=38,
        ), SwapEvent(
            event_identifier='BNC_19ac71eca13ed6e09931b716b1a8b9dc2b896077da48f71f42695937782d461a',
            timestamp=TimestampMS(1606837907000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.9049715199999999'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=39,
        ), SwapEvent(
            event_identifier='BNC_19ac71eca13ed6e09931b716b1a8b9dc2b896077da48f71f42695937782d461a',
            timestamp=TimestampMS(1606837907000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_BTC,
            amount=FVal('0.09564009919439999'),
            identifier=40,
        ), SwapEvent(
            event_identifier='BNC_19ac71eca13ed6e09931b716b1a8b9dc2b896077da48f71f42695937782d461a',
            timestamp=TimestampMS(1606837907000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BNB,
            amount=FVal('0.041427214681599996'),
            identifier=41,
        ), AssetMovement(
            identifier=35,
            event_identifier='da21894e86cb5aea08db8cf0fad34836b96c380ebc401e46922864533f306e46',
            location=Location.BINANCE,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1606853204000),
            asset=A_KNC,
            amount=FVal('0.16'),
        ), SwapEvent(
            event_identifier='BNC_fda3b07228a815935934c201f1861ed2c61f07622ce73a731a258434ca053f3e',
            timestamp=TimestampMS(1606948201000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal('1146.3354'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=42,
        ), SwapEvent(
            event_identifier='BNC_fda3b07228a815935934c201f1861ed2c61f07622ce73a731a258434ca053f3e',
            timestamp=TimestampMS(1606948201000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('IOTA'),
            amount=FVal('882'),
            identifier=43,
        ), HistoryEvent(
            identifier=44,
            event_identifier='BNC_ac8a1a8ccd32547766f312428a59ac8ea667f72c33c0c4695b3fc82a7896645f',
            sequence_index=0,
            timestamp=TimestampMS(1640910825000),
            location=Location.BINANCE,
            asset=A_USDT,
            amount=FVal('500.00000000'),
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            location_label='CSV import',
            notes='Transfer Between Main and Funding Wallet',
        ), HistoryEvent(
            identifier=45,
            event_identifier='BNC_29a2d52a91b9bbb7213d4710ad190d587c4febc197373291289d85ae275ec7a5',
            sequence_index=0,
            timestamp=TimestampMS(1640912422000),
            location=Location.BINANCE,
            asset=A_USDT,
            amount=FVal('100.00000000'),
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            location_label='CSV import',
            notes='Transfer Between Spot Account and UM Futures Account',
        ), HistoryEvent(
            identifier=46,
            event_identifier='BNC_33a197c8698d3de4db57bb5d8a43e48addb28538587f73cd624792036b69a870',
            sequence_index=0,
            timestamp=TimestampMS(1640912706000),
            location=Location.BINANCE,
            asset=A_USDT,
            amount=FVal('60.00000000'),
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            location_label='CSV import',
            notes='Transfer Between Spot Account and CM Futures Account',
        ), HistoryEvent(
            identifier=47,
            event_identifier='BNC_a5e6e8af4008679025ce68ac818ee4ae3f8b9f461d70eeb3d30f20f3c9a8d92f',
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(1640913498)),
            location=Location.BINANCE,
            asset=A_USDT,
            amount=FVal('40.00000000'),
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            location_label='CSV import',
            notes='Transfer Between Spot Account and UM Futures Account',
        ), HistoryEvent(
            identifier=48,
            event_identifier='BNC_5d651c8364e0b853f3f4c4b3812b2d370607fc008bedb30291137fabae0d93ef',
            sequence_index=0,
            timestamp=TimestampMS(1673587740000),
            location=Location.BINANCE,
            asset=Asset('eip155:1/erc20:0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'),
            amount=FVal('0.00001605'),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            location_label='CSV import',
            notes='Reward from Simple Earn Locked Rewards',
        ), HistoryEvent(
            identifier=49,
            event_identifier='BNC_e2433b7eddb388759cbab8d440dda8447a0d1d6733889000f2bd3145454cae59',
            sequence_index=0,
            timestamp=TimestampMS(1673589660000),
            location=Location.BINANCE,
            asset=A_BUSD,
            amount=FVal('0.00003634'),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            location_label='CSV import',
            notes='Reward from Simple Earn Flexible Interest',
        ), HistoryEvent(
            identifier=51,
            event_identifier='BNC_f5b62b836a4f520729099765bd12f49bce839ae53aef5c53f6e2b12cd4a5d2e2',
            sequence_index=0,
            timestamp=TimestampMS(1673590320000),
            location=Location.BINANCE,
            asset=A_BUSD,
            amount=FVal('0.00003634'),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            location_label='CSV import',
            notes='Reward from Simple Earn Flexible Interest',
        ), HistoryEvent(
            identifier=50,
            event_identifier='BNC_8ee2c667b24dc991ccaf81050b48cf33d9ccdd45471e1517efcb64c0bbfcb318',
            sequence_index=0,
            timestamp=TimestampMS(1673593020000),
            location=Location.BINANCE,
            asset=A_BUSD,
            amount=FVal('0.00003634'),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            location_label='CSV import',
            notes='Deposit in Simple Earn Flexible Subscription',
        ), HistoryEvent(
            identifier=52,
            event_identifier='BNC_6f2a1947e66d9d38c1d07ade18706be20fbbddf48cdbfbd345e6976a85333e35',
            sequence_index=0,
            timestamp=TimestampMS(1673593560000),
            location=Location.BINANCE,
            asset=A_BUSD,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            amount=FVal('0.00003634'),
            location_label='CSV import',
            notes='Deposit in Simple Earn Flexible Subscription',
        ), SwapEvent(
            event_identifier='BNC_f6f83c6674ac5c27e6bc83f33bf701f219b18cbfaf8d67b0407c232a2a27507b',
            timestamp=TimestampMS(1685994420000),
            location=Location.BINANCE,
            asset=A_BUSD,
            event_subtype=HistoryEventSubType.SPEND,
            amount=FVal('125.626918'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=53,
        ), SwapEvent(
            event_identifier='BNC_f6f83c6674ac5c27e6bc83f33bf701f219b18cbfaf8d67b0407c232a2a27507b',
            timestamp=TimestampMS(1685994420000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'),
            amount=FVal('140.1195285'),
            identifier=54,
        ), HistoryEvent(
            identifier=55,
            event_identifier='BNC_93ffcc0bba0a90bddb72dd100479e6c784e5dd5ea68e2bf4c5a0a9c3432a24b9',
            sequence_index=0,
            timestamp=TimestampMS(1686389700000),
            location=Location.BINANCE,
            asset=Asset('SUI'),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            amount=FVal('0.0080696'),
            location_label='CSV import',
            notes='Reward from BNB Vault Rewards',
        ), HistoryEvent(
            identifier=56,
            event_identifier='BNC_2d4a94bee000e141e2f5b63195fc805d28757e6f2b7cc8f7af9488e9c3ea3f1b',
            sequence_index=0,
            timestamp=TimestampMS(1686538886000),
            location=Location.BINANCE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_BNB,
            amount=FVal('0.95901726'),
            location_label='CSV import',
            notes='Unstake eip155:1/erc20:0xB8c77482e45F1F44dE1745F52C74426C631bDD52(Binance Coin) in Staking Redemption',  # noqa: E501
        ), HistoryEvent(
            identifier=57,
            event_identifier='BNC_60fcc311b4f38019dde25c9c55b28058faf57f602ecf3d775004515ff934a152',
            sequence_index=0,
            timestamp=TimestampMS(1686539468000),
            location=Location.BINANCE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_BNB,
            amount=FVal('0.96455172'),
            location_label='CSV import',
            notes='Deposit in Staking Purchase',
        ), HistoryEvent(
            identifier=58,
            event_identifier='BNC_4259a864eeb6e39a046bbd4030a62d63bcaafebb36c4a5f55b00d1e78a90569e',
            sequence_index=0,
            timestamp=TimestampMS(1686543089000),
            location=Location.BINANCE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'),
            amount=FVal('602.5193197'),
            location_label='CSV import',
            notes='Deposit in Simple Earn Locked Subscription',
        ), AssetMovement(
            identifier=59,
            event_identifier='504972a5e897bc3324adc5635514fcf1a2e8c8adae380ebdc60cec9d52227176',
            location=Location.BINANCE,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1686571601000),
            asset=A_BUSD,
            amount=FVal('479.6780028'),
        ), AssetMovement(
            identifier=60,
            event_identifier='805fdb95ec899ebd25a799fa8aa9a8735ee3cd423d804b874a3319f42ddb98e5',
            location=Location.BINANCE,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1686571762000),
            asset=A_EUR,
            amount=FVal('2435.34'),
        ), HistoryEvent(
            identifier=61,
            event_identifier='BNC_4b706868b7c8906507b66b1b35017dcaa9eec3c27e63563603e8aa7475243f81',
            sequence_index=0,
            timestamp=TimestampMS(1686824951000),
            location=Location.BINANCE,
            event_type=HistoryEventType.RECEIVE,
            asset=A_BUSD,
            event_subtype=HistoryEventSubType.REWARD,
            amount=FVal('0.35628294'),
            location_label='CSV import',
            notes='Reward from Cash Voucher Distribution',
        ), HistoryEvent(
            identifier=62,
            event_identifier='BNC_6b282ed5ab3de42a924f008ed20e35ebcbbe1618b60c0a120c7c76278240f725',
            sequence_index=0,
            timestamp=TimestampMS(1686825000000),
            location=Location.BINANCE,
            event_type=HistoryEventType.RECEIVE,
            asset=A_BUSD,
            event_subtype=HistoryEventSubType.REWARD,
            amount=FVal('4.87068'),
            location_label='CSV import',
            notes='Reward from Mission Reward Distribution',
        ), SwapEvent(
            event_identifier='BNC_4e6c552e6288429511c687228f46a07646c80265694511a0230954644bcb0bdd',
            timestamp=TimestampMS(1690262284000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            amount=FVal('2641.00000000'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=63,
        ), SwapEvent(
            event_identifier='BNC_4e6c552e6288429511c687228f46a07646c80265694511a0230954644bcb0bdd',
            timestamp=TimestampMS(1690262284000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('2641.26410000'),
            identifier=64,
        ), SwapEvent(
            event_identifier='BNC_143f8cfd2308c8909131f969b4e748c5094f6c988f3df4285655f68f4d65e843',
            timestamp=TimestampMS(1690570138000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_SOL,
            amount=FVal('1.07000000'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=65,
        ), SwapEvent(
            event_identifier='BNC_143f8cfd2308c8909131f969b4e748c5094f6c988f3df4285655f68f4d65e843',
            timestamp=TimestampMS(1690570138000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('26.82490000'),
            identifier=66,
        ), SwapEvent(
            event_identifier='BNC_143f8cfd2308c8909131f969b4e748c5094f6c988f3df4285655f68f4d65e843',
            timestamp=TimestampMS(1690570138000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BNB,
            amount=FVal('0.00008316'),
            identifier=67,
        ), HistoryEvent(
            identifier=68,
            event_identifier='BNC_d6a38298147f2c10d888205893ac2baeccad83d1dbed1477a3e2f4ddd943761f',
            sequence_index=0,
            timestamp=TimestampMS(1694505602000),
            location=Location.BINANCE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDT,
            amount=FVal('0.07779065'),
            location_label='CSV import',
            notes='0.07779065 USDT fee paid on binance USD-MFutures',
        ), HistoryEvent(
            identifier=69,
            event_identifier='BNC_982287169e9675e5c799ca2f9d2b7f345eb6be73dbe6cfdb60a161949fdf8c01',
            sequence_index=0,
            timestamp=TimestampMS(1694623421000),
            location=Location.BINANCE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_USDT,
            amount=FVal('0.05576000'),
            location_label='CSV import',
            notes='0.05576000 USDT realized loss on binance USD-MFutures',
        ), HistoryEvent(
            identifier=70,
            event_identifier='BNC_cd4e771cb6692df31c11743419800b4ccd73c3ac2b4b3f948f731cf663c7db0a',
            sequence_index=0,
            timestamp=TimestampMS(1694623421000),
            location=Location.BINANCE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_USDT,
            amount=FVal('1.29642000'),
            location_label='CSV import',
            notes='1.29642000 USDT realized profit on binance USD-MFutures',
        ), SwapEvent(
            event_identifier='BNC_c6e5a5527ed3ad65bc2bceffdb2a432f5335e04768a0b86256c653a40d12229a',
            timestamp=TimestampMS(1695981386000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal('28.46106000'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=71,
        ), SwapEvent(
            event_identifier='BNC_c6e5a5527ed3ad65bc2bceffdb2a432f5335e04768a0b86256c653a40d12229a',
            timestamp=TimestampMS(1695981386000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.01700000'),
            identifier=72,
        ), SwapEvent(
            event_identifier='BNC_c6e5a5527ed3ad65bc2bceffdb2a432f5335e04768a0b86256c653a40d12229a',
            timestamp=TimestampMS(1695981386000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BNB,
            amount=FVal('0.00009883'),
            identifier=73,
        ), SwapEvent(
            event_identifier='BNC_1ad6c259421cd17f17d0659ce0fb2de063fdaef2e3343baf65e03fde346cda52',
            timestamp=TimestampMS(1704118880000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_EUR,
            amount=FVal('134.4719075'),
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
            identifier=74,
        ), SwapEvent(
            event_identifier='BNC_1ad6c259421cd17f17d0659ce0fb2de063fdaef2e3343baf65e03fde346cda52',
            timestamp=TimestampMS(1704118880000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.03605'),
            identifier=75,
        ), SwapEvent(
            event_identifier='BNC_1ad6c259421cd17f17d0659ce0fb2de063fdaef2e3343baf65e03fde346cda52',
            timestamp=TimestampMS(1704118880000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00003605'),
            identifier=76,
        ), SwapEvent(
            event_identifier='BNC_2ede3e3de73269b127690a1758dee9b896a1ae3b43b05caedd3e34860022aec8',
            timestamp=TimestampMS(1715864275000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_BTC,
            amount=FVal('0.14999997'),
            identifier=77,
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ), SwapEvent(
            event_identifier='BNC_2ede3e3de73269b127690a1758dee9b896a1ae3b43b05caedd3e34860022aec8',
            timestamp=TimestampMS(1715864275000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x71Ab77b7dbB4fa7e017BC15090b2163221420282'),
            amount=FVal('2011.67800000'),
            identifier=78,
        ), SwapEvent(
            event_identifier='BNC_2ede3e3de73269b127690a1758dee9b896a1ae3b43b05caedd3e34860022aec8',
            timestamp=TimestampMS(1715864275000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('eip155:1/erc20:0x71Ab77b7dbB4fa7e017BC15090b2163221420282'),
            amount=FVal('2.01167800'),
            identifier=79,
        ), SwapEvent(
            event_identifier='BNC_de70f198dc94c110e5921f12684714cb2f5375e3396373d26b9fa699def5394a',
            timestamp=TimestampMS(1726136106000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.54321'),
            identifier=80,
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ), SwapEvent(
            event_identifier='BNC_de70f198dc94c110e5921f12684714cb2f5375e3396373d26b9fa699def5394a',
            timestamp=TimestampMS(1726136106000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('1234'),
            identifier=81,
        ), SwapEvent(
            event_identifier='BNC_accc00aaa9c5c1e1b1562b25c18756e98b32a6b6605fea24bfeda63edb70219b',
            timestamp=TimestampMS(1726136111000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.54321'),
            identifier=82,
            notes='Imported from binance CSV file. Binance operation: Buy / Sell',
        ), SwapEvent(
            event_identifier='BNC_accc00aaa9c5c1e1b1562b25c18756e98b32a6b6605fea24bfeda63edb70219b',
            timestamp=TimestampMS(1726136111000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('1234'),
            identifier=83,
        ),
    ]

    with rotki.data.db.conn.read_ctx() as cursor:
        events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(order_by_rules=[('timestamp', True)]),
                    )

    assert expected_events == events
    websocket_connection.wait_until_messages_num(num=1, timeout=10)
    assert websocket_connection.pop_message() == {
        'type': 'progress_updates',
        'data': {
            'subtype': 'csv_import_result',
            'source_name': 'Binance',
            'total': 184,
            'processed': 178,
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
    websocket_connection.wait_until_messages_num(num=1, timeout=10)
    assert websocket_connection.pop_message() == {
        'type': 'progress_updates',
        'data': {
            'subtype': 'csv_import_result',
            'source_name': 'Rotki generic trades',
            'total': 5,
            'processed': 5,
            'messages': [],
        },
    }
    assert websocket_connection.messages_num() == 0

    with rotki.data.db.conn.read_ctx() as cursor:
        events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
                    )

    trade1_id, trade2_id, trade3_id, trade4_id, trade5_id = '39324bc8b48e567efdfdd8b04709f9681285fae0845f0ae09a9744ac37e71184', '468eefc8785bcb4755fdeab34c259bb90839df4689707918738d81d3d8f0e222', '5c5f3e50672360a5765ce521cac1b01d6acc2e8257350fa84f161493dd07880b', '504e930f842eb62b5e4bbbc319497e4d9d3afa0adf37869b21b2f305b9a2f490', 'd68e17cae1ce5548c320227218b7c984e263be4b4b1ff72a3d1dbdde7b8f5312'  # noqa: E501
    expected_events = [SwapEvent(
        identifier=1,
        timestamp=TimestampMS(1659085200000),
        event_identifier=trade1_id,
        location=Location.BINANCE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDC,
        amount=FVal('1875.64'),
        notes='Trade USDC for ETH',
    ), SwapEvent(
        identifier=2,
        timestamp=TimestampMS(1659085200000),
        event_identifier=trade1_id,
        location=Location.BINANCE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=ONE,
    ), SwapEvent(
        identifier=3,
        timestamp=TimestampMS(1659171600000),
        event_identifier=trade2_id,
        location=Location.KRAKEN,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_LTC,
        amount=FVal('392.8870'),
        notes='Trade LTC for BTC',
    ), SwapEvent(
        identifier=4,
        timestamp=TimestampMS(1659171600000),
        event_identifier=trade2_id,
        location=Location.KRAKEN,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('4.3241'),
    ), SwapEvent(
        identifier=5,
        timestamp=TimestampMS(1659344400000),
        event_identifier=trade3_id,
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_UNI,
        amount=FVal('20.0000'),
        notes='Trade UNI for DAI',
    ), SwapEvent(
        identifier=6,
        timestamp=TimestampMS(1659344400000),
        event_identifier=trade3_id,
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_DAI,
        amount=FVal('880.0000'),
    ), SwapEvent(
        identifier=7,
        timestamp=TimestampMS(1659344400000),
        event_identifier=trade3_id,
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USD,
        amount=FVal('0.1040'),
    ), SwapEvent(
        identifier=8,
        timestamp=TimestampMS(1659344900000),
        event_identifier=trade4_id,
        location=Location.EXTERNAL,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ADA,
        amount=FVal('4576.6400'),
        notes='Trade ADA for BCH',
    ), SwapEvent(
        identifier=9,
        timestamp=TimestampMS(1659344900000),
        event_identifier=trade4_id,
        location=Location.EXTERNAL,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BCH,
        amount=FVal('16.3444'),
    ), SwapEvent(
        identifier=10,
        timestamp=TimestampMS(1659344900000),
        event_identifier=trade4_id,
        location=Location.EXTERNAL,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USD,
        amount=FVal('5.1345'),
    ), SwapEvent(
        identifier=11,
        timestamp=TimestampMS(1659345600000),
        event_identifier=trade5_id,
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal('4576.6400'),
        notes='Trade USDT for DAI',
    ), SwapEvent(
        identifier=12,
        timestamp=TimestampMS(1659345600000),
        event_identifier=trade5_id,
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_DAI,
        amount=ZERO,
    ), SwapEvent(
        identifier=13,
        timestamp=TimestampMS(1659345600000),
        event_identifier=trade5_id,
        location=Location.BISQ,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USD,
        amount=FVal('5.1345'),
    )]
    assert events == expected_events


def assert_rotki_generic_events_import_results(rotki: Rotkehlchen, websocket_connection: WebsocketReader):  # noqa: E501
    expected_history_events = [
        HistoryEvent(
            identifier=1,
            event_identifier=(dummy_event_id := '1xyz'),  # placeholder as this field is randomly generated on import  # noqa: E501
            sequence_index=0,
            timestamp=TimestampMS(1658912400000),
            location=Location.KUCOIN,
            asset=A_EUR,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            amount=FVal('1000.00'),
            notes='Deposit EUR to Kucoin',
        ), HistoryEvent(
            identifier=2,
            event_identifier=dummy_event_id,
            sequence_index=1,
            timestamp=TimestampMS(1658998800000),
            location=Location.BINANCE,
            asset=A_USDT,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            amount=FVal('99.00'),
            notes='',
        ), HistoryEvent(
            identifier=3,
            event_identifier=dummy_event_id,
            sequence_index=2,
            timestamp=TimestampMS(1658998800000),
            location=Location.BINANCE,
            asset=A_USDT,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            amount=FVal('1.00'),
            notes='',
        ), HistoryEvent(
            identifier=4,
            event_identifier=dummy_event_id,
            sequence_index=2,
            timestamp=TimestampMS(1659085200000),
            location=Location.KRAKEN,
            asset=A_BNB,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            amount=FVal('1.01'),
            notes='',
        ), HistoryEvent(
            identifier=5,
            event_identifier=dummy_event_id,
            sequence_index=3,
            timestamp=TimestampMS(1659340800000),
            location=Location.EXTERNAL,
            asset=A_ETH,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            amount=FVal('0.0513'),
            notes='ETH Staking reward from QRS',
        ), HistoryEvent(
            identifier=6,
            event_identifier=dummy_event_id,
            sequence_index=4,
            timestamp=TimestampMS(1659430800000),
            location=Location.COINBASE,
            asset=A_BTC,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            amount=FVal('0.0910'),
            notes='',
        ), HistoryEvent(
            identifier=7,
            event_identifier=dummy_event_id,
            sequence_index=5,
            timestamp=TimestampMS(1659513600000),
            location=Location.EXTERNAL,
            asset=A_DAI,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            amount=FVal('1000.00'),
            notes='',
        ),
    ]
    with rotki.data.db.conn.read_ctx() as cursor:
        history_db = DBHistoryEvents(rotki.data.db)
        history_events = history_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
                    )
        warnings = rotki.msg_aggregator.consume_warnings()

    assert len(history_events) == 7
    assert len(expected_history_events) == 7
    assert len(warnings) == 0
    websocket_connection.wait_until_messages_num(num=1, timeout=10)
    assert websocket_connection.pop_message() == {
        'type': 'progress_updates',
        'data': {
            'subtype': 'csv_import_result',
            'source_name': 'Rotki generic events',
            'total': 7,
            'processed': 6,
            'messages': [
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
    dummy_event_id = '1xyz'  # just a placeholder as comparison is done without this field  # noqa: E501
    expected_history_events: list[HistoryEvent | SwapEvent]
    if csv_file_name == 'bitcoin_tax_trades.csv':
        expected_history_events = [
            SwapEvent(
                identifier=1,
                event_identifier=dummy_event_id,
                timestamp=TimestampMS(1528060575000),
                location=Location.COINBASEPRO,
                asset=A_EUR,
                event_subtype=HistoryEventSubType.SPEND,
                amount=FVal('1008'),
            ),
            SwapEvent(
                identifier=2,
                event_identifier=dummy_event_id,
                timestamp=TimestampMS(1528060575000),
                location=Location.COINBASEPRO,
                asset=A_BCH,
                event_subtype=HistoryEventSubType.RECEIVE,
                amount=FVal('0.99735527'),
            ),
            SwapEvent(
                identifier=3,
                event_identifier=dummy_event_id,
                timestamp=TimestampMS(1528060575000),
                location=Location.COINBASEPRO,
                asset=A_EUR,
                event_subtype=HistoryEventSubType.FEE,
                amount=FVal('3.01495511'),
            ),
            SwapEvent(
                identifier=4,
                event_identifier=dummy_event_id,
                timestamp=TimestampMS(1541771471000),
                location=Location.EXTERNAL,
                asset=A_USDT,
                event_subtype=HistoryEventSubType.SPEND,
                amount=FVal('713.952'),
            ),
            SwapEvent(
                identifier=5,
                event_identifier=dummy_event_id,
                timestamp=TimestampMS(1541771471000),
                location=Location.EXTERNAL,
                asset=A_BTC,
                event_subtype=HistoryEventSubType.RECEIVE,
                amount=FVal('0.110778'),
            ),
            SwapEvent(
                identifier=6,
                event_identifier=dummy_event_id,
                timestamp=TimestampMS(1541771471000),
                location=Location.EXTERNAL,
                asset=A_BTC,
                event_subtype=HistoryEventSubType.FEE,
                amount=FVal('0.000222'),
            ),
        ]
        with rotki.data.db.conn.read_ctx() as cursor:
            history_db = DBHistoryEvents(rotki.data.db)
            history_events = history_db.get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(),
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
                event_identifier=dummy_event_id,
                sequence_index=0,
                timestamp=TimestampMS(1543701600000),
                location=Location.EXTERNAL,
                asset=A_BTC,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                amount=FVal('0.05'),
                notes='',
            ),
        ]
        with rotki.data.db.conn.read_ctx() as cursor:
            history_db = DBHistoryEvents(rotki.data.db)
            history_events = history_db.get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(),

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
        history_events = history_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
                    )

    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0
    assert len(history_events) == 5

    expected_history_events = [
        AssetMovement(
            identifier=1,
            event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
            timestamp=TimestampMS(1643328780000),
            location=Location.BITSTAMP,
            asset=A_ETH,
            event_type=HistoryEventType.DEPOSIT,
            amount=FVal('2.00000000'),
        ),
        SwapEvent(
            identifier=2,
            event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
            timestamp=TimestampMS(1643329860000),
            location=Location.BITSTAMP,
            asset=A_ETH,
            event_subtype=HistoryEventSubType.SPEND,
            amount=FVal('1.00000000'),
        ),
        SwapEvent(
            identifier=3,
            event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
            timestamp=TimestampMS(1643329860000),
            location=Location.BITSTAMP,
            asset=A_EUR,
            event_subtype=HistoryEventSubType.RECEIVE,
            amount=FVal('2214.0100000000'),
        ),
        SwapEvent(
            identifier=4,
            event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
            timestamp=TimestampMS(1643329860000),
            location=Location.BITSTAMP,
            asset=A_EUR,
            event_subtype=HistoryEventSubType.FEE,
            amount=FVal('10.87005'),
        ),
        AssetMovement(
            identifier=5,
            event_identifier='1xyz',  # just a placeholder as comparison is done without this field  # noqa: E501
            timestamp=TimestampMS(1643542800000),
            location=Location.BITSTAMP,
            asset=A_EUR,
            event_type=HistoryEventType.WITHDRAWAL,
            amount=FVal('2211.01'),
        ),
    ]

    for actual, expected in zip(history_events, expected_history_events, strict=True):
        assert_is_equal_history_event(actual=actual, expected=expected)


def assert_bittrex_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from bittrex"""
    with rotki.data.db.conn.read_ctx() as cursor:
        events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
                    )

    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0
    assert events == [AssetMovement(
        identifier=5,
        event_identifier='28c432c0faec444c6c0b3c6da30171260273a05a2f684f67fa5e3184500ee83a',
        location=Location.BITTREX,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1451576024000),
        asset=A_ETH,
        amount=ONE,
        extra_data={'transaction_id': '0x'},
    ), AssetMovement(
        identifier=4,
        event_identifier='aac9b816a80599e72bd3e68adb9ce6165adddfcecd54ec682defbc57eb1cfe15',
        location=Location.BITTREX,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1483273298000),
        asset=A_BTC,
        amount=FVal('0.001'),
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
        amount=ONE,
        extra_data={
            'address': '3bamsmdamsd',
            'transaction_id': 'aaaa',
        },
    ), SwapEvent(
        identifier=10,
        event_identifier='620b844bcf05f009434ccfda55a2f4da704b6dd2cf059f45b16e3f5e79827cec',
        timestamp=TimestampMS(1502659923000),
        location=Location.BITTREX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c'),
        amount=FVal('857.78221905'),
        notes='Sold 857.78221905 EDGELESS for 0.15486188 BTC',
    ), SwapEvent(
        identifier=11,
        event_identifier='620b844bcf05f009434ccfda55a2f4da704b6dd2cf059f45b16e3f5e79827cec',
        timestamp=TimestampMS(1502659923000),
        location=Location.BITTREX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('0.1552414260036690'),
    ), SwapEvent(
        identifier=12,
        event_identifier='620b844bcf05f009434ccfda55a2f4da704b6dd2cf059f45b16e3f5e79827cec',
        timestamp=TimestampMS(1502659923000),
        location=Location.BITTREX,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal('0.00038812'),
    ), SwapEvent(
        identifier=7,
        event_identifier='a7a3ab217975bde5c78e497e94ef1acbf4fd40959d56a94cd69c61e8b8bf9bd8',
        timestamp=TimestampMS(1512302656000),
        location=Location.BITTREX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BTC,
        amount=FVal('0.2493676871638700'),
        notes='Bought 731.28354007 SWT for 0.24999841 BTC',
    ), SwapEvent(
        identifier=8,
        event_identifier='a7a3ab217975bde5c78e497e94ef1acbf4fd40959d56a94cd69c61e8b8bf9bd8',
        timestamp=TimestampMS(1512302656000),
        location=Location.BITTREX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0xB9e7F8568e08d5659f5D29C4997173d84CdF2607'),
        amount=FVal('731.28354007'),
    ), SwapEvent(
        identifier=9,
        event_identifier='a7a3ab217975bde5c78e497e94ef1acbf4fd40959d56a94cd69c61e8b8bf9bd8',
        timestamp=TimestampMS(1512302656000),
        location=Location.BITTREX,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal('0.00062343'),
    ), SwapEvent(
        identifier=13,
        event_identifier='130cfe32e8d0afa2baa5be124d912fd1fe4d990303ce517337692d49c99eda21',
        timestamp=TimestampMS(1546269766000),
        location=Location.BITTREX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal('0.10'),
    ), SwapEvent(
        identifier=14,
        event_identifier='130cfe32e8d0afa2baa5be124d912fd1fe4d990303ce517337692d49c99eda21',
        timestamp=TimestampMS(1546269766000),
        location=Location.BITTREX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('0.01'),
    ), SwapEvent(
        identifier=15,
        event_identifier='8ad88468123c6e521de38b9a1b687e8ff960be715a3f7ceb82c8813673d130c0',
        timestamp=TimestampMS(1546269967000),
        location=Location.BITTREX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=ONE,
    ), SwapEvent(
        identifier=16,
        event_identifier='8ad88468123c6e521de38b9a1b687e8ff960be715a3f7ceb82c8813673d130c0',
        timestamp=TimestampMS(1546269967000),
        location=Location.BITTREX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=ONE,
    ), AssetMovement(
        identifier=2,
        event_identifier='538f61a7ca39a7dc1805121b14fcb5e0ba389f952bad6b3f4b52854d94dd4f70',
        location=Location.BITTREX,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1632868521000),
        asset=Asset('BCHA'),
        amount=FVal('0.00000001'),
        extra_data={'transaction_id': '1A313456CCEA5AF45B334881513CF472'},
    ), AssetMovement(
        identifier=1,
        event_identifier='082a31a46ebe3e9f89e49c5b24a52c8069c4f42a9a5a1ec1cb34ae21779cd91d',
        location=Location.BITTREX,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1678175503000),
        asset=A_ETH,
        amount=FVal('0.20084931'),
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
        amount=ONE,
        extra_data={'transaction_id': 'Aaaa'},
    )]


def assert_kucoin_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from kucoin"""
    with rotki.data.db.conn.read_ctx() as cursor:
        swap_events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.KUCOIN),
                    )
    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0
    assert len(warnings) == 0
    expected_swap_events = [SwapEvent(
        identifier=7,
        event_identifier='KUe59e969261df8f5c3224aed041c4e827d9afe527091d4152ff1f3c2232882d58',
        timestamp=TimestampMS(1557570437000),
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BTC,
        amount=FVal('0.0015240225'),
    ), SwapEvent(
        identifier=8,
        event_identifier='KUe59e969261df8f5c3224aed041c4e827d9afe527091d4152ff1f3c2232882d58',
        timestamp=TimestampMS(1557570437000),
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_KCS,
        amount=FVal('10.01'),
    ), SwapEvent(
        identifier=9,
        event_identifier='KUe59e969261df8f5c3224aed041c4e827d9afe527091d4152ff1f3c2232882d58',
        timestamp=TimestampMS(1557570437000),
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal('0.00000152'),
    ), SwapEvent(
        identifier=10,
        event_identifier='KU0ff9a604ad6bf438284ab3632b25e8bd1670e6bb7a8012694910ccd0a429435a',
        timestamp=TimestampMS(1557570438000),
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_KCS,
        amount=FVal('10.02'),
    ), SwapEvent(
        identifier=11,
        event_identifier='KU0ff9a604ad6bf438284ab3632b25e8bd1670e6bb7a8012694910ccd0a429435a',
        timestamp=TimestampMS(1557570438000),
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('0.0015256452'),
    ), SwapEvent(
        identifier=12,
        event_identifier='KU0ff9a604ad6bf438284ab3632b25e8bd1670e6bb7a8012694910ccd0a429435a',
        timestamp=TimestampMS(1557570438000),
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal('0.00000153'),
    ), SwapEvent(
        identifier=1,
        event_identifier='KUc3acf7ffda6afa76573425419ab9ce4973aaa94c297da04bd9923dac9ef507fa',
        timestamp=TimestampMS(1651149360000),
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_XTZ,
        amount=FVal('36.4479'),
    ), SwapEvent(
        identifier=2,
        event_identifier='KUc3acf7ffda6afa76573425419ab9ce4973aaa94c297da04bd9923dac9ef507fa',
        timestamp=TimestampMS(1651149360000),
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        amount=FVal('3.73590975'),
    ), SwapEvent(
        identifier=3,
        event_identifier='KUc3acf7ffda6afa76573425419ab9ce4973aaa94c297da04bd9923dac9ef507fa',
        timestamp=TimestampMS(1651149360000),
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDT,
        amount=FVal('0.00373590975'),
    ), SwapEvent(
        identifier=4,
        event_identifier='KU7d8ea180dd203a993685f4fe1699642b992ae5865616c4cc00c0c5702c211584',
        timestamp=TimestampMS(1651160767000),
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal('280.8559209946952'),
    ), SwapEvent(
        identifier=5,
        event_identifier='KU7d8ea180dd203a993685f4fe1699642b992ae5865616c4cc00c0c5702c211584',
        timestamp=TimestampMS(1651160767000),
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_XRP,
        amount=FVal('432.59183198'),
    ), SwapEvent(
        identifier=6,
        event_identifier='KU7d8ea180dd203a993685f4fe1699642b992ae5865616c4cc00c0c5702c211584',
        timestamp=TimestampMS(1651160767000),
        location=Location.KUCOIN,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDT,
        amount=FVal('0.2808559209946952'),
    )]
    assert swap_events == expected_swap_events


def assert_blockpit_import_results(rotki: Rotkehlchen):
    """A utility function to help assert on correctness of importing data from blockpit"""
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.read_ctx() as cursor:
        history_events = dbevents.get_history_events_internal(cursor=cursor, filter_query=HistoryEventFilterQuery.make())  # noqa: E501

    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == len(warnings) == 0

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
            amount=FVal('0.001537148341223424'),
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
            amount=FVal('10'),
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
            amount=FVal('0.01061899'),
            notes='Receive 0.01061899 EUR in binance',
        ), SwapEvent(
            identifier=4,
            event_identifier='BPT558f00b5b6297cc7b2036b266f6c0a7d60c21fd4659bb66f30d62493f02ea4d9',
            timestamp=TimestampMS(1673181840000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_EUR,
            amount=FVal('168.69217'),
            notes='spot',
        ), SwapEvent(
            identifier=5,
            event_identifier='BPT558f00b5b6297cc7b2036b266f6c0a7d60c21fd4659bb66f30d62493f02ea4d9',
            timestamp=TimestampMS(1673181840000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH_MATIC,
            amount=FVal('223.7'),
        ), SwapEvent(
            identifier=6,
            event_identifier='BPT558f00b5b6297cc7b2036b266f6c0a7d60c21fd4659bb66f30d62493f02ea4d9',
            timestamp=TimestampMS(1673181840000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH_MATIC,
            amount=FVal('0.2237'),
        ), SwapEvent(
            identifier=7,
            event_identifier='BPT0b5b344d00eaa6b7b4aebbc15684e1b997daeb8bf685532f6b427ed4fa55e0e6',
            timestamp=TimestampMS(1673192880000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH_MATIC,
            amount=FVal('140.5'),
            notes='spot',
        ), SwapEvent(
            identifier=8,
            event_identifier='BPT0b5b344d00eaa6b7b4aebbc15684e1b997daeb8bf685532f6b427ed4fa55e0e6',
            timestamp=TimestampMS(1673192880000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_EUR,
            amount=FVal('106.1899'),
        ), SwapEvent(
            identifier=9,
            event_identifier='BPT0b5b344d00eaa6b7b4aebbc15684e1b997daeb8bf685532f6b427ed4fa55e0e6',
            timestamp=TimestampMS(1673192880000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_EUR,
            amount=FVal('0.1061899'),
        ), AssetMovement(
            identifier=10,
            location=Location.BINANCE,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1673194740000),
            asset=A_BNB,
            amount=FVal('0.0095'),
        ), AssetMovement(
            identifier=12,
            location=Location.EXTERNAL,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1673194740000),
            asset=A_BNB,
            amount=FVal('0.0095'),
        ), AssetMovement(
            identifier=11,
            location=Location.BINANCE,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1673194740000),
            asset=A_BNB,
            amount=FVal('0.0005'),
            is_fee=True,
        ), HistoryEvent(
            identifier=13,
            event_identifier='',
            sequence_index=1,
            timestamp=TimestampMS(1673194800000),
            location=Location.EXTERNAL,
            asset=A_BNB,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            amount=FVal('0.00024391'),
            notes='Fee of 0.00024391 BNB in external',
        ), AssetMovement(
            identifier=14,
            location=Location.EXTERNAL,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1673194920000),
            asset=A_BNB,
            amount=FVal('0.00915109'),
        ), AssetMovement(
            identifier=16,
            location=Location.BINANCE,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1673194920000),
            asset=A_BNB,
            amount=FVal('0.00915109'),
        ), AssetMovement(
            identifier=15,
            location=Location.EXTERNAL,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1673194920000),
            asset=A_BNB,
            amount=FVal('0.000105'),
            is_fee=True,
        ), SwapEvent(
            identifier=17,
            event_identifier='BPT73ea29fba318fcf8b32f1fd3e964528c4db0554060691063f4ddd61cb8550ce7',
            timestamp=TimestampMS(1673195040000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            amount=FVal('0.24209916'),
            asset=A_USDT,
        ), SwapEvent(
            identifier=18,
            event_identifier='BPT73ea29fba318fcf8b32f1fd3e964528c4db0554060691063f4ddd61cb8550ce7',
            timestamp=TimestampMS(1673195040000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            amount=FVal('0.00092036'),
            asset=A_BNB,
        ), SwapEvent(
            identifier=19,
            event_identifier='BPT73ea29fba318fcf8b32f1fd3e964528c4db0554060691063f4ddd61cb8550ce7',
            timestamp=TimestampMS(1673195040000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            amount=FVal('0.0000184'),
            asset=A_BNB,
        ), AssetMovement(
            identifier=20,
            location=Location.EXTERNAL,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1673204160000),
            asset=A_EUR,
            amount=FVal('150'),
        ), AssetMovement(
            identifier=21,
            location=Location.BITPANDA,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1674759960000),
            asset=A_EUR,
            amount=FVal('1000'),
        ), AssetMovement(
            identifier=22,
            location=Location.BITPANDA,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1674760200000),
            asset=A_EUR,
            amount=FVal('1000'),
        ), HistoryEvent(
            identifier=23,
            event_identifier='',
            sequence_index=1,
            timestamp=TimestampMS(1675532220000),
            location=Location.KRAKEN,
            asset=A_EUR,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            amount=FVal('0.0181'),
            notes='Spend 0.0181 EUR in kraken',
        ), HistoryEvent(
            identifier=24,
            event_identifier='',
            sequence_index=0,
            timestamp=TimestampMS(1675532700000),
            location=Location.KRAKEN,
            asset=A_EUR,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            amount=FVal('0.0021'),
            notes='Fee of 0.0021 EUR in kraken',
        ), HistoryEvent(
            identifier=25,
            event_identifier='',
            sequence_index=1,
            timestamp=TimestampMS(1675532700000),
            location=Location.KRAKEN,
            asset=A_EUR,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            amount=FVal('0.0025'),
            notes='Receive 0.0025 EUR in kraken',
        ), HistoryEvent(
            identifier=26,
            event_identifier='',
            sequence_index=1,
            timestamp=TimestampMS(1675913100000),
            location=Location.KRAKEN,
            asset=A_ETH_MATIC,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            amount=FVal('0.1932938'),
            notes='Staking reward of 0.1932938 MATIC in kraken',
        ), HistoryEvent(
            identifier=27,
            event_identifier='',
            sequence_index=1,
            timestamp=TimestampMS(1675954800000),
            location=Location.KRAKEN,
            asset=A_EUR,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            amount=FVal('0.06'),
            notes='Receive 0.06 EUR in kraken',
        ),
    ]
    for actual, expected in zip(history_events, expected_history_events, strict=True):
        assert_is_equal_history_event(actual=actual, expected=expected)
