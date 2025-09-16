import json
from http import HTTPStatus
from typing import Final
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants.assets import A_BTC, A_USD, A_USDC, A_USDT
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.cryptocom import Cryptocom
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.tests.utils.constants import A_SOL
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now

EMPTY_BALANCES_RESPONSE: Final = {'id': 1, 'method': 'private/user-balance', 'code': 0, 'result': {'data': [{'total_available_balance': '0', 'total_margin_balance': '0', 'total_initial_margin': '0.00000000', 'total_haircut': '0.00000000', 'total_position_im': '0', 'total_maintenance_margin': '0', 'total_position_cost': '0', 'total_cash_balance': '0', 'total_session_unrealized_pnl': '0', 'instrument_name': 'USD', 'total_session_realized_pnl': '0', 'position_balances': [], 'credit_limits': [], 'total_effective_leverage': '0', 'position_limit': '0', 'used_position_limit': '0', 'total_borrow': '0', 'margin_score': '0', 'is_liquidating': False, 'has_risk': False, 'terminatable': True}]}}  # noqa: E501
BALANCES_RESPONSE: Final = {'id': 1, 'method': 'private/user-balance', 'code': 0, 'result': {'data': [{'total_available_balance': '98.70225541', 'total_margin_balance': '99.93901911', 'total_initial_margin': '1.23676370', 'total_haircut': '1.23676370', 'total_position_im': '0', 'total_maintenance_margin': '0.61838185', 'total_position_cost': '0', 'total_cash_balance': '99.93901911', 'total_collateral_value': '98.70225541', 'total_session_unrealized_pnl': '0', 'instrument_name': 'USD', 'total_session_realized_pnl': '0', 'position_balances': [{'quantity': '0.00016915', 'reserved_qty': '0', 'collateral_amount': '18.55145541', 'haircut': '0.0625', 'collateral_eligible': True, 'market_value': '19.78821911', 'max_withdrawal_balance': '0.00016915', 'instrument_name': 'BTC', 'hourly_interest_rate': '0'}, {'quantity': '80.1508', 'reserved_qty': '0', 'collateral_amount': '80.1508', 'haircut': '0', 'collateral_eligible': True, 'market_value': '80.1508', 'max_withdrawal_balance': '80.1508', 'instrument_name': 'USD', 'hourly_interest_rate': '0'}], 'credit_limits': [], 'total_effective_leverage': '0.198003', 'position_limit': '1998.78038226', 'used_position_limit': '19.78821912', 'total_borrow': '0', 'margin_score': '0', 'is_liquidating': False, 'has_risk': False, 'terminatable': True}]}}  # noqa: E501
DEPOSITS_RESPONSE: Final = {'id': 1, 'method': 'private/get-deposit-history', 'code': 0, 'result': {'deposit_list': [{'currency': 'USDC', 'fee': 0, 'create_time': 1755883811000, 'id': '8626791', 'update_time': 1755884808000, 'amount': 100, 'address': 'REDACTED', 'status': '1', 'txid': '0xa6fc2f080597f3a599d335a90eb6032872525dfcfdd8f5fabb49e76973418cdf/27'}]}}  # noqa: E501
WITHDRAWALS_RESPONSE: Final = {'id': 11, 'method': 'private/get-withdrawal-history', 'code': 0, 'result': {'withdrawal_list': [{'currency': 'USDT', 'client_wid': 'my_withdrawal_002', 'fee': 1.0, 'create_time': 1607063412000, 'id': '2220', 'update_time': 1607063460000, 'amount': 25, 'address': 'REDACTED', 'status': '1', 'txid': '', 'network_id': None}]}}  # noqa: E501
TRADES_RESPONSE: Final = {'id': 1, 'method': 'private/get-trades', 'code': 0, 'result': {'data': [{'account_id': 'REDACTED', 'event_date': '2025-08-22', 'journal_type': 'TRADING', 'side': 'BUY', 'instrument_name': 'SOL_USD', 'fees': '-0.00025', 'trade_id': '6242909981674131791', 'trade_match_id': '4311686018497604499', 'create_time': 1755892532063, 'traded_price': '199.17', 'traded_quantity': '0.050', 'fee_instrument_name': 'SOL', 'client_oid': 'REDACTED', 'taker_side': 'TAKER', 'order_id': '6142909939312653446', 'match_count': 1, 'create_time_ns': '1755892532063684632', 'transact_time_ns': '1755892532063937846'}, {'account_id': 'REDACTED', 'event_date': '2025-08-22', 'journal_type': 'TRADING', 'side': 'BUY', 'instrument_name': 'BTC_USD', 'fees': '-0.00000085', 'trade_id': '6242909981648392989', 'trade_match_id': '4311686018635217937', 'create_time': 1755885101119, 'traded_price': '116760.00', 'traded_quantity': '0.00017', 'fee_instrument_name': 'BTC', 'client_oid': 'REDACTED', 'taker_side': 'TAKER', 'order_id': '6142909939299440672', 'match_count': 1, 'create_time_ns': '1755885101119164986', 'transact_time_ns': '1755885101119383557'}]}}  # noqa: E501


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


def test_query_balances_empty_account(mock_cryptocom):
    """Test querying balances for an empty account."""
    with patch.object(
        target=mock_cryptocom,
        attribute='_api_query',
        return_value=MockResponse(HTTPStatus.OK, text=json.dumps(EMPTY_BALANCES_RESPONSE)),
    ):
        balances, msg = mock_cryptocom.query_balances()

    assert msg == ''
    assert len(balances) == 0


