from contextlib import ExitStack
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.evm.types import (
    EvmAccount,
    EvmIndexer,
    NodeName,
    SerializableChainIndexerOrder,
    WeightedNode,
    string_to_evm_address,
)
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    TX_DECODED,
    HistoryMappingState,
    InternalTxSource,
)
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery, EvmTransactionsFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import DataIntegrityError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
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
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
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
        database: DBHandler,
        gnosis_accounts,
        ethereum_inquirer,
        gnosis_inquirer,
        allow_gnosis_etherscan: None,
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


def test_erc20_transfers_range_not_updated_on_remote_error(database: DBHandler, ethereum_manager: EthereumManager) -> None:  # noqa: E501
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
                attribute='get_token_transaction_data',
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
        database: DBHandler,
        ethereum_manager: EthereumManager,
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


@pytest.mark.parametrize('customized', [False, True])
@pytest.mark.parametrize('has_existing_mapping', [False, True])
def test_existing_decoded_transaction_is_redecoded_for_new_address(
        database: DBHandler,
        ethereum_manager: EthereumManager,
        customized: bool,
        has_existing_mapping: bool,
) -> None:
    """A newly discovered address invalidates stale decoded events."""
    dbevmtx = DBEvmTx(database)
    dbevents = DBHistoryEvents(database)
    transaction = make_ethereum_transaction()
    first_address, new_address = make_evm_address(), make_evm_address()
    with database.user_write() as write_cursor:
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[transaction],
            relevant_address=first_address if has_existing_mapping else None,
        )
        dbevmtx.add_or_ignore_receipt_data(
            write_cursor=write_cursor,
            chain_id=ChainID.ETHEREUM,
            data=_make_receipt_data(transaction.tx_hash),
        )
        dbevents.add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=transaction.tx_hash,
                sequence_index=0,
                timestamp=TimestampMS(transaction.timestamp * 1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
                location_label=first_address,
            ),
            mapping_values=(
                {HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED}
                if customized else None
            ),
        )
        tx_id = write_cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (transaction.tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()[0]
        write_cursor.execute(
            'INSERT INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
            (tx_id, TX_DECODED),
        )
        if customized is False:
            database.add_to_ignored_action_ids(
                write_cursor=write_cursor,
                identifiers=[transaction.identifier],
            )

    database.pending_txs_tracker.mark_decoding_clean(
        SupportedBlockchain.ETHEREUM,
        Timestamp(1000),
    )
    timestamps, newly_inserted = ethereum_manager.transactions._batch_ensure_evm_txns_in_db(
        tx_hashes=[transaction.tx_hash],
        relevant_address=new_address,
    )

    assert timestamps == {transaction.tx_hash: transaction.timestamp}
    assert newly_inserted == []
    should_redecode = customized is False
    expected_remaining_entries = 0 if should_redecode else 1
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM evm_tx_mappings WHERE tx_id=? AND value=?',
            (tx_id, TX_DECODED),
        ).fetchone()[0] == expected_remaining_entries
        assert cursor.execute(
            'SELECT COUNT(*) FROM chain_events_info WHERE tx_ref=?',
            (transaction.tx_hash,),
        ).fetchone()[0] == expected_remaining_entries
        assert cursor.execute(
            'SELECT COUNT(*) FROM evmtx_address_mappings WHERE tx_id=? AND address=?',
            (tx_id, new_address),
        ).fetchone()[0] == 1
        ignored_ids = database.get_ignored_action_ids(cursor)
        if customized:
            assert transaction.identifier not in ignored_ids
        else:
            # Auto-ignored zero-event transactions remain ignored because they cannot be
            # distinguished from transactions the user explicitly ignored.
            assert transaction.identifier in ignored_ids

    assert database.pending_txs_tracker.should_scan_decoding(
        blockchain=SupportedBlockchain.ETHEREUM,
        now=Timestamp(1000),
    ) is should_redecode
    if should_redecode:
        with database.user_write() as write_cursor:
            write_cursor.execute(
                'INSERT INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
                (tx_id, TX_DECODED),
            )
        ethereum_manager.transactions._batch_ensure_evm_txns_in_db(
            tx_hashes=[transaction.tx_hash],
            relevant_address=new_address,
        )
        with database.conn.read_ctx() as cursor:
            assert cursor.execute(
                'SELECT COUNT(*) FROM evm_tx_mappings WHERE tx_id=? AND value=?',
                (tx_id, TX_DECODED),
            ).fetchone()[0] == 1
            assert cursor.execute(
                'SELECT COUNT(*) FROM evmtx_address_mappings WHERE tx_id=? AND address=?',
                (tx_id, new_address),
            ).fetchone()[0] == 1


