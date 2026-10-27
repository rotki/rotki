from unittest.mock import MagicMock, patch

from rotkehlchen.accounting.structures.balance import ClaimEntry
from rotkehlchen.chain.ethereum.modules.lido.balances import LidoBalances
from rotkehlchen.chain.ethereum.modules.lido.constants import CPT_LIDO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import Timestamp


def test_lido_withdrawals_current_owner_and_actual_payout():
    owner, other = make_evm_address(), make_evm_address()
    balances = LidoBalances.__new__(LidoBalances)
    balances.counterparty = CPT_LIDO
    balances.evm_inquirer = MagicMock()
    balances.queue = MagicMock()
    balances.steth = MagicMock()
    wei = 10**18

    def queue_call(*, method_name, arguments=None, **_kwargs):
        if method_name == 'getWithdrawalRequests':
            return [1, 2, 3, 4, 5]
        if method_name == 'getWithdrawalStatus':
            return [
                (2 * wei, 2 * wei, owner, 1001, False, False),
                (3 * wei, 3 * wei, owner, 1002, True, False),
                (4 * wei, 4 * wei, owner, 1003, True, True),
                (5 * wei, 5 * wei, other, 1004, False, False),
                (wei, wei, owner, 1005, False, False),
            ]
        if method_name == 'getLastCheckpointIndex':
            return 10
        if method_name == 'findCheckpointHints':
            assert arguments == [[2], 1, 10]
            return [9]
        if method_name == 'getClaimableEther':
            assert arguments == [[2], [9]]
            return [2 * wei]
        raise AssertionError(method_name)

    balances.queue.call.side_effect = queue_call
    # Pending requests are capped at their original amount and may lose value.
    balances.steth.call.side_effect = [3 * wei, wei // 2]
    with patch.object(Inquirer, 'find_price', return_value=FVal(2000)):
        result = balances.query_balances([owner])

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
    assert balances.steth.call.call_count == 2


def test_lido_withdrawals_empty_and_rpc_error():
    owner, other = make_evm_address(), make_evm_address()
    balances = LidoBalances.__new__(LidoBalances)
    balances.counterparty = CPT_LIDO
    balances.evm_inquirer = MagicMock()
    balances.queue = MagicMock()
    balances.queue.call.side_effect = [[], RemoteError('unavailable')]
    with patch.object(Inquirer, 'find_price') as price:
        assert len(balances.query_balances([owner, other])) == 0
    price.assert_not_called()
