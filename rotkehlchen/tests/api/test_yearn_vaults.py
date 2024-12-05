import random
from contextlib import ExitStack
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer

TEST_ACC1 = '0x7780E86699e941254c8f4D9b7eB08FF7e96BBE10'
TEST_V2_ACC2 = '0x915C4580dFFD112db25a6cf06c76cDd9009637b7'


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('ethereum_modules', [['yearn_vaults']])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2023-05-27 22:45:45 GMT')
def test_query_yearn_vault_balances(rotkehlchen_api_server: 'APIServer') -> None:
    async_query = random.choice([True, False])
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'yearnvaultsbalancesresource',
    ), json={'async_query': async_query})
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_sync_response_with_result(response)

    for vault in result[TEST_ACC1].values():
        assert '%' in vault['roi']
        assert FVal(vault['vault_value']['amount']) > ZERO
        assert FVal(vault['vault_value']['usd_value']) > ZERO
        assert FVal(vault['underlying_value']['amount']) > ZERO
        assert FVal(vault['underlying_value']['usd_value']) > ZERO


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_V2_ACC2]])
@pytest.mark.parametrize('ethereum_modules', [['yearn_vaults_v2']])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_yearn_vault_v2_balances(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    async_query = random.choice([True, False])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        token_balances={
            EvmToken('eip155:1/erc20:0x5f18C75AbDAe578b483E5F43f12a39cF75b973a9'): ['70000000'],
            EvmToken('eip155:1/erc20:0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'): ['2550000000000000000000'],  # noqa: E501
        },
    )

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'yearnvaultsv2balancesresource',
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_sync_response_with_result(response)

    for vault in result[TEST_V2_ACC2].values():
        assert '%' in vault['roi']
        assert FVal(vault['vault_value']['amount']) > ZERO
        assert FVal(vault['vault_value']['usd_value']) > ZERO
        assert FVal(vault['underlying_value']['amount']) > ZERO
        assert FVal(vault['underlying_value']['usd_value']) > ZERO