def test_first_evm_mapping_keeps_events_already_referencing_address(
        database: DBHandler,
        ethereum_manager: EthereumManager,
) -> None:
    """A by-hash decode for an already tracked address should not be invalidated."""
    dbevmtx = DBEvmTx(database)
    transaction = make_ethereum_transaction()
    relevant_address = make_evm_address()
    with database.user_write() as write_cursor:
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[transaction],
            relevant_address=None,
        )
        dbevmtx.add_or_ignore_receipt_data(
            write_cursor=write_cursor,
            chain_id=ChainID.ETHEREUM,
            data=_make_receipt_data(transaction.tx_hash),
        )
        DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=transaction.tx_hash,
                sequence_index=0,
                timestamp=TimestampMS(transaction.timestamp * 1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
                location_label=relevant_address,
            ),
        )
        tx_id = write_cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (transaction.tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()[0]
        write_cursor.execute(
            'INSERT INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
            (tx_id, TX_DECODED),
        )

    ethereum_manager.transactions._batch_ensure_evm_txns_in_db(
        tx_hashes=[transaction.tx_hash],
        relevant_address=relevant_address,
    )

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM evm_tx_mappings WHERE tx_id=? AND value=?',
            (tx_id, TX_DECODED),
        ).fetchone()[0] == 1
        assert cursor.execute(
            'SELECT COUNT(*) FROM chain_events_info WHERE tx_ref=?',
            (transaction.tx_hash,),
        ).fetchone()[0] == 1
        assert cursor.execute(
            'SELECT COUNT(*) FROM evmtx_address_mappings WHERE tx_id=? AND address=?',
            (tx_id, relevant_address),
        ).fetchone()[0] == 1


