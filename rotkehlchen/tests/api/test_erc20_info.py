from http import HTTPStatus

import pytest
import requests

from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_query_token_with_info(rotkehlchen_api_server):
    """Query DAI token to retrieve basic information"""

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfo',
        ), json={
            'address': string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
        },
    )

    result = assert_proper_response_with_result(response)
    assert result['decimals'] == 18
    assert result['symbol'] == 'DAI'
    assert result['name'] == 'Dai Stablecoin'

    # Test a contract without decimals/name/symbol methods
    response_2 = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfo',
        ), json={
            'address': string_to_evm_address('0x7d655c57f71464B6f83811C55D84009Cd9f5221C'),
        },
    )

    result_2 = assert_proper_response_with_result(response_2)
    assert len(result_2.keys()) == 3
    assert all((value is None for value in result_2.values()))

    # Test an address that is not a contract

    response_3 = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfo',
        ), json={
            'address': string_to_evm_address('0x00f195C9ed671173d618e7c03e4A987ef906C739'),
        },
    )

    result_3 = assert_proper_response_with_result(response_3)
    assert len(result_3.keys()) == 3
    assert all((value is None for value in result_3.values()))

    # Test an address that is not valid (this one has extra chars)
    response_4 = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfo',
        ), json={
            'address': string_to_evm_address('0x4652D63f4750bCd9d5f5dAds96087485d31554b10F'),
        },
    )

    assert_error_response(
        response=response_4,
        contained_in_msg='is not an ethereum address',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_avax_query_token_with_info(rotkehlchen_api_server):
    """Query DAI token to retrieve basic information"""

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfoavax',
        ), json={
            'address': string_to_evm_address('0xba7deebbfc5fa1100fb055a87773e1e99cd3507a'),
        },
    )

    result = assert_proper_response_with_result(response)
    assert result['decimals'] == 18
    assert result['symbol'] == 'DAI'
    assert result['name'] == 'Dai Stablecoin'

    # Test a contract without decimals/name/symbol methods
    response_2 = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfoavax',
        ), json={
            'address': string_to_evm_address('0x7d655c57f71464B6f83811C55D84009Cd9f5221C'),
        },
    )

    result_2 = assert_proper_response_with_result(response_2)
    assert len(result_2.keys()) == 3
    assert all((value is None for value in result_2.values()))

    # Test an address that is not a contract

    response_3 = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfoavax',
        ), json={
            'address': string_to_evm_address('0x00f195C9ed671173d618e7c03e4A987ef906C739'),
        },
    )

    result_3 = assert_proper_response_with_result(response_3)
    assert len(result_3.keys()) == 3
    assert all((value is None for value in result_3.values()))

    # Test an address that is not valid (this one has extra chars)
    response_4 = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfoavax',
        ), json={
            'address': string_to_evm_address('0x4652D63f4750bCd9d5f5dAds96087485d31554b10F'),
        },
    )

    assert_error_response(
        response=response_4,
        contained_in_msg='is not an ethereum address',
        status_code=HTTPStatus.BAD_REQUEST,
    )
