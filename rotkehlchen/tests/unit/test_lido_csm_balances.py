from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.modules.lido_csm.balances import LidoCsmBalances
from rotkehlchen.chain.ethereum.modules.lido_csm.constants import (
    CPT_LIDO_CSM,
    LIDO_CSM_MODULE_CONTRACTS,
    LidoCsmStakingModule,
)
from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import LidoCsmMetricsFetcher
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_STETH
from rotkehlchen.db.lido_csm import DBLidoCsm, LidoCsmNodeOperator
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.tests.utils.ethereum import INFURA_ETH_NODE
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import ChainID, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


def _make_evm_inquirer():
    return SimpleNamespace(
        database=MagicMock(),
        chain_id=ChainID.ETHEREUM,
    )


def test_lido_csm_balances_skips_on_error():
    entry = LidoCsmNodeOperator(
        address=make_evm_address(),
        node_operator_id=5,
        staking_module=LidoCsmStakingModule.CSM,
    )

    def _raise_remote_error(*_args, **_kwargs):
        raise RemoteError('boom', cause=FailureCause.NETWORK)

    with patch(
        'rotkehlchen.db.lido_csm.DBLidoCsm.get_node_operators',
        return_value=(entry,),
    ), patch.object(
        LidoCsmBalances,
        '_get_bond_shares',
        side_effect=_raise_remote_error,
    ), patch.object(
        Inquirer,
        'find_price',
        return_value=FVal('2000'),
    ), patch.object(
        LidoCsmMetricsFetcher,
        'get_rewards_tree',
        return_value={},
    ), patch.object(
        LidoCsmMetricsFetcher,
        'get_operator_rewards',
        return_value=FVal(0),
    ):
        balances = LidoCsmBalances(
            evm_inquirer=_make_evm_inquirer(),
            tx_decoder=MagicMock(),
        )
        result = balances.query_balances(addresses=[entry.address])
    assert len(result) == 0


def test_lido_csm_balances_query_each_staking_module_accounting_contract():
    """Operators sharing an id in different modules are priced from their own module's bond"""
    address = make_evm_address()
    entries = tuple(
        LidoCsmNodeOperator(address=address, node_operator_id=3, staking_module=module)
        for module in LidoCsmStakingModule
    )
    shares_by_accounting = {
        LIDO_CSM_MODULE_CONTRACTS[module].accounting: 10 * (idx + 1)
        for idx, module in enumerate(LidoCsmStakingModule)
    }

    def fake_call(self, node_inquirer, method_name, arguments):
        assert method_name == 'getBondShares'
        return shares_by_accounting[self.address]

    with patch(
        'rotkehlchen.db.lido_csm.DBLidoCsm.get_node_operators',
        return_value=entries,
    ), patch.object(EvmContract, 'call', autospec=True, side_effect=fake_call), patch.object(
        LidoCsmBalances,
        '_convert_shares_to_steth',
        side_effect=lambda shares: FVal(shares),  # noqa: PLW0108
    ), patch.object(Inquirer, 'find_price', return_value=FVal('2')), patch.object(
        LidoCsmMetricsFetcher, 'get_rewards_tree', return_value={},
    ), patch.object(
        LidoCsmMetricsFetcher, 'get_operator_rewards', return_value=FVal(0),
    ):
        result = LidoCsmBalances(
            evm_inquirer=_make_evm_inquirer(),
            tx_decoder=MagicMock(),
        ).query_balances(addresses=[address])

    assert result[address].assets[A_STETH][CPT_LIDO_CSM].amount == FVal(30)


@pytest.mark.vcr(filter_query_parameters=['apikey'], match_on=['match_rpc_calls'])
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
        staking_module=LidoCsmStakingModule.CSM,
    )

    balances = LidoCsmBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=ethereum_transaction_decoder,
    )
    result = balances.query_balances(addresses=[node_operator_address])

    operator_balance = result[node_operator_address].assets[A_STETH][CPT_LIDO_CSM]
    assert operator_balance.amount.is_close(FVal('29.154399977908747719'))
    assert operator_balance.value.is_close(FVal('43.7315999668631215785'))


def test_lido_csm_balances_rewards_preserved_when_non_rewards_metrics_fail():
    """Unrelated metrics contract failures do not wipe out pending rewards."""
    address = make_evm_address()
    entry = LidoCsmNodeOperator(
        address=address,
        node_operator_id=42,
        staking_module=LidoCsmStakingModule.CSM,
    )

    forbidden_methods = {
        'getBondCurveId',
        'getBondSummaryShares',
        'getClaimableBondShares',
        'getNodeOperatorSummary',
    }

    def fake_contract_call(self, node_inquirer, method_name, arguments):
        if method_name in forbidden_methods:
            raise AssertionError(
                f'Non-rewards metrics method {method_name} was unexpectedly called',
            )
        if method_name == 'getBondShares':
            return 10 * 10**18
        if method_name == 'treeCid':
            return 'bafkreitree'
        if method_name == 'distributedShares':
            return 2 * 10**18
        if method_name == 'getPooledEthByShares':
            return arguments[0]
        raise AssertionError(f'Unexpected method call {method_name}')

    fake_tree = {
        'values': [
            {'value': [42, 5 * 10**18]},
        ],
    }

    with patch(
        'rotkehlchen.db.lido_csm.DBLidoCsm.get_node_operators',
        return_value=(entry,),
    ), patch.object(
        EvmContract,
        'call',
        autospec=True,
        side_effect=fake_contract_call,
    ), patch.object(
        LidoCsmMetricsFetcher,
        '_fetch_ipfs_json',
        return_value=fake_tree,
    ), patch.object(
        Inquirer,
        'find_price',
        return_value=FVal('2'),
    ):
        balances = LidoCsmBalances(
            evm_inquirer=_make_evm_inquirer(),
            tx_decoder=MagicMock(),
        )
        result = balances.query_balances(addresses=[address])

    # Bond: 10 stETH, Rewards: 5 - 2 = 3 stETH, Total: 13 stETH
    operator_balance = result[address].assets[A_STETH][CPT_LIDO_CSM]
    assert operator_balance.amount == FVal('13')
    assert operator_balance.value == FVal('26')


