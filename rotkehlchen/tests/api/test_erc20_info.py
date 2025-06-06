from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest
import requests

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def assert_default_erc20_info_response(result: Any) -> None:
    assert len(result.keys()) == 3
    for prop, value in result.items():
        if prop == 'decimals':
            assert value == 18
        else:
            assert value is None


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_query_token_with_info(rotkehlchen_api_server: 'APIServer') -> None:
    """Test api for querying evm token details"""

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfo',
        ), json={
            'address': string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            'evm_chain': 'ethereum',
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['decimals'] == 18
    assert result['symbol'] == 'DAI'
    assert result['name'] == 'Dai Stablecoin'

    response = requests.get(  # test non mainnet token
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfo',
        ), json={
            'address': string_to_evm_address('0x94b008aA00579c1307B0EF2c499aD98a8ce58e58'),
            'evm_chain': 'optimism',
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['decimals'] == 6
    assert result['symbol'] == 'USDT'
    assert result['name'] == 'Tether USD'

    # Test a contract without decimals/name/symbol methods
    response_2 = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfo',
        ), json={
            'address': string_to_evm_address('0x7d655c57f71464B6f83811C55D84009Cd9f5221C'),
            'evm_chain': 'ethereum',
        },
    )

    result_2 = assert_proper_sync_response_with_result(response_2)
    assert_default_erc20_info_response(result_2)

    # Test an address that is not a contract
    response_3 = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfo',
        ), json={
            'address': string_to_evm_address('0x00f195C9ed671173d618e7c03e4A987ef906C739'),
            'evm_chain': 'ethereum',
        },
    )

    result_3 = assert_proper_sync_response_with_result(response_3)
    assert_default_erc20_info_response(result_3)

    # Test an address that is not valid (this one has extra chars)
    response_4 = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfo',
        ), json={
            'address': string_to_evm_address('0x4652D63f4750bCd9d5f5dAds96087485d31554b10F'),
            'evm_chain': 'ethereum',
        },
    )

    assert_error_response(
        response=response_4,
        contained_in_msg='is not an ethereum address',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test an address that is a spam token (does not implement the methods)
    response_4 = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'erc20tokeninfo',
        ), json={
            'address': string_to_evm_address('0x53B1030E68F2aEcFAd04794458ace54EC06dc707'),
            'evm_chain': 'ethereum',
        },
    )
    assert_error_response(
        response=response_4,
        contained_in_msg='seems to not be a deployed contract or not a valid erc20 token',
        status_code=HTTPStatus.CONFLICT,
    )
