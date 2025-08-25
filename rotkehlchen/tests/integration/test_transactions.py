from typing import TYPE_CHECKING

import pytest

from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import (
    ETH_ADDRESS1,
    ETH_ADDRESS2,
    ETH_ADDRESS3,
    MOCK_INPUT_DATA,
)
from rotkehlchen.tests.utils.ethereum import (
    INFURA_ETH_NODE,
    TEST_ADDR1,
    TEST_ADDR2,
    setup_ethereum_transactions_test,
)
from rotkehlchen.types import ChainID, EvmTransaction, Timestamp, deserialize_evm_tx_hash
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
@pytest.mark.parametrize('transaction_already_queried', [True, False])
@pytest.mark.freeze_time('2023-01-24 22:45:45 GMT')
@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_transaction_receipt(
        database: 'DBHandler',
        eth_transactions: 'EthereumTransactions',
        ethereum_accounts: list['ChecksumEvmAddress'],
        transaction_already_queried: bool,
) -> None:
    """Test that getting a transaction receipt from the network and saving it in the DB works"""
    transactions, receipts = setup_ethereum_transactions_test(
        database=database,
        transaction_already_queried=transaction_already_queried,
        one_receipt_in_db=False,
    )
    receipt = eth_transactions.get_or_query_transaction_receipt(transactions[0].tx_hash)
    assert receipt == receipts[0]
    filter_query = EvmTransactionsFilterQuery.make(tx_hash=transactions[0].tx_hash)
    eth_transactions.query_chain(
        from_timestamp=Timestamp(0),
        to_timestamp=ts_now(),
        addresses=ethereum_accounts,
    )
    dbevmtx = DBEvmTx(database)
    with database.conn.read_ctx() as cursor:
        results = dbevmtx.get_evm_transactions(
            cursor=cursor,
            filter_=filter_query,
        )
    assert len(results) == 1
    assert results[0] == transactions[0]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
@pytest.mark.parametrize('ethereum_accounts', [[ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3]])
def test_get_or_create_transaction(ethereum_accounts, eth_transactions, database):
    """Tests that get_or_create_transaction works fine. By testing get_or_create_transaction
    it checks that the requirements for a transaction are met before returning it."""
    msg_aggregator = MessagesAggregator()
    tx_hash = deserialize_evm_tx_hash('0x2e68dd828594ea71fe0afccfad7748c90ffcd0f1add44d0d249bf79887da9318')  # noqa: E501
    expected_transaction = EvmTransaction(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1451706400),
        block_number=3,
        from_address=ethereum_accounts[1],
        to_address=ethereum_accounts[2],
        value=FVal('4000000'),
        gas=FVal('5000000'),
        gas_price=FVal('2000000000'),
        gas_used=FVal('25000000'),
        input_data=MOCK_INPUT_DATA,
        nonce=1,
    )

    with database.conn.read_ctx() as cursor:
        # check that the transaction is properly added to the DB
        returned_tx, tx_receipt = eth_transactions.get_or_create_transaction(cursor, tx_hash, relevant_address=ethereum_accounts[2])  # noqa: E501
        assert len(msg_aggregator.consume_errors()) == 0
        assert len(msg_aggregator.consume_warnings()) == 0
        assert returned_tx == expected_transaction
        assert tx_receipt is not None
        # check that the existing transaction is properly returned from the DB
        returned_tx, tx_receipt = eth_transactions.get_or_create_transaction(cursor, tx_hash, relevant_address=ethereum_accounts[2])  # noqa: E501
        assert len(msg_aggregator.consume_errors()) == 0
        assert len(msg_aggregator.consume_warnings()) == 0
        assert returned_tx == expected_transaction

    # check that if there is a tx with no receipt, the receipt is created because it is a
    # requirement for an evm tx.
    with database.conn.write_ctx() as write_cursor:
        write_cursor.execute('DELETE FROM evmtx_receipts WHERE tx_id = ?', (returned_tx.db_id,))

    with database.conn.read_ctx() as cursor:
        tx_receipt = eth_transactions.dbevmtx.get_receipt(cursor, tx_hash, eth_transactions.evm_inquirer.chain_id)  # noqa: E501
        assert tx_receipt is None
        returned_tx, tx_receipt = eth_transactions.get_or_create_transaction(cursor, tx_hash, relevant_address=ethereum_accounts[2])  # noqa: E501
        assert tx_receipt is not None
