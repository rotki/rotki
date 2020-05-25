from http import HTTPStatus
from typing import Dict

import pytest
import requests

from rotkehlchen.chain.ethereum.makerdao import MakerDAOVault
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.checks import (
    assert_serialized_dicts_equal,
    assert_serialized_lists_equal,
)
from rotkehlchen.tests.utils.constants import A_USDC, A_WBTC
from rotkehlchen.typing import ChecksumEthAddress


def mock_proxies(rotki, mapping) -> None:
    def mock_get_proxies() -> Dict[ChecksumEthAddress, ChecksumEthAddress]:
        return mapping
    rotki.chain_manager.makerdao._get_accounts_having_maker_proxy = mock_get_proxies


VAULT_8015 = {
    'identifier': 8015,  # owner is missing and is filled in by the test function
    'collateral_type': 'ETH-A',
    'collateral_asset': 'ETH',
    'collateral_amount': ZERO,
    'collateral_usd_value': ZERO,
    'debt_value': ZERO,
    'collateralization_ratio': None,
    'liquidation_ratio': '150.00%',
    'liquidation_price': None,
    'stability_fee': '0.00%',
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


def _check_vaults_values(vaults, owner):
    expected_vault = VAULT_8015.copy()
    expected_vault['owner'] = owner
    expected_vaults = [expected_vault]
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
    _check_vaults_values(vaults, ethereum_accounts[0])

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
    _check_vaults_values(vaults, ethereum_accounts[0])

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
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_query_only_details_and_not_vaults(rotkehlchen_api_server, ethereum_accounts):
    """Check querying the vaults details endpoint works before even querying vaults"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    proxies_mapping = {ethereum_accounts[0]: '0x689D4C2229717f877A644A0aAd742D67E5D0a2FB'}
    mock_proxies(rotki, proxies_mapping)
    # Query the details first
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ))
    details = assert_proper_response_with_result(response)
    _check_vault_details_values(details)
    # And then query the vaults, which should just use the cached value
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultsresource",
    ))
    vaults = assert_proper_response_with_result(response)
    _check_vaults_values(vaults, ethereum_accounts[0])


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
        'owner': ethereum_accounts[2],
        'collateral_type': 'ETH-A',
        'collateral_asset': 'ETH',
        'collateral_amount': ZERO,
        'collateral_usd_value': ZERO,
        'debt_value': ZERO,
        'collateralization_ratio': None,
        'liquidation_ratio': '150.00%',
        'liquidation_price': None,
        'stability_fee': '0.00%',
    }
    vault_8015_with_owner = VAULT_8015.copy()
    vault_8015_with_owner['owner'] = ethereum_accounts[0]
    expected_vaults = [vault_6021, vault_8015_with_owner]
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


@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_query_vaults_wbtc(rotkehlchen_api_server, ethereum_accounts):
    """Check vault info and details for a vault with WBTC as collateral"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    proxies_mapping = {
        ethereum_accounts[0]: '0x9684e6C1c7B79868839b27F88bA6d5A176367075',  # 8913
    }

    mock_proxies(rotki, proxies_mapping)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultsresource",
    ))
    # That proxy has 3 vaults. We only want to test 8913, which is closed/repaid so just keep that
    vaults = [x for x in assert_proper_response_with_result(response) if x['identifier'] == 8913]
    vault_8913 = MakerDAOVault(
        identifier=8913,
        owner=ethereum_accounts[0],
        collateral_type='WBTC-A',
        urn='0x37f7B3C82A9Edc13FdCcE66E7d500b3698A13294',
        collateral_asset=A_WBTC,
        collateral_amount=ZERO,
        collateral_usd_value=ZERO,
        debt_value=ZERO,
        collateralization_ratio=None,
        liquidation_ratio=FVal(1.5),
        liquidation_price=None,
        stability_fee=FVal(0.01),
    )
    expected_vaults = [vault_8913.serialize()]
    assert_serialized_lists_equal(expected_vaults, vaults)
    # And also make sure that the internal mapping will only query details of 8913
    rotki.chain_manager.makerdao.vault_mappings = {ethereum_accounts[0]: [vault_8913]}

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ))
    vault_8913_details = {
        'identifier': 8913,
        'creation_ts': 1588664698,
        'total_interest_owed': FVal('0.1903819198'),
        'total_liquidated_amount': FVal('141.7'),
        'total_liquidated_usd': FVal('19191.848'),
        'events': [{
            'event_type': 'deposit',
            'amount': FVal('0.011'),
            'timestamp': 1588664698,
            'tx_hash': '0x9ba4a6187fa2c49ba327e7c923846a08a1e972017ec41d3f9f66ef524f7dde59',
        }, {
            'event_type': 'generate',
            'amount': FVal('25'),
            'timestamp': 1588664698,
            'tx_hash': '0x9ba4a6187fa2c49ba327e7c923846a08a1e972017ec41d3f9f66ef524f7dde59',
        }, {
            'event_type': 'payback',
            'amount': FVal('25.000248996'),
            'timestamp': 1588696496,
            'tx_hash': '0x8bd960e7eb8b9e2b81d2446d1844dd63f94636c7800ea5e3b4d926ea0244c66c',
        }, {
            'event_type': 'deposit',
            'amount': FVal('0.0113'),
            'timestamp': 1588720248,
            'tx_hash': '0x678c4da562173c102473f1904ff293a767ebac9ec6c7d728ef2fd41acf00a13a',
        }],  # way too many events in the vault, so no need to check them all
    }
    details = assert_proper_response_with_result(response)
    assert len(details) == 1
    detail = details[0]
    assert detail['identifier'] == vault_8913_details['identifier']
    assert detail['creation_ts'] == vault_8913_details['creation_ts']
    assert FVal(detail['total_interest_owed']).is_close(vault_8913_details['total_interest_owed'])
    assert FVal(detail['total_liquidated_amount']) == ZERO
    assert FVal(detail['total_liquidated_usd']) == ZERO
    for idx, event in enumerate(vault_8913_details['events']):
        assert_serialized_dicts_equal(event, detail['events'][idx])


