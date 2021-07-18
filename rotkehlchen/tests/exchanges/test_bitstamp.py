import warnings as test_warnings
from datetime import datetime, timedelta
from http import HTTPStatus
from json.decoder import JSONDecodeError
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.converters import asset_from_bitstamp
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_LINK, A_USD
from rotkehlchen.errors import RemoteError, UnknownAsset
from rotkehlchen.exchanges.bitstamp import (
    API_ERR_AUTH_NONCE_CODE,
    API_ERR_AUTH_NONCE_MESSAGE,
    API_KEY_ERROR_CODE_ACTION,
    API_MAX_LIMIT,
    USER_TRANSACTION_MIN_SINCE_ID,
    USER_TRANSACTION_SORTING_MODE,
    Bitstamp,
)
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    AssetMovementCategory,
    Trade,
    TradeType,
)
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_GBP
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import Fee, Location, Timestamp
from rotkehlchen.utils.serialization import jsonloads_list


def test_name():
    exchange = Bitstamp('bitstamp1', 'a', b'a', object(), object())
    assert exchange.location == Location.BITSTAMP
    assert exchange.name == 'bitstamp1'


def test_bitstamp_exchange_assets_are_known(mock_bitstamp):
    request_url = f'{mock_bitstamp.base_uri}/v2/trading-pairs-info'
    try:
        response = requests.get(request_url)
    except requests.exceptions.RequestException as e:
        raise RemoteError(
            f'Bitstamp get request at {request_url} connection error: {str(e)}.',
        ) from e

    if response.status_code != 200:
        raise RemoteError(
            f'Bitstamp query responded with error status code: {response.status_code} '
            f'and text: {response.text}',
        )
    try:
        response_list = jsonloads_list(response.text)
    except JSONDecodeError as e:
        raise RemoteError(f'Bitstamp returned invalid JSON response: {response.text}') from e

    # Extract the unique symbols from the exchange pairs
    pairs = [raw_result.get('name') for raw_result in response_list]
    symbols = set()
    for pair in pairs:
        symbols.update(set(pair.split('/')))

    for symbol in symbols:
        try:
            asset_from_bitstamp(symbol)
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.asset_name} in {mock_bitstamp.name}. '
                f'Support for it has to be added',
            ))


def test_validate_api_key_invalid_json(mock_bitstamp):
    """Test when status code is not 200, an invalid JSON response is handled."""
    def mock_api_query_response(endpoint, method='', options=None):  # pylint: disable=unused-argument  # noqa: E501
        return MockResponse(HTTPStatus.FORBIDDEN, '{"key"}')

    with patch.object(mock_bitstamp, '_api_query', side_effect=mock_api_query_response):
        result, msg = mock_bitstamp.validate_api_key()
        assert result is False
        assert msg == 'Bitstamp returned invalid JSON response: {"key"}.'


def test_validate_api_key_err_auth_nonce(mock_bitstamp):
    """Test the error code related with the nonce authentication is properly handled"""
    def mock_api_query_response(endpoint, method='', options=None):  # pylint: disable=unused-argument  # noqa: E501
        return MockResponse(
            HTTPStatus.FORBIDDEN,
            f'{{"code": "{API_ERR_AUTH_NONCE_CODE}", "reason": "whatever"}}',
        )

    with patch.object(mock_bitstamp, '_api_query', side_effect=mock_api_query_response):
        result, msg = mock_bitstamp.query_balances()
        assert result is False
        assert msg == API_ERR_AUTH_NONCE_MESSAGE

        result, msg = mock_bitstamp.validate_api_key()
        assert result is False
        assert msg == API_ERR_AUTH_NONCE_MESSAGE

        movements = mock_bitstamp.query_online_deposits_withdrawals(0, 1)
        assert movements == []
        errors = mock_bitstamp.msg_aggregator.consume_errors()
        assert len(errors) == 1
        assert API_ERR_AUTH_NONCE_MESSAGE in errors[0]

        trades = mock_bitstamp.query_online_trade_history(0, 1)
        assert trades == []
        errors = mock_bitstamp.msg_aggregator.consume_errors()
        assert len(errors) == 1
        assert API_ERR_AUTH_NONCE_MESSAGE in errors[0]


