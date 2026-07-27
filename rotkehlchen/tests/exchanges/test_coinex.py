import hmac
import logging
from hashlib import sha256
from typing import TYPE_CHECKING
from unittest.mock import call, patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_USDT
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.coinex import API_MAX_LIMIT, Coinex, CoinexMarket
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.types import Location, LocationAssetMappingUpdateEntry, Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.globaldb.handler import GlobalDBHandler


def test_name(coinex_exchange: Coinex) -> None:
    assert coinex_exchange.location == Location.COINEX
    assert coinex_exchange.name == 'coinex'


def test_failed_history_query_saves_completed_source(coinex_exchange: Coinex) -> None:
    """Events from a completed source survive a later source failure."""
    event = HistoryEvent(
        group_identifier='incomplete-coinex-query',
        sequence_index=0,
        timestamp=TimestampMS(1000),
        location=Location.COINEX,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=ONE,
        location_label=coinex_exchange.name,
        notes='Saved when a later endpoint fails',
    )
    with (
        patch.object(
            coinex_exchange,
            '_query_asset_movements',
            side_effect=([event], RemoteError('withdrawals failed')),
        ),
        pytest.raises(RemoteError, match='withdrawals failed'),
    ):
        coinex_exchange.query_history_events()

    with coinex_exchange.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE group_identifier=?',
            (event.group_identifier,),
        ).fetchone()[0] == 1
        assert cursor.execute(
            'SELECT COUNT(*) FROM used_query_ranges WHERE name=?',
            (f'{Location.COINEX!s}_history_events_{coinex_exchange.name}',),
        ).fetchone()[0] == 0


def test_history_query_without_full_progress_saves_events(coinex_exchange: Coinex) -> None:
    event = HistoryEvent(
        group_identifier='no-coinex-progress',
        sequence_index=0,
        timestamp=TimestampMS(1000),
        location=Location.COINEX,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=ONE,
        location_label=coinex_exchange.name,
        notes='Saved while the incomplete range remains open',
    )
    with patch.object(
        coinex_exchange,
        'query_online_history_events',
        return_value=([event], Timestamp(0)),
    ):
        coinex_exchange.query_history_events()

    with coinex_exchange.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE group_identifier=?',
            (event.group_identifier,),
        ).fetchone()[0] == 1
        assert cursor.execute(
            'SELECT COUNT(*) FROM used_query_ranges WHERE name=?',
            (f'{Location.COINEX!s}_history_events_{coinex_exchange.name}',),
        ).fetchone()[0] == 0


def test_signature(coinex_exchange: Coinex) -> None:
    request_path = '/v2/spot/user-deals?market=BTCUSDT&market_type=SPOT&page=1&limit=100'
    timestamp = '1700490703564'
    assert coinex_exchange._generate_signature(
        method='GET',
        request_path=request_path,
        timestamp=timestamp,
    ) == hmac.new(
        coinex_exchange.secret,
        msg=f'GET{request_path}{timestamp}'.encode(),
        digestmod=sha256,
    ).hexdigest()


def test_api_query_headers(coinex_exchange: Coinex) -> None:
    assert coinex_exchange.session.headers['X-COINEX-KEY'] == coinex_exchange.api_key

    def mock_get(url, **kwargs):  # pylint: disable=unused-argument
        headers = kwargs['headers']
        assert headers['X-COINEX-TIMESTAMP'] == '1700490703564'
        assert headers['X-COINEX-SIGN'] == coinex_exchange._generate_signature(
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
        patch.object(coinex_exchange.session, 'get', side_effect=mock_get),
        patch('rotkehlchen.exchanges.coinex.ts_now_in_ms', return_value=1700490703564),
    ):
        assert coinex_exchange._api_query(
            endpoint='/assets/spot/balance',
        ) == {'code': 0, 'data': [], 'message': 'OK'}


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_balances(coinex_exchange: Coinex) -> None:
    with patch.object(coinex_exchange, '_api_query', return_value={'code': 0, 'data': [
        {'ccy': 'BTC', 'available': '1.1', 'frozen': '0.4'},
        {'ccy': 'USDT', 'available': '2', 'frozen': '0'},
        {'ccy': 'ETH', 'available': '0', 'frozen': '0'},
    ], 'message': 'OK'}):
        balances, msg = coinex_exchange.query_balances()

    assert msg == ''
    assert balances == {
        A_BTC: Balance(amount=FVal('1.5'), value=FVal('2.25')),
        A_USDT: Balance(amount=FVal('2'), value=FVal('3')),
    }


