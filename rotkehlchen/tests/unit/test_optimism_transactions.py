from contextlib import ExitStack
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.types import EvmIndexer, NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.chain.optimism.constants import OP_BEDROCK_BLOCK, OP_BEDROCK_UPGRADE
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.optimism import OPTIMISM_MAINNET_NODE
from rotkehlchen.types import (
    ChainID,
    EvmInternalTransaction,
    SupportedBlockchain,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2WithL1FeesTransaction
    from rotkehlchen.chain.optimism.transactions import OptimismTransactions
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xd6Ade875eEC93a7aAb7EfB7DBF13d1457443f95B']])
@pytest.mark.parametrize('optimism_manager_connect_at_start', [(OPTIMISM_MAINNET_NODE,)])
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
        transactions = dbevmtx.get_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(tx_hash=tx_hash),
        )
        assert_tx_okay(transactions, should_have_l1=True)

    # Now delete the l1 fee from the DB and see things don't break
    with optimism_transactions.database.user_write() as write_cursor:
        write_cursor.execute('DELETE FROM optimism_transactions WHERE tx_id=2')

    with optimism_transactions.database.conn.read_ctx() as cursor:
        transactions = dbevmtx.get_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(tx_hash=tx_hash),
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
        optimism_transactions: OptimismTransactions,
        optimism_accounts: list[ChecksumEvmAddress],
        optimism_manager_connect_at_start: Sequence[WeightedNode],
):
    """Test that if the L1 fee is initially missing it gets queried from either
    the mainnet node or from an indexer. The RPC and etherscan responses are mocked since they
    no longer return an L1 fee for this tx/chain, but the other indexers are not mocked.
    """
    original_get_transaction_receipt = optimism_transactions.evm_inquirer.get_transaction_receipt
    l1_fee_value = 97960903705252
    for fallback_to_indexers, indexer_patches in (
        (False, []),  # Use the RPC
        (True, [  # Use etherscan. Mock response since etherscan no longer supports Optimism in the free tier  # noqa: E501
            patch.object(optimism_transactions.evm_inquirer.etherscan, 'get_l1_fee', return_value=l1_fee_value),  # noqa: E501
        ]),
        (True, [  # Fall back to blockscout
            patch.object(optimism_transactions.evm_inquirer.etherscan, 'get_l1_fee', side_effect=RemoteError('BOOM')),  # noqa: E501
        ]),
        (True, [  # Fall back to routescan
            patch.object(optimism_transactions.evm_inquirer.etherscan, 'get_l1_fee', side_effect=RemoteError('BOOM')),  # noqa: E501
            patch.object(optimism_transactions.evm_inquirer.blockscout, 'get_l1_fee', side_effect=RemoteError('BOOM')),  # noqa: E501
        ]),
    ):

        def mock_get_transaction_receipt(fallback=fallback_to_indexers, **kwargs: Any) -> dict[str, Any]:  # noqa: E501
            """Mock the l1Fee in the rpc response."""
            tx_receipt = original_get_transaction_receipt(**kwargs)
            tx_receipt['l1Fee'] = None if fallback else l1_fee_value
            return tx_receipt

        with ExitStack() as stack:
            get_tx_receipt_mock = stack.enter_context(patch.object(
                optimism_transactions.evm_inquirer,
                'get_transaction_receipt',
                side_effect=mock_get_transaction_receipt,
            ))
            get_l1_fees_mock = stack.enter_context(patch.object(
                optimism_transactions.evm_inquirer,
                'maybe_get_l1_fees',
                wraps=optimism_transactions.evm_inquirer.maybe_get_l1_fees,
            ))
            stack.enter_context(patch.object(
                optimism_transactions.evm_inquirer,
                'default_call_order',
                new=lambda: list(optimism_manager_connect_at_start),
            ))  # patch default call order to keep it deterministic for the vcr

            for indexer_patch in indexer_patches:
                stack.enter_context(indexer_patch)

            tx, _ = optimism_transactions.evm_inquirer.get_transaction_by_hash(
                tx_hash=deserialize_evm_tx_hash('0x92ae5e1c4b4a2d5e2af9c4abc415a9dc0b826ba1fa158c57219fc1b6e852a061'),
            )

        assert cast('L2WithL1FeesTransaction', tx).l1_fee == l1_fee_value
        assert get_tx_receipt_mock.call_count == 1
        assert get_tx_receipt_mock.call_args_list[0].kwargs['call_order'][0].node_info.name == 'mainnet'  # noqa: E501
        assert get_l1_fees_mock.call_count == (1 if fallback_to_indexers else 0)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xd6Ade875eEC93a7aAb7EfB7DBF13d1457443f95B']])
