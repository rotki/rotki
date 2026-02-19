from contextlib import ExitStack
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.types import (
    EvmIndexer,
    NodeName,
    SerializableChainIndexerOrder,
    WeightedNode,
    string_to_evm_address,
)
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery, EvmTransactionsFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_ethereum_transaction, make_evm_address
from rotkehlchen.types import (
    ChainID,
    EvmInternalTransaction,
    EvmTransaction,
    EVMTxHash,
    Location,
    SupportedBlockchain,
    Timestamp,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.optimism.manager import OptimismManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress


ADDR_1, ADDR_2, ADDR_3 = make_evm_address(), make_evm_address(), make_evm_address()
YAB_ADDRESS = string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')


def _make_receipt_data(tx_hash: EVMTxHash) -> dict[str, Any]:
    return {
        'transactionHash': str(tx_hash),
        'contractAddress': None,
        'status': 1,
        'type': '0x0',
        'logs': [],
    }


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
    ethereum_events, gnosis_events = 3, 2
    dbevmtx = DBEvmTx(database)
    with database.user_write() as write_cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=write_cursor,
            filter_query=EvmEventFilterQuery.make(),
                        aggregate_by_group_ids=False,
        )
        assert len(events) == ethereum_events + gnosis_events

    with database.conn.write_ctx() as write_cursor:
        dbevmtx.delete_transactions(
            write_cursor=write_cursor,
            address=gnosis_accounts[0],
            chain=SupportedBlockchain.GNOSIS,
        )

    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
                        aggregate_by_group_ids=False,
        )
        assert len(events) == ethereum_events
        assert all(event.location == Location.ETHEREUM for event in events)


def test_erc20_transfers_range_not_updated_on_remote_error(database: 'DBHandler', ethereum_manager: 'EthereumManager') -> None:  # noqa: E501
    address = make_evm_address()
    with database.conn.read_ctx() as cursor:  # verify no range is initially stored
        assert database.get_used_query_range(
            cursor=cursor,
            name=(location_string := f'{ethereum_manager.node_inquirer.blockchain.to_range_prefix("tokentxs")}_{address}'),  # noqa: E501
        ) is None

    with ExitStack() as stack:
        for indexer in (
            ethereum_manager.node_inquirer.etherscan,
            ethereum_manager.node_inquirer.blockscout,
            ethereum_manager.node_inquirer.routescan,
        ):
            stack.enter_context(patch.object(
                target=indexer,
                attribute='get_token_transaction_hashes',
                side_effect=RemoteError('FAIL')),
            )

        ethereum_manager.transactions._get_erc20_transfers_for_ranges(
            address=address,
            start_ts=Timestamp(0),
            end_ts=Timestamp(1762453737),
        )

    with database.conn.read_ctx() as cursor:  # ensure the range was not marked as pulled
        assert database.get_used_query_range(cursor=cursor, name=location_string) is None


def test_query_and_save_transactions_returns_only_new_hashes(
        database: 'DBHandler',
        ethereum_manager: 'EthereumManager',
) -> None:
    dbevmtx = DBEvmTx(database)
    with database.user_write() as write_cursor:
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[existing_tx := make_ethereum_transaction()],
            relevant_address=(address := make_evm_address()),
        )

    with patch.object(
            ethereum_manager.node_inquirer,
            'get_transactions',
            return_value=iter([[existing_tx, new_tx := make_ethereum_transaction()]]),
    ):
        queried_hashes = ethereum_manager.transactions._query_and_save_transactions_for_range(
            address=address,
            period=TimestampOrBlockRange(range_type='blocks', from_value=0, to_value=1),
            return_queried_hashes=True,
        )

    assert queried_hashes == [new_tx.tx_hash]
    with database.conn.read_ctx() as cursor:
        txs = dbevmtx.get_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(chain_id=ChainID.ETHEREUM),
        )

    assert {tx.tx_hash for tx in txs} == {existing_tx.tx_hash, new_tx.tx_hash}


