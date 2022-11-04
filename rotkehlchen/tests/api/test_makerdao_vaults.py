"""These tests do not need the ethereum mocks since they never query token balances"""

import random
from http import HTTPStatus
from typing import List, Optional

import pytest
import requests
from flaky import flaky

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.makerdao.vaults import MakerdaoVault
from rotkehlchen.constants.assets import A_DAI, A_USDC, A_WBTC
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.conftest import TestEnvironment, requires_env
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.checks import (
    assert_serialized_dicts_equal,
    assert_serialized_lists_equal,
)
from rotkehlchen.tests.utils.makerdao import mock_proxies

mocked_prices = {
    'ETH': {
        'USD': {
            1582699808: FVal('223.73'),
            1583958747: FVal('194.86'),
            1584061534: FVal('135.44'),
            1584061897: FVal('135.44'),
            1584061977: FVal('135.44'),
            1586785858: FVal('156.82'),
            1587910979: FVal('197.78'),
            1588174425: FVal('215.55'),
            1588964667: FVal('211.54'),
            1589993538: FVal('209.85'),
            1590043499: FVal('198.56'),
            1590043699: FVal('198.56'),
        },
    },
    A_DAI.identifier: {
        'USD': {
            1582699808: FVal('1.002'),
            1584024065: FVal('1.002'),
            1585286480: FVal('1.023'),
            1585286769: FVal('1.023'),
            1585290263: FVal('1.023'),
            1586785858: FVal('1.024'),
            1586788927: FVal('1.024'),
            1586805054: FVal('1.024'),
            1587539880: FVal('1.016'),
            1587539889: FVal('1.016'),
            1587910979: FVal('1.015'),
            1588174425: FVal('1.014'),
            1588664698: FVal('1.006'),
            1588696496: FVal('1.006'),
            1588964616: FVal('1.006'),
            1589989097: FVal('1.003'),
            1590042891: FVal('1.001'),
            1590044118: FVal('1.001'),
            1590521879: FVal('1.003'),
        },
    },
    A_WBTC.identifier: {
        'USD': {
            1588664698: FVal('7915.09'),
            1588720248: FVal('7915.09'),
        },
    },
    A_USDC.identifier: {
        'USD': {
            1585286480: ONE,
            1585290300: ONE,
        },
    },
}

VAULT_8015 = {
    'identifier': 8015,  # owner is missing and is filled in by the test function
    'collateral_type': 'ETH-A',
    'collateral_asset': 'ETH',
    'collateral': {
        'amount': '0',
        'usd_value': '0',
    },
    'debt': {
        'amount': '0',
        'usd_value': '0',
    },
    'collateralization_ratio': None,
    'liquidation_ratio': '145.00%',
    'liquidation_price': None,
    'stability_fee': '0.00%',
}

VAULT_8015_DETAILS = {
    'identifier': 8015,
    'collateral_asset': 'ETH',
    'creation_ts': 1586785858,
    'total_interest_owed': '0.2810015984764',
    'total_liquidated': {
        'amount': '0',
        'usd_value': '0',
    },
    'events': [{
        'event_type': 'deposit',
        'value': {
            'amount': '41.1641807',
            'usd_value': '6455.366829',
        },
        'timestamp': 1586785858,
        'tx_hash': '0xd382ea1efa843c68914b2377057d384aca2a41710b23be89f165bb0a21986512',
    }, {
        'event_type': 'generate',
        'value': {
            'amount': '1800',
            'usd_value': '1843.2',
        },
        'timestamp': 1586785858,
        'tx_hash': '0xd382ea1efa843c68914b2377057d384aca2a41710b23be89f165bb0a21986512',
    }, {
        'event_type': 'payback',
        'value': {
            'amount': '51',
            'usd_value': '52.224',
        },
        'timestamp': 1586788927,
        'tx_hash': '0xc4ddd0e1b0a6cb4e55ac0be34201a5176372734db3bada58a73bccf98e47b3e7',
    }, {
        'event_type': 'generate',
        'value': {
            'amount': '1000',
            'usd_value': '1024',
        },
        'timestamp': 1586805054,
        'tx_hash': '0x135a1ce0059ea8ca161cff4dba0b579538aa4550c96a895f5cebcc0c56e598d8',
    }, {
        'event_type': 'payback',
        'value': {
            'amount': '1076',
            'usd_value': '1093.216',
        },
        'timestamp': 1587539880,
        'tx_hash': '0x3dd24fc5c64f151bc4a8c1d1a0de39ba23aa760ed27a591a462d822eb5c8fb80',
    }, {
        'event_type': 'payback',
        'value': {
            'amount': '1673.2743084',
            'usd_value': '1683.31395425',
        },
        'timestamp': 1588964616,
        'tx_hash': '0x317f829a351ad9a8fb1a1e5f2f1ee786c0081087dc3a9ece8489e4092f258956',
    }, {
        'event_type': 'withdraw',
        'value': {
            'amount': '41.1641807',
            'usd_value': '8707.87080185',
        },
        'timestamp': 1588964667,
        'tx_hash': '0xa67149325d5e2e20fab2befc3553332866c27ed32a4d04a3975e6eb4b130263b',
    }],
}

