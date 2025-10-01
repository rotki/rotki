from typing import TYPE_CHECKING

from rotkehlchen.chain.solana.types import SolanaInstruction, SolanaTransaction
from rotkehlchen.db.constants import TX_DECODED
from rotkehlchen.db.filtering import (
    SolanaTransactionsFilterQuery,
    SolanaTransactionsNotDecodedFilterQuery,
)
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.tests.utils.factories import make_solana_address, make_solana_signature
from rotkehlchen.types import SolanaAddress, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _create_test_solana_transactions() -> tuple[list[SolanaTransaction], SolanaAddress, SolanaAddress, SolanaAddress]:  # noqa: E501
    """Create test Solana transactions with different properties for testing."""
    sol_address1 = make_solana_address()
    sol_address2 = make_solana_address()
    sol_address3 = make_solana_address()
    program_address = make_solana_address()

    txs = []
    for idx, ts in enumerate([Timestamp(1451606400), Timestamp(1451706400), Timestamp(1452806400)], start=1):  # noqa: E501
        txs.append(SolanaTransaction(
            signature=make_solana_signature(),
            slot=10000 + idx,
            block_time=ts,
            fee=5000 + idx,
            success=idx != 3,
            account_keys=[sol_address1, sol_address2, program_address],
            instructions=[
                SolanaInstruction(
                    execution_index=0,
                    parent_execution_index=None,
                    program_id=program_address,
                    data=b'test_data' + bytes(idx),
                    accounts=[sol_address1, sol_address2],
                ),
            ],
    ))

    return txs, sol_address1, sol_address2, sol_address3


def test_add_get_solana_transactions(database: 'DBHandler') -> None:
    txs, sol_address1, sol_address2, _ = _create_test_solana_transactions()
    with database.conn.write_ctx() as write_cursor:
        # add and retrieve the first 2 tx. All should be fine.
        dbsolanatx = DBSolanaTx(database)
        dbsolanatx.add_transactions(
            write_cursor=write_cursor,
            solana_transactions=txs[:2],
            relevant_address=sol_address1,
        )

    with database.conn.read_ctx() as cursor:
        # Test basic retrieval
        returned_transactions = dbsolanatx.get_transactions(
            cursor=cursor,
            filter_=(filter_query := SolanaTransactionsFilterQuery.make()),
        )
        assert len(returned_transactions) == 2
        assert returned_transactions[0].signature == txs[0].signature
        assert returned_transactions[1].signature == txs[1].signature

        # Verify account keys and instructions are correctly stored and retrieved
        assert returned_transactions[0].account_keys == [sol_address1, sol_address2, txs[0].instructions[0].program_id]  # noqa: E501
        assert returned_transactions[0].instructions[0].program_id == txs[0].instructions[0].program_id  # noqa: E501
        assert returned_transactions[0].instructions[0].accounts == [sol_address1, sol_address2]

    # Add the third transaction and see that tx2 is ignored since it already exists.
    with database.conn.write_ctx() as write_cursor:
        dbsolanatx.add_transactions(
            write_cursor=write_cursor,
            solana_transactions=txs[1:],
            relevant_address=sol_address2,
        )

    with database.conn.read_ctx() as cursor:
        returned_transactions = dbsolanatx.get_transactions(
            cursor=cursor,
            filter_=filter_query,
        )
        assert len(returned_transactions) == 3