def test_l1_fee_fetched_during_indexer_tx_query(
        optimism_transactions: OptimismTransactions,
        optimism_accounts: list[ChecksumEvmAddress],
):
    """Test that L1 fees are fetched via indexer's get_l1_fee during transaction queries.

    This tests the fix where get_transactions() in etherscan_like.py now calls get_l1_fee()
    for L2 chains when using non-Etherscan indexers (Blockscout, Routescan) since these
    indexers don't include L1 fee in their txlist response.
    """
    address = optimism_accounts[0]
    expected_l1_fee = 115752642875381
    tx_hash = deserialize_evm_tx_hash('0x6eb136db4d36cf695f4026da16f602ed4a2583b2420dbbcbd4f436943190b665')  # noqa: E501

    for tx_batch in optimism_transactions.evm_inquirer.get_transactions(
        account=address,
        action='txlist',
        period_or_hash=TimestampOrBlockRange(
            range_type='blocks',
            from_value=106757395,
            to_value=106757395,
        ),
    ):
        for tx in tx_batch:
            if tx.tx_hash == tx_hash:
                assert cast('L2WithL1FeesTransaction', tx).l1_fee == expected_l1_fee
                return

    raise AssertionError('Expected transaction not found')


@pytest.mark.parametrize('partial_pre_coverage', [False, True])
@pytest.mark.parametrize('post_succeeds', [False, True])
def test_pre_bedrock_failure_does_not_block_post_coverage(
        optimism_transactions: OptimismTransactions,
        partial_pre_coverage: bool,
        post_succeeds: bool,
) -> None:
    """A failed pre-Bedrock query cannot prevent or falsely complete the newer query."""
    address = make_evm_address()
    start_ts = Timestamp(OP_BEDROCK_UPGRADE - 100)
    end_ts = Timestamp(OP_BEDROCK_UPGRADE + 100)
    inquirer = optimism_transactions.evm_inquirer
    ranges = DBQueryRanges(optimism_transactions.database)
    prefix = inquirer.blockchain.to_range_prefix('internaltxs')
    location_string = f'{prefix}_{address}'
    if partial_pre_coverage:
        with optimism_transactions.database.conn.write_ctx() as cursor:
            ranges.update_used_query_range(
                write_cursor=cursor,
                location_string=location_string,
                queried_ranges=[(start_ts, Timestamp(start_ts + 10))],
            )

    with (
        patch.object(inquirer, '_resolve_timestamp_range', side_effect=[
            (OP_BEDROCK_BLOCK - 10, OP_BEDROCK_BLOCK - 1, frozenset()),
            (OP_BEDROCK_BLOCK, OP_BEDROCK_BLOCK + 10, frozenset()),
        ]) as resolve_range,
        patch.object(inquirer, 'get_transactions_with_source', side_effect=[
            RemoteError('pre-Bedrock indexers unavailable'),
            (iter([[]]), EvmIndexer.BLOCKSCOUT) if post_succeeds else RemoteError(
                'post-Bedrock indexers unavailable',
            ),
        ]),
        patch.object(
            optimism_transactions,
            '_query_and_save_internal_transactions_for_range',
            wraps=optimism_transactions._query_and_save_internal_transactions_for_range,
        ) as query_range,
    ):
        result = optimism_transactions._get_internal_transactions_for_ranges(
            address=address,
            start_ts=start_ts,
            end_ts=end_ts,
        )

    assert result is False
    assert [call.kwargs['update_ranges'] for call in query_range.call_args_list] == [
        True,
        not partial_pre_coverage,
    ]
    assert [call.kwargs for call in resolve_range.call_args_list] == [
        {
            'from_ts': Timestamp(start_ts + 11) if partial_pre_coverage else start_ts,
            'to_ts': Timestamp(OP_BEDROCK_UPGRADE - 1),
        },
        {'from_ts': OP_BEDROCK_UPGRADE, 'to_ts': end_ts},
    ]
    with optimism_transactions.database.conn.read_ctx() as cursor:
        assert optimism_transactions.database.get_used_query_range(
            cursor=cursor,
            name=location_string,
        ) == (
            (OP_BEDROCK_UPGRADE, end_ts) if post_succeeds else
            (start_ts, Timestamp(start_ts + 10)) if partial_pre_coverage else
            None
        )

    if post_succeeds:
        with (
            patch.object(inquirer, '_resolve_timestamp_range', return_value=(
                OP_BEDROCK_BLOCK - 10, OP_BEDROCK_BLOCK - 1, frozenset(),
            )) as resolve_retry,
            patch.object(inquirer, 'get_transactions_with_source', return_value=(
                iter([[]]), EvmIndexer.ROUTESCAN,
            ), side_effect=RemoteError('pre-Bedrock indexers still unavailable') if partial_pre_coverage else None,  # noqa: E501
            ) as query_retry,
        ):
            assert optimism_transactions._get_internal_transactions_for_ranges(
                address=address,
                start_ts=start_ts,
                end_ts=end_ts,
            ) is (not partial_pre_coverage)

        resolve_retry.assert_called_once()
        query_retry.assert_called_once()
        with optimism_transactions.database.conn.read_ctx() as cursor:
            assert optimism_transactions.database.get_used_query_range(
                cursor=cursor,
                name=location_string,
            ) == (
                (OP_BEDROCK_UPGRADE, end_ts) if partial_pre_coverage else (start_ts, end_ts)
            )


