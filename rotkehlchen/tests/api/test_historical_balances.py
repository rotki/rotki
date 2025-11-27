from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

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
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.constants import A_DASH
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
        HistoryEvent(  # another receive
            group_identifier='eth_receive_1',
            sequence_index=1,
            timestamp=ts_sec_to_ms(Timestamp(START_TS + 3000)),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            location=Location.BLOCKCHAIN,
            asset=A_ETH,
            amount=FVal('10'),
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
        AssetMovement(  # AssetMovements should be ignored
            timestamp=ts_sec_to_ms(Timestamp(START_TS + DAY_IN_SECONDS * 2)),
            location=Location.COINBASE,
            event_type=HistoryEventType.WITHDRAWAL,
            asset=A_BTC,
            amount=FVal('3'),
        ),
        HistoryEvent(  # Staking deposit/withdrawals should also be ignored
            group_identifier='btc_spend_1',
            sequence_index=4,
            timestamp=ts_sec_to_ms(Timestamp(START_TS + DAY_IN_SECONDS * 2)),
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            location=Location.BLOCKCHAIN,
            asset=A_BTC,
            amount=ONE,
        ),
    ]
    with db.user_write() as write_cursor:
        DBHistoryEvents(database=db).add_history_events(
            write_cursor=write_cursor,
            history=events,
        )


@pytest.mark.vcr(filter_query_parameters=['api_key'])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_price_queries', [False])
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
    assert result['BTC']['amount'] == '1.5'
    assert result['BTC']['price'] == '15806.226022787'
    assert result['ETH']['amount'] == '10'
    assert result['ETH']['price'] == '1151.10913718085'

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
    assert outcome['result']['BTC']['amount'] == '2'
    assert outcome['result']['ETH']['amount'] == '10'


