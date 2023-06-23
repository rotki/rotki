import random
from http import HTTPStatus
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.ethereum import (
    ETHEREUM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED,
    get_decoded_events_of_transaction,
)
from rotkehlchen.types import ChecksumEvmAddress, deserialize_evm_tx_hash

SWAP_ADDRESS = string_to_evm_address('0x63BC843b9640c4D79d6aE0105bc39F773172d121')


@pytest.mark.parametrize('ethereum_accounts', [[SWAP_ADDRESS]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
def test_get_balances_module_not_activated(rotkehlchen_api_server):
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'modulebalancesresource', module='sushiswap'),
    )
    assert_error_response(
        response=response,
        contained_in_msg='sushiswap module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('ethereum_accounts', [['0x31089Ef6f99FB83F95178DBBf08A7A4Bf2eC9fd2']])
@pytest.mark.parametrize('ethereum_modules', [['sushiswap']])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize(*ETHEREUM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
def test_get_balances(
        rotkehlchen_api_server: APIServer,
        start_with_valid_premium: bool,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        ethereum_accounts: list[ChecksumEvmAddress],
):
    """Check querying the sushiswap balances endpoint works. Uses real data"""
    tx_hex = deserialize_evm_tx_hash('0xbc99e10c1e48969f4a580229abebc97f7a358b7ba8365dca1f829f9c387bec51')  # noqa: E501
    ethereum_inquirer = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer  # noqa: E501
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    async_query = random.choice([False, True])
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'modulebalancesresource', module='sushiswap'),
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


# Get events history tests
TEST_EVENTS_ADDRESS_1 = '0x91E6A718d9A4CB67bDA0e4bf96C6C8154b7F4120'


@pytest.mark.parametrize('ethereum_accounts', [[TEST_EVENTS_ADDRESS_1]])
@pytest.mark.parametrize('ethereum_modules', [['sushiswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_events_history_filtering_by_timestamp(rotkehlchen_api_server: 'APIServer'):
    """Test the events balances from 1627401169 to 1627401170 (both included)."""
    tx_hex = deserialize_evm_tx_hash('0xb226ddb8cbb286a7a998a35263ad258110eed5f923488f03a8d890572cd4608e')  # noqa: E501
    ethereum_inquirer = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer  # noqa: E501
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    # Call time range
    from_timestamp = 1627401169
    to_timestamp = 1627401170
    async_query = random.choice([False, True])
    with patch(
        'rotkehlchen.chain.ethereum.modules.sushiswap.sushiswap.Sushiswap.get_balances',
        side_effect=lambda _: {},
    ):
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'modulestatsresource',
                module='sushiswap',
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

    events_balances = result[TEST_EVENTS_ADDRESS_1]

    assert len(events_balances) == 1