def test_post_bedrock_replacement_keeps_pre_coverage_if_probe_fails(
        optimism_transactions: OptimismTransactions,
) -> None:
    """Do not discard older progress when recent newer coverage cannot be established."""
    address = make_evm_address()
    start_ts = Timestamp(OP_BEDROCK_UPGRADE - 100)
    end_ts = ts_now()
    saved_range = (start_ts, Timestamp(start_ts + 10))
    inquirer = optimism_transactions.evm_inquirer
    location_string = f'{inquirer.blockchain.to_range_prefix("internaltxs")}_{address}'
    with optimism_transactions.database.conn.write_ctx() as cursor:
        DBQueryRanges(optimism_transactions.database).update_used_query_range(
            write_cursor=cursor,
            location_string=location_string,
            queried_ranges=[saved_range],
        )

    with (
        patch.object(inquirer, '_resolve_timestamp_range', side_effect=[
            (OP_BEDROCK_BLOCK - 10, OP_BEDROCK_BLOCK - 1, frozenset()),
            (OP_BEDROCK_BLOCK, OP_BEDROCK_BLOCK + 10, frozenset()),
        ]),
        patch.object(inquirer, 'get_transactions_with_source', side_effect=[
            RemoteError('pre-Bedrock indexers unavailable'),
            (iter([[]]), EvmIndexer.BLOCKSCOUT),
        ]),
        patch.object(inquirer, 'get_blocknumber_by_time', side_effect=RemoteError(
            'could not determine indexed end',
        )) as end_probe,
    ):
        assert optimism_transactions._get_internal_transactions_for_ranges(
            address=address,
            start_ts=start_ts,
            end_ts=end_ts,
        ) is False

    end_probe.assert_called_once_with(ts=end_ts, closest='before')
    with optimism_transactions.database.conn.read_ctx() as cursor:
        assert optimism_transactions.database.get_used_query_range(cursor, location_string) == saved_range  # noqa: E501