@pytest.mark.parametrize('code', API_KEY_ERROR_CODE_ACTION.keys())
def test_validate_api_key_api_key_error_code(
        mock_bitstamp,
        code,
):
    """Test an error code related with the API key ones returns a tuple with
    False (result) and a user friendly message (reason,
    from API_KEY_ERROR_CODE_ACTION values).
    """
    def mock_api_query_response(endpoint):  # pylint: disable=unused-argument
        return MockResponse(
            HTTPStatus.FORBIDDEN,
            f'{{"code": "{code}", "reason": "whatever"}}',
        )

    with patch.object(mock_bitstamp, '_api_query', side_effect=mock_api_query_response):
        result, msg = mock_bitstamp.validate_api_key()

    assert result is False
    assert msg == API_KEY_ERROR_CODE_ACTION[code]


def test_validate_api_key_success(mock_bitstamp):
    """Test when status code is 200 the response is a tuple with True (result)
    and an empty message.
    """
    def mock_api_query_response(endpoint):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, '')

    with patch.object(mock_bitstamp, '_api_query', side_effect=mock_api_query_response):
        result, msg = mock_bitstamp.validate_api_key()

    assert result is True
    assert msg == ''


def test_query_balances_invalid_json(mock_bitstamp):
    """Test an invalid JSON response raises RemoteError.
    """
    def mock_api_query_response(endpoint):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, '{"key"}')

    with patch.object(mock_bitstamp, '_api_query', side_effect=mock_api_query_response):
        with pytest.raises(RemoteError):
            mock_bitstamp.query_balances()


@pytest.mark.parametrize('response, has_reason', (
    ('{"code": "APIXXX", "reason": "has reason"}', True),
    ('{"code": "APIXXX", "text": "has text"}', False),
))
def test_query_balances_non_related_error_code(
        mock_bitstamp,
        response,
        has_reason,
):
    """Test an error code unrelated with the system clock not synced one
    returns a tuple with None (result) and a message (reason, from 'reason'
    response value or `response.text`).
    """
    def mock_api_query_response(endpoint):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.FORBIDDEN, response)

    with patch.object(mock_bitstamp, '_api_query', side_effect=mock_api_query_response):
        result, msg = mock_bitstamp.query_balances()

    assert result is False
    exp_reason = 'has reason' if has_reason else 'has text'
    assert exp_reason in msg


def test_query_balances_skips_not_balance_entry(mock_bitstamp):
    """Test an entry that doesn't end with `_balance` is skipped
    """
    def mock_api_query_response(endpoint):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, '{"link_available": "1.00000000"}')

    with patch.object(mock_bitstamp, '_api_query', side_effect=mock_api_query_response):
        assert mock_bitstamp.query_balances() == ({}, '')


def test_query_balances_skipped_not_asset_entry(mock_bitstamp):
    """Test an entry that can't instantiate Asset is skipped
    """
    def mock_api_query_response(endpoint):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, '{"bbbrrrlink_balance": "1.00000000"}')

    with patch.object(mock_bitstamp, '_api_query', side_effect=mock_api_query_response):
        assert mock_bitstamp.query_balances() == ({}, '')


