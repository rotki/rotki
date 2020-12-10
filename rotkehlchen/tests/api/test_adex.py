import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests

# from rotkehlchen.constants.misc import ZERO
# from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
# from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.tests.unit.test_adex import TEST_ADDR as ADEX_TEST_ADDR
# from rotkehlchen.tests.utils.aave import AAVE_TEST_ACC_1
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
# from rotkehlchen.tests.utils.ethereum import INFURA_TEST
from rotkehlchen.tests.utils.rotkehlchen import setup_balances

# from rotkehlchen.typing import AssetAmount, Location, Price, Timestamp, TradeType


@pytest.mark.parametrize('ethereum_accounts', [[ADEX_TEST_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
def test_get_balances_module_not_activated(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
):
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'adexbalancesresource'),
    )
    assert_error_response(
        response=response,
        contained_in_msg='adex module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('ethereum_accounts', [[ADEX_TEST_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['adex']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_balances_premium(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
        rotki_premium_credentials,  # pylint: disable=unused-argument
        start_with_valid_premium,  # pylint: disable=unused-argument
):
    """Test get balances for premium users works as expected
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Set module premium is required for calling `get_balances()`
    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    rotki.chain_manager.adex.premium = premium

    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server, 'adexbalancesresource'),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    if len(result) != 1:
        test_warnings.warn(
            UserWarning(f'Test account {ADEX_TEST_ADDR} has no balances'),
        )
        return

    for pool_balance in result[ADEX_TEST_ADDR]:
        for attribute in ('pool_id', 'pool_name', 'balance', 'address'):
            assert attribute in pool_balance
        assert pool_balance['balance']['amount']
        assert pool_balance['balance']['usd_value']
