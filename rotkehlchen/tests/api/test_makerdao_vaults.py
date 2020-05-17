from typing import Dict

import pytest
import requests

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.checks import assert_serialized_dicts_equal
from rotkehlchen.typing import ChecksumEthAddress


def mock_proxies(rotki, mapping) -> None:
    def mock_get_proxies() -> Dict[ChecksumEthAddress, ChecksumEthAddress]:
        return mapping
    rotki.chain_manager.makerdao._get_accounts_having_maker_proxy = mock_get_proxies


@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao']])
def test_query_vaults(rotkehlchen_api_server, ethereum_accounts):
    """Check querying the vaults endpoint works. Uses real vault data"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    proxies_mapping = {ethereum_accounts[0]: '0x689D4C2229717f877A644A0aAd742D67E5D0a2FB'}
    mock_proxies(rotki, proxies_mapping)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultsresource",
    ))
    vaults = assert_proper_response_with_result(response)
    assert len(vaults) == 1
    expected_dict = {
        'identifier': 8015,
        'name': 'ETH-A',
        'collateral_asset': 'ETH',
        'collateral_amount': ZERO,
        'collateral_usd_value': ZERO,
        'debt_value': ZERO,
        'collateralization_ratio': None,
        'liquidation_ratio': '150.00%',
        'liquidation_price': None,
    }
    assert_serialized_dicts_equal(expected_dict, vaults[0])


@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao']])
def test_query_vaults_async(rotkehlchen_api_server, ethereum_accounts):
    """Check querying the vaults endpoint asynchronously works. Uses real vault data"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    proxies_mapping = {ethereum_accounts[0]: '0x689D4C2229717f877A644A0aAd742D67E5D0a2FB'}
    mock_proxies(rotki, proxies_mapping)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultsresource",
    ), json={'async_query': True})
    task_id = assert_ok_async_response(response)
    outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert outcome['message'] == ''
    vaults = outcome['result']
    assert len(vaults) == 1
    expected_dict = {
        'identifier': 8015,
        'name': 'ETH-A',
        'collateral_asset': 'ETH',
        'collateral_amount': ZERO,
        'collateral_usd_value': ZERO,
        'debt_value': ZERO,
        'collateralization_ratio': None,
        'liquidation_ratio': '150.00%',
        'liquidation_price': None,
    }
    assert_serialized_dicts_equal(expected_dict, vaults[0])
