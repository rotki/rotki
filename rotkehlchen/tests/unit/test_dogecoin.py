import re
from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.dogecoin.validation import is_valid_dogecoin_address
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.dogechain import DOGECHAIN_BASE_URL
from rotkehlchen.externalapis.sochain import RATE_LIMIT_RETRIES, SOCHAIN_BASE_URL
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.tests.utils.constants import A_DOGE
from rotkehlchen.tests.utils.dogecoin import (
    DOGE_ADDRESS_1,
    DOGE_ADDRESS_2,
    dogechain_address_response,
    mock_balances_by_url,
    rate_limited_response,
    sochain_balance_response,
)
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1
from rotkehlchen.tests.utils.mock import MockResponse

if TYPE_CHECKING:
    from rotkehlchen.chain.dogecoin.manager import DogecoinManager

# what SoChain and Dogechain answer, in the same envelope, for an address they can't look up
SOCHAIN_INVALID_ADDRESS = MockResponse(
    status_code=HTTPStatus.NOT_FOUND,
    text='{"status":"fail","data":{"error_message":"Unable to fetch address balance. Invalid address?"}}',  # noqa: E501
)
DOGECHAIN_INVALID_ADDRESS = MockResponse(
    status_code=HTTPStatus.BAD_REQUEST,
    text='{"status":"fail","data":{"error_message":"invalid address"}}',
)


def test_is_valid_dogecoin_address() -> None:
    """Test that only dogecoin mainnet P2PKH and P2SH addresses are accepted"""
    for address in (
        'DH5yaieqoZN36fDVciNyRueRGvGLR3mr7L',  # P2PKH
        '9t6e296CLrQL3mWDgcnuE8zbqJ9g9Xuprv',  # P2SH starting with 9
        'A4BYSMMJSnHCF1BXQ2P7EFEuK8mhsCPTrp',  # P2SH starting with A
    ):
        assert is_valid_dogecoin_address(address) is True

    for address in (
        'DH5yaieqoZN36fDVciNyRueRGvGLR3mr7X',  # wrong checksum
        UNIT_BTC_ADDRESS1,
        'LbGmfMhiY8ftvpPtwJGjcadLvamDR5q9de',  # litecoin P2PKH
        'nkEyfR5Sgrnr5zTXXZvT8jKUqNWXctGEWY',  # dogecoin testnet P2PKH
        'bc1qhkje0xfvhmgk6mvanxwy09n45df03tj3h3jtnf',
        '0x9531C059098e3d194fF87FebB587aB07B30B1306',
        'D0gecoin',  # not base58
        '',
    ):
        assert is_valid_dogecoin_address(address) is False


def test_query_balances(dogecoin_manager: DogecoinManager) -> None:
    """Test that each address gets its confirmed balance from SoChain, without Dogechain
    being asked"""
    with (
        patch.object(Inquirer, 'find_main_currency_price', return_value=FVal('0.2')),
        patch.object(dogecoin_manager.sochain.session, 'get', side_effect=[
            sochain_balance_response('62221.11119864'),
            sochain_balance_response('0.00000000'),
        ]) as sochain_mock,
        patch.object(dogecoin_manager.dogechain.session, 'get') as dogechain_mock,
    ):
        balances = dogecoin_manager.query_balances([DOGE_ADDRESS_1, DOGE_ADDRESS_2])

    assert [x.kwargs['url'] for x in sochain_mock.call_args_list] == [
        f'{SOCHAIN_BASE_URL}/balance/DOGE/{DOGE_ADDRESS_1}',
        f'{SOCHAIN_BASE_URL}/balance/DOGE/{DOGE_ADDRESS_2}',
    ]
    assert dogechain_mock.call_count == 0
    assert balances[DOGE_ADDRESS_1].assets == {A_DOGE: {DEFAULT_BALANCE_LABEL: Balance(
        amount=(amount := FVal('62221.11119864')),
        value=amount * FVal('0.2'),
    )}}
    assert balances[DOGE_ADDRESS_2].assets == {A_DOGE: {DEFAULT_BALANCE_LABEL: Balance(
        amount=ZERO,
        value=ZERO,
    )}}
    assert all(len(x.liabilities) == 0 for x in balances.values())