def test_query_balances(mock_cryptocom):
    """Test querying balances for an account with some balances."""
    with (patch.object(
        target=mock_cryptocom,
        attribute='_api_query',
        return_value=MockResponse(HTTPStatus.OK, text=json.dumps(BALANCES_RESPONSE)),
    ), patch(
        target='rotkehlchen.inquirer.Inquirer.find_usd_price',
        side_effect=lambda asset: (FVal(112000) if asset == A_BTC else FVal(1)),
    )):
        balances, msg = mock_cryptocom.query_balances()
        assert msg == ''
        assert len(balances) == 2
        assert balances[A_BTC] == Balance(amount=FVal('0.00016915'), usd_value=FVal('18.94480000'))
        assert balances[A_USD] == Balance(amount=FVal('80.1508'), usd_value=FVal('80.1508'))


def test_query_trades(mock_cryptocom):
    """Test querying trades from Crypto.com"""
    call_count = 0
    empty_result = {'code': 0, 'result': {'data': []}}

    def mock_api_query(method, options=None):
        nonlocal call_count

        if method == 'private/get-trades':
            response_data = TRADES_RESPONSE if call_count == 0 else empty_result
            call_count += 1
            return MockResponse(HTTPStatus.OK, text=json.dumps(response_data))
        return MockResponse(HTTPStatus.OK, text=json.dumps(empty_result))

    with (
        patch.object(mock_cryptocom, '_api_query', side_effect=mock_api_query),
        patch('rotkehlchen.exchanges.cryptocom.TRADES_LIMIT', new=1),
    ):
        events, _ = mock_cryptocom.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=ts_now(),
        )
        assert events == [SwapEvent(
            timestamp=TimestampMS(1755892532063),
            location=Location.CRYPTOCOM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USD,
            amount=FVal('9.95850'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.CRYPTOCOM,
                unique_id='6242909981674131791',
            ),
            location_label=mock_cryptocom.name,
        ), SwapEvent(
            timestamp=TimestampMS(1755892532063),
            location=Location.CRYPTOCOM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_SOL,
            amount=FVal('0.050'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.CRYPTOCOM,
                unique_id='6242909981674131791',
            ),
            location_label=mock_cryptocom.name,
        ), SwapEvent(
            timestamp=TimestampMS(1755892532063),
            location=Location.CRYPTOCOM,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_SOL,
            amount=FVal('0.00025'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.CRYPTOCOM,
                unique_id='6242909981674131791',
            ),
            location_label=mock_cryptocom.name,
        ), SwapEvent(
            timestamp=TimestampMS(1755885101119),
            location=Location.CRYPTOCOM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USD,
            amount=FVal('19.8492000'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.CRYPTOCOM,
                unique_id='6242909981648392989',
            ),
            location_label=mock_cryptocom.name,
        ), SwapEvent(
            timestamp=TimestampMS(1755885101119),
            location=Location.CRYPTOCOM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_BTC,
            amount=FVal('0.00017'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.CRYPTOCOM,
                unique_id='6242909981648392989',
            ),
            location_label=mock_cryptocom.name,
        ), SwapEvent(
            timestamp=TimestampMS(1755885101119),
            location=Location.CRYPTOCOM,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BTC,
            amount=FVal('0.00000085'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.CRYPTOCOM,
                unique_id='6242909981648392989',
            ),
            location_label=mock_cryptocom.name,
        )]


def test_query_deposits_withdrawals(mock_cryptocom):
    """Test querying deposits and withdrawals from Crypto.com"""
    def mock_api_query(method, options=None):
        if method == 'private/get-deposit-history':
            return MockResponse(HTTPStatus.OK, text=json.dumps(DEPOSITS_RESPONSE))
        elif method == 'private/get-withdrawal-history':
            return MockResponse(HTTPStatus.OK, text=json.dumps(WITHDRAWALS_RESPONSE))
        return MockResponse(HTTPStatus.OK, text='{"code": 0, "result": {"data": []}}')

    with patch.object(mock_cryptocom, '_api_query', side_effect=mock_api_query):
        events, _ = mock_cryptocom.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=ts_now(),
        )
        assert events == [AssetMovement(
            event_identifier='b8c8a7320bd804ebd989a2b602186716d217b0dfde736add740d13f709146239',
            timestamp=TimestampMS(1755883811000),
            location=Location.CRYPTOCOM,
            event_type=HistoryEventType.DEPOSIT,
            asset=A_USDC,
            amount=FVal(100),
            location_label=mock_cryptocom.name,
            extra_data={
                'reference': '8626791',
                'address': 'REDACTED',
                'transaction_id': '0xa6fc2f080597f3a599d335a90eb6032872525dfcfdd8f5fabb49e76973418cdf',  # noqa: E501
            },
        ), AssetMovement(
            event_identifier='36dc8fa45695e0fdbc31612faaf5841eb181e8e1a5139363fabe2ba7f182759f',
            timestamp=TimestampMS(1607063412000),
            location=Location.CRYPTOCOM,
            event_type=HistoryEventType.WITHDRAWAL,
            asset=A_USDT,
            amount=FVal(25),
            location_label=mock_cryptocom.name,
            extra_data={'reference': '2220', 'address': 'REDACTED', 'transaction_id': ''},
        ), AssetMovement(
            event_identifier='36dc8fa45695e0fdbc31612faaf5841eb181e8e1a5139363fabe2ba7f182759f',
            timestamp=TimestampMS(1607063412000),
            location=Location.CRYPTOCOM,
            event_type=HistoryEventType.WITHDRAWAL,
            asset=A_USDT,
            amount=FVal(1.0),
            location_label=mock_cryptocom.name,
            is_fee=True,
        )]


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