@pytest.mark.vcr(filter_query_parameters=['api_key'])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_price_queries', [False])
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
    # Should show post-withdrawal balance
    assert result['amount'] == '1.7'  # 2 - 0.5 + 0.2
    assert result['price'] == '15806.226022787'


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
    assert len(result['times']) == len(result['values'])
    assert 'last_group_identifier' not in result
    for ts, amount in zip(result['times'], result['values'], strict=True):
        assert ts in {START_TS, START_TS + DAY_IN_SECONDS * 2, START_TS + DAY_IN_SECONDS * 3}
        assert amount in {'2', '1.5', '3.5'}


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_historical_asset_amounts_over_time_with_negative_amount(
        rotkehlchen_api_server: 'APIServer',
        setup_historical_data: None,
) -> None:
    # Add more events to create a scenario with multiple potential negative balance events
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
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
    assert len(result['times']) == 2

    assert result['last_group_identifier'] == [6, events[0].group_identifier]
    assert result['times'][0] == START_TS  # Initial timestamp
    assert result['times'][1] == START_TS + DAY_IN_SECONDS * 2  # First spend
    assert result['values'][0] == '2'  # Initial balance
    assert result['values'][1] == '1.5'  # Balance after first spend


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_historical_assets_in_collection_amounts_over_time(
        rotkehlchen_api_server: 'APIServer',
        setup_historical_data: None,
) -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
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
    assert len(result['times']) == 2

    assert result['last_group_identifier'] == [6, events[0].group_identifier]
    assert result['times'][0] == START_TS  # Initial timestamp
    assert result['times'][1] == START_TS + DAY_IN_SECONDS * 2  # First spend
    assert result['values'][0] == '2'  # Initial balance
    assert result['values'][1] == '1.5'  # Balance after first spend


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_get_historical_balance_before_first_event(
        rotkehlchen_api_server: 'APIServer',
        setup_historical_data: None,
) -> None:
    """Test getting historical balances before any events"""
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'timestamphistoricalbalanceresource',
        ),
        json={'timestamp': START_TS - DAY_IN_SECONDS},  # Day before first event
    )
    assert_error_response(
        response=response,
        contained_in_msg='No historical data found until the given timestamp.',
        status_code=HTTPStatus.NOT_FOUND,
    )


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_price_queries', [False])
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
        globaldb: 'GlobalDBHandler',
        setup_historical_data: None,
) -> None:
    main_currency = A_EUR
    btc_price = Price(FVal('16000.0'))
    eth_price = Price(FVal('1200.0'))
    for offset in range(3):
        globaldb.add_historical_prices(entries=[
            HistoricalPrice(
                from_asset=A_BTC,
                to_asset=main_currency,
                source=HistoricalPriceOracle.CRYPTOCOMPARE,
                timestamp=(ts := Timestamp(START_TS + (DAY_IN_SECONDS * offset))),
                price=btc_price,
            ),
            HistoricalPrice(
                from_asset=A_ETH,
                to_asset=main_currency,
                source=HistoricalPriceOracle.CRYPTOCOMPARE,
                timestamp=ts,
                price=eth_price,
            ),
        ])

    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with db.user_write() as write_cursor:
        DBHistoryEvents(database=db).add_history_events(
            write_cursor=write_cursor,
            history=[HistoryEvent(
                group_identifier='eur_receive_1',
                sequence_index=0,
                timestamp=ts_sec_to_ms(START_TS),  # Day 1
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                location=Location.BLOCKCHAIN,
                asset=A_EUR,
                amount=FVal('20000'),  # Enough EUR to buy BTC
                notes='Receive EUR',
            ), *create_swap_events(
                timestamp=ts_sec_to_ms(DAY_AFTER_START_TS),  # Day 2,
                location=Location.EXTERNAL,
                group_identifier='1xyz',
                spend=AssetAmount(asset=A_EUR, amount=FVal('3200.0')),
                receive=AssetAmount(asset=A_BTC, amount=FVal('0.2')),
            ), *create_swap_events(
                timestamp=ts_sec_to_ms(Timestamp(START_TS + DAY_IN_SECONDS * 2)),  # Day 3,
                location=Location.EXTERNAL,
                group_identifier='2xyz',
                spend=AssetAmount(asset=A_ETH, amount=FVal('0.2')),
                receive=AssetAmount(asset=A_EUR, amount=FVal('240.0')),
            )],
        )

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalnetvalueresource',
        ),
        json={
            'from_timestamp': START_TS,
            'to_timestamp': START_TS + DAY_IN_SECONDS * 3,
        },
    )
    result = assert_proper_sync_response_with_result(response)

    assert len(result['missing_prices']) == 0
    assert 'last_group_identifier' not in result
    assert len(result['times']) == len(result['values']) == 3
    assert all(ts in result['times'] for ts in (
        timestamp_to_daystart_timestamp(START_TS),
        timestamp_to_daystart_timestamp(Timestamp(START_TS + DAY_IN_SECONDS * 2)),
    ))

    expected_timestamps = [
        timestamp_to_daystart_timestamp(START_TS),  # Day 1
        timestamp_to_daystart_timestamp(DAY_AFTER_START_TS),  # Day 2
        timestamp_to_daystart_timestamp(Timestamp(START_TS + DAY_IN_SECONDS * 2)),  # Day 3
    ]
    expected_values = [
        FVal('64000'),  # Day 1: (2 BTC * 16000) + (10 ETH * 1200) + 20000 EUR
        FVal('64000'),  # Day 2: (2.2 BTC * 16000) + (10 ETH * 1200) + 16800 EUR
        FVal('56000'),  # Day 3: (1.7 BTC * 16000) + (9.8 ETH * 1200) + 17040 EUR
    ]

    for timestamp, value, expected_ts, expected_val in zip(
        result['times'],
        result['values'],
        expected_timestamps,
        expected_values,
        strict=True,
    ):
        assert timestamp == expected_ts
        assert FVal(value) == expected_val

    # now, ignore an asset and see the result is expected.
    with db.user_write() as write_cursor:
        db.add_to_ignored_assets(
            write_cursor=write_cursor,
            asset=A_BTC,
        )

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalnetvalueresource',
        ),
        json={
            'from_timestamp': START_TS,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['missing_prices']) == 0
    assert 'last_group_identifier' not in result
    assert len(result['times']) == len(result['values']) == 3
    assert all(ts in result['times'] for ts in expected_timestamps[::2])

    # Expected values after ignoring BTC
    expected_values_ignored = [
        FVal('32000'),  # Day 1: (10 ETH * 1200) + 20000 EUR
        FVal('28800.0'),  # Day 2: (10 ETH * 1200) + (20000 - 3200) EUR = 28800
        FVal('28800.0'),  # Day 3: (9.8 ETH * 1200 = 11760) + (16800 + 240 = 17040) EUR = 28800
    ]
    for timestamp, value, expected_ts, expected_val in zip(
        result['times'],
        result['values'],
        expected_timestamps,
        expected_values_ignored,
        strict=True,
    ):
        assert timestamp == expected_ts
        assert FVal(value) == expected_val


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_historical_netvalue_missing_prices(
        rotkehlchen_api_server: 'APIServer',
        globaldb: 'GlobalDBHandler',
        setup_historical_data: None,
) -> None:
    main_currency = A_EUR
    eth_price = Price(FVal('1200.0'))

    for offset in range(3):
        day_ts = timestamp_to_daystart_timestamp(Timestamp(START_TS + DAY_IN_SECONDS * offset))
        globaldb.add_historical_prices(entries=[
            HistoricalPrice(
                from_asset=A_ETH,
                to_asset=main_currency,
                source=HistoricalPriceOracle.CRYPTOCOMPARE,
                timestamp=day_ts,
                price=eth_price,
            ),
        ])

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalnetvalueresource',
        ),
        json={
            'from_timestamp': START_TS,
            'to_timestamp': START_TS + DAY_IN_SECONDS * 3,
        },
    )
    result = assert_proper_sync_response_with_result(response)

    # Check missing prices are reported
    assert 'last_group_identifier' not in result
    assert len(result['missing_prices']) > 0
    assert all(
        entry[0] == A_BTC.identifier
        for entry in result['missing_prices']
    )

    # Net value should only include ETH
    day1_ts = timestamp_to_daystart_timestamp(START_TS)
    assert result['times'][0] == day1_ts
    assert FVal(result['values'][0]) == FVal('10') * eth_price


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_historical_netvalue_with_negative_amount(
        rotkehlchen_api_server: 'APIServer',
        setup_historical_data: None,
        globaldb: 'GlobalDBHandler',
) -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
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
            timestamp=ts_sec_to_ms(Timestamp(START_TS + DAY_IN_SECONDS * 4)),
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

    main_currency = A_EUR
    btc_price = Price(FVal('16000.0'))
    eth_price = Price(FVal('1200.0'))

    for offset in range(3):
        globaldb.add_historical_prices(entries=[
            HistoricalPrice(
                from_asset=A_BTC,
                to_asset=main_currency,
                source=HistoricalPriceOracle.CRYPTOCOMPARE,
                timestamp=(ts := Timestamp(START_TS + (DAY_IN_SECONDS * offset))),
                price=btc_price,
            ),
            HistoricalPrice(
                from_asset=A_ETH,
                to_asset=main_currency,
                source=HistoricalPriceOracle.CRYPTOCOMPARE,
                timestamp=ts,
                price=eth_price,
            ),
        ])

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalnetvalueresource',
        ),
        json={
            'from_timestamp': START_TS,
            'to_timestamp': START_TS + DAY_IN_SECONDS * 6,
        },
    )
    result = assert_proper_sync_response_with_result(response)

    assert 'last_group_identifier' in result
    assert len(result['missing_prices']) == 0
    assert len(result['times']) == len(result['values']) == 2
    assert all(ts in result['times'] for ts in (
        timestamp_to_daystart_timestamp(START_TS),
        timestamp_to_daystart_timestamp(Timestamp(START_TS + DAY_IN_SECONDS * 2)),
    ))


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