def test_existing_transactions_are_batched_for_redecoding(database: DBHandler) -> None:
    dbevmtx = DBEvmTx(database)
    dbevents = DBHistoryEvents(database)
    transactions = [make_ethereum_transaction() for _ in range(3)]
    tx_ids: list[int] = []
    with database.user_write() as write_cursor:
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=transactions,
            relevant_address=make_evm_address(),
        )
        for transaction in transactions:
            tx_ids.append(tx_id := transaction.get_or_query_db_id(write_cursor))
            write_cursor.execute(
                'INSERT INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
                (tx_id, TX_DECODED),
            )
        dbevents.add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=transactions[0].tx_hash,
                sequence_index=0,
                timestamp=TimestampMS(transactions[0].timestamp * 1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
            ),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED},
        )

    with (
        patch.object(
            DBHistoryEvents,
            'delete_events_by_tx_ref',
            wraps=dbevents.delete_events_by_tx_ref,
        ) as delete_events_mock,
        patch.object(
            database.pending_txs_tracker,
            'mark_decoding_dirty',
            wraps=database.pending_txs_tracker.mark_decoding_dirty,
        ) as mark_decoding_dirty_mock,
        database.user_write() as write_cursor,
    ):
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=transactions,
            relevant_address=make_evm_address(),
        )

    assert delete_events_mock.call_count == 1
    assert set(delete_events_mock.call_args.kwargs['tx_refs']) == {
        transaction.tx_hash for transaction in transactions[1:]
    }
    mark_decoding_dirty_mock.assert_called_once_with(SupportedBlockchain.ETHEREUM)
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            f'SELECT COUNT(*) FROM evm_tx_mappings WHERE value=? AND tx_id IN '
            f'({",".join(["?"] * len(tx_ids))})',
            (TX_DECODED, *tx_ids),
        ).fetchone()[0] == 1
        assert cursor.execute(
            f'SELECT COUNT(*) FROM evmtx_address_mappings WHERE tx_id IN '
            f'({",".join(["?"] * len(tx_ids))})',
            tx_ids,
        ).fetchone()[0] == len(tx_ids) * 2


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [[
    '0xBD6F210A624a792e7d30A2F7591Dc7Abce2F3C48',
]])
def test_shared_transaction_is_redecoded_for_new_address(
        database: DBHandler,
        gnosis_inquirer: GnosisInquirer,
        gnosis_accounts: list[ChecksumEvmAddress],
        allow_gnosis_etherscan: None,
) -> None:
    first_address = gnosis_accounts[0]
    new_address = string_to_evm_address('0xCDF16E42b6740D906858f37e9be495A59DAadE9E')
    tx_hash = deserialize_evm_tx_hash('0x69b568b97434807430a2f9eb5cbbbeaab701a32df76746a4e357386e5c431bab')  # noqa: E501
    initial_events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
        relevant_address=first_address,
    )
    assert len(initial_events) == 3
    assert all(event.location_label != new_address for event in initial_events)

    dbevmtx = DBEvmTx(database)
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.GNOSIS,
                address=new_address,
            )],
        )
        transaction = dbevmtx.get_transactions(
            cursor=write_cursor,
            filter_=EvmTransactionsFilterQuery.make(
                tx_hash=tx_hash,
                chain_id=ChainID.GNOSIS,
            ),
        )[0]
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[transaction],
            relevant_address=new_address,
        )
        tx_id = transaction.get_or_query_db_id(write_cursor)
        assert write_cursor.execute(
            'SELECT COUNT(*) FROM evmtx_address_mappings WHERE tx_id=?',
            (tx_id,),
        ).fetchone()[0] == 2
        assert write_cursor.execute(
            'SELECT COUNT(*) FROM evm_tx_mappings WHERE tx_id=? AND value=?',
            (tx_id, TX_DECODED),
        ).fetchone()[0] == 0
        assert write_cursor.execute(
            'SELECT COUNT(*) FROM chain_events_info WHERE tx_ref=?',
            (tx_hash,),
        ).fetchone()[0] == 0

    with patch_decoder_reload_data():
        decoder.get_and_decode_undecoded_transactions(limit=None)

    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(tx_hashes=[tx_hash]),
        )

    assert len(events) == 4
    assert len(new_address_events := [
        event for event in events if event.location_label == new_address
    ]) == 1
    assert new_address_events[0].asset == Asset(
        'eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430',
    )
    assert new_address_events[0].amount == FVal('4292.336430016873387617')