def test_query_balances_skips_inquirer_error(mock_bitstamp):
    """Test an entry that can't get its USD price because of a remote error is
    skipped
    """
    inquirer = MagicMock()
    inquirer.find_usd_price.side_effect = RemoteError('test')

    def mock_api_query_response(endpoint):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, '{"link_balance": "1.00000000"}')

    with patch('rotkehlchen.exchanges.bitstamp.Inquirer', return_value=inquirer):
        with patch.object(mock_bitstamp, '_api_query', side_effect=mock_api_query_response):
            assert mock_bitstamp.query_balances() == ({}, '')


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_balances_asset_balance(mock_bitstamp, inquirer):  # pylint: disable=unused-argument
    """Test an entry that can't get its USD price is skipped
    """
    balances_data = (
        """
        {
            "eth_available": "0.00000000",
            "eth_balance": "32.00000000",
            "eth_reserved": "0.00000000",
            "eth_withdrawal_fee": "0.04000000",
            "link_available": "0.00000000",
            "link_balance": "1000.00000000",
            "link_reserved": "0.00000000",
            "link_withdrawal_fee": "0.25000000",
            "xrp_available": "0.00000000",
            "xrp_balance": "0.00000000",
            "xrp_reserved": "0.00000000",
            "xrp_withdrawal_fee": "0.02000000"
        }
        """
    )

    def mock_api_query_response(endpoint):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, balances_data)

    with patch.object(mock_bitstamp, '_api_query', side_effect=mock_api_query_response):
        asset_balance, msg = mock_bitstamp.query_balances()
        assert asset_balance == {
            A_ETH: Balance(
                amount=FVal('32'),
                usd_value=FVal('48'),
            ),
            A_LINK: Balance(
                amount=FVal('1000'),
                usd_value=FVal('1500'),
            ),
        }
        assert msg == ''


def test_deserialize_trade_buy(mock_bitstamp):
    raw_trade = {
        'id': 2,
        'type': 2,
        'datetime': '2020-12-02 09:30:00',
        'btc': '0.50000000',
        'usd': '-10000.00000000',
        'btc_usd': '0.00005000',
        'fee': '20.00000000',
        'order_id': 2,
    }
    expected_trade = Trade(
        timestamp=1606901400,
        location=Location.BITSTAMP,
        base_asset=A_BTC,
        quote_asset=A_USD,
        trade_type=TradeType.BUY,
        amount=FVal('0.50000000'),
        rate=FVal('0.00005000'),
        fee=FVal('20.00000000'),
        fee_currency=A_USD,
        link='2',
        notes='',
    )
    trade = mock_bitstamp._deserialize_trade(raw_trade)
    assert trade == expected_trade

    raw_trade = {
        'id': 2,
        'type': 2,
        'datetime': '2019-04-16 08:09:05.149343',
        'btc': '0.00060000',
        'usd': '0',
        'btc_eur': '8364.0',
        'eur': '-5.02',
        'fee': '0.02',
        'order_id': 2,
    }
    expected_trade = Trade(
        timestamp=1555402145,
        location=Location.BITSTAMP,
        base_asset=A_BTC,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=FVal('0.0006'),
        rate=FVal('8364.0'),
        fee=FVal('0.02'),
        fee_currency=A_EUR,
        link='2',
        notes='',
    )
    trade = mock_bitstamp._deserialize_trade(raw_trade)
    assert trade == expected_trade

    raw_trade = {
        'id': 15,
        'type': 2,
        'datetime': '2019-04-15 16:19:14.826000',
        'btc': '0',
        'usd': '-7.70998',
        'eur_usd': '1.12124',
        'eur': '6.87630',
        'fee': '0.02',
        'order_id': 15,
    }
    expected_trade = Trade(
        timestamp=1555345154,
        location=Location.BITSTAMP,
        base_asset=A_EUR,
        quote_asset=A_USD,
        trade_type=TradeType.BUY,
        amount=FVal('6.8763'),
        rate=FVal('1.12124'),
        fee=FVal('0.02'),
        fee_currency=A_USD,
        link='15',
        notes='',
    )
    trade = mock_bitstamp._deserialize_trade(raw_trade)
    assert trade == expected_trade


