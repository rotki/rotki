import hmac
from hashlib import sha256
from unittest.mock import call, patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants.assets import A_BTC, A_USDT
from rotkehlchen.exchanges.coinex import API_MAX_LIMIT, Coinex, CoinexMarket
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.types import Location, Timestamp, TimestampMS


def test_name() -> None:
    exchange = Coinex('coinex', 'a', b'a', object(), object())
    assert exchange.location == Location.COINEX
    assert exchange.name == 'coinex'


def test_signature() -> None:
    exchange = Coinex('coinex', 'access', b'secret', object(), object())
    request_path = '/v2/spot/user-deals?market=BTCUSDT&market_type=SPOT&page=1&limit=100'
    timestamp = '1700490703564'
    assert exchange._generate_signature(
        method='GET',
        request_path=request_path,
        timestamp=timestamp,
    ) == hmac.new(
        b'secret',
        msg=f'GET{request_path}{timestamp}'.encode('latin-1'),
        digestmod=sha256,
    ).hexdigest().lower()


def test_api_query_headers() -> None:
    exchange = Coinex('coinex', 'access', b'secret', object(), object())

    def mock_get(url, **kwargs):  # pylint: disable=unused-argument
        headers = kwargs['headers']
        assert headers['X-COINEX-KEY'] == 'access'
        assert headers['X-COINEX-TIMESTAMP'] == '1700490703564'
        assert headers['X-COINEX-SIGN'] == exchange._generate_signature(
            method='GET',
            request_path='/v2/assets/spot/balance',
            timestamp='1700490703564',
        )

        class Response:
            status_code = 200
            text = '{"code": 0, "data": [], "message": "OK"}'

            @staticmethod
            def json():
                return {'code': 0, 'data': [], 'message': 'OK'}

        return Response()

    with (
        patch.object(exchange.session, 'get', side_effect=mock_get),
        patch('rotkehlchen.exchanges.coinex.ts_now_in_ms', return_value=1700490703564),
    ):
        assert exchange._api_query(endpoint='/assets/spot/balance') == []


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_balances(coinex_exchange: Coinex) -> None:
    with patch.object(coinex_exchange, '_api_query', return_value=[
        {'ccy': 'BTC', 'available': '1.1', 'frozen': '0.4'},
        {'ccy': 'USDT', 'available': '2', 'frozen': '0'},
        {'ccy': 'ETH', 'available': '0', 'frozen': '0'},
    ]):
        balances, msg = coinex_exchange.query_balances()

    assert msg == ''
    assert balances == {
        A_BTC: Balance(amount=FVal('1.5'), value=FVal('2.25')),
        A_USDT: Balance(amount=FVal('2'), value=FVal('3')),
    }


def test_query_asset_movements(coinex_exchange: Coinex) -> None:
    responses = iter([
        [
            {
                'deposit_id': 14270229,
                'created_at': 1637212022134,
                'tx_id': '0xdeposit',
                'ccy': 'USDT',
                'chain': 'CSC',
                'deposit_method': 'on_chain',
                'amount': '200',
                'actual_amount': '200',
                'to_address': '0xabc',
                'confirmations': 12,
                'status': 'finished',
                'remark': '',
            },
        ],
        [
            {
                'withdraw_id': 206,
                'created_at': 1637212023134,
                'ccy': 'USDT',
                'chain': 'CSC',
                'withdraw_method': 'on_chain',
                'amount': '1',
                'actual_amount': '0.9',
                'tx_fee': '0.1',
                'tx_id': '0xwithdraw',
                'to_address': '0xdef',
                'status': 'finished',
                'remark': '',
            },
        ],
    ])

    with patch.object(
            coinex_exchange,
            '_api_query',
            side_effect=lambda **kwargs: next(responses),
    ) as mock_api_query:
        deposits = coinex_exchange._query_asset_movements(
            movement_type='deposit',
            start_ts=Timestamp(1637212022),
            end_ts=Timestamp(1637212024),
        )
        withdrawals = coinex_exchange._query_asset_movements(
            movement_type='withdrawal',
            start_ts=Timestamp(1637212022),
            end_ts=Timestamp(1637212024),
        )

    assert mock_api_query.call_args_list[0].kwargs == {
        'endpoint': '/assets/deposit-history',
        'options': {'status': 'finished', 'page': 1, 'limit': API_MAX_LIMIT},
    }
    assert mock_api_query.call_args_list[1].kwargs == {
        'endpoint': '/assets/withdraw',
        'options': {'status': 'finished', 'page': 1, 'limit': API_MAX_LIMIT},
    }
    assert deposits + withdrawals == [
        AssetMovement(
            location=Location.COINEX,
            location_label='coinex',
            event_subtype=HistoryEventSubType.RECEIVE,
            timestamp=TimestampMS(1637212022134),
            asset=A_USDT,
            amount=FVal('200'),
            unique_id='deposit-14270229',
            extra_data={'address': '0xabc', 'transaction_id': '0xdeposit'},
        ), AssetMovement(
            location=Location.COINEX,
            location_label='coinex',
            event_subtype=HistoryEventSubType.SPEND,
            timestamp=TimestampMS(1637212023134),
            asset=A_USDT,
            amount=FVal('1'),
            unique_id='withdrawal-206',
            extra_data={'address': '0xdef', 'transaction_id': '0xwithdraw'},
        ), AssetMovement(
            location=Location.COINEX,
            location_label='coinex',
            event_subtype=HistoryEventSubType.FEE,
            timestamp=TimestampMS(1637212023134),
            asset=A_USDT,
            amount=FVal('0.1'),
            unique_id='withdrawal-206',
        ),
    ]


def test_query_trades(coinex_exchange: Coinex) -> None:
    market = CoinexMarket(
        market='BTCUSDT',
        base_asset_symbol='BTC',
        quote_asset_symbol='USDT',
        base_asset=A_BTC,
        quote_asset=A_USDT,
    )
    with (
        patch.object(coinex_exchange, '_query_markets', return_value=[market]),
        patch.object(coinex_exchange, '_api_query', return_value=[{
            'created_at': 1689152421692,
            'market': 'BTCUSDT',
            'side': 'buy',
            'order_id': 8678890,
            'filled_amount': '0.00000325',
            'filled_value': '0.0998348650',
            'base_fee': '0',
            'quote_fee': '0.0001',
        }]) as api_query,
    ):
        trades = coinex_exchange._query_trades(
            start_ts=Timestamp(1689152421),
            end_ts=Timestamp(1689152422),
        )

    assert api_query.call_args_list == [call(
        endpoint='/spot/finished-order',
        options={
            'market_type': 'SPOT',
            'start_time': 1689152421000,
            'end_time': 1689152422000,
            'page': 1,
            'limit': API_MAX_LIMIT,
        },
    )]
    group_identifier = create_group_identifier_from_unique_id(
        location=Location.COINEX,
        unique_id='trade-8678890',
    )
    assert trades == [
        SwapEvent(
            timestamp=TimestampMS(1689152421692),
            location=Location.COINEX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal('0.0998348650'),
            location_label='coinex',
            group_identifier=group_identifier,
        ), SwapEvent(
            timestamp=TimestampMS(1689152421692),
            location=Location.COINEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_BTC,
            amount=FVal('0.00000325'),
            location_label='coinex',
            group_identifier=group_identifier,
        ), SwapEvent(
            timestamp=TimestampMS(1689152421692),
            location=Location.COINEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDT,
            amount=FVal('0.0001'),
            location_label='coinex',
            group_identifier=group_identifier,
        ),
    ]