def test_solana_transactions_filtering(database: 'DBHandler') -> None:
    """Test filtering solana transactions by various criteria"""
    txs, sol_address1, _, _ = _create_test_solana_transactions()
    with database.conn.write_ctx() as write_cursor:
        dbsolanatx = DBSolanaTx(database)
        dbsolanatx.add_transactions(
            write_cursor=write_cursor,
            solana_transactions=txs,
            relevant_address=sol_address1,
        )

    expected_sigs = [tx.signature for tx in txs]
    with database.conn.read_ctx() as cursor:
        # Test filtering by timestamp range
        result = dbsolanatx.get_transactions(
            cursor=cursor,
            filter_=SolanaTransactionsFilterQuery.make(
                from_ts=Timestamp(1451606400),
                to_ts=Timestamp(1451706400),
            ),
        )
        assert [tx.signature for tx in result] == expected_sigs[:2]

        # Test filtering by success status - only successful transactions
        filter_query = SolanaTransactionsFilterQuery.make(success=True)
        result = dbsolanatx.get_transactions(cursor, filter_query)
        assert all(tx.success for tx in result)
        assert [tx.signature for tx in result] == expected_sigs[:2]

        # Test filtering by success status - only failed transactions
        filter_query = SolanaTransactionsFilterQuery.make(success=False)
        assert len(result := dbsolanatx.get_transactions(cursor, filter_query)) == 1
        assert not result[0].success
        assert result[0].signature == txs[2].signature

        # Test filtering with limit and ordering
        result = dbsolanatx.get_transactions(
            cursor=cursor,
            filter_=SolanaTransactionsFilterQuery.make(
                offset=0,
                limit=2,
                order_by_rules=[('block_time', False)],  # Descending order
            ),
        )
        # Should get the two most recent transactions in descending order
        assert [tx.signature for tx in result] == expected_sigs[-2:][::-1]

        # Test combining multiple filters
        assert len(result := dbsolanatx.get_transactions(
            cursor=cursor,
            filter_=SolanaTransactionsFilterQuery.make(
                from_ts=Timestamp(1451606400),
                to_ts=Timestamp(1452806400),
                success=True,
            ),
        )) == 2
        assert all(tx.success for tx in result)
        assert [tx.signature for tx in result] == expected_sigs[:2]

        # test transaction query by signature
        assert len(result := dbsolanatx.get_transactions(
            cursor=cursor,
            filter_=SolanaTransactionsFilterQuery.make(signature=txs[1].signature),
        )) == 1
        assert result[0].signature == txs[1].signature

        # test query by non-existent signature
        assert len(dbsolanatx.get_transactions(
            cursor=cursor,
            filter_=SolanaTransactionsFilterQuery.make(signature=make_solana_signature()),
        )) == 0