def test_sochain_waits_out_short_rate_limit(dogecoin_manager: DogecoinManager) -> None:
    """Test that a 429 asking to wait a second is waited out and the request repeated"""
    with (
        patch.object(dogecoin_manager.sochain.session, 'get', side_effect=[
            rate_limited_response('1'),
            sochain_balance_response('5.5'),
        ]) as get_mock,
        patch('rotkehlchen.externalapis.sochain.cancellable_sleep') as sleep_mock,
    ):
        assert dogecoin_manager.sochain.get_balance(DOGE_ADDRESS_1) == FVal('5.5')

    assert get_mock.call_count == 2
    sleep_mock.assert_called_once_with(1)


def test_sochain_fails_on_long_rate_limit(dogecoin_manager: DogecoinManager) -> None:
    """Test that a 429 asking to wait until the daily allowance resets fails the query
    right away instead of waiting for hours"""
    with (
        patch.object(dogecoin_manager.sochain.session, 'get', return_value=rate_limited_response('8460')),  # noqa: E501
        patch('rotkehlchen.externalapis.sochain.cancellable_sleep') as sleep_mock,
        pytest.raises(RemoteError, match='asked to retry after 8460 seconds') as exc_info,
    ):
        dogecoin_manager.sochain.get_balance(DOGE_ADDRESS_1)

    assert exc_info.value.error_code == HTTPStatus.TOO_MANY_REQUESTS
    assert sleep_mock.call_count == 0


def test_sochain_fails_when_rate_limit_persists(dogecoin_manager: DogecoinManager) -> None:
    """Test that short rate limit waits are retried only a limited number of times"""
    with (
        patch.object(dogecoin_manager.sochain.session, 'get', return_value=rate_limited_response('1')) as get_mock,  # noqa: E501
        patch('rotkehlchen.externalapis.sochain.cancellable_sleep') as sleep_mock,
        pytest.raises(RemoteError, match='was rate limited'),
    ):
        dogecoin_manager.sochain.get_balance(DOGE_ADDRESS_1)

    assert get_mock.call_count == RATE_LIMIT_RETRIES + 1
    assert sleep_mock.call_count == RATE_LIMIT_RETRIES


@pytest.mark.parametrize(('response', 'expected_error'), [
    (
        SOCHAIN_INVALID_ADDRESS,
        'failed with HTTP status code 404: Unable to fetch address balance. Invalid address?',
    ),
    (
        MockResponse(status_code=HTTPStatus.BAD_GATEWAY, text='<html>Bad gateway</html>'),
        'returned invalid JSON',
    ),
    (
        MockResponse(status_code=HTTPStatus.OK, text='{"status":"fail","data":{}}'),
        'failed with HTTP status code 200',
    ),
    (
        MockResponse(status_code=HTTPStatus.OK, text='{"status":"success","data":{"unconfirmed":"0"}}'),  # noqa: E501
        "missing key 'confirmed'",
    ),
    (
        MockResponse(status_code=HTTPStatus.OK, text='{"status":"success","data":{"confirmed":"abc"}}'),  # noqa: E501
        'Failed to deserialize value entry',
    ),
    (
        MockResponse(status_code=HTTPStatus.OK, text='["not", "a", "dict"]'),
        'returned invalid JSON',
    ),
])
def test_sochain_fails_on_bad_response(
        dogecoin_manager: DogecoinManager,
        response: MockResponse,
        expected_error: str,
) -> None:
    """Test that a failed or unexpected SoChain response fails the query with its reason"""
    with (
        patch.object(dogecoin_manager.sochain.session, 'get', return_value=response),
        pytest.raises(RemoteError, match=re.escape(expected_error)),
    ):
        dogecoin_manager.sochain.get_balance(DOGE_ADDRESS_1)


def test_dogechain_balance(dogecoin_manager: DogecoinManager) -> None:
    """Test that Dogechain's balance is the confirmed balance of the address summary and
    that its requests go through its rate limiter"""
    with (
        patch.object(
            dogecoin_manager.dogechain.session,
            'get',
            return_value=dogechain_address_response(DOGE_ADDRESS_1, '62221.11119864'),
        ) as get_mock,
        patch.object(dogecoin_manager.dogechain.rate_limiter, 'acquire') as acquire_mock,
    ):
        assert dogecoin_manager.dogechain.get_balance(DOGE_ADDRESS_1) == FVal('62221.11119864')

    assert get_mock.call_args.kwargs['url'] == f'{DOGECHAIN_BASE_URL}/address/{DOGE_ADDRESS_1}'
    assert acquire_mock.call_count == 1


