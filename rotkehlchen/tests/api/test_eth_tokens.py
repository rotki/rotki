from http import HTTPStatus

import pytest
import requests
from typing_extensions import Literal

from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response
from rotkehlchen.tests.utils.blockchain import assert_eth_balances_result
from rotkehlchen.tests.utils.constants import A_GNO, A_RDN
from rotkehlchen.tests.utils.rotkehlchen import setup_balances


@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN, A_GNO]])
def test_query_ethereum_tokens_info(rotkehlchen_api_server):
    """Test that the rest api endpoint to query information about ethereum tokens works fine"""
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ))

    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    # There should be 2 keys in the result dict
    assert len(data['result']) == 2
    all_tokens = data['result']['all_eth_tokens']
    assert isinstance(all_tokens, list)
    for entry in all_tokens:
        assert len(entry) == 4
        assert entry['address'] is not None
        assert entry['symbol'] is not None
        assert entry['name'] is not None
        assert entry['decimal'] >= 0 and entry['decimal'] <= 18

    assert data['result']['owned_eth_tokens'] == ['RDN', 'GNO']


@pytest.mark.parametrize('owned_eth_tokens', [[A_DAI, A_GNO]])
@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_adding_ethereum_tokens(
        rotkehlchen_api_server,
        ethereum_accounts,
        number_of_eth_accounts,
):
    """Test that the rest api endpoint to add new ethereum tokens works properly"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        token_balances={
            'RDN': ['0', '4000000'],
            'DAI': ['50000000', '0'],
            'MKR': ['0', '0'],
            'GNO': ['0', '0'],
        },
        btc_accounts=[],
    )

    # Add RDN and MKR as tracked tokens and make sure that the rdn balance checks out
    with setup.blockchain_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "ethereumtokensresource",
        ), json={'eth_tokens': ['RDN', 'MKR']})

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_eth_balances_result(
        rotki=rotki,
        json_data=json_data,
        eth_accounts=ethereum_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=False,
    )

    # And also query tokens to see that it's properly added to the tracked tokens
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ))
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert data['result']['owned_eth_tokens'] == ['DAI', 'GNO', 'RDN', 'MKR']


def check_modifying_eth_tokens_error_responses(
        rotkehlchen_api_server,
        method: Literal['put', 'delete'],
) -> None:
    """Convenience function to check error response of adding/removing ethereum token endpoints"""
    # See that omitting eth_tokens is an error
    response = getattr(requests, method)(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ), json={})
    assert_error_response(
        response=response,
        contained_in_msg="eth_tokens': ['Missing data for required field",
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # See that providing invalid type for eth_tokens is an error
    response = getattr(requests, method)(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ), json={'eth_tokens': {}})
    assert_error_response(
        response=response,
        contained_in_msg='Tried to initialize an asset out of a non-string identifier',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # See that providing invalid type for eth_tokens is an error
    response = getattr(requests, method)(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ), json={'eth_tokens': {}})
    assert_error_response(
        response=response,
        contained_in_msg='Tried to initialize an asset out of a non-string identifier',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # See that providing invalid type for a single eth token is an error
    response = getattr(requests, method)(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ), json={'eth_tokens': [55, 'RDN']})
    assert_error_response(
        response=response,
        contained_in_msg='Tried to initialize an asset out of a non-string identifier',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # See that providing invalid asset for a single eth token is an error
    response = getattr(requests, method)(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ), json={'eth_tokens': ['NOTATOKEN', 'RDN']})
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset NOTATOKEN provided.',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # See that providing a non-ethereum-token asset is an error
    response = getattr(requests, method)(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ), json={'eth_tokens': ['BTC', 'RDN']})
    assert_error_response(
        response=response,
        contained_in_msg='Tried to initialize a non Ethereum asset as Ethereum Token',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_adding_ethereum_tokens_errors(rotkehlchen_api_server):
    """Test that the rest api endpoint to add new ethereum tokens handles errors properly"""
    check_modifying_eth_tokens_error_responses(rotkehlchen_api_server, method='put')


@pytest.mark.parametrize('owned_eth_tokens', [[A_DAI, A_GNO, A_RDN]])
@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_removing_ethereum_tokens(
        rotkehlchen_api_server,
        ethereum_accounts,
        number_of_eth_accounts,
):
    """Test that the rest api endpoint to add new ethereum tokens works properly"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        token_balances={
            'RDN': ['0', '0'],
            'DAI': ['50000000', '0'],
            'GNO': ['0', '0'],
        },
        btc_accounts=[],
    )

    # Remove GNO and RDN as tracked tokens and make sure that the dai balance checks out
    with setup.blockchain_patch:
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            "ethereumtokensresource",
        ), json={'eth_tokens': ['GNO', 'RDN']})

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_eth_balances_result(
        rotki=rotki,
        json_data=json_data,
        eth_accounts=ethereum_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=False,
    )

    # And also query tokens to see that GNO and RDN are removed from tracked tokens
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ))
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert data['result']['owned_eth_tokens'] == ['DAI']


def test_removing_ethereum_tokens_errors(rotkehlchen_api_server):
    """Test that the rest api endpoint to remove ethereum tokens handles errors properly"""
    check_modifying_eth_tokens_error_responses(rotkehlchen_api_server, method='delete')
