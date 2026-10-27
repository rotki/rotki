from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

from eth_utils.abi import get_abi_output_types

from rotkehlchen.accounting.structures.balance import ClaimEntry
from rotkehlchen.chain.ethereum.modules.lido.balances import LidoBalances
from rotkehlchen.chain.ethereum.modules.lido.constants import CPT_LIDO
from rotkehlchen.chain.evm.contracts import WEB3
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from collections.abc import Callable


def make_balances(
        owners: list[str],
        handlers: dict[str, Callable[..., tuple[Any, ...]]],
) -> tuple[LidoBalances, MagicMock]:
    """LidoBalances whose multicall decodes each call, runs the handler registered for its
    method and encodes the returned outputs, so the real encode/decode paths are exercised."""
    balances = LidoBalances(evm_inquirer=MagicMock(), tx_decoder=MagicMock())
    balances.addresses_with_deposits = lambda **_: {owner: [] for owner in owners}  # type: ignore[method-assign]

    def multicall(calls: list[tuple[str, str]], **_kwargs: Any) -> list[bytes]:
        results = []
        for address, data in calls:
            contract = balances.queue if address == balances.queue.address else balances.steth
            function, arguments = contract.decode_input_data(
                bytes.fromhex(data.removeprefix('0x')),
            )
            results.append(WEB3.codec.encode(
                get_abi_output_types(function.abi),
                handlers[function.fn_name](*arguments.values()),
            ))
        return results

    multicall_mock = MagicMock(side_effect=multicall)
    balances.evm_inquirer.multicall = multicall_mock  # type: ignore[method-assign]
    return balances, multicall_mock


def test_lido_withdrawals_current_owner_and_actual_payout():
    owner, other = make_evm_address(), make_evm_address()
    wei = 10**18
    statuses = [
        (2 * wei, 2 * wei, owner, 1001, False, False),
        (3 * wei, 3 * wei, owner, 1002, True, False),
        (4 * wei, 4 * wei, owner, 1003, True, True),
        (5 * wei, 5 * wei, other, 1004, False, False),
        (wei, wei, owner, 1005, False, False),
    ]
    share_values = {2 * wei: 3 * wei, wei: wei // 2}  # pending requests are capped at their stETH
    balances, multicall = make_balances([owner], {
        'getWithdrawalRequests': lambda _owner: ([1, 2, 3, 4, 5],),
        'getWithdrawalStatus': lambda ids: (statuses,),
        'getPooledEthByShares': lambda shares: (share_values[shares],),
        'getLastCheckpointIndex': lambda: (10,),
        'findCheckpointHints': lambda ids, first, last: ([9] if (ids, first, last) == ([2], 1, 10) else [],),  # noqa: E501
        'getClaimableEther': lambda ids, hints: ([2 * wei] if (ids, hints) == ([2], [9]) else [],),
    })
    with patch.object(Inquirer, 'find_main_currency_price', return_value=FVal(2000)):
        result = balances.query_balances([owner, other])

    balance = result[owner].assets[A_ETH][CPT_LIDO]
    assert balance.amount == FVal('4.5')
    assert balance.value == FVal(9000)
    assert balance.awaiting_claim == FVal('4.5')
    assert sorted(balance.claims, key=lambda claim: int(claim.request_id)) == [
        ClaimEntry(amount=FVal(2), request_id='1', requested_at=Timestamp(1001)),
        ClaimEntry(amount=FVal(2), request_id='2', finalized=True, requested_at=Timestamp(1002)),
        ClaimEntry(amount=FVal('0.5'), request_id='5', requested_at=Timestamp(1005)),
    ]
    assert sum(claim.amount for claim in balance.claims) == balance.awaiting_claim
    assert multicall.call_count == 6  # one batched multicall per step, not one call per request


def test_lido_withdrawals_batch_all_owners_in_one_multicall():
    first, second = make_evm_address(), make_evm_address()
    balances, multicall = make_balances([first, second], {
        'getWithdrawalRequests': lambda _owner: ([],),
    })
    assert len(balances.query_balances([first, second])) == 0
    multicall.assert_called_once()
    assert len(multicall.call_args.kwargs['calls']) == 2


def test_lido_withdrawals_rpc_error():
    owner = make_evm_address()
    balances, multicall = make_balances([owner], {})
    multicall.side_effect = RemoteError('unavailable')
    with patch.object(Inquirer, 'find_main_currency_price') as price:
        assert len(balances.query_balances([owner])) == 0
    price.assert_not_called()


def test_lido_withdrawals_skip_rpc_without_request_events():
    balances, multicall = make_balances([], {})
    assert len(balances.query_balances([make_evm_address()])) == 0
    multicall.assert_not_called()
