from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants import DAY_IN_SECONDS
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer

START_TS = Timestamp(1672531200)


@pytest.fixture(name='setup_historical_data')
def fixture_setup_historical_data(rotkehlchen_api_server: 'APIServer') -> None:
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    events = [
        HistoryEvent(  # Day 1: Initial receive
            event_identifier='btc_receive_1',
            sequence_index=0,
            timestamp=ts_sec_to_ms(START_TS),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            location=Location.BLOCKCHAIN,
            asset=A_BTC,
            balance=Balance(amount=FVal('2')),
            notes='Receive BTC',
        ),
        HistoryEvent(  # another receive
            event_identifier='eth_receive_1',
            sequence_index=1,
            timestamp=ts_sec_to_ms(Timestamp(START_TS + 3000)),
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            location=Location.BLOCKCHAIN,
            asset=A_ETH,
            balance=Balance(amount=FVal('10')),
            notes='Receive ETH',
        ),
        HistoryEvent(  # Day 3: Partial spend
            event_identifier='btc_spend_1',
            sequence_index=2,
            timestamp=ts_sec_to_ms(Timestamp(START_TS + DAY_IN_SECONDS * 2)),
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            location=Location.BLOCKCHAIN,
            asset=A_BTC,
            balance=Balance(amount=FVal('0.5')),
            notes='BTC partial spend',
        ),
    ]
    with db.user_write() as write_cursor:
        DBHistoryEvents(database=db).add_history_events(
            write_cursor=write_cursor,
            history=events,
        )


@pytest.mark.vcr
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
            'timestamp': START_TS + DAY_IN_SECONDS,  # Day 2
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


@pytest.mark.vcr
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_get_historical_asset_balance(
        rotkehlchen_api_server: 'APIServer',
        setup_historical_data: None,
) -> None:
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
    assert result['amount'] == '1.5'  # 2 - 0.5
    assert result['price'] == '15806.226022787'


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