@pytest.mark.parametrize('saved_range', [
    None,
    (Timestamp(OP_BEDROCK_UPGRADE - 100), Timestamp(OP_BEDROCK_UPGRADE - 90)),
    (OP_BEDROCK_UPGRADE, Timestamp(OP_BEDROCK_UPGRADE + 5)),
])
def test_pre_bedrock_success_is_kept_when_post_fails(
        optimism_transactions: OptimismTransactions,
        saved_range: tuple[Timestamp, Timestamp] | None,
) -> None:
    """Do not download the successful older half again after a newer-half failure."""
    address = make_evm_address()
    start_ts = Timestamp(OP_BEDROCK_UPGRADE - 100)
    end_ts = Timestamp(OP_BEDROCK_UPGRADE + 100)
    inquirer = optimism_transactions.evm_inquirer
    location_string = f'{inquirer.blockchain.to_range_prefix("internaltxs")}_{address}'
    if saved_range is not None:
        with optimism_transactions.database.conn.write_ctx() as cursor:
            DBQueryRanges(optimism_transactions.database).update_used_query_range(
                write_cursor=cursor,
                location_string=location_string,
                queried_ranges=[saved_range],
            )

    with (
        patch.object(inquirer, '_resolve_timestamp_range', side_effect=[
            (OP_BEDROCK_BLOCK - 10, OP_BEDROCK_BLOCK - 1, frozenset()),
            (OP_BEDROCK_BLOCK, OP_BEDROCK_BLOCK + 10, frozenset()),
        ]),
        patch.object(inquirer, 'get_transactions_with_source', side_effect=[
            (iter([[]]), EvmIndexer.ROUTESCAN),
            RemoteError('post-Bedrock indexers unavailable'),
        ]),
    ):
        assert optimism_transactions._get_internal_transactions_for_ranges(
            address=address,
            start_ts=start_ts,
            end_ts=end_ts,
        ) is False

    with optimism_transactions.database.conn.read_ctx() as cursor:
        assert optimism_transactions.database.get_used_query_range(
            cursor=cursor,
            name=location_string,
        ) == (start_ts, max(
            Timestamp(OP_BEDROCK_UPGRADE - 1),
            saved_range[1] if saved_range is not None else Timestamp(0),
        ))

    with (
        patch.object(inquirer, '_resolve_timestamp_range', return_value=(
            OP_BEDROCK_BLOCK, OP_BEDROCK_BLOCK + 10, frozenset(),
        )) as resolve_retry,
        patch.object(inquirer, 'get_transactions_with_source', return_value=(
            iter([[]]), EvmIndexer.BLOCKSCOUT,
        )) as query_retry,
    ):
        assert optimism_transactions._get_internal_transactions_for_ranges(
            address=address,
            start_ts=start_ts,
            end_ts=end_ts,
        ) is True

    resolve_retry.assert_called_once()
    query_retry.assert_called_once()
    with optimism_transactions.database.conn.read_ctx() as cursor:
        assert optimism_transactions.database.get_used_query_range(
            cursor=cursor,
            name=location_string,
        ) == (start_ts, end_ts)


def _interrupted_internal_batches(
        internal_tx: EvmInternalTransaction,
) -> Iterator[list[EvmInternalTransaction]]:
    yield [internal_tx]
    raise RemoteError('interrupted internal transaction pagination')