def test_query_asset_movements(coinex_exchange: Coinex) -> None:
    responses = iter([
        {'code': 0, 'data': [
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
            }, {  # deposit outside the queried range that has to be filtered out
                'deposit_id': 14270230,
                'created_at': 1637212025134,
                'tx_id': '0xdeposit2',
                'ccy': 'USDT',
                'chain': 'CSC',
                'deposit_method': 'on_chain',
                'amount': '5',
                'actual_amount': '5',
                'to_address': '0xabc',
                'confirmations': 12,
                'status': 'finished',
                'remark': '',
            },
        ], 'pagination': {'total': 2, 'has_next': False}, 'message': 'OK'},
        {'code': 0, 'data': [
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
        ], 'pagination': {'total': 1, 'has_next': False}, 'message': 'OK'},
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
            amount=FVal('0.9'),  # actual_amount, without the 0.1 fee
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


def test_query_trades(coinex_exchange: Coinex, globaldb: GlobalDBHandler) -> None:
    cet_asset = Asset('eip155:1/erc20:0x081F67aFA0cCF8c7B17540767BBe95DF2bA8D97F').resolve_to_asset_with_oracles()  # noqa: E501
    globaldb.add_location_asset_mappings([
        LocationAssetMappingUpdateEntry(
            location=Location.COINEX,
            location_symbol='CET',
            asset=cet_asset,
        ),
    ])
    market = CoinexMarket(
        market='BTCUSDT',
        base_asset_symbol='BTC',
        quote_asset_symbol='USDT',
        base_asset=A_BTC.resolve_to_asset_with_oracles(),
        quote_asset=A_USDT.resolve_to_asset_with_oracles(),
    )
    with (
        patch.object(coinex_exchange, '_query_markets', return_value=[market]),
        patch.object(coinex_exchange, '_api_query', return_value={'code': 0, 'data': [
            {
                'created_at': '1689152421692',  # str on purpose since docs examples show strings
                'market': 'BTCUSDT',
                'side': 'buy',
                'order_id': 8678890,
                'filled_amount': '0.00000325',
                'filled_value': '0.0998348650',
                'base_fee': '0',
                'quote_fee': '0.0001',
                'discount_fee': '0.0002',
            }, {  # trade outside the queried range that has to be filtered out
                'created_at': 1689152425000,
                'market': 'BTCUSDT',
                'side': 'sell',
                'order_id': 8678891,
                'filled_amount': '1',
                'filled_value': '30000',
                'base_fee': '0',
                'quote_fee': '30',
            }, {  # trade in a delisted/unknown market that has to be skipped
                'created_at': 1689152421700,
                'market': 'LUNAUSDT',
                'side': 'buy',
                'order_id': 8678892,
                'filled_amount': '1',
                'filled_value': '1',
                'base_fee': '0',
                'quote_fee': '0.001',
            },
        ], 'pagination': {'total': 3, 'has_next': False}, 'message': 'OK'}) as api_query,
    ):
        trades = coinex_exchange._query_trades(
            start_ts=Timestamp(1689152421),
            end_ts=Timestamp(1689152422),
        )

    assert api_query.call_args_list == [call(
        endpoint='/spot/finished-order',
        options={
            'market_type': 'SPOT',
            'page': 1,
            'limit': API_MAX_LIMIT,
        },
    )]
    assert coinex_exchange.msg_aggregator.consume_errors() == [
        'Skipped CoinEx trades in unknown or delisted markets: LUNAUSDT',
    ]
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
        ), SwapEvent(
            timestamp=TimestampMS(1689152421692),
            location=Location.COINEX,
            event_subtype=HistoryEventSubType.FEE,
            sequence_index=3,
            asset=cet_asset,
            amount=FVal('0.0002'),
            location_label='coinex',
            group_identifier=group_identifier,
        ),
    ]