VAULT_IGNORE_KEYS = [
    'collateral',
    'debt',
    'collateralization_ratio',
    'stability_fee',
    'liquidation_price',
]


def _check_vaults_values(vaults, owner):
    expected_vault = VAULT_8015.copy()
    expected_vault['owner'] = owner
    expected_vaults = [expected_vault]
    assert_serialized_lists_equal(expected_vaults, vaults, ignore_keys=VAULT_IGNORE_KEYS)


def _check_vault_details_values(details, total_interest_owed_list: List[Optional[FVal]]):
    expected_details = [VAULT_8015_DETAILS]
    assert_serialized_lists_equal(
        expected_details,
        details,
        # Checking only the first 7 events
        length_list_keymap={'events': 7},
        ignore_keys=['total_interest_owed', 'stability_fee'],
    )
    for idx, entry in enumerate(total_interest_owed_list):
        if entry is not None:
            # We check if the total interest owed is bigger than the given one since
            # with a non-zero stability fee, interest always increases
            assert FVal(details[idx]['total_interest_owed']) >= entry


@requires_env([TestEnvironment.NIGHTLY])
@flaky(max_runs=3, min_passes=1)  # some makerdao vault tests take long time and may time out
@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_vaults']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_prices])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_vaults(rotkehlchen_api_server, ethereum_accounts):
    """Check querying the vaults endpoint works. Uses real vault data"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    proxies_mapping = {ethereum_accounts[0]: '0x689D4C2229717f877A644A0aAd742D67E5D0a2FB'}
    mock_proxies(rotki, proxies_mapping, 'makerdao_vaults')
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'makerdaovaultsresource',
    ), json={'async_query': async_query})
    if async_query:
        task_id = assert_ok_async_response(response)
        vaults = wait_for_async_task_with_result(
            rotkehlchen_api_server,
            task_id,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 1.5,
        )
    else:
        vaults = assert_proper_response_with_result(response)

    _check_vaults_values(vaults, ethereum_accounts[0])

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'makerdaovaultdetailsresource',
    ), json={'async_query': async_query})
    if async_query:
        task_id = assert_ok_async_response(response)
        details = wait_for_async_task_with_result(
            rotkehlchen_api_server,
            task_id,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 1.5,
        )
    else:
        details = assert_proper_response_with_result(response)
    _check_vault_details_values(
        details=details,
        total_interest_owed_list=[FVal('0.2810015984764')],
    )


@requires_env([TestEnvironment.NIGHTLY])
@flaky(max_runs=3, min_passes=1)  # some makerdao vault tests take long time and may time out
@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_vaults']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_prices])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_only_details_and_not_vaults(rotkehlchen_api_server, ethereum_accounts):
    """Check querying the vaults details endpoint works before even querying vaults"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    proxies_mapping = {ethereum_accounts[0]: '0x689D4C2229717f877A644A0aAd742D67E5D0a2FB'}
    mock_proxies(rotki, proxies_mapping, 'makerdao_vaults')
    # Query the details first
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ))
    details = assert_proper_response_with_result(response)
    _check_vault_details_values(
        details=details,
        total_interest_owed_list=[FVal('0.2810015984764')],
    )
    # And then query the vaults, which should just use the cached value
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultsresource",
    ))
    vaults = assert_proper_response_with_result(response)
    _check_vaults_values(vaults, ethereum_accounts[0])