def test_deserialize_trade_sell(mock_bitstamp):
    raw_trade = {
        'id': 5,
        'type': 2,
        'datetime': '2020-12-03 11:30:00',
        'eur': '-1.00000000',
        'usd': '1.22000000',
        'eur_usd': '0.81967213',
        'fee': '0.00610000',
        'order_id': 3,
    }
    expected_trade = Trade(
        timestamp=1606995000,
        location=Location.BITSTAMP,
        base_asset=A_EUR,
        quote_asset=A_USD,
        trade_type=TradeType.SELL,
        amount=FVal('1'),
        rate=FVal('0.81967213'),
        fee=FVal('0.00610000'),
        fee_currency=A_USD,
        link='5',
        notes='',
    )
    trade = mock_bitstamp._deserialize_trade(raw_trade)
    assert trade == expected_trade

    raw_trade = {
        'id': 10,
        'type': 2,
        'datetime': '2019-06-25 21:41:08.802256',
        'btc': '-1.81213214',
        'usd': '0',
        'btc_eur': '10119.82',
        'eur': '18338.45',
        'fee': '40.35000',
        'order_id': 3,
    }
    expected_trade = Trade(
        timestamp=1561498868,
        location=Location.BITSTAMP,
        base_asset=A_BTC,
        quote_asset=A_EUR,
        trade_type=TradeType.SELL,
        amount=FVal('1.81213214'),
        rate=FVal('10119.82'),
        fee=FVal('40.35'),
        fee_currency=A_EUR,
        link='10',
        notes='',
    )
    trade = mock_bitstamp._deserialize_trade(raw_trade)
    assert trade == expected_trade


@pytest.mark.parametrize('option', ['limit', 'since_id', 'sort', 'offset'])
def test_api_query_paginated_user_transactions_required_options(mock_bitstamp, option):
    """Test calling the 'user_transactions' endpoint requires a set of specific
    options.
    """
    options = {
        'limit': API_MAX_LIMIT,
        'since_id': USER_TRANSACTION_MIN_SINCE_ID,
        'sort': USER_TRANSACTION_SORTING_MODE,
        'offset': 0,
    }
    del options[option]
    with pytest.raises(KeyError):
        mock_bitstamp._api_query_paginated(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1),
            options=options,
            case='trades',
        )


@pytest.mark.parametrize('option', ['limit', 'since_id', 'sort', 'offset'])
def test_api_query_paginated_user_transactions_required_options_values(mock_bitstamp, option):
    """Test calling the 'user_transactions' endpoint requires a set of specific
    options.
    """
    options = {
        'limit': API_MAX_LIMIT,
        'since_id': USER_TRANSACTION_MIN_SINCE_ID,
        'sort': USER_TRANSACTION_SORTING_MODE,
        'offset': 0,
    }
    options[option] = -1
    with pytest.raises(AssertionError):
        mock_bitstamp._api_query_paginated(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1),
            options=options,
            case='trades',
        )


def test_api_query_paginated_invalid_json(mock_bitstamp):
    """Test an invalid JSON response returns empty list.
    """
    options = {
        'since_id': USER_TRANSACTION_MIN_SINCE_ID,
        'limit': API_MAX_LIMIT,
        'sort': USER_TRANSACTION_SORTING_MODE,
        'offset': 0,
    }

    def mock_api_query_response(endpoint, method, options):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, '[{"key"}]')

    with patch.object(mock_bitstamp, '_api_query', side_effect=mock_api_query_response):
        result = mock_bitstamp._api_query_paginated(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1),
            options=options,
            case='trades',
        )
        assert result == []


@pytest.mark.parametrize('response', (
    '{"code": "APIXXX", "reason": "has reason"}',
    '{"code": "APIXXX", "text": "has text"}',
))
def test_api_query_paginated_non_related_error_code(mock_bitstamp, response):
    """Test an error code unrelated with the system clock not synced one
    returns a an empty list.
    """
    options = {
        'since_id': USER_TRANSACTION_MIN_SINCE_ID,
        'limit': API_MAX_LIMIT,
        'sort': USER_TRANSACTION_SORTING_MODE,
        'offset': 0,
    }

    def mock_api_query_response(endpoint, method, options):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.FORBIDDEN, response)

    with patch.object(mock_bitstamp, '_api_query', side_effect=mock_api_query_response):
        result = mock_bitstamp._api_query_paginated(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1),
            options=options,
            case='trades',
        )

    assert result == []