def test_solana_instruction_execution_order(database: 'DBHandler') -> None:
    """Test that nested instructions are returned in correct execution order"""
    with database.conn.write_ctx() as write_cursor:
        dbsolanatx = DBSolanaTx(database)
        dbsolanatx.add_transactions(
            write_cursor=write_cursor,
            solana_transactions=[SolanaTransaction(
                signature=make_solana_signature(),
                slot=10000,
                block_time=Timestamp(1453906400),
                fee=5000,
                success=True,
                account_keys=[
                    (sol_address1 := make_solana_address()),
                    (sol_address2 := make_solana_address()),
                    (sol_address3 := make_solana_address()),
                    (program_address := make_solana_address()),
                    (program_address2 := make_solana_address()),
                ],
                instructions=[SolanaInstruction(  # Top-level instruction 0
                    execution_index=0,
                    parent_execution_index=None,
                    program_id=program_address,
                    data=b'top_level_0',
                    accounts=[sol_address1, sol_address2],
                ), SolanaInstruction(  # Top-level instruction 1
                        execution_index=1,
                        parent_execution_index=None,
                        program_id=program_address,
                        data=b'top_level_1',
                        accounts=[sol_address2, sol_address3],
                ), SolanaInstruction(  # Inner instructions for instruction 1
                    execution_index=0,
                    parent_execution_index=1,
                    program_id=program_address2,
                    data=b'inner_1_0',
                    accounts=[sol_address1],
                ), SolanaInstruction(
                    execution_index=1,
                    parent_execution_index=1,
                    program_id=program_address2,
                    data=b'inner_1_1',
                    accounts=[sol_address3],
                ), SolanaInstruction(  # Top-level instruction 2
                    execution_index=2,
                    parent_execution_index=None,
                    program_id=program_address,
                    data=b'top_level_2',
                    accounts=[sol_address1, sol_address3],
                ), SolanaInstruction(  # Inner instructions for instruction 2
                    execution_index=0,
                    parent_execution_index=2,
                    program_id=program_address2,
                    data=b'inner_2_0',
                    accounts=[sol_address2],
                ), SolanaInstruction(
                    execution_index=1,
                    parent_execution_index=2,
                    program_id=program_address2,
                    data=b'inner_2_1',
                    accounts=[sol_address1, sol_address2],
                )],
            )],  # only add the nested instructions transaction
            relevant_address=sol_address1,
        )

    with database.conn.read_ctx() as cursor:
        assert len(result := dbsolanatx.get_transactions(
            cursor=cursor,
            filter_=SolanaTransactionsFilterQuery.make(),
        )) == 1
        assert len(instructions := result[0].instructions) == 7  # 3 top-level + 2 inner for instruction 1 + 2 inner for instruction 2  # noqa: E501

        # Verify the correct execution order:
        # 1. Top-level instruction 0 (execution_index=0, parent_execution_index=None)
        # 2. Top-level instruction 1 (execution_index=1, parent_execution_index=None)
        # 3. Inner instruction 0 of instruction 1 (execution_index=0, parent_execution_index=1)
        # 4. Inner instruction 1 of instruction 1 (execution_index=1, parent_execution_index=1)
        # 5. Top-level instruction 2 (execution_index=2, parent_execution_index=None)
        # 6. Inner instruction 0 of instruction 2 (execution_index=0, parent_execution_index=2)
        # 7. Inner instruction 1 of instruction 2 (execution_index=1, parent_execution_index=2)
        expected_order = [
            (0, None, b'top_level_0'),
            (1, None, b'top_level_1'),
            (0, 1, b'inner_1_0'),
            (1, 1, b'inner_1_1'),
            (2, None, b'top_level_2'),
            (0, 2, b'inner_2_0'),
            (1, 2, b'inner_2_1'),
        ]
        for i, (expected_exec_idx, expected_parent_idx, expected_data) in enumerate(expected_order):  # noqa: E501
            assert instructions[i].execution_index == expected_exec_idx
            assert instructions[i].parent_execution_index == expected_parent_idx
            assert instructions[i].data == expected_data


def test_query_txs_not_decoded(database: 'DBHandler') -> None:
    txs, sol_address1, _, _ = _create_test_solana_transactions()
    dbsolanatx = DBSolanaTx(database)
    with database.conn.write_ctx() as write_cursor:
        dbsolanatx.add_transactions(
            write_cursor=write_cursor,
            solana_transactions=txs,
            relevant_address=sol_address1,
        )

    # All txs are not decoded
    undecoded_sigs = dbsolanatx.get_transaction_hashes_not_decoded(
        filter_query=(not_decoded_filter := SolanaTransactionsNotDecodedFilterQuery.make()),
    )
    undecoded_sig_count = dbsolanatx.count_hashes_not_decoded(filter_query=not_decoded_filter)
    assert len(undecoded_sigs) == undecoded_sig_count == 3
    assert all(x.signature in undecoded_sigs for x in txs)

    # Mark one tx as decoded
    with database.conn.write_ctx() as write_cursor:
        tx0 = dbsolanatx.get_transactions(
            cursor=write_cursor,
            filter_=SolanaTransactionsFilterQuery.make(signature=undecoded_sigs[0]),
        )[0]
        write_cursor.execute(
            'INSERT OR IGNORE INTO solana_tx_mappings(tx_id, value) VALUES(?, ?)',
            (tx0.db_id, TX_DECODED),
        )

    # Only the remaining two txs are not decoded
    undecoded_sigs = dbsolanatx.get_transaction_hashes_not_decoded(filter_query=not_decoded_filter)
    undecoded_sig_count = dbsolanatx.count_hashes_not_decoded(filter_query=not_decoded_filter)
    assert len(undecoded_sigs) == undecoded_sig_count == 2
    assert all(x.signature in undecoded_sigs for x in [tx for tx in txs if tx.signature != tx0.signature])  # noqa: E501
