import random
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests
from flaky import flaky

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_LQTY, A_LUSD
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.mock import MockResponse

if TYPE_CHECKING:
    from rotkehlchen.externalapis.etherscan import Etherscan


LQTY_ADDR = string_to_evm_address('0x063c26fF1592688B73d8e2A18BA4C23654e2792E')
LQTY_STAKING = string_to_evm_address('0x00000029fF545c86524Ade7cAF132527707948C4')
LQTY_PROXY = string_to_evm_address('0x9476832d4687c14b2c1a04E2ee4693162a7340B6')
ADDR_WITHOUT_TROVE = string_to_evm_address('0xA0446D8804611944F1B527eCD37d7dcbE442caba')
JUSTIN = string_to_evm_address('0x3DdfA8eC3052539b6C9549F12cEA2C295cfF5296')
LIQUITY_POOL_DEPOSITOR = string_to_evm_address('0xFBcAFB005695afa660836BaC42567cf6917911ac')

liquity_mocked_historical_prices = {
    A_ETH: {
        'USD': {
            1627818194: FVal('3000'),
            1627818617: FVal('3000'),
            1627827057: FVal('3500'),
            1641529258: FVal('3395'),
        },
    },
    A_LQTY: {
        'USD': {
            1627827057.: FVal('3.7'),
        },
    },
    A_LUSD: {
        'USD': {
            1627818194: FVal('1.02'),
            1627818617: FVal('1.019'),
            1627827057: FVal('1.02'),
            1641529258: FVal('1.0010'),
        },
    },
}


