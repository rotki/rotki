from unittest.mock import MagicMock, patch

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.modules.hyperliquid.balances import HyperliquidBalances
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal


def test_hyperliquid_protocol_balances_skip_accounts_tracked_on_hyperliquid_chain() -> None:
    addr_tracked = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')
    addr_arb_only = string_to_evm_address('0x81A336499Abf90f7fB8f44fE7D6dE0f9f2D7cF3D')

    balances_module = HyperliquidBalances.__new__(HyperliquidBalances)
    balances_module.counterparty = 'hyperliquid'
    balances_module.evm_inquirer = MagicMock()
    balances_module.evm_inquirer.database.conn.read_ctx.return_value.__enter__.return_value = (
        MagicMock()
    )
    balances_module.evm_inquirer.database.get_single_blockchain_addresses.return_value = [
        addr_tracked,
    ]
    with (
        patch.object(
            balances_module,
            'addresses_with_deposits',
            return_value={addr_tracked: [], addr_arb_only: []},
        ),
        patch(
            'rotkehlchen.chain.arbitrum_one.modules.hyperliquid.balances.HyperliquidAPI',
        ) as mock_api_cls,
        patch(
            'rotkehlchen.chain.arbitrum_one.modules.hyperliquid.balances.Inquirer',
        ) as mock_inquirer,
    ):
        mock_api_cls.return_value.query_balances.return_value = {Asset('USDC'): FVal('10')}
        mock_inquirer.find_main_currency_price.return_value = FVal('1')
        result = balances_module.query_balances()

    mock_api_cls.return_value.query_balances.assert_called_once_with(address=addr_arb_only)
    assert addr_tracked not in result
    assert result[addr_arb_only].assets[Asset('USDC')]['hyperliquid'].amount == FVal('10')
    assert result[addr_arb_only].assets[Asset('USDC')]['hyperliquid'].value == FVal('10')


def test_hyperliquid_protocol_balances_return_empty_when_all_accounts_tracked() -> None:
    addr_tracked = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')

    balances_module = HyperliquidBalances.__new__(HyperliquidBalances)
    balances_module.counterparty = 'hyperliquid'
    balances_module.evm_inquirer = MagicMock()
    balances_module.evm_inquirer.database.conn.read_ctx.return_value.__enter__.return_value = (
        MagicMock()
    )
    balances_module.evm_inquirer.database.get_single_blockchain_addresses.return_value = [
        addr_tracked,
    ]
    with (
        patch.object(balances_module, 'addresses_with_deposits', return_value={addr_tracked: []}),
        patch(
            'rotkehlchen.chain.arbitrum_one.modules.hyperliquid.balances.HyperliquidAPI',
        ) as mock_api_cls,
    ):
        result = balances_module.query_balances()

    mock_api_cls.return_value.query_balances.assert_not_called()
    assert result == {}