@pytest.mark.parametrize('discovery_type', ['erc20', 'internal'])
def test_cached_transaction_is_mapped_to_discovering_address(
        database: DBHandler,
        ethereum_manager: EthereumManager,
        discovery_type: str,
) -> None:
    """Cached transactions should remain associated with every tracked address."""
    dbevmtx = DBEvmTx(database)
    transaction = make_ethereum_transaction()
    first_address, second_address, unrelated_address = (
        make_evm_address(),
        make_evm_address(),
        make_evm_address(),
    )
    with database.user_write() as write_cursor:
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[transaction],
            relevant_address=first_address,
        )
        dbevmtx.add_or_ignore_receipt_data(
            write_cursor=write_cursor,
            chain_id=ChainID.ETHEREUM,
            data=_make_receipt_data(transaction.tx_hash),
        )

    if discovery_type == 'erc20':
        with (
            patch.object(
                ethereum_manager.node_inquirer,
                'get_blocknumber_by_time',
                side_effect=[0, 1, 0, 1],
            ),
            patch.object(
                ethereum_manager.node_inquirer,
                'get_token_transaction_hashes',
                side_effect=[iter([[transaction.tx_hash]]), iter([[transaction.tx_hash]])],
            ),
        ):
            for _ in range(2):
                ethereum_manager.transactions._query_and_save_erc20_transfers_for_range(
                    address=second_address,
                    period=TimestampOrBlockRange(
                        range_type='timestamps',
                        from_value=Timestamp(0),
                        to_value=Timestamp(1),
                    ),
                    location_string=f'eth_tokentxs_{second_address}',
                    update_ranges=False,
                )
    else:
        internal_transaction = EvmInternalTransaction(
            parent_tx_hash=transaction.tx_hash,
            chain_id=ChainID.ETHEREUM,
            trace_id=1,
            from_address=first_address,
            to_address=second_address,
            value=1,
            gas=1,
            gas_used=1,
        )
        with patch.object(
            ethereum_manager.node_inquirer,
            'get_transactions_with_source',
            side_effect=[
                (iter([[internal_transaction]]), EvmIndexer.ETHERSCAN),
                (iter([[internal_transaction]]), EvmIndexer.ETHERSCAN),
            ],
        ):
            for _ in range(2):
                ethereum_manager.transactions._query_and_save_internal_transactions_for_range(
                    address=second_address,
                    period=TimestampOrBlockRange(
                        range_type='blocks',
                        from_value=0,
                        to_value=1,
                    ),
                )

    with database.user_write() as write_cursor:
        tx_id = transaction.get_or_query_db_id(write_cursor)
        assert write_cursor.execute(
            'SELECT address FROM evmtx_address_mappings WHERE tx_id=? ORDER BY address',
            (tx_id,),
        ).fetchall() == sorted([(first_address,), (second_address,)])
        assert dbevmtx.get_transactions(
            cursor=write_cursor,
            filter_=EvmTransactionsFilterQuery.make(
                accounts=[EvmAccount(address=second_address, chain_id=ChainID.ETHEREUM)],
                chain_id=ChainID.ETHEREUM,
            ),
        ) == [transaction]
        assert dbevmtx.get_transactions(
            cursor=write_cursor,
            filter_=EvmTransactionsFilterQuery.make(
                accounts=[EvmAccount(address=unrelated_address, chain_id=ChainID.ETHEREUM)],
                chain_id=ChainID.ETHEREUM,
            ),
        ) == []
        DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=transaction.tx_hash,
                sequence_index=0,
                timestamp=TimestampMS(transaction.timestamp * 1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
                location_label=second_address,
            ),
        )
        dbevmtx.delete_transactions(
            write_cursor=write_cursor,
            address=first_address,
            chain=SupportedBlockchain.ETHEREUM,
        )

    with database.conn.read_ctx() as cursor:
        assert dbevmtx.get_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(
                accounts=[EvmAccount(address=second_address, chain_id=ChainID.ETHEREUM)],
                chain_id=ChainID.ETHEREUM,
            ),
        ) == [transaction]
        assert len(DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(tx_hashes=[transaction.tx_hash]),
        )) == 1


