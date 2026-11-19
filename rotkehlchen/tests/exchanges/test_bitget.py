from http import HTTPStatus
from typing import Any
from unittest.mock import patch

import pytest

from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USDC, A_USDT
from rotkehlchen.errors.asset import UnsupportedAsset
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.bitget import (
    BITGET_LAUNCH_TS,
    BITGET_MAX_HISTORY_WINDOW,
    BITGET_MAX_RESULTS,
    Bitget,
    BitgetAPIError,
    BitgetSymbol,
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

    assert isinstance(exc_info.value, BitgetAPIError)
    assert exc_info.value.code == '40009'
    assert exc_info.value.cause == FailureCause.REMOTE_REJECTED


def test_api_query_preserves_error_code_from_http_error(bitget_exchange: Bitget) -> None:
    with (
        patch.object(
            bitget_exchange.session,
            'get',
            return_value=MockResponse(
                HTTPStatus.BAD_REQUEST,
                '{"code":"40014","msg":"Incorrect permissions","data":null}',
            ),
        ),
        pytest.raises(BitgetAPIError) as exc_info,
    ):
        bitget_exchange._api_query('/api/v2/mix/account/accounts')

    assert exc_info.value.code == '40014'
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


def _futures_rejection(endpoint: str) -> RemoteError:
    return BitgetAPIError(
        f'Bitget request at {endpoint} failed with error code 40014: Incorrect permissions',
        code='40014',
        cause=FailureCause.REMOTE_REJECTED,
    )


def test_query_balances_skips_rejected_futures(bitget_exchange: Bitget) -> None:
    """A key without futures permission still reports its spot balances"""
    def mock_api_query(endpoint: str, options: dict[str, Any] | None = None) -> Any:
        if endpoint == '/api/v2/mix/account/accounts':
            raise _futures_rejection(endpoint)
        return [{'coin': 'BTC', 'available': '1', 'frozen': '0', 'locked': '0'}]

    with (
        patch.object(bitget_exchange, '_api_query', side_effect=mock_api_query) as query,
        patch.object(
            bitget_exchange,
            'balances_from_amounts',
            side_effect=lambda amounts: amounts,
        ),
    ):
        balances, message, cause = bitget_exchange.query_balances()

    assert query.call_count == 4  # spot + every futures product type
    assert (message, cause) == ('', None)
    assert balances == {A_BTC.resolve_to_asset_with_oracles(): FVal('1')}


def test_query_balances_fails_on_futures_network_error(bitget_exchange: Bitget) -> None:
    """A futures request that could not be answered fails the query instead of underreporting"""
    def mock_api_query(endpoint: str, options: dict[str, Any] | None = None) -> Any:
        if endpoint == '/api/v2/mix/account/accounts':
            raise RemoteError('timeout', cause=FailureCause.NETWORK)
        return [{'coin': 'BTC', 'available': '1', 'frozen': '0', 'locked': '0'}]

    with patch.object(bitget_exchange, '_api_query', side_effect=mock_api_query):
        balances, message, cause = bitget_exchange.query_balances()

    assert balances is None
    assert 'timeout' in message
    assert cause == FailureCause.NETWORK


def test_query_balances_propagates_other_futures_rejections(bitget_exchange: Bitget) -> None:
    def mock_api_query(endpoint: str, options: dict[str, Any] | None = None) -> Any:
        if endpoint == '/api/v2/mix/account/accounts':
            raise BitgetAPIError(
                'Apikey does not exist',
                code='40037',
                cause=FailureCause.REMOTE_REJECTED,
            )
        return [{'coin': 'BTC', 'available': '1', 'frozen': '0', 'locked': '0'}]

    with (
        patch.object(bitget_exchange, '_api_query', side_effect=mock_api_query),
        patch.object(
            bitget_exchange,
            'balances_from_amounts',
            side_effect=lambda amounts: amounts,
        ),
    ):
        balances, message, cause = bitget_exchange.query_balances()

    assert balances is None
    assert 'Apikey does not exist' in message
    assert cause == FailureCause.REMOTE_REJECTED


def test_query_balances_handles_null_union_asset_list(bitget_exchange: Bitget) -> None:
    responses = iter([
        [{'coin': 'BTC', 'available': '1', 'frozen': '0', 'locked': '0'}],
        [{'assetMode': 'union', 'assetList': None}],
        [],
        [],
    ])
    with (
        patch.object(bitget_exchange, '_api_query', side_effect=lambda *args: next(responses)),
        patch.object(
            bitget_exchange,
            'balances_from_amounts',
            side_effect=lambda amounts: amounts,
        ),
    ):
        balances, message, cause = bitget_exchange.query_balances()

    assert (message, cause) == ('', None)
    assert balances == {A_BTC.resolve_to_asset_with_oracles(): FVal('1')}


def test_query_balances_skips_unsupported_assets(bitget_exchange: Bitget) -> None:
    with (
        patch.object(
            bitget_exchange,
            '_api_query',
            side_effect=[
                [{'coin': 'UNSUPPORTED', 'available': '1', 'frozen': '0', 'locked': '0'}],
                [],
                [],
                [],
            ],
        ),
        patch(
            'rotkehlchen.exchanges.bitget.asset_from_bitget',
            side_effect=UnsupportedAsset('UNSUPPORTED'),
        ),
        patch.object(
            bitget_exchange,
            'balances_from_amounts',
            side_effect=lambda amounts: amounts,
        ),
    ):
        balances, message, cause = bitget_exchange.query_balances()

    assert balances == {}
    assert (message, cause) == ('', None)


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


def test_paginated_query_stops_on_repeated_cursor(bitget_exchange: Bitget) -> None:
    """A page whose cursor does not advance ends the pagination instead of looping forever"""
    with patch.object(
        bitget_exchange,
        '_api_query',
        side_effect=[(page := [{'tradeId': '1'}] * BITGET_MAX_RESULTS), page, []],
    ) as query:
        assert bitget_exchange._paginated_query(
            endpoint='/api/v2/spot/trade/fills',
            options={'symbol': 'ETHUSDC'},
            id_key='tradeId',
        ) == page * 2

    assert query.call_count == 2


@pytest.mark.parametrize('page', [None, {'list': None, 'endId': None}])
def test_paginated_query_handles_null_data(bitget_exchange: Bitget, page: Any) -> None:
    with patch.object(bitget_exchange, '_api_query', return_value=page):
        assert bitget_exchange._paginated_query(
            endpoint='/api/v2/mix/position/history-position',
            options={'productType': 'USDT-FUTURES'},
            id_key='positionId',
        ) == []


@pytest.mark.parametrize('page', ['unexpected', {'list': 'unexpected'}])
def test_paginated_query_rejects_unexpected_data(bitget_exchange: Bitget, page: Any) -> None:
    with (
        patch.object(bitget_exchange, '_api_query', return_value=page),
        pytest.raises(RemoteError) as exc_info,
    ):
        bitget_exchange._paginated_query(
            endpoint='/api/v2/mix/position/history-position',
            options={'productType': 'USDT-FUTURES'},
            id_key='positionId',
        )

    assert exc_info.value.cause == FailureCause.BAD_DATA


def test_api_query_rejects_non_object_json(bitget_exchange: Bitget) -> None:
    with (
        patch.object(
            bitget_exchange.session,
            'get',
            return_value=MockResponse(HTTPStatus.BAD_GATEWAY, '["unexpected"]'),
        ),
        pytest.raises(RemoteError) as exc_info,
    ):
        bitget_exchange._api_query('/api/v2/spot/account/assets')

    assert exc_info.value.cause == FailureCause.BAD_DATA


def test_api_query_classifies_invalid_server_response(bitget_exchange: Bitget) -> None:
    with (
        patch.object(
            bitget_exchange.session,
            'get',
            return_value=MockResponse(HTTPStatus.BAD_GATEWAY, 'invalid'),
        ),
        pytest.raises(RemoteError) as exc_info,
    ):
        bitget_exchange._api_query('/api/v2/spot/account/assets')

    assert exc_info.value.cause == FailureCause.NETWORK


@pytest.mark.freeze_time('2023-11-14 23:00:00 GMT')
def test_spot_trade_with_unknown_asset_is_reported(bitget_exchange: Bitget) -> None:
    """A pair with a coin rotki does not know is still queried and its fills are reported"""
    def mock_paginated_query(
            endpoint: str,
            options: dict[str, Any],
            id_key: str,
    ) -> list[dict[str, Any]]:
        if endpoint == '/api/v2/spot/account/bills':
            return [{'coin': 'NOTACOIN'}, {'coin': 'USDT'}]
        return [{
            'symbol': 'NOTACOINUSDT',
            'side': 'buy',
            'size': '2',
            'priceAvg': '3',
            'cTime': '1700000000000',
            'tradeId': 'trade-1',
        }]

    with (
        patch.object(
            bitget_exchange,
            '_query_symbols',
            return_value={'NOTACOINUSDT': BitgetSymbol(base_coin='NOTACOIN', quote_coin='USDT')},
        ),
        patch.object(bitget_exchange, '_paginated_query', side_effect=mock_paginated_query),
        patch.object(bitget_exchange, 'send_unknown_asset_message') as unknown_asset_message,
    ):
        assert bitget_exchange._query_spot_trades(
            start_ts=Timestamp(1699999900),
            end_ts=Timestamp(1700000100),
            event_queue=None,
        ) == []

    unknown_asset_message.assert_called_once_with('NOTACOIN', 'trade')


def test_query_symbols_keeps_unknown_coins(bitget_exchange: Bitget) -> None:
    with patch.object(bitget_exchange, '_api_query', return_value=[
        {'symbol': 'NOTACOINUSDT', 'baseCoin': 'NOTACOIN', 'quoteCoin': 'USDT'},
        {'symbol': 'BROKEN'},
    ]):
        assert bitget_exchange._query_symbols() == {
            'NOTACOINUSDT': BitgetSymbol(base_coin='NOTACOIN', quote_coin='USDT'),
        }


def test_query_symbols_rejects_null_data(bitget_exchange: Bitget) -> None:
    with (
        patch.object(bitget_exchange, '_api_query', return_value=None),
        pytest.raises(RemoteError) as exc_info,
    ):
        bitget_exchange._query_symbols()

    assert exc_info.value.cause == FailureCause.BAD_DATA


@pytest.mark.freeze_time('2025-01-01 00:00:00 GMT')
def test_spot_trades_are_limited_to_available_history(bitget_exchange: Bitget) -> None:
    with (
        patch.object(bitget_exchange, '_query_symbols', return_value={}),
        patch.object(bitget_exchange, '_paginated_query', return_value=[]) as query,
    ):
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
    """Fills are queried per symbol, only for pairs whose coins both appear in trade bills"""
    symbols = {
        'ETHUSDC': BitgetSymbol(base_coin='ETH', quote_coin='USDC'),
        'BTCUSDT': BitgetSymbol(base_coin='BTC', quote_coin='USDT'),
        'BTCUSDC': BitgetSymbol(base_coin='BTC', quote_coin='USDC'),
    }
    queries: list[tuple[str, dict[str, Any]]] = []

    def mock_paginated_query(
            endpoint: str,
            options: dict[str, Any],
            id_key: str,
    ) -> list[dict[str, Any]]:
        queries.append((endpoint, options))
        if endpoint == '/api/v2/spot/account/bills':
            return [{'coin': 'ETH', 'billId': '2'}, {'coin': 'USDC', 'billId': '1'}]
        return [{
            'symbol': 'ETHUSDC',
            'side': 'buy',
            'size': '2',
            'priceAvg': '3',
            'cTime': '1700000000000',
            'tradeId': 'trade-1',
            'feeDetail': {'feeCoin': 'USDC', 'totalFee': '-0.1'},
        }]

    with (
        patch.object(bitget_exchange, '_query_symbols', return_value=symbols),
        patch.object(bitget_exchange, '_paginated_query', side_effect=mock_paginated_query),
    ):
        events = bitget_exchange._query_spot_trades(
            start_ts=(start_ts := Timestamp(1699999900)),
            end_ts=(end_ts := Timestamp(1700000100)),
            event_queue=None,
        )

    assert queries == [
        (
            '/api/v2/spot/account/bills',
            {
                'groupType': 'transaction',
                'startTime': ts_sec_to_ms(start_ts),
                'endTime': ts_sec_to_ms(end_ts),
            },
        ),
        (
            '/api/v2/spot/trade/fills',
            {
                'symbol': 'ETHUSDC',
                'startTime': ts_sec_to_ms(start_ts),
                'endTime': ts_sec_to_ms(end_ts),
            },
        ),
    ]
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
def test_query_margin_history_clamps_future_end(bitget_exchange: Bitget) -> None:
    with patch.object(bitget_exchange, '_paginated_query', return_value=[]) as query:
        assert bitget_exchange.query_online_margin_history(
            start_ts=BITGET_LAUNCH_TS,
            end_ts=Timestamp(ts_now() + 1),
        ) == []

    assert query.call_count == 3
    for call in query.call_args_list:
        assert call.args[1]['startTime'] == ts_sec_to_ms(Timestamp(
            ts_now() - BITGET_MAX_HISTORY_WINDOW,
        ))
        assert call.args[1]['endTime'] == ts_sec_to_ms(Timestamp(ts_now()))


@pytest.mark.freeze_time('2025-01-01 00:00:00 GMT')
def test_query_margin_history_before_available_range(bitget_exchange: Bitget) -> None:
    with patch.object(bitget_exchange, '_paginated_query') as query:
        assert bitget_exchange.query_online_margin_history(
            start_ts=BITGET_LAUNCH_TS,
            end_ts=Timestamp(ts_now() - BITGET_MAX_HISTORY_WINDOW),
        ) == []

    query.assert_not_called()


@pytest.mark.freeze_time('2025-01-01 00:00:00 GMT')
def test_query_margin_history_skips_rejected_product_types(bitget_exchange: Bitget) -> None:
    """A rejected futures product type does not stop the remaining ones from being queried"""
    with patch.object(
        bitget_exchange,
        '_paginated_query',
        side_effect=[_futures_rejection('history-position'), [], []],
    ) as query:
        assert bitget_exchange.query_online_margin_history(
            start_ts=BITGET_LAUNCH_TS,
            end_ts=Timestamp(ts_now()),
        ) == []

    assert query.call_count == 3


@pytest.mark.freeze_time('2025-01-01 00:00:00 GMT')
def test_query_margin_history_propagates_network_error(bitget_exchange: Bitget) -> None:
    with (
        patch.object(
            bitget_exchange,
            '_paginated_query',
            side_effect=RemoteError('timeout', cause=FailureCause.NETWORK),
        ),
        pytest.raises(RemoteError, match='timeout'),
    ):
        bitget_exchange.query_online_margin_history(
            start_ts=BITGET_LAUNCH_TS,
            end_ts=Timestamp(ts_now()),
        )


@pytest.mark.freeze_time('2025-01-01 00:00:00 GMT')
def test_query_margin_history_propagates_other_rejections(bitget_exchange: Bitget) -> None:
    with (
        patch.object(
            bitget_exchange,
            '_paginated_query',
            side_effect=BitgetAPIError(
                'Apikey does not exist',
                code='40037',
                cause=FailureCause.REMOTE_REJECTED,
            ),
        ),
        pytest.raises(RemoteError, match='Apikey does not exist'),
    ):
        bitget_exchange.query_online_margin_history(
            start_ts=BITGET_LAUNCH_TS,
            end_ts=Timestamp(ts_now()),
        )