def test_api_query_paginated_skips_different_type_result(mock_bitstamp):
    """Test results whose type is not in `raw_result_type_filter` are skipped
    """
    options = {
        'since_id': USER_TRANSACTION_MIN_SINCE_ID,
        'limit': API_MAX_LIMIT,
        'sort': USER_TRANSACTION_SORTING_MODE,
        'offset': 0,
    }

    def mock_api_query_response(endpoint, method, options):  # pylint: disable=unused-argument
        return MockResponse(
            HTTPStatus.OK,
            '[{"type": "whatever"}, {"type": "23"}]',
        )

    with patch.object(mock_bitstamp, '_api_query', side_effect=mock_api_query_response):
        result = mock_bitstamp._api_query_paginated(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1),
            options=options,
            case='trades',
        )

    assert result == []


def test_api_query_paginated_stops_timestamp_gt_end_ts(mock_bitstamp):
    """Test the method stops processing results when a result timestamp is gt
    `end_ts`.
    """
    api_limit = 2
    now = datetime.now().replace(microsecond=0)
    gt_now = now + timedelta(seconds=1)
    now_ts = int(now.timestamp())
    gt_now_iso = gt_now.isoformat()
    options = {
        'since_id': USER_TRANSACTION_MIN_SINCE_ID,
        'limit': api_limit,
        'sort': USER_TRANSACTION_SORTING_MODE,
        'offset': 0,
    }
    expected_calls = [
        call(
            endpoint='user_transactions',
            method='post',
            options={
                'since_id': 1,
                'limit': 2,
                'sort': 'asc',
                'offset': 0,
            },
        ),
    ]

    def mock_api_query_response(endpoint, method, options):  # pylint: disable=unused-argument
        return MockResponse(
            HTTPStatus.OK,
            f'[{{"type": "14", "datetime": "{gt_now_iso}"}}]',
        )

    with patch(
        'rotkehlchen.exchanges.bitstamp.API_MAX_LIMIT',
        new_callable=MagicMock(return_value=api_limit),
    ):
        with patch.object(
            mock_bitstamp,
            '_api_query',
            side_effect=mock_api_query_response,
        ) as mock_api_query:
            result = mock_bitstamp._api_query_paginated(
                start_ts=Timestamp(0),
                end_ts=Timestamp(now_ts),
                options=options,
                case='trades',
            )
            assert mock_api_query.call_args_list == expected_calls
    assert result == []


