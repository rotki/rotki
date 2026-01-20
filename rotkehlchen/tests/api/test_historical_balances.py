from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import gevent
import pytest
import requests

from rotkehlchen.api.v1.types import TaskName
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import DAY_IN_SECONDS, HOUR_IN_SECONDS, ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_USD
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.tasks.historical_balances import process_historical_balances
from rotkehlchen.tests.fixtures.messages import MockRotkiNotifier
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.constants import A_DASH
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import AssetAmount, ChainID, Location, Price, Timestamp
from rotkehlchen.utils.misc import timestamp_to_daystart_timestamp, ts_now, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.globaldb.handler import GlobalDBHandler

START_TS = Timestamp(1672531200)
DAY_AFTER_START_TS = Timestamp(START_TS + DAY_IN_SECONDS)


@pytest.fixture(name='setup_historical_data')
def fixture_setup_historical_data(rotkehlchen_api_server: 'APIServer') -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    events = [
        HistoryEvent(  # Day 1: Initial receive
            group_identifier='btc_receive_1',
            sequence_index=0,
            timestamp=ts_sec_to_ms(START_TS),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            location=Location.BLOCKCHAIN,
            asset=A_BTC,
            amount=FVal('2'),
            notes='Receive BTC',
        ),
        EvmEvent(  # ETH receive at same bucket as deposit
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=ts_sec_to_ms(Timestamp(START_TS + 3000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal('10'),
            location_label=(user_addy := make_evm_address()),
            notes='Receive ETH',
        ),
        HistoryEvent(  # Day 3: Partial spend
            group_identifier='btc_spend_1',
            sequence_index=2,
            timestamp=ts_sec_to_ms(Timestamp(START_TS + DAY_IN_SECONDS * 2)),
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            location=Location.BLOCKCHAIN,
            asset=A_BTC,
            amount=FVal('0.5'),
            notes='BTC partial spend',
        ),
        AssetMovement(
            timestamp=ts_sec_to_ms(day_3_ts := Timestamp(START_TS + DAY_IN_SECONDS * 2)),
            location=Location.COINBASE,
            event_type=HistoryEventType.DEPOSIT,
            asset=A_BTC,
            amount=ONE,
        ),
        AssetMovement(
            timestamp=ts_sec_to_ms(Timestamp(day_3_ts + 1)),
            location=Location.COINBASE,
            event_type=HistoryEventType.WITHDRAWAL,
            asset=A_BTC,
            amount=ONE,
        ),
        EvmEvent(  # Deposit into account (receive funds)
            tx_ref=make_evm_tx_hash(),
            sequence_index=1,
            timestamp=ts_sec_to_ms(day_3_ts),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            amount=FVal('0.5'),
            location_label=user_addy,
            notes='Deposit 0.5 ETH',
            address=make_evm_address(),
        ),
    ]
    with db.user_write() as write_cursor:
        DBHistoryEvents(database=db).add_history_events(
            write_cursor=write_cursor,
            history=events,
        )

    # Process events to populate event_metrics table
    process_historical_balances(
        database=db,
        msg_aggregator=db.msg_aggregator,
    )


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('have_decoders', [True])
def test_get_historical_balance(
        rotkehlchen_api_server: 'APIServer',
        setup_historical_data: None,
) -> None:
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'timestamphistoricalbalanceresource',
        ),
        json={'timestamp': START_TS + DAY_IN_SECONDS * 2},
    )

    result = assert_proper_sync_response_with_result(response)
    assert result['processing_required'] is False
    assert result['entries']['BTC'] == '2.5'  # 2 - 0.5 + 1 (deposit to exchange, withdrawal not yet)  # noqa: E501
    assert result['entries']['ETH'] == '10.5'  # 10 + 0.5 (deposit into account)

    # try retrieving the balance of a day without event and
    # see that the balance of the previous day is used.
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'timestamphistoricalbalanceresource',
        ),
        json={
            'timestamp': DAY_AFTER_START_TS,  # Day 2
            'async_query': True,
        },
    )
    task_id = assert_ok_async_response(response)
    outcome = wait_for_async_task(
        rotkehlchen_api_server,
        task_id,
    )
    # Balances(amount) should be same as day 1
    assert outcome['result']['processing_required'] is False
    assert outcome['result']['entries']['BTC'] == '2'
    assert outcome['result']['entries']['ETH'] == '10'


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('have_decoders', [True])
def test_get_historical_asset_balance(
        rotkehlchen_api_server: 'APIServer',
        setup_historical_data: None,
) -> None:
    """Test that the historical asset balance endpoint works correctly with both
    history events (from the setup_historical_data fixture) and also with an exchange trade.
    """
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with db.user_write() as write_cursor:
        DBHistoryEvents(database=db).add_history_events(
            write_cursor=write_cursor,
            history=create_swap_events(
                timestamp=ts_sec_to_ms(DAY_AFTER_START_TS),
                location=Location.EXTERNAL,
                spend=AssetAmount(asset=A_EUR, amount=FVal('3200.0')),
                receive=AssetAmount(asset=A_BTC, amount=FVal('0.2')),
                group_identifier='tradeid',
            ),
        )

    process_historical_balances(database=db, msg_aggregator=db.msg_aggregator)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'timestamphistoricalbalanceresource',
        ),
        json={
            'asset': 'BTC',
            'timestamp': START_TS + DAY_IN_SECONDS * 2,  # Day 3
        },
    )

    result = assert_proper_sync_response_with_result(response)
    assert result['processing_required'] is False
    assert result['entries']['BTC'] == '2.7'  # 2 - 0.5 + 1 (exchange deposit) + 0.2 (swap)


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('have_decoders', [True])
def test_get_historical_balance_with_filters(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Test that the historical balance endpoint correctly filters by location, location_label, and protocol."""  # noqa: E501
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    addr1, addr2 = make_evm_address(), make_evm_address()
    day2_ts, day3_ts = Timestamp(START_TS + DAY_IN_SECONDS), Timestamp(START_TS + DAY_IN_SECONDS * 2)  # noqa: E501
    with db.user_write() as write_cursor:
        DBHistoryEvents(database=db).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(  # Day 1: Receive ETH on Ethereum (address 1)
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=ts_sec_to_ms(START_TS),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('5'),
                location_label=addr1,
                address=addr1,
            ), EvmEvent(  # Day 1: Receive ETH on Ethereum (address 2)
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=ts_sec_to_ms(START_TS),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('4'),
                location_label=addr2,
                address=addr2,
            ), EvmEvent(  # Day 1: Receive ETH on Base (address 1)
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=ts_sec_to_ms(START_TS),
                location=Location.BASE,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('3'),
                location_label=addr1,
                address=addr1,
            ), EvmEvent(  # Day 1: Receive wrapped token from Aave (address 1)
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=ts_sec_to_ms(START_TS),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                asset=A_ETH,
                amount=FVal('10'),
                location_label=addr1,
                address=addr1,
                counterparty='aave',
            ), EvmEvent(  # Day 2: Receive more ETH on Ethereum (address 1)
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=ts_sec_to_ms(day2_ts),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('2'),
                location_label=addr1,
                address=addr1,
            ), EvmEvent(  # Day 2: Receive wrapped from Compound (address 1)
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=ts_sec_to_ms(day2_ts),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                asset=A_ETH,
                amount=FVal('6'),
                location_label=addr1,
                address=addr1,
                counterparty='compound',
            ), EvmEvent(  # Day 3: Spend ETH on Base (address 1)
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=ts_sec_to_ms(day3_ts),
                location=Location.BASE,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('1'),
                location_label=addr1,
                address=addr1,
            )],
        )

    process_historical_balances(database=db, msg_aggregator=db.msg_aggregator)

    for filters, expected_eth in (
        # Location filters
        ({'timestamp': START_TS, 'location': 'ethereum'}, '19'),  # 5 + 4 + 10 (aave)
        ({'timestamp': START_TS, 'location': 'base'}, '3'),
        # Location label filters
        ({'timestamp': START_TS, 'location_label': addr1}, '18'),  # 5 + 3 + 10 (aave)
        ({'timestamp': START_TS, 'location_label': addr2}, '4'),
        ({'timestamp': START_TS, 'location': 'ethereum', 'location_label': addr1}, '15'),  # 5 + 10
        # Protocol filters
        ({'timestamp': START_TS, 'protocol': 'aave'}, '10'),
        ({'timestamp': day2_ts, 'protocol': 'aave'}, '10'),
        ({'timestamp': day2_ts, 'protocol': 'compound'}, '6'),
        ({'timestamp': day2_ts, 'protocol': 'aave', 'location_label': addr1}, '10'),
        # Combined filters
        ({'timestamp': START_TS}, '22'),  # 5 + 4 + 3 + 10 (aave)
        ({'timestamp': day2_ts, 'location_label': addr1}, '26'),  # 5 + 2 + 3 + 10 + 6
        ({'timestamp': day3_ts, 'location': 'base', 'location_label': addr1}, '2'),  # 3 - 1
        ({'timestamp': day3_ts}, '29'),  # 7 + 4 + 2 + 10 + 6
        ({'timestamp': day3_ts, 'asset': 'ETH', 'location': 'ethereum', 'location_label': addr1}, '23'),  # 7 + 10 + 6  # noqa: E501
    ):
        result = assert_proper_sync_response_with_result(requests.post(
            api_url_for(rotkehlchen_api_server, 'timestamphistoricalbalanceresource'),
            json=filters,
        ))
        assert result['processing_required'] is False, f'Failed for filters: {filters}'
        assert result['entries']['ETH'] == expected_eth, f'Failed for filters: {filters}'

    for filters, error_msg in (  # test validation errors
        ({'timestamp': START_TS, 'location_label': make_evm_address()}, 'Unknown location label'),
        ({'timestamp': START_TS, 'protocol': 'idontexist'}, 'Unknown protocol'),
    ):
        assert_error_response(
            response=requests.post(
                api_url_for(rotkehlchen_api_server, 'timestamphistoricalbalanceresource'),
                json=filters,
            ),
            contained_in_msg=error_msg,
        )


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_historical_asset_amounts_over_time(
        rotkehlchen_api_server: 'APIServer',
        setup_historical_data: None,
) -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with db.user_write() as write_cursor:
        DBHistoryEvents(database=db).add_history_events(
            write_cursor=write_cursor,
            history=[*create_swap_events(
                timestamp=ts_sec_to_ms(Timestamp(START_TS + DAY_IN_SECONDS * 3)),
                location=Location.EXTERNAL,
                spend=AssetAmount(asset=A_EUR, amount=FVal('24000.0')),
                receive=AssetAmount(asset=A_BTC, amount=FVal('1.5')),
                group_identifier='trade1',
            ), *create_swap_events(  # Second swap with same asset and timestamp (multiple fill events of the same order)  # noqa: E501
                timestamp=ts_sec_to_ms(Timestamp(START_TS + DAY_IN_SECONDS * 3)),
                location=Location.EXTERNAL,
                spend=AssetAmount(asset=A_EUR, amount=FVal('8000.0')),
                receive=AssetAmount(asset=A_BTC, amount=FVal('0.5')),
                group_identifier='trade2',
            )],
        )

    process_historical_balances(database=db, msg_aggregator=db.msg_aggregator)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetamountsresource',
        ),
        json={
            'asset': 'BTC',
            'from_timestamp': START_TS,
            'to_timestamp': START_TS + DAY_IN_SECONDS * 10,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    # Check all balance amount change points are present with correct amounts
    # Day 1: 2 (receive), Day 3: 2.5 (deposit to exchange), Day 3+1s: 1.5 (withdrawal), Day 4: 3.5 (swaps)  # noqa: E501
    assert len(result['times']) == len(result['values'])
    day_3_ts = START_TS + DAY_IN_SECONDS * 2
    for ts, amount in zip(result['times'], result['values'], strict=True):
        assert ts in {START_TS, day_3_ts, day_3_ts + 1, START_TS + DAY_IN_SECONDS * 3}
        assert amount in {'2', '2.5', '1.5', '3.5'}


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_historical_asset_amounts_over_time_with_negative_amount(
        rotkehlchen_api_server: 'APIServer',
        setup_historical_data: None,
) -> None:
    # Add more events to create a scenario with multiple potential negative balance events
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    db.msg_aggregator.rotki_notifier = MockRotkiNotifier()  # type: ignore[assignment]
    events = [
        HistoryEvent(
            group_identifier='btc_spend_2',
            sequence_index=3,
            timestamp=ts_sec_to_ms(Timestamp(START_TS + DAY_IN_SECONDS * 3)),
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            location=Location.BLOCKCHAIN,
            asset=A_BTC,
            amount=FVal('1.6'),  # spending more than remaining balance
            notes='BTC first overspend attempt',
        ),
        HistoryEvent(
            group_identifier='btc_spend_3',
            sequence_index=4,
            timestamp=ts_sec_to_ms(four_days_after_start := Timestamp(START_TS + DAY_IN_SECONDS * 4)),  # noqa: E501
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            location=Location.BLOCKCHAIN,
            asset=A_BTC,
            amount=FVal('0.7'),
            notes='BTC second overspend attempt',
        ),
    ]
    with db.user_write() as write_cursor:
        DBHistoryEvents(database=db).add_history_events(
            write_cursor=write_cursor,
            history=events,
        )

    process_historical_balances(database=db, msg_aggregator=db.msg_aggregator)

    # Check that negative balance was detected via WS message
    messages = db.msg_aggregator.rotki_notifier.messages  # type: ignore[union-attr]
    assert any(m.message_type == WSMessageType.NEGATIVE_BALANCE_DETECTED for m in messages)

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetamountsresource',
        ),
        json={
            'asset': 'BTC',
            'from_timestamp': START_TS,
            'to_timestamp': four_days_after_start,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['times']) == len(result['values'])
    day_3_ts = START_TS + DAY_IN_SECONDS * 2
    assert len(result['times']) == 3
    assert result['times'][0] == START_TS  # Initial timestamp
    assert result['times'][1] == day_3_ts  # After spend and exchange deposit
    assert result['times'][2] == day_3_ts + 1  # After exchange withdrawal
    assert result['values'][0] == '2'  # Initial balance
    assert result['values'][1] == '2.5'  # Balance after spend and deposit (withdrawal not yet)
    assert result['values'][2] == '1.5'  # Balance after withdrawal


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_historical_assets_in_collection_amounts_over_time(
        rotkehlchen_api_server: 'APIServer',
        setup_historical_data: None,
) -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    db.msg_aggregator.rotki_notifier = MockRotkiNotifier()  # type: ignore[assignment]
    events = [
        HistoryEvent(
            group_identifier='btc_spend_2',
            sequence_index=3,
            timestamp=ts_sec_to_ms(Timestamp(START_TS + DAY_IN_SECONDS * 3)),
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            location=Location.BLOCKCHAIN,
            asset=Asset('eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'),  # WBTC
            amount=FVal('1.6'),  # spending more than remaining balance
            notes='BTC first overspend attempt',
        ),
        HistoryEvent(
            group_identifier='btc_spend_3',
            sequence_index=4,
            timestamp=ts_sec_to_ms(four_days_after_start := Timestamp(START_TS + DAY_IN_SECONDS * 4)),  # noqa: E501
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            location=Location.BLOCKCHAIN,
            asset=Asset('eip155:100/erc20:0x8e5bBbb09Ed1ebdE8674Cda39A0c169401db4252'),  # WBTC
            amount=FVal('0.7'),
            notes='BTC second overspend attempt',
        ),
    ]
    with db.user_write() as write_cursor:
        DBHistoryEvents(database=db).add_history_events(
            write_cursor=write_cursor,
            history=events,
        )

    process_historical_balances(database=db, msg_aggregator=db.msg_aggregator)

    # Check that negative balance was detected via WS message
    messages = db.msg_aggregator.rotki_notifier.messages  # type: ignore[union-attr]
    assert any(m.message_type == WSMessageType.NEGATIVE_BALANCE_DETECTED for m in messages)

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetamountsresource',
        ),
        json={
            'collection_id': 40,
            'from_timestamp': START_TS,
            'to_timestamp': four_days_after_start,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['times']) == len(result['values'])
    day_3_ts = START_TS + DAY_IN_SECONDS * 2
    assert len(result['times']) == 3
    assert result['times'][0] == START_TS  # Initial timestamp
    assert result['times'][1] == day_3_ts  # After spend and exchange deposit
    assert result['times'][2] == day_3_ts + 1  # After exchange withdrawal
    assert result['values'][0] == '2'  # Initial balance
    assert result['values'][1] == '2.5'  # Balance after spend and deposit (withdrawal not yet)
    assert result['values'][2] == '1.5'  # Balance after withdrawal


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('have_decoders', [True])
def test_get_historical_balance_before_first_event(
        rotkehlchen_api_server: 'APIServer',
        setup_historical_data: None,
) -> None:
    """Test getting historical balances before any events returns processing_required=False
    since no events exist before the requested timestamp."""
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'timestamphistoricalbalanceresource',
        ),
        json={'timestamp': START_TS - DAY_IN_SECONDS},  # Day before first event
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['processing_required'] is False
    assert 'entries' not in result


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('have_decoders', [True])
def test_get_historical_balance_unknown_asset(rotkehlchen_api_server: 'APIServer') -> None:
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'timestamphistoricalbalanceresource',
        ),
        json={
            'asset': 'UNKNOWN',
            'timestamp': START_TS,
        },
    )

    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset UNKNOWN',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('have_decoders', [True])
def test_get_historical_asset_balance_without_premium(rotkehlchen_api_server: 'APIServer') -> None:
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'timestamphistoricalbalanceresource',
        ),
        json={
            'asset': 'BTC',
            'timestamp': START_TS,
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='does not have a premium subscription',
        status_code=HTTPStatus.FORBIDDEN,
    )


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_historical_netvalue(
        rotkehlchen_api_server: 'APIServer',
        setup_historical_data: None,
) -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with db.user_write() as write_cursor:
        DBHistoryEvents(database=db).add_history_events(
            write_cursor=write_cursor,
            history=[HistoryEvent(
                group_identifier='eur_receive_1',
                sequence_index=0,
                timestamp=ts_sec_to_ms(START_TS),
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                location=Location.BLOCKCHAIN,
                asset=A_EUR,
                amount=FVal('20000'),
                notes='Receive EUR',
            ), *create_swap_events(
                timestamp=ts_sec_to_ms(DAY_AFTER_START_TS),
                location=Location.BLOCKCHAIN,
                group_identifier='1xyz',
                spend=AssetAmount(asset=A_EUR, amount=FVal('3200.0')),
                receive=AssetAmount(asset=A_BTC, amount=FVal('0.2')),
            ), *create_swap_events(
                timestamp=ts_sec_to_ms(Timestamp(START_TS + DAY_IN_SECONDS * 2)),
                location=Location.BLOCKCHAIN,
                group_identifier='2xyz',
                spend=AssetAmount(asset=A_ETH, amount=FVal('0.2')),
                receive=AssetAmount(asset=A_EUR, amount=FVal('240.0')),
            )],
        )

    process_historical_balances(database=db, msg_aggregator=db.msg_aggregator)

    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'historicalnetvalueresource'),
        json={'from_timestamp': START_TS, 'to_timestamp': START_TS + DAY_IN_SECONDS * 3},
    )
    result = assert_proper_sync_response_with_result(response)

    assert result['processing_required'] is False
    assert len(result['times']) == len(result['values']) == 3

    expected_timestamps = [
        timestamp_to_daystart_timestamp(START_TS),  # Day 1
        timestamp_to_daystart_timestamp(DAY_AFTER_START_TS),  # Day 2
        timestamp_to_daystart_timestamp(Timestamp(START_TS + DAY_IN_SECONDS * 2)),  # Day 3
    ]
    expected_balances = [
        {  # Day 1: Initial balances (2 BTC, 10 ETH from fixture) + 20000 EUR receive
            A_BTC.identifier: '2',
            A_ETH.identifier: '10',
            A_EUR.identifier: '20000',
        },
        {  # Day 2: After EUR -> BTC swap (+0.2 BTC, -3200 EUR)
            A_BTC.identifier: '2.2',
            A_ETH.identifier: '10',
            A_EUR.identifier: '16800',
        },
        {  # Day 3: After BTC spend (-0.5) and ETH -> EUR swap (-0.2 ETH, +240 EUR)
            A_BTC.identifier: '1.7000000000000002',
            A_ETH.identifier: '10.5',
            A_EUR.identifier: '17040',
        },
    ]

    for timestamp, balances, expected_ts, expected_bal in zip(
        result['times'],
        result['values'],
        expected_timestamps,
        expected_balances,
        strict=True,
    ):
        assert timestamp == expected_ts
        assert balances == expected_bal

    # now, ignore an asset and see the result is expected.
    with db.user_write() as write_cursor:
        db.add_to_ignored_assets(write_cursor=write_cursor, asset=A_BTC)

    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'historicalnetvalueresource'),
        json={'from_timestamp': START_TS},
    )
    result = assert_proper_sync_response_with_result(response)

    assert result['processing_required'] is False
    assert len(result['times']) == len(result['values']) == 3

    expected_balances_ignored = [
        {A_ETH.identifier: '10', A_EUR.identifier: '20000'},
        {A_ETH.identifier: '10', A_EUR.identifier: '16800'},
        {A_ETH.identifier: '10.5', A_EUR.identifier: '17040'},
    ]

    for timestamp, balances, expected_ts, expected_bal in zip(
        result['times'],
        result['values'],
        expected_timestamps,
        expected_balances_ignored,
        strict=True,
    ):
        assert timestamp == expected_ts
        assert balances == expected_bal


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_historical_netvalue_with_negative_balance_events(
        rotkehlchen_api_server: 'APIServer',
        setup_historical_data: None,
) -> None:
    """Test that get_historical_netvalue handles negative balance scenarios properly."""
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    db.msg_aggregator.rotki_notifier = MockRotkiNotifier()  # type: ignore[assignment]

    # Add events that would create negative balance
    events = [
        HistoryEvent(
            group_identifier='btc_spend_2',
            sequence_index=3,
            timestamp=ts_sec_to_ms(Timestamp(START_TS + DAY_IN_SECONDS * 3)),
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            location=Location.BLOCKCHAIN,
            asset=A_BTC,
            amount=FVal('1.6'),  # spending more than remaining balance (1.5)
            notes='BTC overspend',
        ),
    ]
    with db.user_write() as write_cursor:
        DBHistoryEvents(database=db).add_history_events(
            write_cursor=write_cursor,
            history=events,
        )

    gevent.sleep(0.01)  # allow db write to complete before processing
    process_historical_balances(database=db, msg_aggregator=db.msg_aggregator)

    # Verify negative balance was detected via WS message
    messages = db.msg_aggregator.rotki_notifier.messages  # type: ignore[union-attr]
    assert any(m.message_type == WSMessageType.NEGATIVE_BALANCE_DETECTED for m in messages)

    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'historicalnetvalueresource'),
        json={'from_timestamp': START_TS, 'to_timestamp': START_TS + DAY_IN_SECONDS * 4},
    )
    result = assert_proper_sync_response_with_result(response)

    # All events evaluated (including negative balance skips) so processing_required is False
    assert result['processing_required'] is False
    expected_timestamps = [
        timestamp_to_daystart_timestamp(START_TS),  # Day 1
        timestamp_to_daystart_timestamp(Timestamp(START_TS + DAY_IN_SECONDS * 2)),  # Day 3
    ]
    expected_balances = [
        {A_BTC.identifier: '2', A_ETH.identifier: '10'},  # Day 1: Initial receives from fixture
        {A_BTC.identifier: '1.5', A_ETH.identifier: '10.5'},  # Day 3: After partial BTC spend and ETH deposit into account  # noqa: E501
    ]

    assert len(result['times']) == len(expected_timestamps)
    assert len(result['values']) == len(expected_balances)
    for timestamp, balances, expected_ts, expected_bal in zip(
        result['times'],
        result['values'],
        expected_timestamps,
        expected_balances,
        strict=True,
    ):
        assert timestamp == expected_ts
        assert balances == expected_bal


@pytest.mark.vcr(filter_query_parameters=['api_key'])
@pytest.mark.freeze_time('2025-03-06 00:00:00 GMT')
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_get_historical_prices_per_asset(
        rotkehlchen_api_server: 'APIServer',
        globaldb: 'GlobalDBHandler',
) -> None:
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalpricesperassetresource',
        ),
        json={
            'asset': 'BTC',
            'from_timestamp': START_TS,
            'to_timestamp': START_TS + 2 * DAY_IN_SECONDS,
            'interval': DAY_IN_SECONDS,
            'async_query': True,
        },
    )
    task_id = assert_ok_async_response(response)
    outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert outcome['result']['no_prices_timestamps'] == []
    assert outcome['result']['prices'] == {
        '1672531200': '15519.8178641018',
        '1672617600': '15615.0005870507',
        '1672704000': '15806.226022787',
    }

    # invalid asset
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalpricesperassetresource',
        ),
        json={
            'asset': 'INVALID',
            'from_timestamp': START_TS,
            'to_timestamp': DAY_AFTER_START_TS,
            'interval': DAY_IN_SECONDS,
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset INVALID',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test timestamps not aligned with interval - API should auto-adjust them
    two_day_interval = DAY_IN_SECONDS * 2
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalpricesperassetresource',
        ),
        json={
            'asset': 'ETH',
            'from_timestamp': START_TS + 5000,  # Not interval-aligned
            'to_timestamp': START_TS + 3 * DAY_IN_SECONDS - 1000,  # Also not aligned
            'interval': two_day_interval,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert str(START_TS) in result['prices']
    assert str(START_TS + 2 * two_day_interval) in result['prices']

    # asset with no historical prices
    get_or_create_evm_token(
        userdb=rotkehlchen_api_server.rest_api.rotkehlchen.data.db,
        evm_address=string_to_evm_address('0x5875eEE11Cf8398102FdAd704C9E96607675467a'),
        chain_id=ChainID.BASE,
        decimals=18,
        symbol='sUSDS',
    )
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalpricesperassetresource',
        ),
        json={
            'asset': 'eip155:8453/erc20:0x5875eEE11Cf8398102FdAd704C9E96607675467a',
            'from_timestamp': START_TS,
            'to_timestamp': DAY_AFTER_START_TS,
            'interval': DAY_IN_SECONDS,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['prices'] == {}
    assert result['no_prices_timestamps'] == [START_TS, DAY_AFTER_START_TS]

    # invalid from_timestamp > to_timestamp
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalpricesperassetresource',
        ),
        json={
            'asset': 'BTC',
            'from_timestamp': DAY_AFTER_START_TS,
            'to_timestamp': START_TS,
            'interval': DAY_IN_SECONDS,
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='from_timestamp must be smaller than to_timestamp',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # test only cached prices
    globaldb.add_historical_prices([HistoricalPrice(
        from_asset=A_DASH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=START_TS,
        price=Price(FVal('10')),
    ), HistoricalPrice(
        from_asset=A_DASH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=DAY_AFTER_START_TS,
        price=Price(FVal('20')),
    )])
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalpricesperassetresource',
        ),
        json={
            'asset': 'DASH',
            'from_timestamp': START_TS,
            'to_timestamp': START_TS + (DAY_IN_SECONDS * 10),
            'interval': DAY_IN_SECONDS,
            'only_cache_period': 3600,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['prices'] == {
        str(START_TS): '10',
        str(DAY_AFTER_START_TS): '20',
    }

    # test future timestamp exclusion
    current_time = ts_now()
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalpricesperassetresource',
        ),
        json={
            'asset': 'BTC',
            'from_timestamp': current_time - DAY_IN_SECONDS,
            'to_timestamp': (future_ts := current_time + DAY_IN_SECONDS),  # Include timestamp in the future  # noqa: E501
            'interval': DAY_IN_SECONDS,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert str(future_ts) not in result['prices']
    assert future_ts not in result['no_prices_timestamps']
    assert future_ts not in result['rate_limited_prices_timestamps']
    assert max(int(ts) for ts in result['prices']) <= current_time

    # test excluded timestamps
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalpricesperassetresource',
        ),
        json={
            'asset': 'BTC',
            'from_timestamp': START_TS,
            'to_timestamp': START_TS + 2 * DAY_IN_SECONDS,
            'interval': DAY_IN_SECONDS,
            'exclude_timestamps': [DAY_AFTER_START_TS],  # Exclude middle timestamp
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert str(START_TS) in result['prices']
    assert str(DAY_AFTER_START_TS) not in result['prices']
    assert str(START_TS + 2 * DAY_IN_SECONDS) in result['prices']
    assert DAY_AFTER_START_TS not in result['no_prices_timestamps']

    # Test both rate limited and no price found scenarios
    original_query_historical_price = PriceHistorian.query_historical_price

    def mock_query_historical_price(from_asset, to_asset, timestamp):
        # Rate limit for one timestamp
        if timestamp == DAY_AFTER_START_TS:
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=True,
            )
        # No price found for another timestamp
        elif timestamp == START_TS + 2 * DAY_IN_SECONDS:
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
                rate_limited=False,
            )
        # Normal behavior for other timestamps
        return original_query_historical_price(from_asset, to_asset, timestamp)

    with patch('rotkehlchen.history.price.PriceHistorian.query_historical_price', side_effect=mock_query_historical_price):  # noqa: E501
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'historicalpricesperassetresource',
            ),
            json={
                'asset': 'BTC',
                'from_timestamp': START_TS,
                'to_timestamp': START_TS + 3 * DAY_IN_SECONDS,
                'interval': DAY_IN_SECONDS,
            },
        )
        result = assert_proper_sync_response_with_result(response)
        # The first timestamp should have a price
        assert str(START_TS) in result['prices']

        # The second timestamp should be rate limited
        assert str(DAY_AFTER_START_TS) not in result['prices']
        assert DAY_AFTER_START_TS not in result['no_prices_timestamps']
        assert DAY_AFTER_START_TS in result['rate_limited_prices_timestamps']

        # The third timestamp should have no price found (not rate limited)
        assert str(START_TS + 2 * DAY_IN_SECONDS) not in result['prices']
        assert START_TS + 2 * DAY_IN_SECONDS in result['no_prices_timestamps']
        assert START_TS + 2 * DAY_IN_SECONDS not in result['rate_limited_prices_timestamps']

        # The fourth timestamp should have a price (uses original function)
        assert str(START_TS + 3 * DAY_IN_SECONDS) in result['prices']


def test_historical_price_cache_only_special_assets(
        rotkehlchen_api_server: 'APIServer',
        globaldb: 'GlobalDBHandler',
) -> None:
    """Test special assets work with only_cache_period."""
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    # Test EURe collection asset cache consistency
    response_no_cache = requests.post(  # Query without cache
        api_url_for(rotkehlchen_api_server, 'historicalpricesperassetresource'),
        json={
            'asset': (eure_asset := 'eip155:100/erc20:0xcB444e90D8198415266c6a2724b7900fb12FC56E'),
            'interval': DAY_IN_SECONDS,
            'from_timestamp': START_TS,
            'to_timestamp': START_TS + DAY_IN_SECONDS,
        },
    )
    result_no_cache = assert_proper_sync_response_with_result(response_no_cache)
    response_cache_only = requests.post(  # query with cache only
        api_url_for(rotkehlchen_api_server, 'historicalpricesperassetresource'),
        json={
            'asset': eure_asset,
            'interval': DAY_IN_SECONDS,
            'from_timestamp': START_TS,
            'to_timestamp': START_TS + DAY_IN_SECONDS,
            'only_cache_period': HOUR_IN_SECONDS,
        },
    )
    result_cache_only = assert_proper_sync_response_with_result(response_cache_only)
    assert result_no_cache['prices'] == result_cache_only['prices']

    with db.conn.write_ctx() as write_cursor:
        db.set_setting(write_cursor=write_cursor, name='main_currency', value=A_USD)

    # KFEE should return fixed $0.01 price
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalpricesperassetresource',
        ),
        json={
            'asset': 'KFEE',
            'from_timestamp': (kfee_ts := START_TS + DAY_IN_SECONDS),
            'to_timestamp': kfee_ts + 10,
            'interval': 5,
            'only_cache_period': HOUR_IN_SECONDS,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert str(kfee_ts) in result['prices']
    assert result['prices'][str(kfee_ts)] == '0.01'

    # Test that ETH2 should use ETH price
    globaldb.add_historical_prices(entries=[HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_USD,
        timestamp=START_TS,
        price=Price(FVal('1400')),
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
    )])
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalpricesperassetresource',
        ),
        json={
            'asset': 'ETH2',
            'interval': DAY_IN_SECONDS,
            'from_timestamp': START_TS,
            'to_timestamp': START_TS + DAY_IN_SECONDS,
            'only_cache_period': HOUR_IN_SECONDS,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert str(START_TS) in result['prices']
    assert result['prices'][str(START_TS)] == '1400'


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_historical_asset_amounts_processing_required(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Test that processing_required flag is returned correctly and that the
    processing trigger endpoint works."""
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    events = [
        HistoryEvent(
            group_identifier='btc_receive_1',
            sequence_index=0,
            timestamp=ts_sec_to_ms(START_TS),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            location=Location.BLOCKCHAIN,
            asset=A_BTC,
            amount=FVal('2'),
            notes='Receive BTC',
        ),
    ]
    with db.user_write() as write_cursor:
        DBHistoryEvents(database=db).add_history_events(
            write_cursor=write_cursor,
            history=events,
        )

    # events exist but are not yet processed
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetamountsresource',
        ),
        json={
            'asset': 'BTC',
            'from_timestamp': START_TS,
            'to_timestamp': START_TS + DAY_IN_SECONDS,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['processing_required'] is True
    assert 'times' not in result
    assert 'values' not in result

    # trigger processing via the API
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'triggertaskresource',
        ),
        json={'async_query': False, 'task': TaskName.HISTORICAL_BALANCE_PROCESSING.serialize()},
    )
    assert_proper_sync_response_with_result(response)

    # now data should be available
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetamountsresource',
        ),
        json={
            'asset': 'BTC',
            'from_timestamp': START_TS,
            'to_timestamp': START_TS + DAY_IN_SECONDS,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['processing_required'] is False
    assert 'times' in result
    assert 'values' in result


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_historical_asset_amounts_no_events(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Test that processing_required=False is returned when no events exist in time range."""
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetamountsresource',
        ),
        json={
            'asset': 'BTC',
            'from_timestamp': START_TS,
            'to_timestamp': START_TS + DAY_IN_SECONDS,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['processing_required'] is False
    assert 'times' not in result
    assert 'values' not in result
