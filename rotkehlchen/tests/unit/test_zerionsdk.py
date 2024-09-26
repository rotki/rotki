import warnings as test_warnings
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.chain.ethereum.defi.zerionsdk import KNOWN_ZERION_PROTOCOL_NAMES, ZerionSDK
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import INFURA_ETH_NODE, wait_until_all_nodes_connected
from rotkehlchen.types import ChainID


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
@pytest.mark.parametrize('mocked_current_prices', [{
    'SNX': FVal('1'),
    'cUSDT': FVal('1'),
    'USDT': FVal('1'),
}])
def test_query_all_protocol_balances_for_account(
        ethereum_manager,
        function_scope_messages_aggregator,
        inquirer,
        ethereum_manager_connect_at_start,
        database,
):
    """Simple test that we can get balances for various defi protocols via zerion

    At the moment we are using random accounts that at some point have balances in a protocol.
    So the test just checks that some balance is queried. No specific.

    TODO: Perhaps create a small rotki tests account on the mainnet that keeps a
    certain balance in a few DeFi protocols and does not change them. This way
    we can have something stable to check again.
    """
    wait_until_all_nodes_connected(
        connect_at_start=ethereum_manager_connect_at_start,
        evm_inquirer=ethereum_manager.node_inquirer,
    )
    inquirer.inject_evm_managers(((ChainID.ETHEREUM, ethereum_manager),))
    zerion = ZerionSDK(ethereum_manager.node_inquirer, function_scope_messages_aggregator, database)  # noqa: E501
    with patch(
        'rotkehlchen.chain.evm.decoding.curve.curve_cache._query_curve_data_from_api',
        new=MagicMock(return_value=[]),
    ):
        balances = zerion.all_balances_for_account('0xf753beFE986e8Be8EBE7598C9d2b6297D9DD6662')

    if len(balances) == 0:
        test_warnings.warn(UserWarning('Test account for DeFi balances has no balances'))
        return

    assert len(balances) > 0
    errors = function_scope_messages_aggregator.consume_errors()
    assert len(errors) == 0
    warnings = function_scope_messages_aggregator.consume_warnings()
    assert len(warnings) == 0


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_protocol_names_are_known(
        ethereum_inquirer,
        function_scope_messages_aggregator,
        inquirer,  # pylint: disable=unused-argument
        database,
):
    zerion = ZerionSDK(ethereum_inquirer, function_scope_messages_aggregator, database)
    protocol_names = zerion.contract.call(
        node_inquirer=zerion.ethereum,
        method_name='getProtocolNames',
        arguments=[],
    )

    # Make sure that none of the already known names has changed. If it has changed.
    # If it has that may cause trouble as we saw in: https://github.com/rotki/rotki/issues/1803
    for expected_name in KNOWN_ZERION_PROTOCOL_NAMES:
        msg = f'Could not find "{expected_name}" in the zerion protocol names'
        assert expected_name in protocol_names, msg

    # informative pass with some warnings if a protocol is added by zerion we don't know about
    # We should check those warnings from time to time and add them to the known
    # protocols and add an icon for them among other things
    for name in protocol_names:
        if name not in KNOWN_ZERION_PROTOCOL_NAMES:
            test_warnings.warn(
                UserWarning(f'Unknown protocol "{name}" seen in Zerion protocol names'),
            )