@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_query_vaults_usdc(rotkehlchen_api_server, ethereum_accounts):
    """Check vault info and details for a vault with USDC as collateral"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    proxies_mapping = {
        ethereum_accounts[0]: '0xBE79958661741079679aFf75DbEd713cE71a979d',  # 7588
    }

    mock_proxies(rotki, proxies_mapping)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultsresource",
    ))
    vaults = assert_proper_response_with_result(response)
    vault_7588 = MakerDAOVault(
        identifier=7588,
        owner=ethereum_accounts[0],
        collateral_type='USDC-A',
        urn='0x56D88244073B2fC17af5B1E6088936D5bAaDc37B',
        collateral_asset=A_USDC,
        collateral_amount=ZERO,
        collateral_usd_value=ZERO,
        debt_value=ZERO,
        collateralization_ratio=None,
        liquidation_ratio=FVal(1.2),
        liquidation_price=None,
        stability_fee=FVal(0.0075),
    )
    expected_vaults = [vault_7588.serialize()]
    assert_serialized_lists_equal(expected_vaults, vaults)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ))
    vault_7588_details = {
        'identifier': 7588,
        'creation_ts': 1585286480,
        'total_interest_owed': FVal('0.00050636718'),
        'total_liquidated_amount': ZERO,
        'total_liquidated_usd': ZERO,
        'events': [{
            'event_type': 'deposit',
            'amount': FVal('45'),
            'timestamp': 1585286480,
            'tx_hash': '0x8b553dd0e8ee5385ec91105bf911143666d9df0ecd84c04f288278f7658aa7d6',
        }, {
            'event_type': 'generate',
            'amount': FVal('20'),
            'timestamp': 1585286480,
            'tx_hash': '0x8b553dd0e8ee5385ec91105bf911143666d9df0ecd84c04f288278f7658aa7d6',
        }, {
            'event_type': 'generate',
            'amount': FVal('15.99'),
            'timestamp': 1585286769,
            'tx_hash': '0xdb861c893a51e4649ff3740cd3658cd4c9b1d048d3b8b4d117f4319bd60aee01',
        }, {
            'event_type': 'payback',
            'amount': FVal('35.990506367'),
            'timestamp': 1585290263,
            'tx_hash': '0xdd7825fe4a93c6f1ffa25a91b6da2396c229fe16b17242ad5c0bf7962928b2ec',
        }, {
            'event_type': 'withdraw',
            'amount': FVal('45'),
            'timestamp': 1585290300,
            'tx_hash': '0x97462ebba7ce2467787bf6de25a25c24e538cf8a647919112c5f048b6a293408',
        }],
    }
    details = assert_proper_response_with_result(response)
    expected_details = [vault_7588_details]
    assert_serialized_lists_equal(expected_details, details)


@pytest.mark.skip('This vault is special and does not work. needs investigation')
@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_query_vaults_usdc_strange(rotkehlchen_api_server, ethereum_accounts):
    """Strange case of a USDC vault that is not queried correctly

    https://oasis.app/borrow/7538?network=mainnet
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    proxies_mapping = {
        ethereum_accounts[0]: '0x15fEaFd4358b8C03c889D6661b0CA1Be3389792F',  # 7538
    }

    mock_proxies(rotki, proxies_mapping)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultsresource",
    ))
    # That proxy has 3 vaults. We only want to test 7538, which is closed/repaid so just keep that
    vaults = [x for x in assert_proper_response_with_result(response) if x['identifier'] == 7538]
    vault_7538 = MakerDAOVault(
        identifier=7538,
        owner=ethereum_accounts[0],
        collateral_type='USDC-A',
        urn='0x70E58566C7baB6faaFE03fbA69DF45Ef4f48223B',
        collateral_asset=A_USDC,
        collateral_amount=ZERO,
        collateral_usd_value=ZERO,
        debt_value=ZERO,
        collateralization_ratio=None,
        liquidation_ratio=FVal(1.2),
        liquidation_price=None,
    )
    expected_vaults = [vault_7538.serialize()]
    assert_serialized_lists_equal(expected_vaults, vaults)
    # And also make sure that the internal mapping will only query details of 7538
    rotki.chain_manager.makerdao.vault_mappings = {ethereum_accounts[0]: [vault_7538]}

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ))
    vault_7538_details = {
        'identifier': 7538,
        'creation_ts': 1585145754,
        'total_interest_owed': FVal('0.0005943266'),
        'total_liquidated_amount': ZERO,
        'total_liquidated_usd': ZERO,
        'events': [{
            'event_type': 'deposit',
            'amount': FVal('250.12'),
            'timestamp': 1588664698,
            'tx_hash': '0x9ba4a6187fa2c49ba327e7c923846a08a1e972017ec41d3f9f66ef524f7dde59',
        }, {
            'event_type': 'generate',
            'amount': FVal('25'),
            'timestamp': 1588664698,
            'tx_hash': '0x9ba4a6187fa2c49ba327e7c923846a08a1e972017ec41d3f9f66ef524f7dde59',
        }, {
            'event_type': 'payback',
            'amount': FVal('25.000248996'),
            'timestamp': 1588696496,
            'tx_hash': '0x8bd960e7eb8b9e2b81d2446d1844dd63f94636c7800ea5e3b4d926ea0244c66c',
        }, {
            'event_type': 'deposit',
            'amount': FVal('0.0113'),
            'timestamp': 1588720248,
            'tx_hash': '0x678c4da562173c102473f1904ff293a767ebac9ec6c7d728ef2fd41acf00a13a',
        }],
    }
    details = assert_proper_response_with_result(response)
    expected_details = [vault_7538_details]
    assert_serialized_lists_equal(expected_details, details)