def test_query_and_save_internal_transactions_returns_only_new_hashes(
        database: 'DBHandler',
        ethereum_manager: 'EthereumManager',
) -> None:
    existing_parent_tx, new_parent_tx = make_ethereum_transaction(), make_ethereum_transaction()
    dbevmtx = DBEvmTx(database)
    with database.user_write() as write_cursor:
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[existing_parent_tx],
            relevant_address=(address := make_evm_address()),
        )
        dbevmtx.add_or_ignore_receipt_data(
            write_cursor=write_cursor,
            chain_id=ChainID.ETHEREUM,
            data=_make_receipt_data(existing_parent_tx.tx_hash),
        )

    def _mock_get_transaction_by_hash(
            tx_hash: EVMTxHash,
            call_order=None,
    ) -> tuple[EvmTransaction, dict[str, Any]]:
        if tx_hash == new_parent_tx.tx_hash:
            return new_parent_tx, _make_receipt_data(new_parent_tx.tx_hash)
        raise AssertionError(f'Unexpected tx hash {tx_hash!s}')

    with patch.object(
        ethereum_manager.node_inquirer,
        'get_transactions',
        return_value=iter([[EvmInternalTransaction(
            parent_tx_hash=existing_parent_tx.tx_hash,
            chain_id=ChainID.ETHEREUM,
            trace_id=1,
            from_address=make_evm_address(),
            to_address=make_evm_address(),
            value=1,
            gas=1,
            gas_used=1,
        ), EvmInternalTransaction(
            parent_tx_hash=new_parent_tx.tx_hash,
            chain_id=ChainID.ETHEREUM,
            trace_id=2,
            from_address=make_evm_address(),
            to_address=make_evm_address(),
            value=1,
            gas=1,
            gas_used=1,
        ),
    ]])), patch.object(
        ethereum_manager.node_inquirer,
        'get_transaction_by_hash',
        side_effect=_mock_get_transaction_by_hash,
    ):
        queried_hashes = ethereum_manager.transactions._query_and_save_internal_transactions_for_range_or_parent_hash(  # noqa: E501
            address=address,
            period_or_hash=TimestampOrBlockRange(range_type='blocks', from_value=0, to_value=1),
            return_queried_hashes=True,
        )

    assert queried_hashes == [new_parent_tx.tx_hash]


