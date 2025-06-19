import json
from contextlib import ExitStack
from http import HTTPStatus
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USDT
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.cryptocom import Cryptocom
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location, Timestamp


def test_name():
    exchange = Cryptocom('cryptocom1', 'a', b'a', object(), object())
    assert exchange.location == Location.CRYPTOCOM
    assert exchange.name == 'cryptocom1'


def test_api_query_response_handling():
    """Test proper processing of API responses"""
    exchange = Cryptocom('cryptocom1', 'a', b'a', object(), object())

    # Test successful response
    response = MockResponse(HTTPStatus.OK, text='{"code": 0, "result": {"data": []}}')
    result = exchange._process_response(response)
    assert result.code == 0
    assert result.result == {'data': []}

    # Test error response
    response = MockResponse(HTTPStatus.OK, text='{"code": 10003, "message": "Invalid API key"}')
    result = exchange._process_response(response)
    assert result.code == 10003
    assert result.message == 'Invalid API key'

    # Test invalid JSON
    response = MockResponse(HTTPStatus.OK, text='invalid json')
    with pytest.raises(RemoteError):
        exchange._process_response(response)


def test_query_balances(mock_cryptocom):
    """Test querying balances from Crypto.com"""
    def mock_api_query(method, options=None):
        if method == 'private/user-balance':
            response_data = {
                'code': 0,
                'result': {
                    'data': [
                        {
                            'currency': 'BTC',
                            'available': '0.5',
                            'order': '0.1',
                            'stake': '0',
                        },
                        {
                            'currency': 'ETH',
                            'available': '10.5',
                            'order': '0',
                            'stake': '0.5',
                        },
                        {
                            'currency': 'USDT',
                            'available': '1000',
                            'order': '0',
                            'stake': '0',
                        },
                    ],
                },
            }
            return MockResponse(HTTPStatus.OK, text=json.dumps(response_data))
        return MockResponse(HTTPStatus.OK, text='{"code": 0, "result": {}}')

    with ExitStack() as stack:
        stack.enter_context(patch.object(mock_cryptocom, '_api_query', side_effect=mock_api_query))
        stack.enter_context(patch(
            'rotkehlchen.inquirer.Inquirer.find_usd_price',
            side_effect=lambda asset: (
                FVal(30000) if asset == A_BTC
                else FVal(2000) if asset == A_ETH
                else FVal(1)
            ),
        ))

        balances, msg = mock_cryptocom.query_balances()
        assert msg == ''
        assert len(balances) == 3
        assert balances[A_BTC] == Balance(amount=FVal('0.6'), usd_value=FVal('18000'))
        assert balances[A_ETH] == Balance(amount=FVal('11'), usd_value=FVal('22000'))
        assert balances[A_USDT] == Balance(amount=FVal('1000'), usd_value=FVal('1000'))


def test_query_trades(mock_cryptocom):
    """Test querying trades from Crypto.com"""
    def mock_api_query(method, options=None):
        if method == 'private/get-trades':
            response_data = {
                'code': 0,
                'result': {
                    'data': [
                        {
                            'trade_id': '123456',
                            'instrument_name': 'BTC_USDT',
                            'side': 'BUY',
                            'traded_quantity': '0.5',
                            'traded_price': '30000',
                            'fee': '0.001',
                            'fee_currency': 'BTC',
                            'create_time': 1640000000000,
                        },
                        {
                            'trade_id': '123457',
                            'instrument_name': 'ETH_USDT',
                            'side': 'SELL',
                            'traded_quantity': '2',
                            'traded_price': '2000',
                            'fee': '4',
                            'fee_currency': 'USDT',
                            'create_time': 1640001000000,
                        },
                    ],
                },
            }
            return MockResponse(HTTPStatus.OK, text=json.dumps(response_data))
        return MockResponse(HTTPStatus.OK, text='{"code": 0, "result": {"data": []}}')

    with ExitStack() as stack:
        stack.enter_context(patch.object(mock_cryptocom, '_api_query', side_effect=mock_api_query))

        events, end_ts = mock_cryptocom.query_online_history_events(
            start_ts=Timestamp(1640000000),
            end_ts=Timestamp(1640002000),
        )

        assert end_ts == Timestamp(1640002000)
        # Each trade creates 2 swap events (spend and receive) + fee events
        assert len(events) == 6

        # Check first trade (BUY BTC with USDT)
        buy_events = [e for e in events if e.event_identifier.startswith('61cb2089')]
        assert len(buy_events) == 3  # spend, receive, fee
        spend_event = next(
            e for e in buy_events if e.event_subtype == HistoryEventSubType.SPEND
        )
        receive_event = next(
            e for e in buy_events if e.event_subtype == HistoryEventSubType.RECEIVE
        )

        assert spend_event.asset == A_USDT
        assert spend_event.amount == FVal('15000')  # 0.5 * 30000
        assert receive_event.asset == A_BTC
        assert receive_event.amount == FVal('0.5')

        # Check second trade (SELL ETH for USDT)
        sell_events = [e for e in events if e.event_identifier.startswith('7dcbb147')]
        assert len(sell_events) == 3  # spend, receive, fee
        spend_event = next(
            e for e in sell_events if e.event_subtype == HistoryEventSubType.SPEND
        )
        receive_event = next(
            e for e in sell_events if e.event_subtype == HistoryEventSubType.RECEIVE
        )

        assert spend_event.asset == A_ETH
        assert spend_event.amount == FVal('2')
        assert receive_event.asset == A_USDT
        assert receive_event.amount == FVal('4000')  # 2 * 2000


