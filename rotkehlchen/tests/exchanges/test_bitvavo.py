from typing import Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants.assets import A_BTC, A_EUR
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.bitvavo import (
    BITVAVO_KEY_HEADER,
    BITVAVO_SIGNATURE_HEADER,
    BITVAVO_TIMESTAMP_HEADER,
    Bitvavo,
)
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret
from rotkehlchen.tests.utils.messages import consume_errors, consume_errors_and_unknown_assets
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ApiSecret, ExchangeAuthCredentials, Location, Timestamp

TIMESTAMP_MS = 1700490703564


def test_name(bitvavo_exchange: Bitvavo) -> None:
    assert bitvavo_exchange.location == Location.BITVAVO
    assert bitvavo_exchange.name == 'bitvavo'


def test_signature_matches_bitvavo_documentation(bitvavo_exchange: Bitvavo) -> None:
    """The worked example of https://docs.bitvavo.com/docs/rest-api/introduction/ with its
    published inputs and result, so the signing is checked against Bitvavo's own numbers.
    """
    bitvavo_exchange.secret = ApiSecret(b'bitvavo')
    assert bitvavo_exchange._generate_signature(
        method='POST',
        request_path='/v2/order',
        timestamp='1548172481125',
        body='{"market":"BTC-EUR","side":"buy","price":"5000","amount":"1.23","orderType":"limit"}',
    ) == '44d022723a20973a18f7ee97398b9fdd405d2d019c8d39e24b8cc0dcb39ca016'


def test_api_query_headers(bitvavo_exchange: Bitvavo) -> None:
    """The key travels in the session headers, the timestamp and signature per request, and
    the signature covers the path and query string exactly as requests puts them on the wire.
    """
    assert bitvavo_exchange.session.headers[BITVAVO_KEY_HEADER] == bitvavo_exchange.api_key

    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        assert (sent_path := requests.Request(
            method='GET',
            url=url,
            params=kwargs['params'],
        ).prepare().path_url) == '/v2/balance?symbol=BTC'
        headers = kwargs['headers']
        assert headers[BITVAVO_TIMESTAMP_HEADER] == str(TIMESTAMP_MS)
        assert headers[BITVAVO_SIGNATURE_HEADER] == bitvavo_exchange._generate_signature(
            method='GET',
            request_path=sent_path,
            timestamp=str(TIMESTAMP_MS),
        )
        return MockResponse(200, '[{"symbol": "BTC", "available": "1", "inOrder": "0"}]')

    with (
        patch.object(bitvavo_exchange.session, 'get', side_effect=mock_get),
        patch('rotkehlchen.exchanges.bitvavo.ts_now_in_ms', return_value=TIMESTAMP_MS),
    ):
        assert bitvavo_exchange._api_query(
            endpoint='/balance',
            options={'symbol': 'BTC'},
        ) == [{'symbol': 'BTC', 'available': '1', 'inOrder': '0'}]


@pytest.mark.parametrize(('response', 'expected_in_msg'), [
    (
        MockResponse(403, '{"errorCode": 311, "error": "Your API key does not have the View access permission."}'),  # noqa: E501
        'error code 311: Your API key does not have the View access permission.',
    ),
    (MockResponse(429, '{"errorCode": 105, "error": "You exceeded the rate limit."}'), 'rate limiting'),  # noqa: E501
    (
        MockResponse(502, '<html>bad gateway</html>'),
        'invalid JSON with HTTP status 502',
    ),
    (MockResponse(500, '{"unexpected": "shape"}'), 'HTTP status 500'),
])
def test_api_query_errors(
        bitvavo_exchange: Bitvavo,
        response: MockResponse,
        expected_in_msg: str,
) -> None:
    with (
        patch.object(bitvavo_exchange.session, 'get', return_value=response),
        pytest.raises(RemoteError, match=expected_in_msg),
    ):
        bitvavo_exchange._api_query(endpoint='/balance')


def test_validate_api_key(bitvavo_exchange: Bitvavo) -> None:
    with patch.object(bitvavo_exchange, '_api_query', return_value=[]):
        assert bitvavo_exchange.validate_api_key() == (True, '')

    with patch.object(
        bitvavo_exchange,
        '_api_query',
        side_effect=RemoteError('Bitvavo request at x failed with error code 305: inactive'),
    ):
        valid, msg = bitvavo_exchange.validate_api_key()

    assert valid is False
    assert 'error code 305' in msg


