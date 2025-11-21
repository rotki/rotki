import random
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.chain.evm.types import ChecksumEvmAddress, string_to_evm_address
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.ethereum import (
    INFURA_ETH_NODE,
    get_decoded_events_of_transaction,
)
from rotkehlchen.types import deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer

# Addresses
# DAI/WETH pool: 0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11
# From that pool find a holder and test
LP_HOLDER_ADDRESS = string_to_evm_address('0x1778CB9fd8D489C740568A9bF16004D948d9b6bF')


@pytest.mark.parametrize('ethereum_accounts', [[LP_HOLDER_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
def test_get_balances_module_not_activated(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],  # pylint: disable=unused-argument
) -> None:
    response = requests.get(
        api_url_for(
            api_server=rotkehlchen_api_server,
            endpoint='evmmodulebalanceswithversionresource',
            module='uniswap',
            version='2',
        ),
    )
    assert_error_response(
        response=response,
        contained_in_msg='uniswap module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[LP_HOLDER_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
def test_get_balances(
        rotkehlchen_api_server: 'APIServer',
        start_with_valid_premium: bool,
        inquirer: Inquirer,  # pylint: disable=unused-argument
) -> None:
    """
    Check querying the uniswap balances endpoint works. Uses real data. Needs the deposit
    event in uniswap to trigger the logic based on events to query pool balances.

    TODO: https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=46377335
    """
    tx_hash = deserialize_evm_tx_hash('0x856a5b5d95623f85923938e1911dfda6ad1dd185f45ab101bac99371aeaed329')  # noqa: E501
    ethereum_inquirer = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer  # noqa: E501
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    async_query = random.choice([False, True])
    response = requests.get(
        api_url_for(
            api_server=rotkehlchen_api_server,
            endpoint='evmmodulebalanceswithversionresource',
            module='uniswap',
            version='2',
        ),
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
        result = assert_proper_sync_response_with_result(response)

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
        assert lp['user_balance']['value']

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

            assert len(lp_asset['user_balance']) == 3
            assert lp_asset['user_balance']['amount']
            assert lp_asset['user_balance']['value']

        if lp['address'] == '0xF20EF17b889b437C151eB5bA15A47bFc62bfF469':
            assert lp['user_balance']['amount'] == '0.000120107033813428'
