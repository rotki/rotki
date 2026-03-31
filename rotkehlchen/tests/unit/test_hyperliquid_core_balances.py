from collections import defaultdict
from unittest.mock import MagicMock, patch

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.hyperliquid.manager import HyperliquidManager
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal

ADDR_A = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')


def test_query_balances_merges_evm_and_core_balances() -> None:
    manager = HyperliquidManager.__new__(HyperliquidManager)
    manager.node_inquirer = MagicMock()

    evm_balances: defaultdict[str, BalanceSheet] = defaultdict(BalanceSheet)
    evm_balances[ADDR_A].assets[Asset('HYPE')][DEFAULT_BALANCE_LABEL] = Balance(
        amount=FVal('0.075'),
        value=FVal('1.5'),
    )

    with (
        patch(
            'rotkehlchen.chain.evm.manager.EvmManager.query_balances',
            return_value=evm_balances,
        ),
        patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI') as mock_api_cls,
        patch('rotkehlchen.chain.hyperliquid.manager.Inquirer') as mock_inquirer,
        patch('rotkehlchen.chain.hyperliquid.manager.CachedSettings'),
    ):
        mock_api_cls.return_value.query_balances.return_value = {Asset('USDC'): FVal('500')}
        mock_inquirer.find_price.return_value = FVal('1')

        result = manager.query_balances(addresses=[ADDR_A])

    assert result[ADDR_A].assets[Asset('HYPE')][DEFAULT_BALANCE_LABEL].amount == FVal('0.075')
    assert result[ADDR_A].assets[Asset('USDC')][DEFAULT_BALANCE_LABEL].amount == FVal('500')


def test_query_balances_core_failure_returns_evm_only() -> None:
    manager = HyperliquidManager.__new__(HyperliquidManager)
    manager.node_inquirer = MagicMock()

    evm_balances: defaultdict[str, BalanceSheet] = defaultdict(BalanceSheet)
    evm_balances[ADDR_A].assets[Asset('HYPE')][DEFAULT_BALANCE_LABEL] = Balance(
        amount=FVal('1'),
        value=FVal('20'),
    )

    with (
        patch(
            'rotkehlchen.chain.evm.manager.EvmManager.query_balances',
            return_value=evm_balances,
        ),
        patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI') as mock_api_cls,
    ):
        mock_api_cls.return_value.query_balances.side_effect = RemoteError('api down')
        result = manager.query_balances(addresses=[ADDR_A])

    assert result[ADDR_A].assets[Asset('HYPE')][DEFAULT_BALANCE_LABEL].amount == FVal('1')
    assert len(result[ADDR_A].assets) == 1