def test_edit_exchange_credentials_updates_key_header(bitvavo_exchange: Bitvavo) -> None:
    """A changed API key has to replace the one the session sends, otherwise requests keep
    authenticating with the old key while being signed with the new secret.
    """
    assert bitvavo_exchange.edit_exchange_credentials(ExchangeAuthCredentials(
        api_key=(new_key := make_api_key()),
        api_secret=(new_secret := make_api_secret()),
        passphrase=None,
    )) is True
    assert bitvavo_exchange.session.headers[BITVAVO_KEY_HEADER] == new_key
    assert bitvavo_exchange.secret == new_secret


def test_edit_exchange_credentials_without_changes(bitvavo_exchange: Bitvavo) -> None:
    old_key = bitvavo_exchange.api_key
    assert bitvavo_exchange.edit_exchange_credentials(ExchangeAuthCredentials(
        api_key=None,
        api_secret=None,
        passphrase=None,
    )) is False
    assert bitvavo_exchange.session.headers[BITVAVO_KEY_HEADER] == old_key


def test_first_connection(bitvavo_exchange: Bitvavo) -> None:
    bitvavo_exchange.first_connection()
    assert bitvavo_exchange.first_connection_made is True


def test_api_query_connection_error(bitvavo_exchange: Bitvavo) -> None:
    with (
        patch.object(
            bitvavo_exchange.session,
            'get',
            side_effect=requests.exceptions.ConnectionError('no route to host'),
        ),
        pytest.raises(RemoteError, match='connection error: no route to host'),
    ):
        bitvavo_exchange._api_query(endpoint='/balance')


def test_query_balances_unexpected_data(bitvavo_exchange: Bitvavo) -> None:
    with patch.object(bitvavo_exchange, '_api_query', return_value={'not': 'a list'}):
        balances, msg = bitvavo_exchange.query_balances()

    assert balances is None
    assert 'unexpected data' in msg


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_balances_skips_malformed_entries(bitvavo_exchange: Bitvavo) -> None:
    """A malformed entry is reported and skipped, the rest of the balances still count."""
    with patch.object(bitvavo_exchange, '_api_query', return_value=[
        {'symbol': 'BTC', 'available': '1', 'inOrder': '0'},
        {'symbol': 'ETH', 'available': 'not a number', 'inOrder': '0'},
        {'symbol': 'EUR'},  # amounts missing
    ]):
        balances, msg = bitvavo_exchange.query_balances()

    assert msg == ''
    assert balances == {A_BTC: Balance(amount=FVal('1'), value=FVal('1.5'))}
    assert consume_errors(bitvavo_exchange.msg_aggregator) == [
        'Failed to deserialize a Bitvavo balance entry. Check logs for details. Ignoring it.',
    ] * 2


def test_query_online_margin_history(bitvavo_exchange: Bitvavo) -> None:
    assert bitvavo_exchange.query_online_margin_history(
        start_ts=Timestamp(0),
        end_ts=Timestamp(1),
    ) == []


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_balances(bitvavo_exchange: Bitvavo) -> None:
    """available and inOrder are summed, zero balances and unknown assets are skipped."""
    with patch.object(bitvavo_exchange, '_api_query', return_value=[
        {'symbol': 'BTC', 'available': '1.1', 'inOrder': '0.4'},
        {'symbol': 'EUR', 'available': '250.5', 'inOrder': '0'},
        {'symbol': 'ETH', 'available': '0', 'inOrder': '0'},
        {'symbol': 'NOTAREALASSET', 'available': '5', 'inOrder': '0'},
    ]):
        balances, msg = bitvavo_exchange.query_balances()

    assert msg == ''
    assert balances == {
        A_BTC: Balance(amount=FVal('1.5'), value=FVal('2.25')),
        A_EUR: Balance(amount=FVal('250.5'), value=FVal('375.75')),
    }
    assert consume_errors_and_unknown_assets(bitvavo_exchange.msg_aggregator) == ([], ['NOTAREALASSET'])  # noqa: E501


def test_query_balances_remote_error(bitvavo_exchange: Bitvavo) -> None:
    with patch.object(bitvavo_exchange, '_api_query', side_effect=RemoteError('boom')):
        balances, msg = bitvavo_exchange.query_balances()

    assert balances is None
    assert msg == 'Failed to query Bitvavo balances due to a remote error: boom'