@flaky(max_runs=3, min_passes=1)  # etherscan may occasionally time out
@pytest.mark.parametrize('ethereum_accounts', [[LQTY_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_trove_position(rotkehlchen_api_server, inquirer):  # pylint: disable=unused-argument
    """Test that we can get the status of the user's troves"""
    async_query = random.choice([False, True])
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'liquitytrovesresource',
    ), json={'async_query': async_query})
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert LQTY_ADDR in result
    trove_data = result[LQTY_ADDR]
    assert 'collateral' in trove_data
    assert 'debt' in trove_data
    assert 'collateralization_ratio' in trove_data
    assert 'liquidation_price' in trove_data
    assert trove_data['active'] is True


@pytest.mark.parametrize('should_mock_web3', [True])
@pytest.mark.parametrize('ethereum_mock_data', [{
    'eth_call': {
        '0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696': {
            '0x252dba420000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000200000000000000000000000004678f0a6958e4d2bc4f1baf7bc52e8f3564f3fe400000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024c455279100000000000000000000000000000029ff545c86524ade7caf132527707948c400000000000000000000000000000000000000000000000000000000': {  # noqa: E501
                # calling addr() on resolver for bruno.eth
                'latest': '0x0000000000000000000000000000000000000000000000000000000000f8434600000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000000',  # noqa: E501
            },
            '0xbce38bd70000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000000000000000060000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001a00000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d0000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002416934fc400000000000000000000000000000029ff545c86524ade7caf132527707948c4000000000000000000000000000000000000000000000000000000000000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000249beab5c000000000000000000000000000000029ff545c86524ade7caf132527707948c4000000000000000000000000000000000000000000000000000000000000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000248b9345ad00000000000000000000000000000029ff545c86524ade7caf132527707948c400000000000000000000000000000000000000000000000000000000': {  # noqa: E501
                # calling addr() on resolver for bruno.eth and coin type Bitcoin
                'latest': '0x00000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000003000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000e0000000000000000000000000000000000000000000000000000000000000016000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000161c26959c6f563b4000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000014ac11f9fee4cc7000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000055ca33d91',  # noqa: E501
            },
        },
    },
}])
@pytest.mark.parametrize('ethereum_accounts', [[LQTY_STAKING]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_trove_staking(rotkehlchen_api_server, inquirer):  # pylint: disable=unused-argument
    """Test that we can get the status of the staked lqty"""
    async_query = random.choice([False, True])
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'liquitystakingresource',
    ), json={'async_query': async_query})
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert LQTY_STAKING in result
    stake_data = result[LQTY_STAKING]
    assert stake_data == {
        'balances': {
            'staked': {
                'asset': A_LQTY.identifier,
                'amount': '25.491052675181405108',
                'usd_value': '38.2365790127721076620',
            },
            'lusd_rewards': {
                'asset': A_LUSD.identifier,
                'amount': '0.093099083885857991',
                'usd_value': '0.1396486258287869865',
            },
            'eth_rewards': {
                'asset': A_ETH.identifier,
                'amount': '0.000000023029038481',
                'usd_value': '0.0000000345435577215',
            },
        },
        'proxies': None,
    }


@pytest.mark.parametrize('ethereum_accounts', [[ADDR_WITHOUT_TROVE]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_account_without_info(rotkehlchen_api_server, inquirer):  # pylint: disable=unused-argument
    """Test that we can get the status of the trove and the staked lqty"""
    async_query = random.choice([False, True])
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'liquitytrovesresource',
    ), json={'async_query': async_query})
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert ADDR_WITHOUT_TROVE not in result


@pytest.mark.parametrize('ethereum_accounts', [[LQTY_PROXY, ADDR_WITHOUT_TROVE, LQTY_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_account_with_proxy(rotkehlchen_api_server, inquirer):  # pylint: disable=unused-argument
    """Test that we can get the status of a trove created using DSProxy"""
    async_query = random.choice([False, True])
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'liquitytrovesresource',
    ), json={'async_query': async_query})
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert LQTY_PROXY in result
    assert ADDR_WITHOUT_TROVE not in result
    assert LQTY_ADDR in result
    # test that the list of addresses was not mutated
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert len(rotki.chains_aggregator.accounts.eth) == 3


@pytest.mark.parametrize('ethereum_accounts', [[JUSTIN, LIQUITY_POOL_DEPOSITOR]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_stability_pool(rotkehlchen_api_server):
    """Test that we can get the status of the deposits in the stability pool"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    eth_multicall = rotki.chains_aggregator.ethereum.node_inquirer.contracts.contract(string_to_evm_address('0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696'))  # noqa: E501

    def mock_etherscan_transaction_response(etherscan: 'Etherscan'):
        def mocked_request_dict(url, *_args, **_kwargs):
            # if '0xeefBa1e63905eF1D7ACbA5a8513c70307C1cE441' in url:
            if f'to={eth_multicall.address}' in url:
                if 'data=0x252dba42' in url:  # aggregate
                    payload = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000000000000000000f1d3ed00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000000"}'  # noqa: E501
                elif 'data=0xbce38bd7' in url:  # tryAggregate
                    payload = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000014000000000000000000000000000000000000000000000000000000000000001c0000000000000000000000000000000000000000000000000000000000000024000000000000000000000000000000000000000000000000000000000000002c000000000000000000000000000000000000000000000000000000000000003400000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000025741350d10dcdd3f00000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000182ca8387c1e947389a80000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000872593255709e930eb1b7000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000002d94f2ad87a21c00000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000008737d8d1f366513ff80000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000073bcd36975544d15f2be"}'  # noqa: E501
            else:
                raise AssertionError('Got in unexpected section during test')
            return MockResponse(200, payload)
        return patch.object(etherscan.session, 'get', wraps=mocked_request_dict)

    async_query = random.choice([False, True])
    with mock_etherscan_transaction_response(rotki.chains_aggregator.ethereum.node_inquirer.etherscan):  # noqa: E501
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'liquitystabilitypoolresource',
        ), json={'async_query': async_query})

    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert JUSTIN in result
    assert LIQUITY_POOL_DEPOSITOR in result
    expected_amount = FVal('43.180853032438783295')
    assert result[JUSTIN]['balances']['gains']['asset'] == A_ETH
    assert FVal(result[JUSTIN]['balances']['gains']['amount']) == expected_amount
    assert FVal(result[JUSTIN]['balances']['gains']['usd_value']) == expected_amount * FVal(1.5)
    expected_amount = FVal('114160.573902982554552744')
    assert result[JUSTIN]['balances']['rewards']['asset'] == A_LQTY
    assert FVal(result[JUSTIN]['balances']['rewards']['amount']) == expected_amount
    assert FVal(result[JUSTIN]['balances']['rewards']['usd_value']) == expected_amount * FVal(1.5)
    expected_amount = FVal('10211401.723115634393264567')
    assert result[JUSTIN]['balances']['deposited']['asset'] == A_LUSD
    assert FVal(result[JUSTIN]['balances']['deposited']['amount']) == expected_amount
    assert FVal(result[JUSTIN]['balances']['deposited']['usd_value']) == expected_amount * FVal(1.5)  # noqa: E501


@pytest.mark.parametrize('use_custom_database', ['liquity_stats.db'])
@pytest.mark.parametrize('new_db_unlock_actions', [None])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('add_accounts_to_db', [[False]])
@pytest.mark.parametrize('ethereum_accounts', [
    [
        '0xF662f831361c8Ab48d807f7753eb3d641be25d24',
        '0xbB8311c7bAD518f0D8f907Cad26c5CcC85a06dC4',
    ],
])
def test_staking_stats(rotkehlchen_api_server, ethereum_accounts):
    """
    Test that the stats generated by the liquity endpoint are correct using pre-queried
    information and that the stats combining all the data are consistent with the
    information for each tracked address
    """
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'evmpendingtransactionsdecodingresource',
        ), json={'async_query': False, 'data': [{'evm_chain': 'ethereum'}]},
    )
    async_query = random.choice([False])
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'liquitystakingstats',
    ), json={'async_query': async_query})
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    global_stats = result['global_stats']
    address_0_data = result['by_address'][ethereum_accounts[0]]
    address_1_data = result['by_address'][ethereum_accounts[1]]
    assert FVal(address_1_data['total_deposited_stability_pool']) == FVal('396454.0')
    assert FVal(address_0_data['total_deposited_stability_pool']) == FVal('1519146.7290263602')
    assert FVal(global_stats['total_deposited_stability_pool']) == FVal(address_0_data['total_deposited_stability_pool']) + FVal(address_1_data['total_deposited_stability_pool'])  # noqa: E501
    assert len(global_stats['staking_gains']) == 3
    assert len(global_stats['stability_pool_gains']) == 2
    assert FVal(global_stats['stability_pool_gains'][0]['amount']).is_close(FVal(address_0_data['stability_pool_gains'][0]['amount']) + FVal(address_1_data['stability_pool_gains'][0]['amount']), max_diff='1e-8')  # noqa: E501
    assert address_0_data['stability_pool_gains'][0]['amount'] == '1.7820064710306824'
    assert address_1_data['stability_pool_gains'][0]['amount'] == '12.294706987216218'
    assert address_1_data['stability_pool_gains'][1]['amount'] == '4240.34942308358'


@pytest.mark.vcr(match_on=['uri', 'method'], filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xbB8311c7bAD518f0D8f907Cad26c5CcC85a06dC4']])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_proxy_info_is_shown(rotkehlchen_api_server, ethereum_accounts):
    """Check that information about proxies is added to the responses for liquity endpoints"""
    user_address = ethereum_accounts[0]
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'liquitystabilitypoolresource',
    ), json={'async_query': False})

    result = assert_proper_response_with_result(response)
    assert 'gains' in result[user_address]['proxies']['0x33EAfDB72b69BFBe6b5911eDCbab41011e63C523']

    # check the other endpoint.
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'liquitystakingresource',
    ), json={'async_query': False})
    result = assert_proper_response_with_result(response)
    assert 'staked' in result[user_address]['proxies']['0x33EAfDB72b69BFBe6b5911eDCbab41011e63C523']  # noqa: E501