def test_lido_csm_balances_tree_downloaded_once_for_multiple_operators():
    """Rewards tree is downloaded only once across multiple operators in the same batch."""
    address_1 = make_evm_address()
    address_2 = make_evm_address()
    entries = (
        LidoCsmNodeOperator(
            address=address_1,
            node_operator_id=1,
            staking_module=LidoCsmStakingModule.CSM,
        ),
        LidoCsmNodeOperator(
            address=address_2,
            node_operator_id=2,
            staking_module=LidoCsmStakingModule.CSM,
        ),
        LidoCsmNodeOperator(
            address=address_1,
            node_operator_id=3,
            staking_module=LidoCsmStakingModule.CSM,
        ),
    )

    fake_tree = {
        'values': [
            {'value': [1, 10 * 10**18]},
            {'value': [2, 20 * 10**18]},
            {'value': [3, 30 * 10**18]},
        ],
    }
    ipfs_mock = MagicMock(return_value=fake_tree)

    def fake_contract_call(self, node_inquirer, method_name, arguments):
        if method_name == 'getBondShares':
            return 10**18
        if method_name == 'treeCid':
            return 'bafkreitree'
        if method_name == 'distributedShares':
            return 0
        if method_name == 'getPooledEthByShares':
            return arguments[0]
        raise AssertionError(f'Unexpected method call {method_name}')

    with patch(
        'rotkehlchen.db.lido_csm.DBLidoCsm.get_node_operators',
        return_value=entries,
    ), patch.object(
        EvmContract,
        'call',
        autospec=True,
        side_effect=fake_contract_call,
    ), patch.object(
        LidoCsmMetricsFetcher,
        '_fetch_ipfs_json',
        new=ipfs_mock,
    ), patch.object(
        Inquirer,
        'find_price',
        return_value=FVal('1'),
    ):
        balances = LidoCsmBalances(
            evm_inquirer=_make_evm_inquirer(),
            tx_decoder=MagicMock(),
        )
        result = balances.query_balances(addresses=[address_1, address_2])

    assert ipfs_mock.call_count == 1
    # address_1: operator 1 (1 bond + 10 rewards) + operator 3 (1 bond + 30 rewards) = 42
    assert result[address_1].assets[A_STETH][CPT_LIDO_CSM].amount == FVal('42')
    # address_2: operator 2 (1 bond + 20 rewards) = 21
    assert result[address_2].assets[A_STETH][CPT_LIDO_CSM].amount == FVal('21')


def test_lido_csm_balances_tree_download_failure_cached_within_batch():
    """If tree download fails, subsequent operators in the same batch do not retry it."""
    address_1 = make_evm_address()
    address_2 = make_evm_address()
    entries = (
        LidoCsmNodeOperator(
            address=address_1,
            node_operator_id=1,
            staking_module=LidoCsmStakingModule.CSM,
        ),
        LidoCsmNodeOperator(
            address=address_2,
            node_operator_id=2,
            staking_module=LidoCsmStakingModule.CSM,
        ),
    )

    fetch_tree_mock = MagicMock(side_effect=RemoteError(
        'IPFS gateway timeout',
        cause=FailureCause.NETWORK,
    ))

    with patch(
        'rotkehlchen.db.lido_csm.DBLidoCsm.get_node_operators',
        return_value=entries,
    ), patch.object(
        LidoCsmBalances,
        '_get_bond_shares',
        return_value=10 * 10**18,
    ), patch.object(
        LidoCsmBalances,
        '_convert_shares_to_steth',
        return_value=FVal('10'),
    ), patch.object(
        LidoCsmMetricsFetcher,
        'get_rewards_tree',
        new=fetch_tree_mock,
    ), patch.object(
        Inquirer,
        'find_price',
        return_value=FVal('1'),
    ):
        balances = LidoCsmBalances(
            evm_inquirer=_make_evm_inquirer(),
            tx_decoder=MagicMock(),
        )
        result = balances.query_balances(addresses=[address_1, address_2])

    assert fetch_tree_mock.call_count == 1
    # Bond amount is preserved even though rewards failed
    assert result[address_1].assets[A_STETH][CPT_LIDO_CSM].amount == FVal('10')
    assert result[address_2].assets[A_STETH][CPT_LIDO_CSM].amount == FVal('10')
