from http import HTTPStatus
from typing import Dict

import pytest
import requests

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
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


VAULT_8015 = {
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

VAULT_8015_DETAILS = {
    'identifier': 8015,
    'creation_ts': 1586785858,
    'total_interest_owed': FVal('0.2743084'),
    'total_liquidated_amount': ZERO,
    'total_liquidated_usd': ZERO,
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
}


def _check_vaults_values(vaults):
    expected_vaults = [VAULT_8015]
    assert_serialized_lists_equal(expected_vaults, vaults)


def _check_vault_details_values(details):
    expected_details = [VAULT_8015_DETAILS]
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


@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao']])
def test_query_vaults_details_non_premium(rotkehlchen_api_server):
    """Check querying the vaults details endpoint without premium does not work"""
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ))
    assert_error_response(
        response=response,
        contained_in_msg='Currently logged in user testuser does not have a premium subscription',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [3])
@pytest.mark.parametrize('ethereum_modules', [['makerdao']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [{
    'ETH': {
        'USD': {
            1584061534: FVal(135.44),
            1584061897: FVal(135.44),
            1584061977: FVal(135.44),
        },
    },
}])
def test_query_vaults_details_liquidation(rotkehlchen_api_server, ethereum_accounts):
    """Check vault details of a vault with liquidations

    Also use three accounts, two of which have vaults associated with them to test
    that vaults for multiple accounts get detected
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    proxies_mapping = {
        ethereum_accounts[0]: '0x689D4C2229717f877A644A0aAd742D67E5D0a2FB',
        ethereum_accounts[2]: '0x420F88De6dadA0a77Db7b9EdBe3A0C614346031E',
    }
    mock_proxies(rotki, proxies_mapping)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultsresource",
    ))
    vaults = assert_proper_response_with_result(response)
    vault_6021 = {
        'identifier': 6021,
        'name': 'ETH-A',
        'collateral_asset': 'ETH',
        'collateral_amount': ZERO,
        'collateral_usd_value': ZERO,
        'debt_value': ZERO,
        'collateralization_ratio': None,
        'liquidation_ratio': '150.00%',
        'liquidation_price': None,
    }
    expected_vaults = [vault_6021, VAULT_8015]
    assert_serialized_lists_equal(expected_vaults, vaults)

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ))
    vault_6021_details = {
        'identifier': 6021,
        'creation_ts': 1582699808,
        'total_interest_owed': FVal('-11078.655097848869'),
        'total_liquidated_amount': FVal('141.7'),
        'total_liquidated_usd': FVal('19191.848'),
        'events': [{
            'event_type': 'deposit',
            'amount': FVal('140'),
            'timestamp': 1582699808,
            'tx_hash': '0x3246ef91fd3d6e1f7c5766de4fa1f0991ba67d92e518447ba8207fe98569c309',
        }, {
            'event_type': 'generate',
            'amount': FVal('14000'),
            'timestamp': 1582699808,
            'tx_hash': '0x3246ef91fd3d6e1f7c5766de4fa1f0991ba67d92e518447ba8207fe98569c309',
        }, {
            'event_type': 'deposit',
            'amount': FVal('1.7'),
            'timestamp': 1583958747,
            'tx_hash': '0x65ac798cb9f22068e43fd9ef8303a31e436989062ae87e25650cc44c7788ab62',
        }, {
            'event_type': 'payback',
            'amount': FVal('2921.344902'),
            'timestamp': 1584024065,
            'tx_hash': '0x6e44d22d6898ee012369787cd75ea6fb9ace6f995cd157675f370e8ba4a7b9ad',
        }, {
            'event_type': 'liquidation',
            'amount': FVal('50'),
            'timestamp': 1584061534,
            'tx_hash': '0xb02050d914ab40f59a9e07eb4f8161ce36eb97cea9c189b027eb1ceeac83a516',
        }, {
            'event_type': 'liquidation',
            'amount': FVal('50'),
            'timestamp': 1584061897,
            'tx_hash': '0x678f31d49dd70d76c0ce441343c0060dc600f4c8dbb4cee2b08c6b451b6097cd',
        }, {
            'event_type': 'liquidation',
            'amount': FVal('41.7'),
            'timestamp': 1584061977,
            'tx_hash': '0xded0f9de641087692555d92a7fa94fa9fa7abf22744b2d16c20a66c5e48a8edf',
        }],
    }
    details = assert_proper_response_with_result(response)
    expected_details = [vault_6021_details, VAULT_8015_DETAILS]
    assert_serialized_lists_equal(expected_details, details)