@pytest.mark.freeze_time(datetime(2020, 12, 3, 12, 0, 0))
def test_api_query_paginated_trades_pagination(mock_bitstamp):
    """Test pagination logic for trades works as expected.

    First request: 2 results, 1 valid trade (id 2)
    Second request: 2 results, no trades
    Third request: 2 results, 1 valid trade (id 5) and 1 invalid trade (id 6)

    Trades with id 2 and 5 are expected to be returned.
    """
    # Not a trade
    user_transaction_1 = """
    {
        "id": 1,
        "type": "-1",
        "datetime": "2020-12-02 09:00:00"
    }
    """
    # First trade, buy BTC with USD, within timestamp range
    user_transaction_2 = """
    {
        "id": 2,
        "type": "2",
        "datetime": "2020-12-02 09:30:00",
        "btc": "0.50000000",
        "usd": "-10000.00000000",
        "btc_usd": "0.00005000",
        "fee": "20.00000000",
        "order_id": 2
    }
    """
    # Not a trade
    user_transaction_3 = """
    {
        "id": 3,
        "type": "-1",
        "datetime": "2020-12-02 18:00:00"
    }
    """
    # Not a trade
    user_transaction_4 = """
    {
        "id": 4,
        "type": "-1",
        "datetime": "2020-12-03 9:00:00"
    }
    """
    # Second trade, sell EUR for USD, within timestamp range
    user_transaction_5 = """
    {
        "id": 5,
        "type": "2",
        "datetime": "2020-12-03 11:30:00",
        "eur": "-1.00000000",
        "usd": "1.22000000",
        "eur_usd": "0.81967213",
        "fee": "0.00610000",
        "order_id": 3
    }
    """
    # Third trade, buy ETH with USDC, out of timestamp range
    user_transaction_6 = """
    {
        "id": 6,
        "type": "2",
        "datetime": "2020-12-03 12:00:01",
        "eth": "1.00000000",
        "usdc": "-750.00000000",
        "eth_usdc": "0.00133333",
        "fee": "3.75000000",
        "order_id": 1
    }
    """
    api_limit = 2
    now = datetime.now()
    now_ts = int(now.timestamp())
    options = {
        'since_id': USER_TRANSACTION_MIN_SINCE_ID,
        'limit': api_limit,
        'sort': USER_TRANSACTION_SORTING_MODE,
        'offset': 0,
    }
    expected_calls = [
        call(
            endpoint='user_transactions',
            method='post',
            options={
                'since_id': 1,
                'limit': 2,
                'sort': 'asc',
                'offset': 0,
            },
        ),
        call(
            endpoint='user_transactions',
            method='post',
            options={
                'since_id': 3,
                'limit': 2,
                'sort': 'asc',
                'offset': 0,
            },
        ),
        call(
            endpoint='user_transactions',
            method='post',
            options={
                'since_id': 3,
                'limit': 2,
                'sort': 'asc',
                'offset': 2,
            },
        ),
    ]

    def get_paginated_response():
        results = [
            f'[{user_transaction_1},{user_transaction_2}]',
            f'[{user_transaction_3},{user_transaction_4}]',
            f'[{user_transaction_5},{user_transaction_6}]',
        ]
        for result_ in results:
            yield result_

    def mock_api_query_response(endpoint, method, options):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, next(get_response))

    get_response = get_paginated_response()

    with patch(
        'rotkehlchen.exchanges.bitstamp.API_MAX_LIMIT',
        new_callable=MagicMock(return_value=api_limit),
    ):
        with patch.object(
            mock_bitstamp,
            '_api_query',
            side_effect=mock_api_query_response,
        ) as mock_api_query:
            result = mock_bitstamp._api_query_paginated(
                start_ts=Timestamp(0),
                end_ts=Timestamp(now_ts),
                options=options,
                case='trades',
            )
            assert mock_api_query.call_args_list == expected_calls

    expected_result = [
        Trade(
            timestamp=1606901400,
            location=Location.BITSTAMP,
            base_asset=A_BTC,
            quote_asset=A_USD,
            trade_type=TradeType.BUY,
            amount=FVal('0.50000000'),
            rate=FVal('0.00005000'),
            fee=FVal('20.00000000'),
            fee_currency=A_USD,
            link='2',
            notes='',
        ),
        Trade(
            timestamp=1606995000,
            location=Location.BITSTAMP,
            base_asset=A_EUR,
            quote_asset=A_USD,
            trade_type=TradeType.SELL,
            amount=FVal('1'),
            rate=FVal('0.81967213'),
            fee=FVal('0.00610000'),
            fee_currency=A_USD,
            link='5',
            notes='',
        ),
    ]
    assert result == expected_result


@pytest.mark.parametrize('start_ts, since_id', [(0, 1), (1, 6)])
def test_query_online_trade_history(mock_bitstamp, start_ts, since_id):
    """Test `since_id` value will change depending on `start_ts` value.
    Also tests `db_trades` are sorted by `link` (as int) in ascending mode.
    """
    trades = [
        Trade(
            timestamp=1606995000,
            location=Location.BITSTAMP,
            base_asset=A_EUR,
            quote_asset=A_USD,
            trade_type=TradeType.SELL,
            amount=FVal('1.22000000'),
            rate=FVal('0.81967213'),
            fee=FVal('0.00610000'),
            fee_currency=A_EUR,
            link='5',
            notes='',
        ),
        Trade(
            timestamp=1606901400,
            location=Location.BITSTAMP,
            base_asset=A_BTC,
            quote_asset=A_USD,
            trade_type=TradeType.BUY,
            amount=FVal('0.50000000'),
            rate=FVal('0.00005000'),
            fee=FVal('20.00000000'),
            fee_currency=A_USD,
            link='2',
            notes='',
        ),
    ]
    database = MagicMock()
    database.get_trades.return_value = trades

    expected_call = call(
        start_ts=start_ts,
        end_ts=2,
        options={
            'since_id': since_id,
            'limit': 1000,
            'sort': 'asc',
            'offset': 0,
        },
        case='trades',
    )
    with patch.object(mock_bitstamp, 'db', new_callable=MagicMock(return_value=database)):
        with patch.object(mock_bitstamp, '_api_query_paginated') as mock_api_query_paginated:
            mock_bitstamp.query_online_trade_history(
                start_ts=Timestamp(start_ts),
                end_ts=Timestamp(2),
            )
            assert mock_api_query_paginated.call_args == expected_call


