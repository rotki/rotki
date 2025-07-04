from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_VELODROME
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    SupportedBlockchain,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_optimism_balances(
        rotkehlchen_instance: 'Rotkehlchen',
        optimism_accounts: list[ChecksumEvmAddress],
        load_global_caches: list[str],
):
    """
    Tests the balance of an account that has an asset both in wallet and staked in a gauge.
    The total balance should be the sum of the two.
    """
    velodrome_v2_weth_op_lp_token = 'eip155:10/erc20:0xd25711EdfBf747efCE181442Cc1D8F5F8fc8a0D3'
    user_database = rotkehlchen_instance.data.db
    with user_database.conn.write_ctx() as write_cursor:  # add the asset to the account
        write_cursor.execute(
            'INSERT INTO evm_accounts_details VALUES (?, ?, ?, ?)',
            (optimism_accounts[0], ChainID.OPTIMISM.value, 'tokens', velodrome_v2_weth_op_lp_token),  # noqa: E501
        )

    optimism_inquirer = rotkehlchen_instance.chains_aggregator.optimism.node_inquirer
    tx_hex = deserialize_evm_tx_hash('0xed7e13e4941bba33edbbd70c4f48c734629fd67fe4eac43ce1bed3ef8f3da7df')  # transaction that interacts with the gauge address  # noqa: E501
    get_decoded_events_of_transaction(  # decode events that interact with the gauge address. This is needed because the query_balances which is used later only queries balances for addresses interacted with gauges. This also populates the global db with the event assets  # noqa: E501
        evm_inquirer=optimism_inquirer,
        tx_hash=tx_hex,
        load_global_caches=load_global_caches,
    )
    blockchain_result = rotkehlchen_instance.chains_aggregator.query_balances(
        blockchain=SupportedBlockchain.OPTIMISM,
        ignore_cache=True,
    )
    account_balance = blockchain_result.per_account.optimism[optimism_accounts[0]].assets[velodrome_v2_weth_op_lp_token]  # noqa: E501
    assert account_balance == {CPT_VELODROME: Balance(amount=FVal('0.086313645974870917'), usd_value=FVal('0.1294704689623063755'))}  # noqa: E501
