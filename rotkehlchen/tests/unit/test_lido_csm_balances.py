from types import SimpleNamespace
from typing import TYPE_CHECKING
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
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


def _make_evm_inquirer():
    return SimpleNamespace(
        database=MagicMock(),
        chain_id=ChainID.ETHEREUM,
    )


def test_lido_csm_balances_accumulates():
    entry = LidoCsmNodeOperator(address=make_evm_address(), node_operator_id=9)
    with patch(
        'rotkehlchen.db.lido_csm.DBLidoCsm.get_node_operators',
        return_value=(entry,),
    ), patch.object(
        LidoCsmBalances,
        '_get_bond_shares',
        return_value=1_000_000_000_000_000_000,
    ), patch.object(
        LidoCsmBalances,
        '_convert_shares_to_steth',
        return_value=FVal('1.5'),
    ), patch.object(
        Inquirer,
        'find_price',
        return_value=FVal('2000'),
    ), patch.object(
        LidoCsmMetricsFetcher,
        'get_operator_stats',
        return_value=LidoCsmNodeOperatorStats(
            operator_type=LidoCsmOperatorType.UNKNOWN,
            current_bond=FVal(0),
            required_bond=FVal(0),
            claimable_bond=FVal(0),
            total_deposited_validators=0,
            rewards_steth=FVal(0),
        ),
    ):
        balances = LidoCsmBalances(
            evm_inquirer=_make_evm_inquirer(),
            tx_decoder=MagicMock(),
        )
        result = balances.query_balances()

    assert result[entry.address].assets[A_STETH][CPT_LIDO_CSM] == Balance(
        amount=FVal('1.5'),
        value=FVal('3000'),
    )


def test_lido_csm_balances_skips_on_error():
    entry = LidoCsmNodeOperator(address=make_evm_address(), node_operator_id=5)

    def _raise_remote_error(*_args, **_kwargs):
        raise RemoteError('boom')

    with patch(
        'rotkehlchen.db.lido_csm.DBLidoCsm.get_node_operators',
        return_value=(entry,),
    ), patch.object(
        LidoCsmBalances,
        '_get_bond_shares',
        side_effect=_raise_remote_error,
    ), patch.object(
        Inquirer,
        'find_usd_price',
        return_value=FVal('2000'),
    ), patch.object(
        LidoCsmMetricsFetcher,
        'get_operator_stats',
        return_value=LidoCsmNodeOperatorStats(
            operator_type=LidoCsmOperatorType.UNKNOWN,
            current_bond=FVal(0),
            required_bond=FVal(0),
            claimable_bond=FVal(0),
            total_deposited_validators=0,
            rewards_steth=FVal(0),
        ),
    ):
        balances = LidoCsmBalances(
            evm_inquirer=_make_evm_inquirer(),
            tx_decoder=MagicMock(),
        )
        result = balances.query_balances()
    assert len(result) == 0


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
def test_lido_csm_balances_real_data(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
        inquirer: 'Inquirer',
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
    result = balances.query_balances()

    operator_balance = result[node_operator_address].assets[A_STETH][CPT_LIDO_CSM]
    assert operator_balance.amount.is_close(FVal('26.318054536101981594'))
    assert operator_balance.value.is_close(FVal('39.477081804152972391'))
