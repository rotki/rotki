import random
import warnings as test_warnings
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests
from flaky import flaky

from rotkehlchen.chain.ethereum.interfaces.ammswap.types import LiquidityPoolEventsBalance
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_WETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.constants import A_DOLLAR_BASED
from rotkehlchen.tests.utils.ethereum import (
    ETHEREUM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED,
    get_decoded_events_of_transaction,
)
from rotkehlchen.types import AssetAmount, Price, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer

# Addresses
# DAI/WETH pool: 0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11
# From that pool find a holder and test
LP_HOLDER_ADDRESS = string_to_evm_address('0x1778CB9fd8D489C740568A9bF16004D948d9b6bF')
LP_V3_HOLDER_ADDRESS = string_to_evm_address('0xEf45d2ad5e0E01e4B57A6229B590c7982997Ace8')

# Uniswap Factory contract
TEST_ADDRESS_FACTORY_CONTRACT = (
    string_to_evm_address('0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f')
)


@pytest.mark.parametrize('ethereum_accounts', [[LP_HOLDER_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
def test_get_balances_module_not_activated(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
):
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'modulebalancesresource', module='uniswap_v2'),
    )
    assert_error_response(
        response=response,
        contained_in_msg='uniswap module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('ethereum_accounts', [[LP_HOLDER_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize(*ETHEREUM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
def test_get_balances(
        rotkehlchen_api_server: 'APIServer',
        start_with_valid_premium: bool,
        inquirer: Inquirer,  # pylint: disable=unused-argument
):
    """Check querying the uniswap balances endpoint works. Uses real data"""
    tx_hex = deserialize_evm_tx_hash('0x856a5b5d95623f85923938e1911dfda6ad1dd185f45ab101bac99371aeaed329')  # noqa: E501
    ethereum_inquirer = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer  # noqa: E501
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    async_query = random.choice([False, True])
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'modulebalancesresource', module='uniswap_v2'),
        json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(
            server=rotkehlchen_api_server,
            task_id=task_id,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 10,
        )
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)

    address_balances = result[LP_HOLDER_ADDRESS]
    for lp in address_balances:
        # LiquidityPool attributes
        assert lp['address'].startswith('0x')
        assert len(lp['assets']) == 2
        if start_with_valid_premium:
            assert lp['total_supply'] is not None
        else:
            assert lp['total_supply'] is None
        assert lp['user_balance']['amount']
        assert lp['user_balance']['usd_value']

        # LiquidityPoolAsset attributes
        for lp_asset in lp['assets']:
            lp_asset_type = type(lp_asset['asset'])

            assert lp_asset_type in (str, dict)

            # Unknown asset, at least contains token address
            if lp_asset_type is dict:
                assert lp_asset['asset']['evm_address'].startswith('0x')
            # Known asset, contains identifier
            else:
                assert not lp_asset['asset'].startswith('0x')

            if start_with_valid_premium:
                assert lp_asset['total_amount'] is not None
            else:
                assert lp_asset['total_amount'] is None
            assert lp_asset['usd_price']
            assert len(lp_asset['user_balance']) == 2
            assert lp_asset['user_balance']['amount']
            assert lp_asset['user_balance']['usd_value']

        if lp['address'] == '0xF20EF17b889b437C151eB5bA15A47bFc62bfF469':
            assert lp['user_balance']['amount'] == '0.000120107033813428'


