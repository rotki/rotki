from collections import defaultdict
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.hyperliquid.manager import HyperliquidManager
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.assets import A_HYPE, A_USDC
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
from rotkehlchen.fval import FVal

ADDR_A = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')


def test_query_balances_merges_evm_and_core_balances(
        hyperliquid_manager: HyperliquidManager,
) -> None:
    evm_balances: defaultdict[str, BalanceSheet] = defaultdict(BalanceSheet)
    evm_balances[ADDR_A].assets[A_HYPE][DEFAULT_BALANCE_LABEL] = Balance(
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
        mock_api_cls.return_value.query_balances.return_value = {A_USDC: FVal('500')}
        mock_inquirer.find_price.return_value = ONE

        result = hyperliquid_manager.query_balances(addresses=[ADDR_A])

    assert result[ADDR_A].assets[A_HYPE][DEFAULT_BALANCE_LABEL].amount == FVal('0.075')
    assert result[ADDR_A].assets[A_USDC][DEFAULT_BALANCE_LABEL].amount == FVal('500')


def test_query_balances_core_failure_returns_evm_only(
        hyperliquid_manager: HyperliquidManager,
) -> None:
    evm_balances: defaultdict[str, BalanceSheet] = defaultdict(BalanceSheet)
    evm_balances[ADDR_A].assets[A_HYPE][DEFAULT_BALANCE_LABEL] = Balance(
        amount=ONE,
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
        result = hyperliquid_manager.query_balances(addresses=[ADDR_A])

    assert result[ADDR_A].assets[A_HYPE][DEFAULT_BALANCE_LABEL].amount == ONE
    assert len(result[ADDR_A].assets) == 1


@pytest.mark.vcr(match_on=['uri', 'method', 'body'], record_mode='once')
def test_query_balances_fetches_core_balances_with_vcr(
        globaldb,
) -> None:
    result = HyperliquidAPI().query_balances(
        address=ADDR_A,
        include_discovered_dexs=False,
    )

    assert any(amount > ZERO for amount in result.values())
