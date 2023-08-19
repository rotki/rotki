
import pytest
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH, A_OP
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.types import SupportedBlockchain
from rotkehlchen.utils.misc import ts_now

TEST_ADDY = '0x9531C059098e3d194fF87FebB587aB07B30B1306'


@pytest.mark.vcr(filter_query_parameters=['apikey'], match_on=['uri', 'method', 'raw_body'], allow_playback_repeats=True)  # noqa: E501
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('network_mocking', [False])
def test_add_optimism_blockchain_account(rotkehlchen_api_server):
    """Test adding an optimism account when there is none in the db
    works as expected and that balances are returned and tokens are detected.
    """
    optimism_chain_key = SupportedBlockchain.OPTIMISM.serialize()
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=optimism_chain_key,
        ),
        json={
            'accounts': [{'address': TEST_ADDY}],
        },
    )
    assert_proper_response(response)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'named_blockchain_balances_resource',
        blockchain=optimism_chain_key,
    ))
    result = assert_proper_response_with_result(response)

    # Check per account
    account_balances = result['per_account'][optimism_chain_key][TEST_ADDY]
    assert 'liabilities' in account_balances
    asset_eth = account_balances['assets'][A_ETH.identifier]
    assert FVal(asset_eth['amount']) >= ZERO
    assert FVal(asset_eth['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_eth = result['totals']['assets'][A_ETH.identifier]
    assert FVal(total_eth['amount']) >= ZERO
    assert FVal(total_eth['usd_value']) >= ZERO

    now = ts_now()
    # now check that detecting tokens works
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'detecttokensresource',
            blockchain=optimism_chain_key,
        ),
    )
    result = assert_proper_response_with_result(response)
    optimism_tokens = [
        A_OP,
        Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
        Asset('eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'),
    ]
    assert result[TEST_ADDY]['last_update_timestamp'] >= now
    assert result[TEST_ADDY]['tokens'] == optimism_tokens

    # and query balances again to see tokens also appear
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain=optimism_chain_key,
        ),
        json={
            'ignore_cache': True,
        },
    )
    result = assert_proper_response_with_result(response)

    # Check per account
    account_balances = result['per_account'][optimism_chain_key][TEST_ADDY]
    assert 'liabilities' in account_balances
    assert len(account_balances['assets']) == len(optimism_tokens) + 1
    for asset_id in (A_ETH.identifier, *optimism_tokens):
        asset = account_balances['assets'][asset_id]
        assert FVal(asset['amount']) >= ZERO
        assert FVal(asset['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    assert len(result['totals']['assets']) == len(optimism_tokens) + 1
    for asset_id in ('ETH', *optimism_tokens):
        asset = result['totals']['assets'][asset_id]
        assert FVal(asset['amount']) >= ZERO
        assert FVal(asset['usd_value']) >= ZERO