def test_pre_bedrock_interruption_keeps_batch_progress(
        optimism_transactions: OptimismTransactions,
) -> None:
    """Keep a fetched older batch when the newer half also fails."""
    address = make_evm_address()
    start_ts = Timestamp(OP_BEDROCK_UPGRADE - 100)
    end_ts = Timestamp(OP_BEDROCK_UPGRADE + 100)
    batch_ts = Timestamp(OP_BEDROCK_UPGRADE - 50)
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=make_evm_tx_hash(),
        chain_id=ChainID.OPTIMISM,
        trace_id=1,
        from_address=address,
        to_address=make_evm_address(),
        value=1,
        gas=1,
        gas_used=1,
    )
    inquirer = optimism_transactions.evm_inquirer
    location_string = f'{inquirer.blockchain.to_range_prefix("internaltxs")}_{address}'

    with (
        patch.object(inquirer, '_resolve_timestamp_range', side_effect=[
            (OP_BEDROCK_BLOCK - 10, OP_BEDROCK_BLOCK - 1, frozenset()),
            (OP_BEDROCK_BLOCK, OP_BEDROCK_BLOCK + 10, frozenset()),
        ]),
        patch.object(inquirer, 'get_transactions_with_source', side_effect=[
            (_interrupted_internal_batches(internal_tx), EvmIndexer.ROUTESCAN),
            RemoteError('post-Bedrock indexers unavailable'),
        ]) as query_indexers,
        patch.object(optimism_transactions, '_process_internal_transactions_batch', return_value=[
            (internal_tx, batch_ts),
        ]),
        patch.object(optimism_transactions.dbevmtx, 'add_evm_internal_transactions') as save_batch,
        patch.object(
            optimism_transactions,
            '_query_and_save_internal_transactions_for_range',
            wraps=optimism_transactions._query_and_save_internal_transactions_for_range,
        ) as query_range,
    ):
        assert optimism_transactions._get_internal_transactions_for_ranges(
            address=address,
            start_ts=start_ts,
            end_ts=end_ts,
        ) is False

    assert query_indexers.call_count == 2
    save_batch.assert_called_once()
    with optimism_transactions.database.conn.read_ctx() as cursor:
        assert optimism_transactions.database.get_used_query_range(
            cursor=cursor,
            name=location_string,
        ) == (start_ts, batch_ts)
    assert [call.kwargs['update_ranges'] for call in query_range.call_args_list] == [True, False]


@pytest.mark.parametrize('pre_already_covered', [False, True])
def test_successful_bedrock_split_marks_combined_range_once(
        optimism_transactions: OptimismTransactions,
        pre_already_covered: bool,
) -> None:
    """A successful split makes one final mark and one recent-end probe."""
    address = make_evm_address()
    start_ts = Timestamp(OP_BEDROCK_UPGRADE - 100)
    end_ts = ts_now()
    inquirer = optimism_transactions.evm_inquirer
    location_string = f'{inquirer.blockchain.to_range_prefix("internaltxs")}_{address}'
    if pre_already_covered:
        with optimism_transactions.database.conn.write_ctx() as cursor:
            DBQueryRanges(optimism_transactions.database).update_used_query_range(
                write_cursor=cursor,
                location_string=location_string,
                queried_ranges=[(start_ts, Timestamp(OP_BEDROCK_UPGRADE + 5))],
            )

    resolved_ranges: list[tuple[int, int, frozenset[EvmIndexer]]] = [
        (OP_BEDROCK_BLOCK, OP_BEDROCK_BLOCK + 10, frozenset()),
    ]
    indexer_results: list[tuple[Iterator[list[EvmInternalTransaction]], EvmIndexer]] = [
        (iter([[]]), EvmIndexer.BLOCKSCOUT),
    ]
    if not pre_already_covered:
        resolved_ranges.insert(0, (OP_BEDROCK_BLOCK - 10, OP_BEDROCK_BLOCK - 1, frozenset()))
        indexer_results.insert(0, (iter([[]]), EvmIndexer.ROUTESCAN))

    with (
        patch.object(inquirer, '_resolve_timestamp_range', side_effect=resolved_ranges),
        patch.object(inquirer, 'get_transactions_with_source', side_effect=indexer_results),
        patch.object(
            inquirer, 'get_blocknumber_by_time', return_value=OP_BEDROCK_BLOCK + 10,
        ) as end_block_probe,
        patch.object(inquirer, 'get_block_timestamp', return_value=end_ts) as end_timestamp_probe,
        patch.object(
            optimism_transactions,
            '_mark_range_as_queried',
            wraps=optimism_transactions._mark_range_as_queried,
        ) as mark_range,
    ):
        assert optimism_transactions._get_internal_transactions_for_ranges(
            address=address,
            start_ts=start_ts,
            end_ts=end_ts,
        ) is True

    assert mark_range.call_count == 1
    assert mark_range.call_args.kwargs == {
        'location_string': location_string,
        'start_ts': start_ts,
        'end_ts': end_ts,
        'replace_existing': False,
    }
    end_block_probe.assert_called_once_with(ts=end_ts, closest='before')
    assert end_timestamp_probe.call_count == 1
    with optimism_transactions.database.conn.read_ctx() as cursor:
        assert optimism_transactions.database.get_used_query_range(
            cursor=cursor,
            name=location_string,
        ) == (start_ts, end_ts)