@pytest.mark.parametrize('ethereum_accounts', [['0x6C0F75eb3D69B9Ea2fB88dbC37fc086a12bBC93F']])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_get_events_history_filtering_by_timestamp_case1(
        rotkehlchen_api_server: 'APIServer',
        inquirer,  # pylint: disable=unused-argument
        ethereum_accounts,
):
    """Test the events balances from 1604273256 to 1604283808 (both included).

    LPs involved by the address within this time range: 1, $BASED-WETH

    By calling the endpoint with a specific time range:
      - Not all the events are queried.
      - The events balances do not factorise the current balances in the
      protocol (meaning the response amounts should be assertable).
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    ethereum_inquirer = rotki.chains_aggregator.ethereum.node_inquirer
    database = rotki.data.db

    expected_events_balances_1 = [
        LiquidityPoolEventsBalance(
            pool_address=string_to_evm_address('0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89'),
            token0=A_DOLLAR_BASED.resolve_to_evm_token(),
            token1=A_WETH.resolve_to_evm_token(),
            profit_loss0=AssetAmount(FVal('35.489683548121546956')),
            profit_loss1=AssetAmount(FVal('-0.059966416263997186')),
            usd_profit_loss=Price(FVal('-35.19515540870021242982170811')),
        ),
    ]

    tx_hex_1 = deserialize_evm_tx_hash('0xa9ce328d0e2d2fa8932890bfd4bc61411abd34a4aaa48fc8b853c873a55ea824')  # noqa: E501
    tx_hex_2 = deserialize_evm_tx_hash('0x27ddad4f187e965a3ee37257b75d297ff79b2663fd0a2d8d15f7efaccf1238fa')  # noqa: E501
    for tx_hex in (tx_hex_1, tx_hex_2):
        get_decoded_events_of_transaction(
            evm_inquirer=ethereum_inquirer,
            database=database,
            tx_hash=tx_hex,
        )

    # Call time range
    from_timestamp = 1604273256
    to_timestamp = 1604283808

    async_query = random.choice([False, True])
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'modulestatsresource',
            module='uniswap',
        ),
        json={
            'async_query': async_query,
            'from_timestamp': from_timestamp,
            'to_timestamp': to_timestamp,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=120)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)

    events_balances = result[ethereum_accounts[0]]
    assert len(events_balances) == 1
    expected_event = expected_events_balances_1[0].serialize()
    expected_event.pop('usd_profit_loss')
    events_balances[0].pop('usd_profit_loss')
    assert expected_event == events_balances[0]


@flaky(max_runs=3, min_passes=1)  # etherscan may occasionally time out
@pytest.mark.parametrize('ethereum_accounts', [[LP_V3_HOLDER_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_v3_balances_premium(rotkehlchen_api_server):
    """Check querying the uniswap balances v3 endpoint works."""
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'modulebalancesresource', module='uniswap_v3'),
    )
    result = assert_proper_response_with_result(response)

    if LP_V3_HOLDER_ADDRESS not in result or len(result[LP_V3_HOLDER_ADDRESS]) == 0:
        test_warnings.warn(
            UserWarning(f'Test account {LP_V3_HOLDER_ADDRESS} has no uniswap balances'),
        )
        return

    address_balances = result[LP_V3_HOLDER_ADDRESS]
    for lp in address_balances:
        # LiquidityPool attributes
        assert lp['address'].startswith('0x')
        assert len(lp['price_range']) == 2
        assert isinstance(lp['price_range'], list)
        assert lp['nft_id']
        assert isinstance(lp['nft_id'], str)
        assert len(lp['assets']) == 2
        assert lp['user_balance']['amount']
        assert lp['user_balance']['usd_value']

        # LiquidityPoolAsset attributes
        for lp_asset in lp['assets']:
            lp_asset_type = type(lp_asset['asset'])

            assert lp_asset_type in (str, dict)

            # Unknown asset, at least contains token address
            if lp_asset_type is dict:
                assert lp_asset['asset']['evm_address'].startswith('0x')
            # Known asset, contains identifier
            else:
                assert not lp_asset['asset'].startswith('0x')
            assert lp_asset['total_amount'] is not None
            assert lp_asset['usd_price']
            assert len(lp_asset['user_balance']) == 2
            assert lp_asset['user_balance']['amount']
            assert lp_asset['user_balance']['usd_value']


@pytest.mark.parametrize('ethereum_accounts', [[LP_V3_HOLDER_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [False])
def test_get_v3_balances_no_premium(rotkehlchen_api_server):
    """Check querying the uniswap balances v3 endpoint works."""
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'modulebalancesresource', module='uniswap_v3'),
    )
    result = assert_proper_response_with_result(response)

    if LP_V3_HOLDER_ADDRESS not in result or len(result[LP_V3_HOLDER_ADDRESS]) == 0:
        test_warnings.warn(
            UserWarning(f'Test account {LP_V3_HOLDER_ADDRESS} has no uniswap balances'),
        )
        return

    address_balances = result[LP_V3_HOLDER_ADDRESS]
    for lp in address_balances:
        # LiquidityPool attributes
        assert lp['address'].startswith('0x')
        assert len(lp['price_range']) == 2
        assert isinstance(lp['price_range'], list)
        assert lp['nft_id']
        assert isinstance(lp['nft_id'], str)
        assert len(lp['assets']) == 2
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
            # check that the user_balances are not returned
            assert lp_asset['total_amount'] is None
            assert FVal(lp_asset['usd_price']) == ZERO
            assert FVal(lp_asset['user_balance']['amount']) == ZERO
            assert FVal(lp_asset['user_balance']['usd_value']) == ZERO