@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_vaults']])
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


@requires_env([TestEnvironment.NIGHTLY])
@pytest.mark.parametrize('number_of_eth_accounts', [3])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_vaults']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_prices])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
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
    mock_proxies(rotki, proxies_mapping, 'makerdao_vaults')
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
        'collateral': {
            'amount': ZERO,
            'usd_value': ZERO,
        },
        'debt': {
            'amount': ZERO,
            'usd_value': ZERO,
        },
        'collateralization_ratio': None,
        'liquidation_ratio': '145.00%',
        'liquidation_price': None,
        'stability_fee': '0.00%',
    }
    vault_8015_with_owner = VAULT_8015.copy()
    vault_8015_with_owner['owner'] = ethereum_accounts[0]
    assert_serialized_dicts_equal(vault_6021, vaults[0], ignore_keys=['stability_fee'])
    assert_serialized_dicts_equal(
        vault_8015_with_owner,
        vaults[1],
        ignore_keys=VAULT_IGNORE_KEYS,
    )
    assert len(vaults) == 2

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ))
    vault_6021_details = {
        'identifier': 6021,
        'collateral_asset': 'ETH',
        'creation_ts': 1582699808,
        'total_interest_owed': '-11078.655097848869',
        'total_liquidated': {
            'amount': '141.7',
            'usd_value': '19191.848',
        },
        'events': [{
            'event_type': 'deposit',
            'value': {
                'amount': '140',
                'usd_value': '31322.2',
            },
            'timestamp': 1582699808,
            'tx_hash': '0x3246ef91fd3d6e1f7c5766de4fa1f0991ba67d92e518447ba8207fe98569c309',
        }, {
            'event_type': 'generate',
            'value': {
                'amount': '14000',
                'usd_value': '14028',
            },
            'timestamp': 1582699808,
            'tx_hash': '0x3246ef91fd3d6e1f7c5766de4fa1f0991ba67d92e518447ba8207fe98569c309',
        }, {
            'event_type': 'deposit',
            'value': {
                'amount': '1.7',
                'usd_value': '331.262',
            },
            'timestamp': 1583958747,
            'tx_hash': '0x65ac798cb9f22068e43fd9ef8303a31e436989062ae87e25650cc44c7788ab62',
        }, {
            'event_type': 'payback',
            'value': {
                'amount': '2921.344902',
                'usd_value': '2927.187591',
            },
            'timestamp': 1584024065,
            'tx_hash': '0x6e44d22d6898ee012369787cd75ea6fb9ace6f995cd157675f370e8ba4a7b9ad',
        }, {
            'event_type': 'liquidation',
            'value': {
                'amount': '50',
                'usd_value': '6772',
            },
            'timestamp': 1584061534,
            'tx_hash': '0xb02050d914ab40f59a9e07eb4f8161ce36eb97cea9c189b027eb1ceeac83a516',
        }, {
            'event_type': 'liquidation',
            'value': {
                'amount': '50',
                'usd_value': '6772',
            },
            'timestamp': 1584061897,
            'tx_hash': '0x678f31d49dd70d76c0ce441343c0060dc600f4c8dbb4cee2b08c6b451b6097cd',
        }, {
            'event_type': 'liquidation',
            'value': {
                'amount': '41.7',
                'usd_value': '5647.848',
            },
            'timestamp': 1584061977,
            'tx_hash': '0xded0f9de641087692555d92a7fa94fa9fa7abf22744b2d16c20a66c5e48a8edf',
        }],
    }
    details = assert_proper_response_with_result(response)
    assert len(details) == 2
    assert_serialized_dicts_equal(vault_6021_details, details[0], ignore_keys=['stability_fee'])
    assert_serialized_dicts_equal(
        VAULT_8015_DETAILS,
        details[1],
        length_list_keymap={'events': 7},
        ignore_keys=['total_interest_owed'],
    )
    assert FVal(details[1]['total_interest_owed']) >= FVal(
        VAULT_8015_DETAILS['total_interest_owed'],
    )