def test_query_trades_skips_discount_fee_without_cet_mapping(
        coinex_exchange: Coinex,
        caplog: pytest.LogCaptureFixture,
) -> None:
    market = CoinexMarket(
        market='BTCUSDT',
        base_asset_symbol='BTC',
        quote_asset_symbol='USDT',
        base_asset=A_BTC.resolve_to_asset_with_oracles(),
        quote_asset=A_USDT.resolve_to_asset_with_oracles(),
    )
    with (
        caplog.at_level(logging.WARNING),
        patch.object(coinex_exchange, '_query_markets', return_value=[market]),
        patch(
            'rotkehlchen.exchanges.coinex.asset_from_coinex',
            side_effect=UnknownAsset('CET'),
        ) as mock_asset_from_coinex,
        patch.object(coinex_exchange, '_api_query', return_value={'code': 0, 'data': [{
            'created_at': 1689152421692,
            'market': 'BTCUSDT',
            'side': 'buy',
            'order_id': 8678890,
            'filled_amount': '0.00000325',
            'filled_value': '0.0998348650',
            'base_fee': '0.00000001',
            'quote_fee': '0.0001',
            'discount_fee': '0.0002',
        }], 'pagination': {'total': 1, 'has_next': False}, 'message': 'OK'}),
    ):
        trades = coinex_exchange._query_trades(
            start_ts=Timestamp(1689152421),
            end_ts=Timestamp(1689152422),
        )

    assert mock_asset_from_coinex.call_args_list == [call('CET')]
    assert (
        'Skipping CoinEx discount fee for order 8678890 because CET could not be resolved' in
        caplog.text
    )
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
            asset=A_BTC,
            amount=FVal('0.00000001'),
            location_label='coinex',
            group_identifier=group_identifier,
        ), SwapEvent(
            timestamp=TimestampMS(1689152421692),
            location=Location.COINEX,
            event_subtype=HistoryEventSubType.FEE,
            sequence_index=3,
            asset=A_USDT,
            amount=FVal('0.0001'),
            location_label='coinex',
            group_identifier=group_identifier,
        ),
    ]


def test_paginated_query_follows_has_next(coinex_exchange: Coinex) -> None:
    """Test that pagination follows the API's has_next flag
    even when pages are smaller than the requested limit.
    """
    def make_deposit(deposit_id: int) -> dict:
        return {
            'deposit_id': deposit_id,
            'created_at': 1637212022134,
            'tx_id': f'0xdeposit{deposit_id}',
            'ccy': 'USDT',
            'chain': 'CSC',
            'deposit_method': 'on_chain',
            'amount': '200',
            'actual_amount': '200',
            'to_address': '0xabc',
            'confirmations': 12,
            'status': 'finished',
            'remark': '',
        }

    responses = iter([
        {'code': 0, 'data': [make_deposit(1)], 'pagination': {'total': 2, 'has_next': True}, 'message': 'OK'},  # noqa: E501
        {'code': 0, 'data': [make_deposit(2)], 'pagination': {'total': 2, 'has_next': False}, 'message': 'OK'},  # noqa: E501
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

    assert [entry.kwargs['options']['page'] for entry in mock_api_query.call_args_list] == [1, 2]
    assert [movement.group_identifier for movement in deposits] == [
        create_group_identifier_from_unique_id(
            location=Location.COINEX,
            unique_id=f'deposit-{deposit_id}',
        ) for deposit_id in (1, 2)
    ]
