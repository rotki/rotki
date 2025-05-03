from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.types import EvmAccount, string_to_evm_address
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery, EvmTransactionsFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import ChainID, Location, SupportedBlockchain, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
    from rotkehlchen.db.dbhandler import DBHandler


ADDR_1, ADDR_2, ADDR_3 = make_evm_address(), make_evm_address(), make_evm_address()
YAB_ADDRESS = string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')


def test_query_transactions_single_chain(eth_transactions: 'EthereumTransactions'):
    """
    Test that when querying transactions for a single chain, addresses only for that chain are
    queried. This tests passes several addresses for different chains to `EthereumTransactions`
    and checks that only ethereum addresses are queried.
    """
    queried_addresses = []

    def mock_single_address_query_transactions(address, **kwargs):  # pylint: disable=unused-argument
        queried_addresses.append(address)

    query_patch = patch.object(
        eth_transactions,
        'single_address_query_transactions',
        wraps=mock_single_address_query_transactions,
    )

    with query_patch:
        eth_transactions.query_chain(filter_query=EvmTransactionsFilterQuery.make(
            accounts=[
                EvmAccount(address=ADDR_1, chain_id=ChainID.OPTIMISM),
                EvmAccount(address=ADDR_2, chain_id=ChainID.ETHEREUM),
                EvmAccount(address=ADDR_3, chain_id=ChainID.ETHEREUM),
            ],
        ))

    assert queried_addresses == [ADDR_2, ADDR_3]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[YAB_ADDRESS]])
@pytest.mark.parametrize('gnosis_accounts', [[YAB_ADDRESS]])
def test_delete_transactions_by_chain(
        database: 'DBHandler',
        gnosis_accounts,
        ethereum_inquirer,
        gnosis_inquirer,
) -> None:
    """
    Test that deleting transactions by chain doesn't delete events
    for the same address in other chains.s
    """
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xac02ba9db26eee16f72a4b155fd07517ead140a539b1c41b67ba5a52b85d9dcb'),
        relevant_address=gnosis_accounts[0],
    )
    get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xafce539bd7fb898c5f03fdccf4c34e2c5c9ca321d612142953a7baf2849caafd'),
        relevant_address=gnosis_accounts[0],
    )

    with database.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT tx_id, topic_id FROM evmtx_receipt_log_topics JOIN '
            'evmtx_receipt_logs ON evmtx_receipt_log_topics.log=evmtx_receipt_logs.identifier ',
        )
        # We have two transactions, the first one uses topic_ids [1, 2] from evmtx_topics_index
        # and the second transaction uses topics_ids [2, 3, 4]. The topic with id 2 is
        # common to both transactions.
        assert cursor.fetchall() == [(1, 1), (1, 2), (2, 3), (2, 4), (2, 2)]

    ethereum_events, gnosis_events = 3, 2
    dbevmtx = DBEvmTx(database)
    with database.user_write() as write_cursor:
        events = DBHistoryEvents(database).get_history_events(
            cursor=write_cursor,
            filter_query=EvmEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
        assert len(events) == ethereum_events + gnosis_events

    with database.conn.write_ctx() as write_cursor:
        dbevmtx.delete_transactions(
            write_cursor=write_cursor,
            address=gnosis_accounts[0],
            chain=SupportedBlockchain.GNOSIS,
        )

    with database.conn.read_ctx() as cursor:
        topic_ids_in_use = [
            row[0] for row in cursor.execute('SELECT topic_id FROM evmtx_topics_index')
        ]
        # After deleting the second transaction we keep the topic_id that was being used only
        # by the first transaction and the topic that was common to both.
        assert topic_ids_in_use == [1, 2]

    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
        assert len(events) == ethereum_events
        assert all(event.location == Location.ETHEREUM for event in events)

    # delete all the transactions and check that the evmtx_topics_index table
    # gets emptied
    with database.conn.write_ctx() as write_cursor:
        dbevmtx.delete_transactions(
            write_cursor=write_cursor,
            address=gnosis_accounts[0],
            chain=SupportedBlockchain.ETHEREUM,
        )

    with database.conn.read_ctx() as cursor:
        # after deleting the first transaction added we don't keep any topic indexed.
        assert cursor.execute('SELECT COUNT(*) FROM evmtx_topics_index').fetchone()[0] == 0