@requires_env([TestEnvironment.NIGHTLY])
@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_vaults']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_prices])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_vaults_wbtc(rotkehlchen_api_server, ethereum_accounts):
    """Check vault info and details for a vault with WBTC as collateral"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    proxies_mapping = {
        ethereum_accounts[0]: '0x9684e6C1c7B79868839b27F88bA6d5A176367075',  # 8913
    }

    mock_proxies(rotki, proxies_mapping, 'makerdao_vaults')
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultsresource",
    ))
    # That proxy has 3 vaults. We only want to test 8913, which is closed/repaid so just keep that
    vaults = [x for x in assert_proper_response_with_result(response) if x['identifier'] == 8913]
    vault_8913 = MakerdaoVault(
        identifier=8913,
        owner=ethereum_accounts[0],
        collateral_type='WBTC-A',
        urn='0x37f7B3C82A9Edc13FdCcE66E7d500b3698A13294',
        collateral_asset=A_WBTC,
        collateral=Balance(ZERO, ZERO),
        debt=Balance(ZERO, ZERO),
        collateralization_ratio=None,
        liquidation_ratio=FVal(1.45),
        liquidation_price=None,
        stability_fee=FVal(0.02),
    )
    expected_vaults = [vault_8913.serialize()]
    assert_serialized_lists_equal(expected_vaults, vaults, ignore_keys=['stability_fee'])
    # And also make sure that the internal mapping will only query details of 8913
    makerdao_vaults = rotki.chains_aggregator.get_module('makerdao_vaults')
    makerdao_vaults.vault_mappings = {ethereum_accounts[0]: [vault_8913]}

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ))
    vault_8913_details = {
        'identifier': 8913,
        'collateral_asset': A_WBTC.identifier,
        'creation_ts': 1588664698,
        'total_interest_owed': '0.1903819198',
        'total_liquidated': {
            'amount': '0',
            'usd_value': '0',
        },
        'events': [{
            'event_type': 'deposit',
            'value': {
                'amount': '0.011',
                'usd_value': '87.06599',
            },
            'timestamp': 1588664698,
            'tx_hash': '0x9ba4a6187fa2c49ba327e7c923846a08a1e972017ec41d3f9f66ef524f7dde59',
        }, {
            'event_type': 'generate',
            'value': {
                'amount': '25',
                'usd_value': '25.15',
            },
            'timestamp': 1588664698,
            'tx_hash': '0x9ba4a6187fa2c49ba327e7c923846a08a1e972017ec41d3f9f66ef524f7dde59',
        }, {
            'event_type': 'payback',
            'value': {
                'amount': '25.000248996',
                'usd_value': '25.15025',
            },
            'timestamp': 1588696496,
            'tx_hash': '0x8bd960e7eb8b9e2b81d2446d1844dd63f94636c7800ea5e3b4d926ea0244c66c',
        }, {
            'event_type': 'deposit',
            'value': {
                'amount': '0.0113',
                'usd_value': '89.440517',
            },
            'timestamp': 1588720248,
            'tx_hash': '0x678c4da562173c102473f1904ff293a767ebac9ec6c7d728ef2fd41acf00a13a',
        }],  # way too many events in the vault, so no need to check them all
    }
    details = assert_proper_response_with_result(response)
    assert len(details) == 1
    assert_serialized_dicts_equal(
        details[0],
        vault_8913_details,
        # Checking only the first 4 events
        length_list_keymap={'events': 4},
    )


@flaky(max_runs=3, min_passes=1)  # some makerdao vault tests take long time and may time out
@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_vaults']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_prices])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_vaults_usdc(rotkehlchen_api_server, ethereum_accounts):
    """Check vault info and details for a vault with USDC as collateral"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    proxies_mapping = {
        ethereum_accounts[0]: '0xBE79958661741079679aFf75DbEd713cE71a979d',  # 7588
    }

    mock_proxies(rotki, proxies_mapping, 'makerdao_vaults')
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultsresource",
    ))
    vaults = assert_proper_response_with_result(response)
    vault_7588 = MakerdaoVault(
        identifier=7588,
        owner=ethereum_accounts[0],
        collateral_type='USDC-A',
        urn='0x56D88244073B2fC17af5B1E6088936D5bAaDc37B',
        collateral_asset=A_USDC,
        collateral=Balance(ZERO, ZERO),
        debt=Balance(ZERO, ZERO),
        collateralization_ratio=None,
        liquidation_ratio=FVal('1.03'),
        liquidation_price=None,
        stability_fee=FVal('0.04'),
    )
    expected_vaults = [vault_7588.serialize()]
    assert_serialized_lists_equal(
        expected_vaults,
        vaults, ignore_keys=['stability_fee', 'liquidation_ratio'],
    )
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ))
    vault_7588_details = {
        'identifier': 7588,
        'collateral_asset': A_USDC.identifier,
        'creation_ts': 1585286480,
        'total_interest_owed': '0.00050636718',
        'total_liquidated': {
            'amount': '0',
            'usd_value': '0',
        },
        'events': [{
            'event_type': 'deposit',
            'value': {
                'amount': '45',
                'usd_value': '45',
            },
            'timestamp': 1585286480,
            'tx_hash': '0x8b553dd0e8ee5385ec91105bf911143666d9df0ecd84c04f288278f7658aa7d6',
        }, {
            'event_type': 'generate',
            'value': {
                'amount': '20',
                'usd_value': '20.46',
            },
            'timestamp': 1585286480,
            'tx_hash': '0x8b553dd0e8ee5385ec91105bf911143666d9df0ecd84c04f288278f7658aa7d6',
        }, {
            'event_type': 'generate',
            'value': {
                'amount': '15.99',
                'usd_value': '16.35777',
            },
            'timestamp': 1585286769,
            'tx_hash': '0xdb861c893a51e4649ff3740cd3658cd4c9b1d048d3b8b4d117f4319bd60aee01',
        }, {
            'event_type': 'payback',
            'value': {
                'amount': '35.990506367',
                'usd_value': '36.818288',
            },
            'timestamp': 1585290263,
            'tx_hash': '0xdd7825fe4a93c6f1ffa25a91b6da2396c229fe16b17242ad5c0bf7962928b2ec',
        }, {
            'event_type': 'withdraw',
            'value': {
                'amount': '45',
                'usd_value': '45',
            },
            'timestamp': 1585290300,
            'tx_hash': '0x97462ebba7ce2467787bf6de25a25c24e538cf8a647919112c5f048b6a293408',
        }],
    }
    details = assert_proper_response_with_result(response)
    expected_details = [vault_7588_details]
    assert_serialized_lists_equal(expected_details, details, ignore_keys=['liquidation_ratio'])