@pytest.mark.parametrize('saved_range_start', [
    None,
    OP_BEDROCK_UPGRADE,
    Timestamp(OP_BEDROCK_UPGRADE - 100),
])
def test_post_bedrock_interruption_keeps_batch_progress(
        optimism_transactions: OptimismTransactions,
        saved_range_start: Timestamp | None,
) -> None:
    """A failed page after a saved batch leaves the post-Bedrock range resumable."""
    address = make_evm_address()
    start_ts = Timestamp(OP_BEDROCK_UPGRADE - 100)
    end_ts = Timestamp(OP_BEDROCK_UPGRADE + 100)
    batch_ts = Timestamp(OP_BEDROCK_UPGRADE + 10)
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=make_evm_tx_hash(),
        chain_id=ChainID.OPTIMISM,
        trace_id=1,
        from_address=address,
        to_address=make_evm_address(),
        value=1,
        gas=1,
        gas_used=1,
    )
    inquirer = optimism_transactions.evm_inquirer
    location_string = f'{inquirer.blockchain.to_range_prefix("internaltxs")}_{address}'
    if saved_range_start is not None:
        with optimism_transactions.database.conn.write_ctx() as cursor:
            DBQueryRanges(optimism_transactions.database).update_used_query_range(
                write_cursor=cursor,
                location_string=location_string,
                queried_ranges=[(saved_range_start, Timestamp(OP_BEDROCK_UPGRADE + 5))],
            )

    resolved_ranges: list[tuple[int, int, frozenset[EvmIndexer]]] = [
        (OP_BEDROCK_BLOCK, OP_BEDROCK_BLOCK + 10, frozenset()),
    ]
    indexer_results: list[RemoteError | tuple[Iterator[list[EvmInternalTransaction]], EvmIndexer]] = [  # noqa: E501
        (_interrupted_internal_batches(internal_tx), EvmIndexer.BLOCKSCOUT),
    ]
    if saved_range_start != start_ts:  # older half is not already covered
        resolved_ranges.insert(0, (OP_BEDROCK_BLOCK - 10, OP_BEDROCK_BLOCK - 1, frozenset()))
        indexer_results.insert(0, RemoteError('pre-Bedrock indexers unavailable'))

    with (
        patch.object(inquirer, '_resolve_timestamp_range', side_effect=resolved_ranges),
        patch.object(inquirer, 'get_transactions_with_source', side_effect=indexer_results),
        patch.object(optimism_transactions, '_process_internal_transactions_batch', return_value=[
            (internal_tx, batch_ts),
        ]),
        patch.object(optimism_transactions.dbevmtx, 'add_evm_internal_transactions'),
    ):
        assert optimism_transactions._get_internal_transactions_for_ranges(
            address=address,
            start_ts=start_ts,
            end_ts=end_ts,
        ) is False

    with optimism_transactions.database.conn.read_ctx() as cursor:
        assert optimism_transactions.database.get_used_query_range(
            cursor=cursor,
            name=location_string,
        ) == (
            saved_range_start if saved_range_start is not None else OP_BEDROCK_UPGRADE,
            batch_ts,
        )