def test_deserialize_asset_movement_deposit(mock_bitstamp):
    raw_movement = {
        'id': 2,
        'type': '0',
        'datetime': '2020-12-02 09:30:00',
        'btc': '0.50000000',
        'usd': '0.00000000',
        'btc_usd': '0.00',
        'fee': '0.00050000',
        'order_id': 2,
        'eur': '0.00',
    }
    asset = A_BTC
    movement = AssetMovement(
        timestamp=1606901400,
        location=Location.BITSTAMP,
        category=AssetMovementCategory.DEPOSIT,
        address=None,
        transaction_id=None,
        asset=asset,
        amount=FVal('0.5'),
        fee_asset=asset,
        fee=Fee(FVal('0.0005')),
        link='2',
    )
    expected_movement = mock_bitstamp._deserialize_asset_movement(raw_movement)
    assert movement == expected_movement

    raw_movement = {
        'id': 3,
        'type': '0',
        'datetime': '2018-03-21 06:46:06.559877',
        'btc': '0',
        'usd': '0.00000000',
        'btc_usd': '0.00',
        'fee': '0.1',
        'order_id': 2,
        'gbp': '1000.51',
    }
    asset = A_GBP
    movement = AssetMovement(
        timestamp=1521614766,
        location=Location.BITSTAMP,
        category=AssetMovementCategory.DEPOSIT,
        address=None,
        transaction_id=None,
        asset=asset,
        amount=FVal('1000.51'),
        fee_asset=asset,
        fee=Fee(FVal('0.1')),
        link='3',
    )
    expected_movement = mock_bitstamp._deserialize_asset_movement(raw_movement)
    assert movement == expected_movement


def test_deserialize_asset_movement_withdrawal(mock_bitstamp):
    raw_movement = {
        'id': 5,
        'type': '1',
        'datetime': '2020-12-02 09:30:00',
        'btc': '0.00000000',
        'usd': '-10000.00000000',
        'btc_usd': '0.00',
        'fee': '50.00000000',
        'order_id': 2,
        'eur': '0.00',
    }
    asset = A_USD
    movement = AssetMovement(
        timestamp=1606901400,
        location=Location.BITSTAMP,
        category=AssetMovementCategory.WITHDRAWAL,
        address=None,
        transaction_id=None,
        asset=asset,
        amount=FVal('10000'),
        fee_asset=asset,
        fee=Fee(FVal('50')),
        link='5',
    )
    expected_movement = mock_bitstamp._deserialize_asset_movement(raw_movement)
    assert movement == expected_movement

    raw_movement = {
        'id': 5,
        'type': '1',
        'datetime': '2018-03-21 06:46:06.559877',
        'btc': '0',
        'usd': '0',
        'btc_usd': '0.00',
        'fee': '0.1',
        'order_id': 2,
        'eur': '500',
    }
    asset = A_EUR
    movement = AssetMovement(
        timestamp=1521614766,
        location=Location.BITSTAMP,
        category=AssetMovementCategory.WITHDRAWAL,
        address=None,
        transaction_id=None,
        asset=asset,
        amount=FVal('500'),
        fee_asset=asset,
        fee=Fee(FVal('0.1')),
        link='5',
    )
    expected_movement = mock_bitstamp._deserialize_asset_movement(raw_movement)
    assert movement == expected_movement