@requires_env([TestEnvironment.NIGHTLY])
@flaky(max_runs=3, min_passes=1)  # some makerdao vault tests take long time and may time out
@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_vaults']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_prices])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_two_vaults_same_account_same_collateral(rotkehlchen_api_server, ethereum_accounts):
    """Check that no events are duplicated between vaults for same collateral by same account

    Test for vaults side of https://github.com/rotki/rotki/issues/1032
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    proxies_mapping = {
        # proxy for 8632 and 8543
        ethereum_accounts[0]: '0xAe9996b76bdAa003ace6D66328A6942565f5768d',
    }
    mock_proxies(rotki, proxies_mapping, 'makerdao_vaults')

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultsresource",
    ))
    vaults = assert_proper_response_with_result(response)
    vault_8543 = {
        'identifier': 8543,
        'owner': ethereum_accounts[0],
        'collateral_type': 'ETH-A',
        'collateral_asset': 'ETH',
        'collateral': {
            'amount': '0',
            'usd_value': '0',
        },
        'debt': {
            'amount': '0',
            'usd_value': '0',
        },
        'collateralization_ratio': None,
        'liquidation_ratio': '145.00%',
        'liquidation_price': None,
        'stability_fee': '0.00%',
    }
    vault_8632 = {
        'identifier': 8632,
        'owner': ethereum_accounts[0],
        'collateral_type': 'ETH-A',
        'collateral_asset': 'ETH',
        'collateral': {
            'amount': '0',
            'usd_value': '0',
        },
        'debt': {
            'amount': '0',
            'usd_value': '0',
        },
        'collateralization_ratio': None,
        'liquidation_ratio': '145.00%',
        'liquidation_price': None,
        'stability_fee': '0.00%',
    }
    assert len(vaults) == 2
    assert_serialized_dicts_equal(vaults[0], vault_8543, ignore_keys=['stability_fee'])
    assert_serialized_dicts_equal(vaults[1], vault_8632, ignore_keys=VAULT_IGNORE_KEYS)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ))
    vault_8543_details = {
        'identifier': 8543,
        'collateral_asset': 'ETH',
        'creation_ts': 1587910979,
        'total_interest_owed': '0',
        'total_liquidated': {
            'amount': '0',
            'usd_value': '0',
        },
        'events': [{
            'event_type': 'deposit',
            'value': {
                'amount': '1',
                'usd_value': '197.78',
            },
            'timestamp': 1587910979,
            'tx_hash': '0xf59858df4e42cdc2aecfebdcf38e1df841866c6a9eb3adb6bde9a844564a3bb6',
        }, {
            'event_type': 'generate',
            'value': {
                'amount': '80',
                'usd_value': '81.2',
            },
            'timestamp': 1587910979,
            'tx_hash': '0xf59858df4e42cdc2aecfebdcf38e1df841866c6a9eb3adb6bde9a844564a3bb6',
        }, {
            'event_type': 'payback',
            'value': {
                'amount': '80',
                'usd_value': '80.24',
            },
            'timestamp': 1589989097,
            'tx_hash': '0x52396f7d20db54e2e9e716698b643a39815ff149a6cccbe9c7597dc9e06bb9d3',
        }, {
            'event_type': 'deposit',
            'value': {
                'amount': '3.5',
                'usd_value': '734.475',
            },
            'timestamp': 1589993538,
            'tx_hash': '0x3c3942dc40fe68303098d91e765ceecaed4664bba0ef8f8e684b6f0e61968c6c',
        }, {
            'event_type': 'withdraw',
            'value': {
                'amount': '4.5',
                'usd_value': '893.52',
            },
            'timestamp': 1590043499,
            'tx_hash': '0xbcd4158f0089404f6ab5378517762cddc13d21c9d2fcf3fd45cf1cf4b656242c',
        }],
    }
    vault_8632_details = {
        'identifier': 8632,
        'collateral_asset': 'ETH',
        'creation_ts': 1588174425,
        'total_interest_owed': '0',
        'total_liquidated': {
            'amount': '0',
            'usd_value': '0',
        },
        'events': [{
            'event_type': 'deposit',
            'value': {
                'amount': '2.4',
                'usd_value': '517.32',
            },
            'timestamp': 1588174425,
            'tx_hash': '0xdb677a4257b5bdb305c278102d7b2460408bb7a3981414b994f4dd80a737ac2a',
        }, {
            'event_type': 'generate',
            'value': {
                'amount': '192',
                'usd_value': '194.688',
            },
            'timestamp': 1588174425,
            'tx_hash': '0xdb677a4257b5bdb305c278102d7b2460408bb7a3981414b994f4dd80a737ac2a',
        }, {
            'event_type': 'payback',
            'value': {
                'amount': '192',
                'usd_value': '192.192',
            },
            'timestamp': 1590042891,
            'tx_hash': '0x488a937677030cc810d0062001c08c944ecf6329b24a45ae9480bada8147bf75',
        }, {
            'event_type': 'deposit',
            'value': {
                'amount': '4.4',
                'usd_value': '873.664',
            },
            'timestamp': 1590043699,
            'tx_hash': '0x712ddb654b878bcb30c5344d7c18f7f796fe94abd6e5b8a22b2da0a6c99bb425',
        }, {
            'event_type': 'generate',
            'value': {
                'amount': '429.79',
                'usd_value': '430.21979',
            },
            'timestamp': 1590044118,
            'tx_hash': '0x36bfa27e157c03393a8816f6c1e3e990474f8f7473413810d87e2f4981d58044',
        }],
    }
    details = assert_proper_response_with_result(response)
    assert len(details) == 2
    assert_serialized_dicts_equal(details[0], vault_8543_details, ignore_keys=['stability_fee'])
    assert_serialized_dicts_equal(
        details[1],
        vault_8632_details,
        ignore_keys=[
            'total_interest_owed',
            'total_liquidated_amount',
            'total_liquidated_usd',
            'stability_fee',
        ],
        # Checking only the first 5 events, since that's how many we had when the test was written
        length_list_keymap={'events': 5},
    )


@requires_env([TestEnvironment.NIGHTLY])
@pytest.mark.skip('This vault is special and does not work. needs investigation')
@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_vaults']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_query_vaults_usdc_strange(rotkehlchen_api_server, ethereum_accounts):
    """Strange case of a USDC vault that is not queried correctly

    https://oasis.app/borrow/7538?network=mainnet
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    proxies_mapping = {
        ethereum_accounts[0]: '0x15fEaFd4358b8C03c889D6661b0CA1Be3389792F',  # 7538
    }

    mock_proxies(rotki, proxies_mapping, 'makerdao_vaults')
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultsresource",
    ))
    # That proxy has 3 vaults. We only want to test 7538, which is closed/repaid so just keep that
    vaults = [x for x in assert_proper_response_with_result(response) if x['identifier'] == 7538]
    vault_7538 = MakerdaoVault(
        identifier=7538,
        owner=ethereum_accounts[0],
        collateral_type='USDC-A',
        urn='0x70E58566C7baB6faaFE03fbA69DF45Ef4f48223B',
        collateral_asset=A_USDC,
        collateral=Balance(ZERO, ZERO),
        debt=Balance(ZERO, ZERO),
        collateralization_ratio=None,
        liquidation_ratio=FVal(1.1),
        liquidation_price=None,
    )
    expected_vaults = [vault_7538.serialize()]
    assert_serialized_lists_equal(expected_vaults, vaults)
    # And also make sure that the internal mapping will only query details of 7538
    makerdao_vaults = rotki.chains_aggregator.get_module('makerdao_vaults')
    makerdao_vaults.vault_mappings = {ethereum_accounts[0]: [vault_7538]}

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaovaultdetailsresource",
    ))
    vault_7538_details = {
        'identifier': 7538,
        'collateral_asset': A_USDC.identifier,
        'creation_ts': 1585145754,
        'total_interest_owed': '0.0005943266',
        'total_liquidated': {
            'amount': '0',
            'usd_value': '0',
        },
        'events': [{
            'event_type': 'deposit',
            'value': {
                'amount': '250.12',
                'usd_value': '250.12',
            },
            'timestamp': 1588664698,
            'tx_hash': '0x9ba4a6187fa2c49ba327e7c923846a08a1e972017ec41d3f9f66ef524f7dde59',
        }, {
            'event_type': 'generate',
            'value': {
                'amount': '25',
                'usd_value': '25',
            },
            'timestamp': 1588664698,
            'tx_hash': '0x9ba4a6187fa2c49ba327e7c923846a08a1e972017ec41d3f9f66ef524f7dde59',
        }, {
            'event_type': 'payback',
            'value': {
                'amount': '25.000248996',
                'usd_value': '25.000248996',
            },
            'timestamp': 1588696496,
            'tx_hash': '0x8bd960e7eb8b9e2b81d2446d1844dd63f94636c7800ea5e3b4d926ea0244c66c',
        }, {
            'event_type': 'deposit',
            'value': {
                'amount': '0.0113',
                'usd_value': '0.0113',
            },
            'timestamp': 1588720248,
            'tx_hash': '0x678c4da562173c102473f1904ff293a767ebac9ec6c7d728ef2fd41acf00a13a',
        }],
    }
    details = assert_proper_response_with_result(response)
    expected_details = [vault_7538_details]
    assert_serialized_lists_equal(expected_details, details)
