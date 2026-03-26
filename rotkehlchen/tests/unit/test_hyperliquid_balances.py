"""Tests for Hyperliquid balance query overrides.

The MyCrypto BalanceScanner contract is not deployed on Hyperliquid L1,
so HyperliquidInquirer and HyperliquidTokens override the default
batch-scanning methods with individual RPC calls.  HyperliquidManager
also merges proprietary spot/perp balances from the Hyperliquid Info API.
"""

from collections import defaultdict
from unittest.mock import MagicMock, patch

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.hyperliquid.manager import HyperliquidManager
from rotkehlchen.chain.hyperliquid.node_inquirer import HyperliquidInquirer
from rotkehlchen.chain.hyperliquid.tokens import HyperliquidTokens
from rotkehlchen.chain.structures import EvmTokenDetectionData
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal

ADDR_A = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')
ADDR_B = string_to_evm_address('0x04B0f18B9B1fF987c5D5e134516F449Aa9A2e004')


# ── HyperliquidInquirer.get_multi_balance ────────────────────────────


def test_get_multi_balance_individual_calls() -> None:
    """get_multi_balance queries each address individually via _query."""
    inquirer = HyperliquidInquirer.__new__(HyperliquidInquirer)
    inquirer.chain_name = 'hyperliquid'
    inquirer.blockchain = MagicMock()
    inquirer.blockchain.serialize.return_value = 'hyperliquid'

    call_order = [MagicMock()]

    # Return different raw wei values per address
    def fake_query(_self, method, call_order, **kwargs):
        if kwargs['address'] == ADDR_A:
            return 75_000_000_000_000_000  # 0.075 HYPE in wei
        return 1_000_000_000_000_000_000  # 1.0 HYPE in wei

    with (
        patch.object(HyperliquidInquirer, '_query', new=fake_query),
        patch.object(HyperliquidInquirer, 'default_call_order', return_value=call_order),
    ):
        result = inquirer.get_multi_balance(accounts=[ADDR_A, ADDR_B], call_order=call_order)

    assert result[ADDR_A] == FVal('0.075')
    assert result[ADDR_B] == FVal('1')


def test_get_multi_balance_empty_accounts() -> None:
    """Empty account list returns empty dict without making any calls."""
    inquirer = HyperliquidInquirer.__new__(HyperliquidInquirer)
    with patch.object(
        HyperliquidInquirer,
        '_query',
        new=MagicMock(side_effect=AssertionError('should not be called')),
    ):
        result = inquirer.get_multi_balance(accounts=[])
    assert result == {}


def test_get_multi_balance_rpc_failure_returns_zero() -> None:
    """If _query raises RemoteError for an address, that address gets zero balance."""
    inquirer = HyperliquidInquirer.__new__(HyperliquidInquirer)
    inquirer.chain_name = 'hyperliquid'
    inquirer.blockchain = MagicMock()
    inquirer.blockchain.serialize.return_value = 'hyperliquid'

    def failing_query(_self, method, call_order, **kwargs):
        if kwargs['address'] == ADDR_A:
            raise RemoteError('node down')
        return 2_000_000_000_000_000_000

    with (
        patch.object(HyperliquidInquirer, '_query', new=failing_query),
        patch.object(HyperliquidInquirer, 'default_call_order', return_value=[MagicMock()]),
    ):
        result = inquirer.get_multi_balance(accounts=[ADDR_A, ADDR_B])

    assert result[ADDR_A] == FVal(0)
    assert result[ADDR_B] == FVal('2')


# ── HyperliquidTokens.get_token_balances ─────────────────────────────


def test_get_token_balances_individual_calls() -> None:
    """get_token_balances calls balanceOf individually per token."""
    tokens_manager = HyperliquidTokens.__new__(HyperliquidTokens)
    mock_inquirer = MagicMock()
    mock_inquirer.chain_name = 'hyperliquid'
    mock_inquirer.contracts.erc20_abi = [{'name': 'balanceOf'}]
    tokens_manager.evm_inquirer = mock_inquirer

    token_a = EvmTokenDetectionData(
        identifier='eip155:999/erc20:0x5555555555555555555555555555555555555555',
        address=string_to_evm_address('0x5555555555555555555555555555555555555555'),
        decimals=18,
    )
    token_b = EvmTokenDetectionData(
        identifier='eip155:999/erc20:0x1111111111111111111111111111111111111111',
        address=string_to_evm_address('0x1111111111111111111111111111111111111111'),
        decimals=6,
    )

    def fake_call_contract(contract_address, abi, method_name, arguments, call_order):
        if contract_address == token_a.address:
            return 5 * 10**18  # 5 tokens with 18 decimals
        return 0  # zero balance

    mock_inquirer.call_contract = fake_call_contract

    result = tokens_manager.get_token_balances(
        address=ADDR_A,
        tokens=[token_a, token_b],
        call_order=None,
    )

    assert result[Asset(token_a.identifier)] == FVal('5')
    assert Asset(token_b.identifier) not in result  # zero balance excluded


