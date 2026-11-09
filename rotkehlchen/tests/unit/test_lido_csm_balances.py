from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.modules.lido_csm.balances import LidoCsmBalances
from rotkehlchen.chain.ethereum.modules.lido_csm.constants import CPT_LIDO_CSM, LidoCsmOperatorType
from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import (
    LidoCsmMetricsFetcher,
    LidoCsmNodeOperatorStats,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_STETH
from rotkehlchen.db.lido_csm import DBLidoCsm, LidoCsmNodeOperator
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.tests.utils.ethereum import INFURA_ETH_NODE
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import ChainID, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.contracts import EvmContract


# The contract calls of the metrics that have nothing to do with rewards
METRICS_ONLY_CALLS = (
    'getBondCurveId',
    'getBondSummaryShares',
    'getClaimableBondShares',
    'getNodeOperatorSummary',
)
REWARDS_TREE = {'values': [{'value': [1, 10**18]}, {'value': [2, 3 * 10**18]}]}


class FakeLidoContracts:
    """Stands in for every contract of the balances query, with bond shares of 1 for each
    operator and 0.5 distributed shares, and stETH shares worth one stETH."""

    def __init__(self, failing: tuple[str, ...] = ()) -> None:
        self.failing = failing
        self.called: list[str] = []

    def call(self, *, method_name: str, arguments: list[int], **_: object) -> int | str:
        self.called.append(method_name)
        if method_name in self.failing:
            raise RemoteError(f'{method_name} failed')

        match method_name:
            case 'getBondShares':
                return 10**18
            case 'getPooledEthByShares':
                return arguments[0]
            case 'treeCid':
                return 'tree-cid'
            case 'distributedShares':
                return 5 * 10**17

        raise AssertionError(f'Unexpected contract call to {method_name}')


def _make_balances(contracts: FakeLidoContracts) -> LidoCsmBalances:
    balances = LidoCsmBalances(
        evm_inquirer=cast(
            'EthereumInquirer',
            SimpleNamespace(database=MagicMock(), chain_id=ChainID.ETHEREUM),
        ),
        tx_decoder=MagicMock(),
    )
    contract = cast('EvmContract', contracts)
    balances._accounting_contract = balances._steth_contract = contract
    fetcher = balances._metrics_fetcher
    fetcher.accounting_contract = fetcher.module_contract = contract
    fetcher.steth_contract = fetcher.fee_distributor_contract = contract
    return balances


@pytest.fixture(name='operators')
def fixture_operators():
    operators = (
        LidoCsmNodeOperator(address=make_evm_address(), node_operator_id=1),
        LidoCsmNodeOperator(address=make_evm_address(), node_operator_id=2),
    )
    with patch(
        'rotkehlchen.db.lido_csm.DBLidoCsm.get_node_operators',
        return_value=operators,
    ), patch.object(Inquirer, 'find_price', return_value=FVal('2000')):
        yield operators


def _steth_amounts(result: BalancesSheetType, operators: tuple[LidoCsmNodeOperator, ...]) -> list[FVal]:  # noqa: E501
    return [result[x.address].assets[A_STETH][CPT_LIDO_CSM].amount for x in operators]


def test_lido_csm_balances_accumulates(operators):
    """Test that each operator's balance is the bond plus the pending rewards"""
    balances = _make_balances(FakeLidoContracts())
    with patch.object(LidoCsmMetricsFetcher, '_fetch_ipfs_json', return_value=REWARDS_TREE):
        result = balances.query_balances(addresses=[x.address for x in operators])

    assert result[operators[0].address].assets[A_STETH][CPT_LIDO_CSM] == Balance(
        amount=FVal('1.5'),
        value=FVal('3000'),
    )
    assert _steth_amounts(result, operators)[1] == FVal('3.5')


def test_lido_csm_balances_download_rewards_tree_once(operators):
    """Test that many operators share one download of the tree and of its cid"""
    contracts = FakeLidoContracts()
    balances = _make_balances(contracts)
    with patch.object(
        LidoCsmMetricsFetcher,
        '_fetch_ipfs_json',
        return_value=REWARDS_TREE,
    ) as fetch_tree:
        balances.query_balances(addresses=[x.address for x in operators])

    assert fetch_tree.call_count == 1
    assert contracts.called.count('treeCid') == 1


def test_lido_csm_balances_ignore_metrics_failures(operators):
    """Test that the balance needs none of the calls that only the metrics use, so their
    failure can't take the pending rewards away, as happened with the CSM v3 upgrade."""
    contracts = FakeLidoContracts(failing=METRICS_ONLY_CALLS)
    balances = _make_balances(contracts)
    with patch.object(LidoCsmMetricsFetcher, '_fetch_ipfs_json', return_value=REWARDS_TREE):
        result = balances.query_balances(addresses=[x.address for x in operators])

    assert _steth_amounts(result, operators) == [FVal('1.5'), FVal('3.5')]
    assert set(contracts.called).isdisjoint(METRICS_ONLY_CALLS)


def test_lido_csm_balances_keep_bond_if_rewards_tree_fails(operators):
    """Test that a failed tree download leaves the bond and is not repeated per operator"""
    balances = _make_balances(FakeLidoContracts())
    with patch.object(
        LidoCsmMetricsFetcher,
        '_fetch_ipfs_json',
        side_effect=RemoteError('rate limited'),
    ) as fetch_tree:
        result = balances.query_balances(addresses=[x.address for x in operators])

    assert fetch_tree.call_count == 1
    assert _steth_amounts(result, operators) == [FVal('1'), FVal('1')]
    # the user is told that the rewards are missing
    balances.evm_inquirer.database.msg_aggregator.add_warning.assert_called_once()


def test_lido_csm_balances_use_stored_rewards_if_rewards_tree_fails():
    """Test that rewards that can't be fetched fall back to the last stored value
    for the operators that have one, instead of being reported as zero"""
    operators = (
        LidoCsmNodeOperator(
            address=make_evm_address(),
            node_operator_id=1,
            metrics=LidoCsmNodeOperatorStats(
                operator_type=LidoCsmOperatorType.PERMISSIONLESS,
                current_bond=ONE,
                required_bond=ONE,
                claimable_bond=ZERO,
                total_deposited_validators=1,
                rewards_steth=FVal('0.25'),
            ),
        ),
        LidoCsmNodeOperator(address=make_evm_address(), node_operator_id=2),
    )
    balances = _make_balances(FakeLidoContracts())
    with (
        patch('rotkehlchen.db.lido_csm.DBLidoCsm.get_node_operators', return_value=operators),
        patch.object(Inquirer, 'find_price', return_value=FVal('2000')),
        patch.object(LidoCsmMetricsFetcher, '_fetch_ipfs_json', side_effect=RemoteError('429')),
    ):
        result = balances.query_balances(addresses=[x.address for x in operators])

    assert _steth_amounts(result, operators) == [FVal('1.25'), FVal('1')]


def test_lido_csm_balances_keep_bond_if_pending_rewards_fail(operators):
    """Test that a failed call for the distributed shares leaves the bond"""
    balances = _make_balances(FakeLidoContracts(failing=('distributedShares',)))
    with patch.object(LidoCsmMetricsFetcher, '_fetch_ipfs_json', return_value=REWARDS_TREE):
        result = balances.query_balances(addresses=[x.address for x in operators])

    assert _steth_amounts(result, operators) == [FVal('1'), FVal('1')]


def test_lido_csm_balances_skips_on_error(operators):
    balances = _make_balances(FakeLidoContracts(failing=('getBondShares',)))
    with patch.object(LidoCsmMetricsFetcher, '_fetch_ipfs_json', return_value=REWARDS_TREE):
        result = balances.query_balances(addresses=[x.address for x in operators])

    assert len(result) == 0


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
def test_lido_csm_balances_real_data(
        ethereum_inquirer: EthereumInquirer,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        inquirer: Inquirer,
):
    """Queries the real Lido CSM contracts for node operator id 1 using VCR."""
    node_operator_address = string_to_evm_address('0xbB8311c7bAD518f0D8f907Cad26c5CcC85a06dC4')
    db = DBLidoCsm(ethereum_inquirer.database)
    with ethereum_inquirer.database.user_write() as cursor:
        ethereum_inquirer.database.add_blockchain_accounts(
            write_cursor=cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=node_operator_address,
            )],
        )
    db.add_node_operator(
        address=node_operator_address,
        node_operator_id=1,
    )

    balances = LidoCsmBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=ethereum_transaction_decoder,
    )
    result = balances.query_balances(addresses=[node_operator_address])

    operator_balance = result[node_operator_address].assets[A_STETH][CPT_LIDO_CSM]
    assert operator_balance.amount.is_close(FVal('29.154399977908747719'))
    assert operator_balance.value.is_close(FVal('43.7315999668631215785'))
