from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChainID, SupportedBlockchain, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2WithL1FeesTransaction
    from rotkehlchen.chain.optimism.transactions import OptimismTransactions
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xd6Ade875eEC93a7aAb7EfB7DBF13d1457443f95B']])
def test_query_transactions_no_fee(optimism_transactions, optimism_accounts):
    """Test to query an optimism transaction with and without l1_fee existing in the DB.
    Make sure that if l1_fee is missing in the DB nothing breaks, but it's just seen as 0.
    Note that the transaction used here is from after the bedrock upgrade and tests the case where
    the l1_fee is present in the data from onchain.
    """
    address = optimism_accounts[0]
    dbevmtx = optimism_transactions.dbevmtx
    tx_hash = deserialize_evm_tx_hash('0x6eb136db4d36cf695f4026da16f602ed4a2583b2420dbbcbd4f436943190b665')  # noqa: E501
    to_address = '0xDEF1ABE32c034e558Cdd535791643C58a13aCC10'

    def assert_tx_okay(transactions, should_have_l1):
        assert len(transactions) == 1
        assert transactions[0].tx_hash == tx_hash
        assert transactions[0].chain_id == ChainID.OPTIMISM
        assert transactions[0].db_id == 2
        assert transactions[0].l1_fee == (115752642875381 if should_have_l1 else 0)
        assert transactions[0].gas == 523212
        assert transactions[0].gas_used == 322803
        assert transactions[0].timestamp == 1689113567
        assert transactions[0].from_address == address
        assert transactions[0].to_address == to_address

    optimism_transactions.single_address_query_transactions(
        address=address,
        start_ts=1689113567,
        end_ts=1689113567,
    )
    with optimism_transactions.database.conn.read_ctx() as cursor:
        transactions = dbevmtx.get_evm_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(tx_hash=tx_hash),
            has_premium=True,
        )
        assert_tx_okay(transactions, should_have_l1=True)

    # Now delete the l1 fee from the DB and see things don't break
    with optimism_transactions.database.user_write() as write_cursor:
        write_cursor.execute('DELETE FROM optimism_transactions WHERE tx_id=2')

    with optimism_transactions.database.conn.read_ctx() as cursor:
        transactions = dbevmtx.get_evm_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(tx_hash=tx_hash),
            has_premium=True,
        )
        assert_tx_okay(transactions, should_have_l1=False)

    # check that the get_or_create_transaction method makes sure that the requirements for an
    # optimism transaction (l1_fee existing in the database) are met before returning it.
    with optimism_transactions.database.conn.read_ctx() as cursor:
        tx, _ = optimism_transactions.get_or_create_transaction(cursor, tx_hash, string_to_evm_address(to_address))  # noqa: E501
        assert_tx_okay([tx], should_have_l1=True)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
@pytest.mark.parametrize('optimism_manager_connect_at_start', [(
    WeightedNode(node_info=NodeName(name='drpc', endpoint='https://optimism.drpc.org', owned=False, blockchain=SupportedBlockchain.OPTIMISM), active=True, weight=FVal('0.5')),  # noqa: E501
    WeightedNode(node_info=NodeName(name='mainnet', endpoint='https://mainnet.optimism.io', owned=False, blockchain=SupportedBlockchain.OPTIMISM), active=True, weight=FVal('0.5')),  # noqa: E501
)])
def test_l1_fee_queried_when_missing(
        optimism_transactions: 'OptimismTransactions',
        optimism_accounts: list['ChecksumEvmAddress'],
        optimism_manager_connect_at_start: Sequence[WeightedNode],
):
    """Test that if the L1 fee is initially missing it gets queried from either
    the mainnet node or from etherscan.
    """
    original_get_transaction_receipt = optimism_transactions.evm_inquirer.get_transaction_receipt
    for fallback_to_etherscan in (False, True):

        def mock_get_transaction_receipt(fallback=fallback_to_etherscan, **kwargs: Any) -> dict[str, Any]:  # noqa: E501
            """Simulate a missing l1Fee from the mainnet node in the fallback_to_etherscan case."""
            nonlocal fallback_to_etherscan
            tx_receipt = original_get_transaction_receipt(**kwargs)
            if fallback:
                tx_receipt['l1Fee'] = None

            return tx_receipt

        with (
            patch.object(
                optimism_transactions.evm_inquirer,
                'get_transaction_receipt',
                side_effect=mock_get_transaction_receipt,
            ) as get_tx_receipt_mock,
            patch.object(
                optimism_transactions.evm_inquirer.etherscan,
                'maybe_get_l1_fees',
                wraps=optimism_transactions.evm_inquirer.etherscan.maybe_get_l1_fees,
            ) as get_l1_fees_mock,
            patch.object(
                optimism_transactions.evm_inquirer,
                'default_call_order',
                new=lambda: list(optimism_manager_connect_at_start),
            ),  # patch default call order to keep it deterministic for the vcr
        ):
            tx, _ = optimism_transactions.evm_inquirer.get_transaction_by_hash(
                tx_hash=deserialize_evm_tx_hash('0x92ae5e1c4b4a2d5e2af9c4abc415a9dc0b826ba1fa158c57219fc1b6e852a061'),
            )

        assert cast('L2WithL1FeesTransaction', tx).l1_fee == 97960903705252
        assert get_tx_receipt_mock.call_count == 1
        assert get_tx_receipt_mock.call_args_list[0].kwargs['call_order'][0].node_info.name == 'mainnet'  # noqa: E501
        assert get_l1_fees_mock.call_count == (1 if fallback_to_etherscan else 0)