@pytest.mark.parametrize(('response', 'expected_error'), [
    (DOGECHAIN_INVALID_ADDRESS, 'failed with HTTP status code 400: invalid address'),
    (
        MockResponse(status_code=HTTPStatus.OK, text='{"status":"success","data":{"address":"x"}}'),  # noqa: E501
        'no confirmed balance in the address summary',
    ),
    (
        MockResponse(
            status_code=HTTPStatus.OK,
            text='{"status":"success","data":{"summary":{"confirmed_balance":"abc"}}}',
        ),
        'Failed to deserialize value entry',
    ),
])
def test_dogechain_fails_on_bad_response(
        dogecoin_manager: DogecoinManager,
        response: MockResponse,
        expected_error: str,
) -> None:
    """Test that a failed or unexpected Dogechain response fails the query with its reason"""
    with (
        patch.object(dogecoin_manager.dogechain.session, 'get', return_value=response),
        pytest.raises(RemoteError, match=re.escape(expected_error)),
    ):
        dogecoin_manager.dogechain.get_balance(DOGE_ADDRESS_1)


@pytest.mark.parametrize('sochain_failure', [
    requests.exceptions.ConnectionError('Connection refused'),
    MockResponse(status_code=HTTPStatus.SERVICE_UNAVAILABLE, text='<html>Unavailable</html>'),
    MockResponse(status_code=HTTPStatus.OK, text='{"status":"success","data":{"unconfirmed":"0"}}'),  # noqa: E501
    rate_limited_response('8460'),  # the daily allowance of keyless requests is used up
])
def test_query_balances_falls_back_to_dogechain(
        dogecoin_manager: DogecoinManager,
        sochain_failure: MockResponse | requests.exceptions.ConnectionError,
) -> None:
    """Test that when SoChain fails the balances of all addresses come from Dogechain"""
    with (
        patch.object(Inquirer, 'find_main_currency_price', return_value=FVal('0.2')),
        patch.object(dogecoin_manager.sochain.session, 'get', side_effect=[
            sochain_balance_response('1'),
            sochain_failure,
        ]) as sochain_mock,
        patch.object(dogecoin_manager.dogechain.session, 'get', side_effect=mock_balances_by_url(
            balances={DOGE_ADDRESS_1: '62221.11119864', DOGE_ADDRESS_2: '10.5'},
            response_fn=dogechain_address_response,
        )) as dogechain_mock,
        patch('rotkehlchen.externalapis.sochain.cancellable_sleep') as sleep_mock,
    ):
        balances = dogecoin_manager.query_balances([DOGE_ADDRESS_1, DOGE_ADDRESS_2])

    assert sochain_mock.call_count == 2
    assert [x.kwargs['url'] for x in dogechain_mock.call_args_list] == [
        f'{DOGECHAIN_BASE_URL}/address/{DOGE_ADDRESS_1}',
        f'{DOGECHAIN_BASE_URL}/address/{DOGE_ADDRESS_2}',
    ]
    assert sleep_mock.call_count == 0
    assert {
        address: balance.assets[A_DOGE][DEFAULT_BALANCE_LABEL]
        for address, balance in balances.items()
    } == {
        DOGE_ADDRESS_1: Balance(amount=FVal('62221.11119864'), value=FVal('12444.222239728')),
        DOGE_ADDRESS_2: Balance(amount=FVal('10.5'), value=FVal('2.1')),
    }


def test_query_balances_fails_when_all_apis_fail(dogecoin_manager: DogecoinManager) -> None:
    """Test that when both SoChain and Dogechain fail the query fails with both reasons,
    so the balances of the last successful query are kept instead of partial ones"""
    with (
        patch.object(Inquirer, 'find_main_currency_price', return_value=FVal('0.2')),
        patch.object(dogecoin_manager.sochain.session, 'get', return_value=rate_limited_response('8460')),  # noqa: E501
        patch.object(dogecoin_manager.dogechain.session, 'get', side_effect=[
            dogechain_address_response(DOGE_ADDRESS_1, '1'),
            MockResponse(status_code=HTTPStatus.BAD_GATEWAY, text='{"status":"fail","data":{"error_message":"retry shortly"}}'),  # noqa: E501
        ]),
        pytest.raises(RemoteError) as exc_info,
    ):
        dogecoin_manager.query_balances([DOGE_ADDRESS_1, DOGE_ADDRESS_2])

    assert str(exc_info.value).startswith('External dogecoin request failed for all available APIs.')  # noqa: E501
    assert 'SoChain error is: "SoChain API request' in str(exc_info.value)
    assert 'asked to retry after 8460 seconds' in str(exc_info.value)
    assert 'Dogechain error is: "Dogechain API request' in str(exc_info.value)
    assert 'failed with HTTP status code 502: retry shortly' in str(exc_info.value)
