import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus
from typing import Any, Optional

import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.ethereum.modules.compound.compound import A_COMP
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_CUSDC, A_DAI, A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import ChecksumEvmAddress

TEST_ACC1 = '0x2bddEd18E2CA464355091266B7616956944ee7eE'


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
def test_query_compound_balances(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: Optional[list[ChecksumEvmAddress]],
) -> None:
    """Check querying the compound balances endpoint works. Uses real data.

    TODO: Here we should use a test account for which we will know what balances
    it has and we never modify
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion'],
    )
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'compoundbalancesresource',
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=60)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    if len(result) != 1:
        test_warnings.warn(UserWarning(f'Test account {TEST_ACC1} has no compound balances'))
        return

    lending = result[TEST_ACC1]['lending']
    for _, entry in lending.items():
        assert len(entry) == 2
        assert len(entry['balance']) == 2
        assert 'amount' in entry['balance']
        assert 'usd_value' in entry['balance']
        assert '%' in entry['apy']
    borrowing = result[TEST_ACC1]['borrowing']
    for _, entry in borrowing.items():
        assert len(entry) == 2
        assert len(entry['balance']) == 2
        assert 'amount' in entry['balance']
        assert 'usd_value' in entry['balance']
        assert '%' in entry['apy']
    rewards = result[TEST_ACC1]['rewards']
    if len(rewards) != 0:
        assert len(rewards) == 1
        assert A_COMP.identifier in rewards


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
def test_query_compound_balances_module_not_activated(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: Optional[list[ChecksumEvmAddress]],
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=None)

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'compoundbalancesresource',
        ))
    assert_error_response(
        response=response,
        contained_in_msg='compound module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


mocked_historical_prices: dict[str, Any] = {
    A_DAI.identifier: {
        'USD': {
            1581184577: FVal('1.008'),
            1587601131: FVal('1.016'),
            1587766729: FVal('1.016'),
            1582378248: FVal('1.026'),
            1597288823: FVal('1.018'),
            1598038125: FVal('1.006'),
            1597954197: FVal('1.005'),
            1597369409: FVal('1.008'),
            1597452580: FVal('1.011'),
            1598138282: FVal('1.003'),
            1597982781: FVal('1.006'),
        },
    },
    A_CUSDC.identifier: {
        'USD': {
            1588459991: FVal('0.02102'),
            1586159213: FVal('0.02102'),
            1585790265: FVal('0.02101'),
            1585844643: FVal('0.02101'),
            1588464109: FVal('0.02102'),
        },
    },
    A_USDC.identifier: {
        'USD': {
            1585558039: ONE,
        },
    },
    'ETH': {
        'USD': {
            1585735112: FVal('136.05'),
            1585558230: FVal('132.31'),
            1585790265: FVal('141.59'),
            1585820470: FVal('141.59'),
            1585844643: FVal('141.59'),
            1585903297: FVal('141.45'),
            1586159213: FVal('171.66'),
            1588459991: FVal('214.15'),
            1588464109: FVal('210.06'),
        },
    },
    A_COMP.identifier: {
        'USD': {
            1597452580: FVal('196.9'),
        },
    },
}
mocked_current_prices: dict[str, Any] = {}


TEST_ACCOUNTS = [
    # For mint/redeem
    '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    # For borrowing/liquidations
    '0xC440f3C87DC4B6843CABc413916220D4f4FeD117',
    # For mint/redeem + comp
    '0xF59D4937BF1305856C3a267bB07791507a3377Ee',
    # For repay
    '0x65304d6aff5096472519ca86a6a1fea31cb47Ced',
]