def test_query_and_save_internal_transactions_returns_only_new_hashes(
        database: DBHandler,
        ethereum_manager: EthereumManager,
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
        'get_transactions_with_source',
        return_value=(iter([[EvmInternalTransaction(
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
    ]]), EvmIndexer.ETHERSCAN)), patch.object(
        ethereum_manager.node_inquirer,
        'get_transaction_by_hash',
        side_effect=_mock_get_transaction_by_hash,
    ):
        queried_hashes = ethereum_manager.transactions._query_and_save_internal_transactions_for_range(  # noqa: E501
            address=address,
            period=TimestampOrBlockRange(range_type='blocks', from_value=0, to_value=1),
            return_queried_hashes=True,
        )

    assert queried_hashes == [new_parent_tx.tx_hash]


def test_query_single_parent_hash_replaces_existing_internal_transactions(
        database: DBHandler,
        ethereum_manager: EthereumManager,
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
        'get_transactions_with_source',
        return_value=(iter([[EvmInternalTransaction(
            parent_tx_hash=parent_tx.tx_hash,
            chain_id=ChainID.ETHEREUM,
            trace_id=1,
            from_address=sender,
            to_address=receiver,
            value=100,
            gas=30945,
            gas_used=0,
        )]]), EvmIndexer.ETHERSCAN),
    ):
        ethereum_manager.transactions._query_and_save_internal_transactions_for_parent_hash(
            parent_tx_hash=parent_tx.tx_hash,
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


def test_empty_repull_blocked_when_db_has_internals(
        database: DBHandler,
        ethereum_manager: EthereumManager,
) -> None:
    """Case A: empty re-pull + DB has existing internals => raises RemoteError, DB unchanged."""
    dbevmtx = DBEvmTx(database)
    parent_tx = make_ethereum_transaction()
    sender, receiver = make_evm_address(), make_evm_address()
    existing_internal_tx = EvmInternalTransaction(
        parent_tx_hash=parent_tx.tx_hash,
        chain_id=ChainID.ETHEREUM,
        trace_id=1,
        from_address=sender,
        to_address=receiver,
        value=100,
        gas=0,
        gas_used=0,
    )
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
            transactions=[existing_internal_tx],
            relevant_address=None,
        )

    # Indexer returns empty list (simulating Blockscout indexing issue)
    with patch.object(
        ethereum_manager.node_inquirer,
        'get_transactions_with_source',
        return_value=(iter([[]]), EvmIndexer.BLOCKSCOUT),
    ), pytest.raises(DataIntegrityError, match='empty result'):
        ethereum_manager.transactions._query_and_save_internal_transactions_for_parent_hash(
            parent_tx_hash=parent_tx.tx_hash,
        )

    # DB must remain untouched
    with database.conn.read_ctx() as cursor:
        parent_tx_id = cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (parent_tx.tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()[0]
    stored = dbevmtx.get_evm_internal_transactions(
        parent_tx_hash=parent_tx.tx_hash,
        blockchain=SupportedBlockchain.ETHEREUM,
        parent_tx_id=parent_tx_id,
    )
    assert stored == [existing_internal_tx]


def test_empty_repull_allowed_when_db_has_no_internals(
        database: DBHandler,
        ethereum_manager: EthereumManager,
) -> None:
    """Case B: empty re-pull + DB has no internals => no error, normal empty handling."""
    dbevmtx = DBEvmTx(database)
    parent_tx = make_ethereum_transaction()
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

    # Indexer returns empty list and DB has no existing internals — should be a no-op
    with patch.object(
        ethereum_manager.node_inquirer,
        'get_transactions_with_source',
        return_value=(iter([[]]), EvmIndexer.BLOCKSCOUT),
    ):
        ethereum_manager.transactions._query_and_save_internal_transactions_for_parent_hash(
            parent_tx_hash=parent_tx.tx_hash,
        )

    with database.conn.read_ctx() as cursor:
        parent_tx_id = cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (parent_tx.tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()[0]
    stored = dbevmtx.get_evm_internal_transactions(
        parent_tx_hash=parent_tx.tx_hash,
        blockchain=SupportedBlockchain.ETHEREUM,
        parent_tx_id=parent_tx_id,
    )
    assert stored == []


def test_nonempty_repull_replaces_existing_internals(
        database: DBHandler,
        ethereum_manager: EthereumManager,
) -> None:
    """Case C: non-empty re-pull + DB has existing internals => replacement succeeds."""
    dbevmtx = DBEvmTx(database)
    parent_tx = make_ethereum_transaction()
    sender, receiver = make_evm_address(), make_evm_address()
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
                value=50,
                gas=0,
                gas_used=0,
            )],
            relevant_address=None,
        )

    updated_internal_tx = EvmInternalTransaction(
        parent_tx_hash=parent_tx.tx_hash,
        chain_id=ChainID.ETHEREUM,
        trace_id=1,
        from_address=sender,
        to_address=receiver,
        value=50,
        gas=21000,  # updated gas
        gas_used=0,
    )
    with patch.object(
        ethereum_manager.node_inquirer,
        'get_transactions_with_source',
        return_value=(iter([[updated_internal_tx]]), EvmIndexer.ROUTESCAN),
    ):
        ethereum_manager.transactions._query_and_save_internal_transactions_for_parent_hash(
            parent_tx_hash=parent_tx.tx_hash,
        )

    with database.conn.read_ctx() as cursor:
        parent_tx_id = cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (parent_tx.tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()[0]
    stored = dbevmtx.get_evm_internal_transactions(
        parent_tx_hash=parent_tx.tx_hash,
        blockchain=SupportedBlockchain.ETHEREUM,
        parent_tx_id=parent_tx_id,
    )
    assert stored == [updated_internal_tx]
    # the indexer that produced the row is persisted and read back (equality only checks
    # identity, so assert source explicitly). 'routescan' -> InternalTxSource.ROUTESCAN
    assert stored[0].source == InternalTxSource.ROUTESCAN


def test_query_range_replaces_internal_transactions_for_address(
        database: DBHandler,
        ethereum_manager: EthereumManager,
) -> None:
    """Range refetch should replace stale internals for the queried address only."""
    dbevmtx = DBEvmTx(database)
    parent_tx = make_ethereum_transaction()
    queried_address, receiver = make_evm_address(), make_evm_address()
    unrelated_sender, unrelated_receiver = make_evm_address(), make_evm_address()
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
                from_address=queried_address,
                to_address=receiver,
                value=100,
                gas=0,
                gas_used=0,
            ), EvmInternalTransaction(
                parent_tx_hash=parent_tx.tx_hash,
                chain_id=ChainID.ETHEREUM,
                trace_id=2,
                from_address=unrelated_sender,
                to_address=unrelated_receiver,
                value=111,
                gas=123,
                gas_used=0,
            )],
            relevant_address=None,
        )

    with database.conn.read_ctx() as cursor:
        tx_identifier = cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (parent_tx.tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()[0]
        rows_before = cursor.execute(
            'SELECT trace_id, from_address, to_address, value, gas, gas_used '
            'FROM evm_internal_transactions WHERE parent_tx=? ORDER BY trace_id ASC',
            (tx_identifier,),
        ).fetchall()
    assert rows_before == [
        (1, queried_address, receiver, '100', '0', '0'),
        (2, unrelated_sender, unrelated_receiver, '111', '123', '0'),
    ]

    with patch.object(
        ethereum_manager.node_inquirer,
        'get_transactions_with_source',
        return_value=(iter([[EvmInternalTransaction(
            parent_tx_hash=parent_tx.tx_hash,
            chain_id=ChainID.ETHEREUM,
            trace_id=1,
            from_address=queried_address,
            to_address=receiver,
            value=100,
            gas=30945,
            gas_used=0,
        )]]), EvmIndexer.ETHERSCAN),
    ):
        ethereum_manager.transactions._query_and_save_internal_transactions_for_range(
            address=queried_address,
            period=TimestampOrBlockRange(range_type='blocks', from_value=0, to_value=1),
        )

    with database.conn.read_ctx() as cursor:
        tx_identifier = cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (parent_tx.tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()[0]
        rows = cursor.execute(
            'SELECT trace_id, from_address, to_address, value, gas, gas_used, source '
            'FROM evm_internal_transactions WHERE parent_tx=? ORDER BY trace_id ASC',
            (tx_identifier,),
        ).fetchall()

    # the refetched row (trace_id 1) gets the real indexer source ('etherscan'); the
    # untouched unrelated row (trace_id 2) keeps its legacy source from the initial insert
    assert rows == [
        (1, queried_address, receiver, '100', '30945', '0', InternalTxSource.ETHERSCAN.serialize_for_db()),  # noqa: E501
        (2, unrelated_sender, unrelated_receiver, '111', '123', '0', InternalTxSource.LEGACY.serialize_for_db()),  # noqa: E501
    ]


def test_query_and_save_erc20_transfers_returns_only_new_hashes(
        database: DBHandler,
        ethereum_manager: EthereumManager,
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
        database: DBHandler,
        optimism_manager: OptimismManager,
        optimism_accounts: list[ChecksumEvmAddress],
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
                attribute='get_token_transaction_data',
                wraps=indexer.get_token_transaction_data,
            ) if name == tested_indexer else patch.object(
                target=indexer,
                attribute='get_token_transaction_data',
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
        parent_tx_id = cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (tx_hash1, ChainID.OPTIMISM.serialize_for_db()),
        ).fetchone()[0]
        internal_txs = dbevmtx.get_evm_internal_transactions(
            parent_tx_hash=tx_hash1,
            blockchain=SupportedBlockchain.OPTIMISM,
            parent_tx_id=parent_tx_id,
        )
        assert len(internal_txs) == 1  # tx has two internal txs but only one involves the tracked address.  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_all_indexers_get_same_tx_results(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Test that all indexers return the same results for the same tx queries."""
    txlist_results: list[list[EvmTransaction]] = []
    txlistinteral_results: list[list[EvmInternalTransaction]] = []
    period = TimestampOrBlockRange(
        range_type='timestamps',
        from_value=Timestamp(1720000000),
        to_value=Timestamp(1735000000),
    )
    for indexer in (
        ethereum_inquirer.etherscan,
        ethereum_inquirer.blockscout,
        ethereum_inquirer.routescan,
    ):
        # get_transactions returns an iterator of lists. Consume the iterator, check that only
        # one list was returned, and append that list to the result lists.
        assert len(txlist_result := cast('list[list[EvmTransaction]]', list(indexer.get_transactions(  # noqa: E501
            chain_id=ethereum_inquirer.chain_id,
            account=ethereum_accounts[0],
            action='txlist',
            period_or_hash=period,
        )))) == 1
        txlist_results.append(txlist_result[0])

        assert len(txlistinternal_result := cast(
            'list[list[EvmInternalTransaction]]',
            list(indexer.get_transactions(
            chain_id=ethereum_inquirer.chain_id,
            account=ethereum_accounts[0],
            action='txlistinternal',
            period_or_hash=period,
            )),
        )) == 1
        txlistinteral_results.append(txlistinternal_result[0])

    # Check that there are 6 txs and 1 internal tx for the requested range and that the results
    # from each indexer all match. trace_id is excluded since it varies between indexers.
    assert len(txlist_results[0]) == 6
    assert all(x == txlist_results[0] for x in txlist_results[1:])
    assert len(txlistinteral_results[0]) == 1
    for idx, internal_tx_list in enumerate(txlistinteral_results):
        txlistinteral_results[idx] = [x._replace(trace_id=0) for x in internal_tx_list]
    assert all(x == txlistinteral_results[0] for x in txlistinteral_results[1:])


def test_wait_until_no_query_for_releases_locks_on_error(
        eth_transactions: EthereumTransactions,
) -> None:
    """Test that the address tx locks are released when the caller's body raises.

    Regression test for account removal failing while holding the locks
    (remove_single_blockchain_accounts enters the context manager via ExitStack,
    which throws the body's exception into the generator at the yield point),
    leaking the locks forever and permanently blocking all transaction querying
    for those addresses - and with it the periodic tx query task - until restart.
    """
    addresses = [make_evm_address(), make_evm_address()]

    def removal_that_fails() -> None:
        with ExitStack() as stack:
            stack.enter_context(eth_transactions.wait_until_no_query_for(addresses))
            raise ValueError('simulated error during account removal')

    with pytest.raises(ValueError, match='simulated'):
        removal_that_fails()

    for address in addresses:
        assert eth_transactions.address_tx_locks[address].locked() is False