def test_query_deposits_withdrawals(mock_cryptocom):
    """Test querying deposits and withdrawals from Crypto.com"""
    def mock_api_query(method, options=None):
        if method == 'private/get-deposit-history':
            response_data = {
                'code': 0,
                'result': {
                    'data': [
                        {
                            'id': 'dep123',
                            'currency': 'BTC',
                            'amount': '1.5',
                            'fee': '0',
                            'address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
                            'txid': 'abc123',
                            'status': 'completed',
                            'transaction_type': 'deposit',
                            'update_time': 1640000000000,
                        },
                    ],
                },
            }
            return MockResponse(HTTPStatus.OK, text=json.dumps(response_data))
        elif method == 'private/get-withdrawal-history':
            response_data = {
                'code': 0,
                'result': {
                    'data': [
                        {
                            'id': 'with456',
                            'currency': 'ETH',
                            'amount': '5',
                            'fee': '0.01',
                            'address': '0x123...',
                            'txid': 'def456',
                            'status': 'completed',
                            'transaction_type': 'withdrawal',
                            'update_time': 1640001000000,
                        },
                    ],
                },
            }
            return MockResponse(HTTPStatus.OK, text=json.dumps(response_data))
        return MockResponse(HTTPStatus.OK, text='{"code": 0, "result": {"data": []}}')

    with ExitStack() as stack:
        stack.enter_context(patch.object(mock_cryptocom, '_api_query', side_effect=mock_api_query))

        events, end_ts = mock_cryptocom.query_online_history_events(
            start_ts=Timestamp(1640000000),
            end_ts=Timestamp(1640002000),
        )

        assert end_ts == Timestamp(1640002000)
        assert len(events) == 3  # deposit, withdrawal, withdrawal fee

        # Check deposit
        deposit = next(e for e in events if e.event_type == HistoryEventType.DEPOSIT)
        assert isinstance(deposit, AssetMovement)
        assert deposit.location == Location.CRYPTOCOM
        assert deposit.asset == A_BTC
        assert deposit.amount == FVal('1.5')
        # Check that we have a proper event identifier
        assert deposit.event_identifier is not None
        assert len(deposit.event_identifier) > 0

        # Check withdrawal
        withdrawal_events = [e for e in events if e.event_type == HistoryEventType.WITHDRAWAL]
        assert len(withdrawal_events) == 2  # withdrawal and fee are both withdrawal events
        withdrawal = next(
            e for e in withdrawal_events
            if e.event_subtype == HistoryEventSubType.REMOVE_ASSET
        )
        assert isinstance(withdrawal, AssetMovement)
        assert withdrawal.location == Location.CRYPTOCOM
        assert withdrawal.asset == A_ETH
        assert withdrawal.amount == FVal('5')

        # Check withdrawal fee
        fee_events = [e for e in events if e.event_subtype == HistoryEventSubType.FEE]
        assert len(fee_events) == 1
        fee_event = fee_events[0]
        assert fee_event.asset == A_ETH
        assert fee_event.amount == FVal('0.01')


def test_validate_api_key(mock_cryptocom):
    """Test API key validation"""
    # Test successful validation
    def mock_api_query_success(method, options=None):
        return MockResponse(HTTPStatus.OK, text='{"code": 0, "result": {"data": []}}')

    with patch.object(mock_cryptocom, '_api_query', side_effect=mock_api_query_success):
        result, msg = mock_cryptocom.validate_api_key()
        assert result is True
        assert msg == ''

    # Test failed validation
    def mock_api_query_fail(method, options=None):
        return MockResponse(HTTPStatus.OK, text='{"code": 10003, "message": "Invalid API key"}')

    with patch.object(mock_cryptocom, '_api_query', side_effect=mock_api_query_fail):
        result, msg = mock_cryptocom.validate_api_key()
        assert result is False
        assert 'Invalid API key' in msg
