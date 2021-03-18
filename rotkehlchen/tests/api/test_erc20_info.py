import requests
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result


def test_query_token_with_info(rotkehlchen_api_server):
    """Query DAI token to retrieve basic information"""

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "erc20tokeninfo",
        ), json={
            'address': string_to_ethereum_address("0x6B175474E89094C44Da98b954EedeAC495271d0F"),
        },
    )

    assert_proper_response_with_result(response)
    data = response.json()
    assert data['result']['decimals'] == 18
    assert data['result']['symbol'] == 'DAI'
    assert data['result']['name'] == 'Dai Stablecoin'


def test_query_with_empty_contract(rotkehlchen_api_server):
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "erc20tokeninfo",
        ), json={
            'address': string_to_ethereum_address("0x7d655c57f71464B6f83811C55D84009Cd9f5221C"),
        },
    )

    assert_proper_response_with_result(response)
    data = response.json()
    assert len(data['result'].keys()) == 1
    assert data['result']['decimals'] == 18
