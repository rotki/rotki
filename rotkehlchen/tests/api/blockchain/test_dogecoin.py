from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.assets import A_DOGE, A_EUR
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)
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
from rotkehlchen.types import ChainType, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer

DOGE_KEY = SupportedBlockchain.DOGECOIN.serialize()


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('mocked_current_prices', [{(A_DOGE, A_EUR): FVal('0.2')}])
def test_add_query_and_remove_dogecoin_accounts(rotkehlchen_api_server: APIServer) -> None:
    """Test that dogecoin addresses can be added, have their balances queried and
    cached, and be removed again"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with (
        patch.object(
            rotki.chains_aggregator.dogecoin.sochain.session,
            'get',
            side_effect=mock_balances_by_url(
                balances={DOGE_ADDRESS_1: '62221.11119864', DOGE_ADDRESS_2: '10.5'},
                response_fn=lambda _address, confirmed: sochain_balance_response(confirmed),
            ),
        ) as get_mock,
        patch.object(rotki.chains_aggregator.dogecoin.dogechain.session, 'get') as dogechain_mock,
    ):
        assert assert_proper_sync_response_with_result(requests.put(
            api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain=DOGE_KEY),  # noqa: E501
            json={'accounts': [
                {'address': DOGE_ADDRESS_1, 'label': 'savings'},
                {'address': DOGE_ADDRESS_2},
            ]},
        )) == [DOGE_ADDRESS_1, DOGE_ADDRESS_2]
        result = assert_proper_sync_response_with_result(requests.post(
            api_url_for(rotkehlchen_api_server, 'named_blockchain_balances_resource', blockchain=DOGE_KEY),  # noqa: E501
        ))

    assert get_mock.call_count == 2
    assert dogechain_mock.call_count == 0
    assert result['per_account'] == {DOGE_KEY: {
        DOGE_ADDRESS_1: {'assets': {A_DOGE.identifier: {DEFAULT_BALANCE_LABEL: {
            'amount': '62221.11119864',
            'value': '12444.222239728',
        }}}, 'liabilities': {}},
        DOGE_ADDRESS_2: {'assets': {A_DOGE.identifier: {DEFAULT_BALANCE_LABEL: {
            'amount': '10.5',
            'value': '2.1',
        }}}, 'liabilities': {}},
    }}
    assert result['totals'] == {'assets': {A_DOGE.identifier: {DEFAULT_BALANCE_LABEL: {
        'amount': '62231.61119864',
        'value': '12446.322239728',
    }}}, 'liabilities': {}}

    # the cached balances are read back without querying SoChain again. Their value comes
    # from the cached prices, so only the amounts are compared.
    with patch.object(rotki.chains_aggregator.dogecoin.sochain.session, 'get') as get_mock:
        cached_result = assert_proper_sync_response_with_result(requests.get(
            api_url_for(rotkehlchen_api_server, 'named_blockchain_balances_resource', blockchain=DOGE_KEY),  # noqa: E501
            json={'only_cache': True},
        ))
    assert get_mock.call_count == 0
    assert {
        address: balances['assets'][A_DOGE.identifier][DEFAULT_BALANCE_LABEL]['amount']
        for address, balances in cached_result['per_account'][DOGE_KEY].items()
    } == {DOGE_ADDRESS_1: '62221.11119864', DOGE_ADDRESS_2: '10.5'}

    assert {
        account['address']: account
        for account in assert_proper_sync_response_with_result(requests.get(
            api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain=DOGE_KEY),  # noqa: E501
        ))
    } == {
        DOGE_ADDRESS_1: {'address': DOGE_ADDRESS_1, 'label': 'savings', 'tags': None},
        DOGE_ADDRESS_2: {'address': DOGE_ADDRESS_2, 'label': None, 'tags': None},
    }

    result = assert_proper_sync_response_with_result(requests.delete(
        api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain=DOGE_KEY),
        json={'accounts': [DOGE_ADDRESS_2]},
    ))
    assert set(result['per_account'][DOGE_KEY]) == {DOGE_ADDRESS_1}
    assert rotki.chains_aggregator.accounts.get(SupportedBlockchain.DOGECOIN) == (DOGE_ADDRESS_1,)
    with rotki.data.db.conn.read_ctx() as cursor:
        assert rotki.data.db.get_blockchain_accounts(cursor).doge == (DOGE_ADDRESS_1,)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_dogecoin_account_rejects_invalid_address(rotkehlchen_api_server: APIServer) -> None:
    """Test that only dogecoin addresses can be added to the dogecoin chain"""
    for address in (UNIT_BTC_ADDRESS1, 'DH5yaieqoZN36fDVciNyRueRGvGLR3mr7X'):
        assert_error_response(
            response=requests.put(
                api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain=DOGE_KEY),  # noqa: E501
                json={'accounts': [{'address': address}]},
            ),
            contained_in_msg=f'Given value {address} is not a valid dogecoin address',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    assert_error_response(  # and dogecoin xpubs are not supported
        response=requests.put(
            api_url_for(rotkehlchen_api_server, 'btcxpubresource', blockchain=DOGE_KEY),
            json={'xpub': 'xpub6CUGRUonZSQ4TWtTMmzXdrXDtypWKiKrhko4egpiMZbpiaQL2jkwSB1icqYh2cfDfVxdx4df189oLKnC5fSwqPfgyP3hooxujYzAu3fDVmz'},  # noqa: E501
        ),
        contained_in_msg='is not allowed in this endpoint',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    assert rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.accounts.get(
        SupportedBlockchain.DOGECOIN,
    ) == ()


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('doge_accounts', [[DOGE_ADDRESS_1]])
@pytest.mark.parametrize('mocked_current_prices', [{(A_DOGE, A_EUR): FVal('0.2')}])
def test_query_dogecoin_balances_falls_back_to_dogechain(
        rotkehlchen_api_server: APIServer,
) -> None:
    """Test that when SoChain's daily allowance is used up the balances come from Dogechain,
    without waiting for the allowance to reset"""
    dogecoin_manager = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.dogecoin
    with (
        patch.object(
            dogecoin_manager.sochain.session,
            'get',
            return_value=rate_limited_response('8460'),
        ),
        patch.object(
            dogecoin_manager.dogechain.session,
            'get',
            return_value=dogechain_address_response(DOGE_ADDRESS_1, '62221.11119864'),
        ) as dogechain_mock,
        patch('rotkehlchen.externalapis.sochain.cancellable_sleep') as sleep_mock,
    ):
        result = assert_proper_sync_response_with_result(requests.post(api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain=DOGE_KEY,
        )))

    assert dogechain_mock.call_count == 1
    assert sleep_mock.call_count == 0
    assert result['per_account'][DOGE_KEY][DOGE_ADDRESS_1]['assets'][A_DOGE.identifier] == {
        DEFAULT_BALANCE_LABEL: {'amount': '62221.11119864', 'value': '12444.222239728'},
    }


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('doge_accounts', [[DOGE_ADDRESS_1]])
def test_query_dogecoin_balances_fails_when_all_apis_fail(
        rotkehlchen_api_server: APIServer,
) -> None:
    """Test that a query neither SoChain nor Dogechain can answer fails with both reasons"""
    dogecoin_manager = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.dogecoin
    with (
        patch.object(
            dogecoin_manager.sochain.session,
            'get',
            return_value=rate_limited_response('8460'),
        ),
        patch.object(
            dogecoin_manager.dogechain.session,
            'get',
            return_value=MockResponse(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                text='{"status":"fail","data":{"error_message":"retry shortly"}}',
            ),
        ),
        patch('rotkehlchen.externalapis.sochain.cancellable_sleep') as sleep_mock,
    ):
        response = requests.post(api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain=DOGE_KEY,
        ))

    assert_error_response(
        response=response,
        contained_in_msg='External dogecoin request failed for all available APIs',
        status_code=HTTPStatus.BAD_GATEWAY,
    )
    assert 'asked to retry after 8460 seconds' in (message := response.json()['message'])
    assert 'failed with HTTP status code 503: retry shortly' in message
    assert sleep_mock.call_count == 0


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('doge_accounts', [[DOGE_ADDRESS_1, DOGE_ADDRESS_2]])
def test_dogecoin_chain_type_accounts(rotkehlchen_api_server: APIServer) -> None:
    """Test that dogecoin is listed as a supported chain of its own chain type and that
    its accounts can be labeled and removed through the chain type endpoints"""
    assert {
        'id': DOGE_KEY,
        'name': 'dogecoin',
        'type': ChainType.DOGECOIN.serialize(),
        'native_token': A_DOGE.identifier,
        'image': 'dogecoin.svg',
    } in assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'supportedchainsresource'),
    ))

    assert assert_proper_sync_response_with_result(requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'chaintypeaccountresource',
            chain_type=ChainType.DOGECOIN.serialize(),
        ),
        json={'accounts': [{'address': DOGE_ADDRESS_1, 'label': 'cold wallet'}]},
    )) is True
    assert {'address': DOGE_ADDRESS_1, 'label': 'cold wallet', 'tags': None} in assert_proper_sync_response_with_result(requests.get(  # noqa: E501
        api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain=DOGE_KEY),
    ))

    assert_proper_sync_response_with_result(requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'chaintypeaccountresource',
            chain_type=ChainType.DOGECOIN.serialize(),
        ),
        json={'accounts': [DOGE_ADDRESS_1, DOGE_ADDRESS_2]},
    ))
    assert rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.accounts.get(
        SupportedBlockchain.DOGECOIN,
    ) == ()