def test_query_single_parent_hash_replaces_existing_internal_transactions(
        database: 'DBHandler',
        ethereum_manager: 'EthereumManager',
) -> None:
    """For parent hash queries we should replace old internal tx rows atomically.

    This avoids accumulating duplicate-like rows when indexers return the same transfer
    with different gas metadata after a repull.
    """
    dbevmtx = DBEvmTx(database)
    parent_tx, sender, receiver = make_ethereum_transaction(), make_evm_address(), make_evm_address()  # noqa: E501
    receiver = make_evm_address()
    with database.user_write() as write_cursor:
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[parent_tx],
            relevant_address=None,
        )
        dbevmtx.add_or_ignore_receipt_data(
            write_cursor=write_cursor,
            chain_id=ChainID.ETHEREUM,
            data=_make_receipt_data(parent_tx.tx_hash),
        )
        dbevmtx.add_evm_internal_transactions(
            write_cursor=write_cursor,
            transactions=[EvmInternalTransaction(
                parent_tx_hash=parent_tx.tx_hash,
                chain_id=ChainID.ETHEREUM,
                trace_id=1,
                from_address=sender,
                to_address=receiver,
                value=100,
                gas=0,
                gas_used=0,
            )],
            relevant_address=None,
        )

    with patch.object(
        ethereum_manager.node_inquirer,
        'get_transactions',
        return_value=iter([[EvmInternalTransaction(
            parent_tx_hash=parent_tx.tx_hash,
            chain_id=ChainID.ETHEREUM,
            trace_id=1,
            from_address=sender,
            to_address=receiver,
            value=100,
            gas=30945,
            gas_used=0,
        )]]),
    ):
        ethereum_manager.transactions._query_and_save_internal_transactions_for_range_or_parent_hash(
            period_or_hash=parent_tx.tx_hash,
        )

    with database.conn.read_ctx() as cursor:
        tx_identifier = cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (parent_tx.tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()[0]
        rows = cursor.execute(
            'SELECT trace_id, from_address, to_address, value, gas, gas_used '
            'FROM evm_internal_transactions WHERE parent_tx=?',
            (tx_identifier,),
        ).fetchall()

    assert rows == [(1, sender, receiver, '100', '30945', '0')]


def test_query_and_save_erc20_transfers_returns_only_new_hashes(
        database: 'DBHandler',
        ethereum_manager: 'EthereumManager',
) -> None:
    address = make_evm_address()
    existing_tx = make_ethereum_transaction()
    new_tx = make_ethereum_transaction()
    dbevmtx = DBEvmTx(database)
    with database.user_write() as write_cursor:
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[existing_tx],
            relevant_address=address,
        )
        dbevmtx.add_or_ignore_receipt_data(
            write_cursor=write_cursor,
            chain_id=ChainID.ETHEREUM,
            data=_make_receipt_data(existing_tx.tx_hash),
        )

    period = TimestampOrBlockRange(
        range_type='timestamps',
        from_value=Timestamp(0),
        to_value=Timestamp(1),
    )
    location_string = (
        f'{ethereum_manager.node_inquirer.blockchain.to_range_prefix("tokentxs")}_{address}'
    )

    def _mock_get_transaction_by_hash(
            tx_hash: EVMTxHash,
            call_order=None,
    ) -> tuple[EvmTransaction, dict[str, Any]]:
        if tx_hash == new_tx.tx_hash:
            return new_tx, _make_receipt_data(new_tx.tx_hash)
        raise AssertionError(f'Unexpected tx hash {tx_hash!s}')

    with patch.object(
            ethereum_manager.node_inquirer,
            'get_blocknumber_by_time',
            side_effect=[0, 1],
    ), patch.object(
            ethereum_manager.node_inquirer,
            'get_token_transaction_hashes',
            return_value=iter([[existing_tx.tx_hash, new_tx.tx_hash]]),
    ), patch.object(
            ethereum_manager.node_inquirer,
            'get_transaction_by_hash',
            side_effect=_mock_get_transaction_by_hash,
    ):
        queried_hashes = ethereum_manager.transactions._query_and_save_erc20_transfers_for_range(
            address=address,
            period=period,
            location_string=location_string,
            return_queried_hashes=True,
        )

    assert queried_hashes == [new_tx.tx_hash]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', [{'evm_indexers_order': SerializableChainIndexerOrder(
    order={ChainID.OPTIMISM: [EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT, EvmIndexer.ROUTESCAN]},
)}])
@pytest.mark.parametrize('optimism_manager_connect_at_start', [(WeightedNode(node_info=NodeName(name='mainnet-optimism', endpoint='https://mainnet.optimism.io', owned=True, blockchain=SupportedBlockchain.OPTIMISM), active=True, weight=ONE),)])  # noqa: E501
@pytest.mark.parametrize('optimism_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
@pytest.mark.parametrize('tested_indexer', ['blockscout', 'routescan'])
def test_indexers_fall_back_properly(
        database: 'DBHandler',
        optimism_manager: 'OptimismManager',
        optimism_accounts: list['ChecksumEvmAddress'],
        tested_indexer: str,
) -> None:
    """Test that queries such as txlist, txlistinteral, etc which rely on indexers such as
    etherscan, blockscout, and routescan properly fall back to the next indexer on failure.
    """
    assert optimism_manager.node_inquirer.blockscout is not None
    txs_mocks, hashes_mocks, unused_mocks, have_reached_tested_indexer = [], [], [], False
    with ExitStack() as stack:
        for indexer, name in (
            (optimism_manager.node_inquirer.etherscan, 'etherscan'),
            (optimism_manager.node_inquirer.blockscout, 'blockscout'),
            (optimism_manager.node_inquirer.routescan, 'routescan'),
        ):
            stack.enter_context(patch.object(
                target=indexer,
                attribute='get_blocknumber_by_time',
                wraps=indexer.get_blocknumber_by_time,
            ) if name == tested_indexer else patch.object(
                target=indexer,
                attribute='get_blocknumber_by_time',
                side_effect=RemoteError('FAIL'),
            ))
            txs_mock = stack.enter_context(patch.object(
                target=indexer,
                attribute='get_transactions',
                wraps=indexer.get_transactions,
            ) if name == tested_indexer else patch.object(
                target=indexer,
                attribute='get_transactions',
                side_effect=RemoteError('FAIL'),
            ))
            hashes_mock = stack.enter_context(patch.object(
                target=indexer,
                attribute='get_token_transaction_hashes',
                wraps=indexer.get_token_transaction_hashes,
            ) if name == tested_indexer else patch.object(
                target=indexer,
                attribute='get_token_transaction_hashes',
                side_effect=RemoteError('FAIL'),
            ))

            if have_reached_tested_indexer:
                unused_mocks.extend([txs_mock, hashes_mock])
            else:
                txs_mocks.append(txs_mock)
                hashes_mocks.append(hashes_mock)

            if name == tested_indexer:
                have_reached_tested_indexer = True

        optimism_manager.transactions.single_address_query_transactions(
            address=optimism_accounts[0],
            start_ts=Timestamp(1729116000),
            end_ts=Timestamp(1729117000),
        )  # Query a small range that returns only two txs

    # Check the txlist and txlistinternal actions were called for all used indexers
    assert all(txs_mock.call_count == 2 for txs_mock in txs_mocks)
    assert all(
        {x.kwargs['action'] for x in txs_mock.call_args_list} == {'txlist', 'txlistinternal'}
        for txs_mock in txs_mocks
    )
    # Check that the tx hashes query only happened once for all used indexers
    assert all(hashes_mock.call_count == 1 for hashes_mock in hashes_mocks)
    assert all(hashes_mock.call_args_list == hashes_mocks[0].call_args_list for hashes_mock in hashes_mocks)  # noqa: E501
    # Check that all unused indexers were not called
    assert all(unused_mock.call_count == 0 for unused_mock in unused_mocks)

    # Check that the actual tx data is present in the DB
    dbevmtx = DBEvmTx(database)
    with database.conn.read_ctx() as cursor:
        txs = dbevmtx.get_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(),
        )
        assert len(txs) == 2
        assert {x.tx_hash for x in txs} == {
            (tx_hash1 := deserialize_evm_tx_hash('0x24cf6c88c9645cb5e92596488206319c39a0a1c4e2829a83c690df8f11cb80b6')),  # noqa: E501
            deserialize_evm_tx_hash('0x6d11b151d37310d148ca9177b436bad7f5caea7bb41591acf7b2d11466088d80'),
        }

        # Check that an internal tx (always queried via an indexer) was properly retrieved.
        internal_txs = dbevmtx.get_evm_internal_transactions(
            parent_tx_hash=tx_hash1,
            blockchain=SupportedBlockchain.OPTIMISM,
        )
        assert len(internal_txs) == 1  # tx has two internal txs but only one involves the tracked address.  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_all_indexers_get_same_tx_results(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that all indexers return the same results for the same tx queries."""
    txlist_results: list[list[EvmTransaction]] = []
    txlistinteral_results: list[list[EvmInternalTransaction]] = []
    for indexer in (
        ethereum_inquirer.etherscan,
        ethereum_inquirer.blockscout,
        ethereum_inquirer.routescan,
    ):
        for action, result_list in (
            ('txlist', txlist_results),
            ('txlistinternal', txlistinteral_results),
        ):
            # get_transactions returns an iterator of lists. Consume the iterator, check that
            # only one list was returned, and append that list to the result_list.
            assert len(result := list(indexer.get_transactions(  # type: ignore[call-overload]  # mypy doesn't understand that action will be a valid literal
                chain_id=ethereum_inquirer.chain_id,
                account=ethereum_accounts[0],
                action=action,
                period_or_hash=TimestampOrBlockRange(
                    range_type='timestamps',
                    from_value=Timestamp(1720000000),
                    to_value=Timestamp(1735000000),
                ),
            ))) == 1
            result_list.append(result[0])

    # Check that there are 6 txs and 1 internal tx for the requested range and that the results
    # from each indexer all match. trace_id is excluded since it varies between indexers.
    assert len(txlist_results[0]) == 6
    assert all(x == txlist_results[0] for x in txlist_results[1:])
    assert len(txlistinteral_results[0]) == 1
    for idx, internal_tx_list in enumerate(txlistinteral_results):
        txlistinteral_results[idx] = [x._replace(trace_id=0) for x in internal_tx_list]
    assert all(x == txlistinteral_results[0] for x in txlistinteral_results[1:])