def test_get_token_balances_rpc_failure_skips_token() -> None:
    """If balanceOf fails for a token, it's silently skipped."""
    tokens_manager = HyperliquidTokens.__new__(HyperliquidTokens)
    mock_inquirer = MagicMock()
    mock_inquirer.chain_name = 'hyperliquid'
    mock_inquirer.contracts.erc20_abi = [{'name': 'balanceOf'}]
    mock_inquirer.call_contract.side_effect = RemoteError('rpc error')
    tokens_manager.evm_inquirer = mock_inquirer

    token = EvmTokenDetectionData(
        identifier='eip155:999/erc20:0x5555555555555555555555555555555555555555',
        address=string_to_evm_address('0x5555555555555555555555555555555555555555'),
        decimals=18,
    )

    result = tokens_manager.get_token_balances(
        address=ADDR_A,
        tokens=[token],
        call_order=None,
    )
    assert len(result) == 0


# ── HyperliquidManager.query_balances ────────────────────────────────


def test_query_balances_merges_evm_and_proprietary() -> None:
    """query_balances combines EVM on-chain balances with proprietary API balances."""
    manager = HyperliquidManager.__new__(HyperliquidManager)
    manager.node_inquirer = MagicMock()

    evm_balances: defaultdict[str, BalanceSheet] = defaultdict(BalanceSheet)
    evm_balances[ADDR_A].assets[Asset('HYPE')][DEFAULT_BALANCE_LABEL] = Balance(
        amount=FVal('0.075'),
        value=FVal('1.5'),
    )

    with (
        patch.object(
            HyperliquidManager,
            'query_balances',
            wraps=manager.query_balances,
        ),
        patch(
            'rotkehlchen.chain.evm.manager.EvmManager.query_balances',
            return_value=evm_balances,
        ),
        patch(
            'rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI',
        ) as mock_api_cls,
        patch('rotkehlchen.chain.hyperliquid.manager.Inquirer') as mock_inquirer,
        patch('rotkehlchen.chain.hyperliquid.manager.CachedSettings'),
    ):
        mock_api = mock_api_cls.return_value
        mock_api.query_balances.return_value = {
            Asset('USDC'): FVal('500'),
        }
        mock_inquirer.find_price.return_value = FVal('1')

        result = manager.query_balances(addresses=[ADDR_A])

    # EVM balance preserved
    assert result[ADDR_A].assets[Asset('HYPE')][DEFAULT_BALANCE_LABEL].amount == FVal('0.075')
    # proprietary balance added
    assert result[ADDR_A].assets[Asset('USDC')][DEFAULT_BALANCE_LABEL].amount == FVal('500')


def test_query_balances_proprietary_failure_returns_evm_only() -> None:
    """If the proprietary API fails, EVM balances are still returned."""
    manager = HyperliquidManager.__new__(HyperliquidManager)
    manager.node_inquirer = MagicMock()

    evm_balances: defaultdict[str, BalanceSheet] = defaultdict(BalanceSheet)
    evm_balances[ADDR_A].assets[Asset('HYPE')][DEFAULT_BALANCE_LABEL] = Balance(
        amount=FVal('1'),
        value=FVal('20'),
    )

    with (
        patch.object(
            HyperliquidManager,
            'query_balances',
            wraps=manager.query_balances,
        ),
        patch(
            'rotkehlchen.chain.evm.manager.EvmManager.query_balances',
            return_value=evm_balances,
        ),
        patch(
            'rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI',
        ) as mock_api_cls,
        patch('rotkehlchen.chain.hyperliquid.manager.Inquirer'),
        patch('rotkehlchen.db.settings.CachedSettings'),
    ):
        mock_api = mock_api_cls.return_value
        mock_api.query_balances.side_effect = RemoteError('api down')

        result = manager.query_balances(addresses=[ADDR_A])

    assert result[ADDR_A].assets[Asset('HYPE')][DEFAULT_BALANCE_LABEL].amount == FVal('1')
    assert len(result[ADDR_A].assets) == 1  # no proprietary balances added
