import random
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.chain.evm.types import string_to_evm_address
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
from rotkehlchen.types import ChecksumEvmAddress, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
SWAP_ADDRESS = string_to_evm_address('0x63BC843b9640c4D79d6aE0105bc39F773172d121')


@pytest.mark.parametrize('ethereum_accounts', [[SWAP_ADDRESS]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
def test_get_balances_module_not_activated(rotkehlchen_api_server: 'APIServer') -> None:
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'evmmodulebalancesresource', module='sushiswap'),
    )
    assert_error_response(
        response=response,
        contained_in_msg='sushiswap module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x31089Ef6f99FB83F95178DBBf08A7A4Bf2eC9fd2']])
@pytest.mark.parametrize('ethereum_modules', [['sushiswap']])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
def test_get_balances(
        rotkehlchen_api_server: 'APIServer',
        start_with_valid_premium: bool,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Check querying the sushiswap balances endpoint works. Uses real data. Needs the deposit
    event in uniswap to trigger the logic based on events to query pool balances.
    """
    tx_hash = deserialize_evm_tx_hash('0xbc99e10c1e48969f4a580229abebc97f7a358b7ba8365dca1f829f9c387bec51')  # noqa: E501
    ethereum_inquirer = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer  # noqa: E501
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    async_query = random.choice([False, True])
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'evmmodulebalancesresource', module='sushiswap'),
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

    address_balances = result[ethereum_accounts[0]]
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

            assert len(lp_asset['user_balance']) == 2
            assert lp_asset['user_balance']['amount']
            assert lp_asset['user_balance']['value']