@pytest.mark.parametrize('start_ts, since_id', [(0, 1), (1, 6)])
def test_query_online_deposits_withdrawals(mock_bitstamp, start_ts, since_id):
    """Test `since_id` value will change depending on `start_ts` value.
    Also tests `db_asset_movements` are sorted by `link` (as int) in ascending
    mode.
    """
    asset_btc = A_BTC
    asset_usd = A_USD
    movements = [
        AssetMovement(
            timestamp=1606901400,
            location=Location.BITSTAMP,
            category=AssetMovementCategory.WITHDRAWAL,
            address=None,
            transaction_id=None,
            asset=asset_usd,
            amount=FVal('10000'),
            fee_asset=asset_usd,
            fee=Fee(FVal('50')),
            link='5',
        ),
        AssetMovement(
            timestamp=1606901400,
            location=Location.BITSTAMP,
            category=AssetMovementCategory.DEPOSIT,
            address=None,
            transaction_id=None,
            asset=asset_btc,
            amount=FVal('0.5'),
            fee_asset=asset_btc,
            fee=Fee(FVal('0.0005')),
            link='2',
        ),
    ]
    database = MagicMock()
    database.get_asset_movements.return_value = movements

    expected_call = call(
        start_ts=start_ts,
        end_ts=2,
        options={
            'since_id': since_id,
            'limit': 1000,
            'sort': 'asc',
            'offset': 0,
        },
        case='asset_movements',
    )
    with patch.object(mock_bitstamp, 'db', new_callable=MagicMock(return_value=database)):
        with patch.object(mock_bitstamp, '_api_query_paginated') as mock_api_query_paginated:
            mock_bitstamp.query_online_deposits_withdrawals(
                start_ts=Timestamp(start_ts),
                end_ts=Timestamp(2),
            )
            assert mock_api_query_paginated.call_args == expected_call


@pytest.mark.freeze_time(datetime(2020, 12, 3, 12, 0, 0))
@pytest.mark.parametrize('bitstamp_api_key', ['123456'])
@pytest.mark.parametrize('bitstamp_api_secret', [str.encode('abcdefg')])
def test_api_query_request_headers_checks(mock_bitstamp):
    """Test request headers are not polluted by previous requests
    """
    options = {
        'limit': API_MAX_LIMIT,
        'since_id': USER_TRANSACTION_MIN_SINCE_ID,
        'sort': USER_TRANSACTION_SORTING_MODE,
        'offset': 0,
    }
    uuid = MagicMock()
    uuid.uuid4.return_value = 'hijklm'

    session = mock_bitstamp.session
    with patch('rotkehlchen.exchanges.bitstamp.uuid', new=uuid):
        mock_bitstamp._api_query(endpoint='balance')
        assert session.headers['X-Auth'] == 'BITSTAMP 123456'
        assert session.headers['X-Auth-Version'] == 'v2'
        assert session.headers['X-Auth-Signature'] == (
            'eb84d115027532cba9ebab8c692c488284c54551ab4601aa9ce6280187dc9c86'
        )
        assert session.headers['X-Auth-Nonce'] == 'hijklm'
        assert session.headers['X-Auth-Timestamp'] == '1606996800000'
        assert 'Content-Type' not in session.headers

        mock_bitstamp._api_query(endpoint='balance', options=options.copy())
        assert session.headers['X-Auth'] == 'BITSTAMP 123456'
        assert session.headers['X-Auth-Version'] == 'v2'
        assert session.headers['X-Auth-Signature'] == (
            '29728913d776144f0c8d522a58e77bb6c4492b25dbf7b3ebd41c4eb64c28cf0c'
        )
        assert session.headers['X-Auth-Nonce'] == 'hijklm'
        assert session.headers['X-Auth-Timestamp'] == '1606996800000'
        assert session.headers['Content-Type'] == 'application/x-www-form-urlencoded'

        mock_bitstamp._api_query(endpoint='balance')
        assert session.headers['X-Auth'] == 'BITSTAMP 123456'
        assert session.headers['X-Auth-Version'] == 'v2'
        assert session.headers['X-Auth-Signature'] == (
            'eb84d115027532cba9ebab8c692c488284c54551ab4601aa9ce6280187dc9c86'
        )
        assert session.headers['X-Auth-Nonce'] == 'hijklm'
        assert session.headers['X-Auth-Timestamp'] == '1606996800000'
        assert 'Content-Type' not in session.headers
