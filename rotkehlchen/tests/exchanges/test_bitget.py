from http import HTTPStatus
from typing import Any
from unittest.mock import patch

import pytest

from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USDC, A_USDT
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.bitget import (
    BITGET_LAUNCH_TS,
    BITGET_MAX_HISTORY_WINDOW,
    BITGET_MAX_RESULTS,
    Bitget,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_BITGET
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms


def test_api_query_signs_path_and_returns_data(bitget_exchange: Bitget) -> None:
    response = MockResponse(HTTPStatus.OK, '{"code":"00000","msg":"success","data":[]}')
    with (
        patch('rotkehlchen.exchanges.bitget.ts_now_in_ms', return_value=123456789),
        patch.object(bitget_exchange, '_generate_signature', return_value='signature') as signer,
        patch.object(bitget_exchange.session, 'get', return_value=response) as get,
    ):
        assert bitget_exchange._api_query(
            '/api/v2/mix/account/accounts',
            {'productType': 'USDT-FUTURES'},
        ) == []

    signer.assert_called_once_with(
        '123456789',
        '/api/v2/mix/account/accounts?productType=USDT-FUTURES',
    )
    assert get.call_args.kwargs['headers'] == {
        'ACCESS-SIGN': 'signature',
        'ACCESS-TIMESTAMP': '123456789',
    }


def test_api_query_classifies_rejected_request(bitget_exchange: Bitget) -> None:
    with (
        patch.object(
            bitget_exchange.session,
            'get',
            return_value=MockResponse(
                HTTPStatus.OK,
                '{"code":"40009","msg":"sign signature error","data":null}',
            ),
        ),
        pytest.raises(RemoteError) as exc_info,
    ):
        bitget_exchange._api_query('/api/v2/spot/account/assets')

    assert exc_info.value.cause == FailureCause.REMOTE_REJECTED


def test_symbol_query_failure_is_propagated(bitget_exchange: Bitget) -> None:
    with (
        patch.object(
            bitget_exchange,
            '_api_query',
            side_effect=RemoteError('temporary failure', cause=FailureCause.NETWORK),
        ),
        pytest.raises(RemoteError, match='temporary failure'),
    ):
        bitget_exchange._query_spot_trades(
            start_ts=Timestamp(1699999900),
            end_ts=Timestamp(1700000100),
            event_queue=None,
        )


def test_query_balances(bitget_exchange: Bitget) -> None:
    responses: dict[tuple[str, str | None], list[dict[str, Any]]] = {
        ('/api/v2/spot/account/assets', None): [
            {
                'coin': 'BTC',
                'available': '1',
                'frozen': '0.2',
                'locked': '0.3',
                'limitAvailable': '99',
            },
            {'coin': 'ETH', 'available': '0', 'frozen': '0', 'locked': '0'},
        ],
        ('/api/v2/mix/account/accounts', 'USDT-FUTURES'): [
            {'assetMode': 'single', 'marginCoin': 'USDT', 'accountEquity': '4'},
        ],
        ('/api/v2/mix/account/accounts', 'COIN-FUTURES'): [
            {
                'assetMode': 'union',
                'assetList': [
                    {'coin': 'BTC', 'balance': '0.5'},
                    {'coin': 'ETH', 'balance': '2'},
                ],
            },
        ],
        ('/api/v2/mix/account/accounts', 'USDC-FUTURES'): [],
    }

    def mock_api_query(endpoint: str, options: dict[str, Any] | None = None) -> Any:
        return responses[endpoint, None if options is None else options.get('productType')]

    with (
        patch.object(bitget_exchange, '_api_query', side_effect=mock_api_query),
        patch.object(
            bitget_exchange,
            'balances_from_amounts',
            side_effect=lambda amounts: amounts,
        ),
    ):
        balances, message, cause = bitget_exchange.query_balances()

    assert message == ''
    assert cause is None
    assert balances == {
        A_BTC.resolve_to_asset_with_oracles(): FVal('2'),
        A_ETH.resolve_to_asset_with_oracles(): FVal('2'),
        A_USDT.resolve_to_asset_with_oracles(): FVal('4'),
    }


def test_paginated_query(bitget_exchange: Bitget) -> None:
    first_page = [{'tradeId': str(idx)} for idx in range(BITGET_MAX_RESULTS)]
    last_page = [{'tradeId': 'last'}]
    options_seen = []

    def mock_api_query(endpoint: str, options: dict[str, Any]) -> list[dict[str, str]]:
        options_seen.append((endpoint, options.copy()))
        return first_page if len(options_seen) == 1 else last_page

    with patch.object(bitget_exchange, '_api_query', side_effect=mock_api_query):
        assert bitget_exchange._paginated_query(
            endpoint='/api/v2/spot/trade/fills',
            options={'startTime': 1, 'endTime': 2},
            id_key='tradeId',
        ) == [*first_page, *last_page]

    assert options_seen == [
        (
            '/api/v2/spot/trade/fills',
            {'startTime': 1, 'endTime': 2, 'limit': BITGET_MAX_RESULTS},
        ),
        (
            '/api/v2/spot/trade/fills',
            {
                'startTime': 1,
                'endTime': 2,
                'limit': BITGET_MAX_RESULTS,
                'idLessThan': str(BITGET_MAX_RESULTS - 1),
            },
        ),
    ]


@pytest.mark.freeze_time('2025-01-01 00:00:00 GMT')
def test_spot_trades_are_limited_to_available_history(bitget_exchange: Bitget) -> None:
    bitget_exchange.first_connection_made = True
    with patch.object(bitget_exchange, '_paginated_query', return_value=[]) as query:
        assert bitget_exchange._query_spot_trades(
            start_ts=BITGET_LAUNCH_TS,
            end_ts=Timestamp(ts_now()),
            event_queue=None,
        ) == []

    assert query.call_args.args[1]['startTime'] == ts_sec_to_ms(Timestamp(
        ts_now() - BITGET_MAX_HISTORY_WINDOW,
    ))


@pytest.mark.freeze_time('2023-11-14 23:00:00 GMT')
def test_query_spot_trades(bitget_exchange: Bitget) -> None:
    bitget_exchange.first_connection_made = True
    bitget_exchange.symbols = {'ETHUSDC': (A_ETH.resolve_to_asset_with_oracles(), A_USDC.resolve_to_asset_with_oracles())}  # noqa: E501
    with patch.object(bitget_exchange, '_paginated_query', return_value=[{
        'symbol': 'ETHUSDC',
        'side': 'buy',
        'size': '2',
        'priceAvg': '3',
        'cTime': '1700000000000',
        'tradeId': 'trade-1',
        'feeDetail': {'feeCoin': 'USDC', 'totalFee': '-0.1'},
    }]):
        events = bitget_exchange._query_spot_trades(
            start_ts=Timestamp(1699999900),
            end_ts=Timestamp(1700000100),
            event_queue=None,
        )

    assert [(event.event_subtype, event.asset, event.amount) for event in events] == [
        (HistoryEventSubType.SPEND, A_USDC, FVal(6)),
        (HistoryEventSubType.RECEIVE, A_ETH, FVal(2)),
        (HistoryEventSubType.FEE, A_USDC, FVal('0.1')),
    ]
    assert all(event.location == LOCATION_BITGET for event in events)


@pytest.mark.parametrize(('event_type', 'endpoint', 'subtypes', 'amount'), [
    (
        HistoryEventType.DEPOSIT,
        '/api/v2/spot/wallet/deposit-records',
        [HistoryEventSubType.RECEIVE],
        FVal(5),
    ),
    (
        HistoryEventType.WITHDRAWAL,
        '/api/v2/spot/wallet/withdrawal-records',
        [HistoryEventSubType.SPEND, HistoryEventSubType.FEE],
        FVal('4.8'),
    ),
])
def test_query_movements(
        bitget_exchange: Bitget,
        event_type: HistoryEventType,
        endpoint: str,
        subtypes: list[HistoryEventSubType],
        amount: FVal,
) -> None:
    with patch.object(bitget_exchange, '_paginated_query', return_value=[{
        'coin': 'USDC',
        'status': 'success',
        'size': '5',
        'fee': '0.2',
        'uTime': '1700000000000',
        'orderId': 'movement-1',
        'tradeId': 'transaction-1',
        'toAddress': 'address-1',
    }]) as query:
        events = bitget_exchange._query_movements(
            start_ts=Timestamp(1699999900),
            end_ts=Timestamp(1700000100),
            event_type=event_type,
        )

    assert query.call_args.args[0] == endpoint
    assert [event.event_subtype for event in events] == subtypes
    assert events[0].asset == A_USDC
    assert events[0].amount == amount
    assert events[0].extra_data == {
        'address': 'address-1',
        'transaction_id': 'transaction-1',
    }


@pytest.mark.freeze_time('2025-01-01 00:00:00 GMT')
def test_query_margin_history(bitget_exchange: Bitget) -> None:
    position = {
        'positionId': 'position-1',
        'ctime': '1700000000000',
        'utime': '1700000100000',
        'pnl': '4',
        'totalFunding': '-0.5',
        'openFee': '-0.1',
        'closeFee': '-0.2',
        'marginCoin': 'USDT',
        'holdSide': 'long',
        'symbol': 'ETHUSDT',
        'marginMode': 'crossed',
    }
    with patch.object(
        bitget_exchange,
        '_paginated_query',
        side_effect=[[position], [], []],
    ) as query:
        positions = bitget_exchange.query_online_margin_history(
            start_ts=BITGET_LAUNCH_TS,
            end_ts=Timestamp(ts_now()),
        )

    assert len(positions) == 1
    assert positions[0].profit_loss == FVal('3.5')
    assert positions[0].fee == FVal('0.3')
    assert positions[0].pl_currency == A_USDT
    assert positions[0].notes == 'Long ETHUSDT crossed futures position'
    assert query.call_args_list[0].args[1]['startTime'] == ts_sec_to_ms(Timestamp(
        ts_now() - BITGET_MAX_HISTORY_WINDOW,
    ))


@pytest.mark.freeze_time('2025-01-01 00:00:00 GMT')
def test_query_margin_history_before_available_range(bitget_exchange: Bitget) -> None:
    with patch.object(bitget_exchange, '_paginated_query') as query:
        assert bitget_exchange.query_online_margin_history(
            start_ts=BITGET_LAUNCH_TS,
            end_ts=Timestamp(ts_now() - BITGET_MAX_HISTORY_WINDOW),
        ) == []

    query.assert_not_called()
