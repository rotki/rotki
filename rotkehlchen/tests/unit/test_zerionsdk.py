import warnings as test_warnings

import pytest

from rotkehlchen.chain.ethereum.defi.zerionsdk import ZerionSDK
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
    zerion = ZerionSDK(ethereum_manager, function_scope_messages_aggregator)
    balances = zerion.all_balances_for_account('0xf753beFE986e8Be8EBE7598C9d2b6297D9DD6662')
    if len(balances) == 0:
        test_warnings.warn(UserWarning('Test account for DeFi balances has no balances'))
        return

    assert len(balances) > 0
    errors = function_scope_messages_aggregator.consume_errors()
    assert len(errors) == 0
    warnings = function_scope_messages_aggregator.consume_warnings()
    assert len(warnings) == 0


KNOWN_ZERION_PROTOCOL_NAMES = (
    'Curve • Vesting',
    'Curve • Liquidity Gauges',
    'ygov.finance (v1)',
    'ygov.finance (v2)',
    'mStable • Staking',
    'Swerve • Liquidity Gauges',
    'Pickle Finance • Farms',
    'Pickle Finance • Staking',
    'Aave • Staking',
    'C.R.E.A.M. • Staking',
    'Compound Governance',
    'zlot.finance',
    'FinNexus',
    'Pickle Finance',
    'DODO',
    'Berezka',
    'bZx',
    'C.R.E.A.M.',
    'Swerve',
    'SashimiSwap',
    'Harvest',
    'Harvest • Profit Sharing',
    'KIMCHI',
    'SushiSwap',
    'Nexus Mutual',
    'Mooniswap',
    'Matic',
    'Aragon',
    'Melon',
    'yearn.finance • Vaults',
    'KeeperDAO',
    'mStable',
    'KyberDAO',
    'DDEX • Spot',
    'DDEX • Margin',
    'DDEX • Lending',
    'Ampleforth',
    'Maker Governance',
    'Gnosis Protocol',
    'Chi Gastoken by 1inch',
    'Idle • Risk-Adjusted',
    'Aave • Uniswap Market',
    'Uniswap V2',
    'PieDAO',
    'Multi-Collateral Dai',
    'Bancor',
    'DeFi Money Market',
    'TokenSets',
    '0x Staking',
    'Uniswap V1',
    'Synthetix',
    'PoolTogether',
    'Dai Savings Rate',
    'Chai',
    'iearn.finance (v3)',
    'iearn.finance (v2)',
    'Idle',
    'Idle • Early Rewards',
    'dYdX',
    'Curve',
    'Compound',
    'Balancer',
    'Aave',
    'SnowSwap',
    'Aave V2',
    'Aave V2 • Variable Debt',
    'Aave V2 • Stable Debt',
)


def test_protocol_names_are_known(
        ethereum_manager,
        function_scope_messages_aggregator,
        inquirer,  # pylint: disable=unused-argument
):
    zerion = ZerionSDK(ethereum_manager, function_scope_messages_aggregator)
    protocol_names = zerion.contract.call(
        ethereum=zerion.ethereum,
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
