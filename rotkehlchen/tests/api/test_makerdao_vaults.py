from typing import Dict

import pytest
import requests

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.checks import assert_serialized_lists_equal
from rotkehlchen.typing import ChecksumEthAddress


def mock_proxies(rotki, mapping) -> None:
    def mock_get_proxies() -> Dict[ChecksumEthAddress, ChecksumEthAddress]:
        return mapping
    rotki.chain_manager.makerdao._get_accounts_having_maker_proxy = mock_get_proxies


def _check_vaults_values(vaults):
    expected_vaults = [{
        'identifier': 8015,
        'name': 'ETH-A',
        'collateral_asset': 'ETH',
        'collateral_amount': ZERO,
        'collateral_usd_value': ZERO,
        'debt_value': ZERO,
        'collateralization_ratio': None,
        'liquidation_ratio': '150.00%',
        'liquidation_price': None,
    }]
    assert_serialized_lists_equal(expected_vaults, vaults)


def _check_vault_details_values(details):
    expected_details = [{
        'creation_ts': 1586785858,
        'total_interest_owed': FVal('0.2743084'),
        'events': [{
            'event_type': 'deposit',
            'amount': FVal('41.1641807'),
            'timestamp': 1586785858,
            'tx_hash': '0xd382ea1efa843c68914b2377057d384aca2a41710b23be89f165bb0a21986512',
        }, {
            'event_type': 'generate',
            'amount': FVal('1800'),
            'timestamp': 1586785858,
            'tx_hash': '0xd382ea1efa843c68914b2377057d384aca2a41710b23be89f165bb0a21986512',
        }, {
            'event_type': 'payback',
            'amount': FVal('51'),
            'timestamp': 1586788927,
            'tx_hash': '0xc4ddd0e1b0a6cb4e55ac0be34201a5176372734db3bada58a73bccf98e47b3e7',
        }, {
            'event_type': 'generate',
            'amount': FVal('1000'),
            'timestamp': 1586805054,
            'tx_hash': '0x135a1ce0059ea8ca161cff4dba0b579538aa4550c96a895f5cebcc0c56e598d8',
        }, {
            'event_type': 'payback',
            'amount': FVal('1076'),
            'timestamp': 1587539880,
            'tx_hash': '0x3dd24fc5c64f151bc4a8c1d1a0de39ba23aa760ed27a591a462d822eb5c8fb80',
        }, {
            'event_type': 'payback',
            'amount': FVal('1673.2743084'),
            'timestamp': 1588964616,
            'tx_hash': '0x317f829a351ad9a8fb1a1e5f2f1ee786c0081087dc3a9ece8489e4092f258956',
        }, {
            'event_type': 'withdraw',
            'amount': FVal('41.1641807'),
            'timestamp': 1588964667,
            'tx_hash': '0xa67149325d5e2e20fab2befc3553332866c27ed32a4d04a3975e6eb4b130263b',
        }],
    }]
    assert_serialized_lists_equal(expected_details, details)


@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
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
    _check_vaults_values(vaults)

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ))
    details = assert_proper_response_with_result(response)
    _check_vault_details_values(details)


@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
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
    _check_vaults_values(vaults)

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ), json={'async_query': True})
    task_id = assert_ok_async_response(response)
    outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert outcome['message'] == ''
    details = outcome['result']
    _check_vault_details_values(details)
