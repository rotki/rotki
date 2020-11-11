from http import HTTPStatus
import random
import warnings as test_warnings

from eth_utils.typing import HexAddress, HexStr
import pytest
import requests

from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.typing import ChecksumEthAddress


# Addresses
# Harvest Finance USDC-WETH vault
TEST_ADDRESS_USDC_WETH = ChecksumEthAddress(
    HexAddress(HexStr('0xA79a083FDD87F73c2f983c5551EC974685D6bb36')),
)


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDRESS_USDC_WETH]])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
def test_get_balances_module_not_activated(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
):
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'uniswapbalancesresource'),
    )
    assert_error_response(
        response=response,
        contained_in_msg='uniswap module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDRESS_USDC_WETH]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_balances_graph(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
        rotki_premium_credentials,
        start_with_valid_premium,
):
    """Check querying the uniswap balances endpoint works. Uses real data.

    Requires the graph available and premium credentials.

    TODO: Here we should use a test account for which we will know what
    balances it has and we never modify
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    # Set module premium attribute
    rotki.chain_manager.uniswap.premium = premium

    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'uniswapbalancesresource'),
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
            UserWarning(f'Test account {TEST_ADDRESS_USDC_WETH} has no uniswap balances'),
        )
        return

    address_balances = result[TEST_ADDRESS_USDC_WETH]

    for lp in address_balances:
        # LiquidityPool attributes
        assert lp['address'].startswith('0x')
        assert len(lp['assets']) == 2
        assert lp['total_supply']
        assert lp['user_balance']['amount']
        assert lp['user_balance']['usd_value']

        # LiquidityPoolAsset attributes
        for lp_asset in lp['assets']:
            lp_asset_type = type(lp_asset['asset'])

            assert lp_asset_type in (str, dict)

            # Unknown asset, at least contains token address
            if lp_asset_type is dict:
                assert lp_asset['asset']['ethereum_address'].startswith('0x')
            # Known asset, contains identifier
            else:
                assert not lp_asset['asset'].startswith('0x')

            assert lp_asset['total_amount']
            assert lp_asset['usd_price']
            assert len(lp_asset['user_balance']) == 2
            assert lp_asset['user_balance']['amount']
            assert lp_asset['user_balance']['usd_value']
