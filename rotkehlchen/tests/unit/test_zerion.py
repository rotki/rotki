import warnings as test_warnings

import pytest

from rotkehlchen.chain.ethereum.zerion import Zerion
from rotkehlchen.fval import FVal


@pytest.mark.parametrize('mocked_current_prices', [{
    'SNX': FVal('1'),
    'cUSDT': FVal('1'),
    'USDT': FVal('1'),
}])
def test_query_all_protocol_balances_for_account(
        ethereum_manager,
        function_scope_messages_aggregator,
        inquirer,  # pylint: disable=unused-argument
):
    """Simple test that we can get balances for various defi protocols via zerion

    At the moment we are using random accounts that at some point have balances in a protocol.
    So the test just checks that some balance is queried. No specific.

    TODO: Perhaps create a small rotki tests account on the mainnet that keeps a
    certain balance in a few DeFi protocols and does not change them. This way
    we can have something stable to check again.
    """
    zerion = Zerion(ethereum_manager, function_scope_messages_aggregator)
    balances = zerion.all_balances_for_account('0xf753beFE986e8Be8EBE7598C9d2b6297D9DD6662')
    if len(balances) == 0:
        test_warnings.warn(UserWarning('Test account for DeFi balances has no balances'))
        return

    assert len(balances) > 0
    errors = function_scope_messages_aggregator.consume_errors()
    assert len(errors) == 0
    warnings = function_scope_messages_aggregator.consume_warnings()
    assert len(warnings) == 0
