from unittest.mock import MagicMock, patch

from rotkehlchen.accounting.structures.balance import Balance, ClaimEntry
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.modules.venice.balances import VeniceBalances
from rotkehlchen.chain.base.modules.venice.constants import CPT_VENICE, VVV_TOKEN_ID
from rotkehlchen.chain.evm.contracts import WEB3
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp


def test_venice_pending_withdrawals() -> None:
    inquirer = MagicMock()
    addresses = [string_to_evm_address(f'0x{i:040x}') for i in range(1, 4)]
    # Both an unexpired and an expired cooldown remain owned until unstake is called.
    # An amount of zero also covers an already claimed withdrawal.
    inquirer.multicall.return_value = [
        WEB3.codec.encode(['uint256', 'uint256', 'uint256'], [10, 9999999999, 2 * 10**18]),
        WEB3.codec.encode(['uint256', 'uint256', 'uint256'], [20, 1, 3 * 10**18]),
        WEB3.codec.encode(['uint256', 'uint256', 'uint256'], [30, 0, 0]),
    ]
    protocol = VeniceBalances(evm_inquirer=inquirer, tx_decoder=MagicMock())
    with (
        patch.object(
            protocol,
            'addresses_with_deposits',
            return_value={address: [] for address in addresses},
        ),
        patch('rotkehlchen.chain.base.modules.venice.balances.Inquirer.find_main_currency_price', return_value=FVal(4)),  # noqa: E501
    ):
        balances = protocol.query_balances(addresses)

    asset = Asset(VVV_TOKEN_ID)
    assert balances[addresses[0]].assets[asset][CPT_VENICE] == Balance(
        amount=FVal(2),
        value=FVal(8),
        awaiting_claim=FVal(2),
        claims=(ClaimEntry(amount=FVal(2), available_at=Timestamp(9999999999)),),
    )
    assert balances[addresses[1]].assets[asset][CPT_VENICE] == Balance(
        amount=FVal(3),
        value=FVal(12),
        awaiting_claim=FVal(3),
        claims=(ClaimEntry(amount=FVal(3), available_at=Timestamp(1)),),
    )
    assert addresses[2] not in balances
    assert len(inquirer.multicall.call_args.kwargs['calls']) == len(addresses)


def test_venice_skips_rpc_without_unstake_events() -> None:
    inquirer = MagicMock()
    protocol = VeniceBalances(evm_inquirer=inquirer, tx_decoder=MagicMock())
    with patch.object(protocol, 'addresses_with_deposits', return_value={}):
        assert len(protocol.query_balances([string_to_evm_address(f'0x{1:040x}')])) == 0
    inquirer.multicall.assert_not_called()
