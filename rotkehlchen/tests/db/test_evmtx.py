from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import (
    ETH_ADDRESS1,
    ETH_ADDRESS2,
    ETH_ADDRESS3,
    MOCK_INPUT_DATA,
)
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.types import (
    BlockchainAccountData,
    ChainID,
    EvmInternalTransaction,
    EvmTransaction,
    SupportedBlockchain,
    Timestamp,
    make_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator


def test_add_get_evm_transactions(data_dir, username, sql_vm_instructions_cb):
    """Test that adding and retrieving evm transactions from the DB works fine.

    Also duplicates should be ignored and an error returned
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True)
    tx2_hash = make_evm_tx_hash(b'.h\xdd\x82\x85\x94\xeaq\xfe\n\xfc\xcf\xadwH\xc9\x0f\xfc\xd0\xf1\xad\xd4M\r$\x9b\xf7\x98\x87\xda\x93\x18')  # noqa: E501
    with data.db.user_write() as cursor:
        data.db.add_blockchain_accounts(
            write_cursor=cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            account_data=[
                BlockchainAccountData(address=ETH_ADDRESS1),
                BlockchainAccountData(address=ETH_ADDRESS2),
                BlockchainAccountData(address=ETH_ADDRESS3),
            ],
        )

    tx1 = EvmTransaction(
        tx_hash=make_evm_tx_hash(b'1'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1451606400),
        block_number=1,
        from_address=ETH_ADDRESS1,
        to_address=ETH_ADDRESS3,
        value=FVal('2000000'),
        gas=FVal('5000000'),
        gas_price=FVal('2000000000'),
        gas_used=FVal('25000000'),
        input_data=MOCK_INPUT_DATA,
        nonce=1,
    )
    tx2 = EvmTransaction(
        tx_hash=tx2_hash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1451706400),
        block_number=3,
        from_address=ETH_ADDRESS2,
        to_address=ETH_ADDRESS3,
        value=FVal('4000000'),
        gas=FVal('5000000'),
        gas_price=FVal('2000000000'),
        gas_used=FVal('25000000'),
        input_data=MOCK_INPUT_DATA,
        nonce=1,
    )
    tx3 = EvmTransaction(
        tx_hash=make_evm_tx_hash(b'3'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1452806400),
        block_number=5,
        from_address=ETH_ADDRESS3,
        to_address=ETH_ADDRESS1,
        value=FVal('1000000'),
        gas=FVal('5000000'),
        gas_price=FVal('2000000000'),
        gas_used=FVal('25000000'),
        input_data=MOCK_INPUT_DATA,
        nonce=3,
    )

    # Add and retrieve the first 2 tx. All should be fine.
    with data.db.user_write() as cursor:
        dbevmtx = DBEvmTx(data.db)
        dbevmtx.add_evm_transactions(cursor, [tx1, tx2], relevant_address=ETH_ADDRESS3)
        errors = msg_aggregator.consume_errors()
        warnings = msg_aggregator.consume_warnings()
        assert len(errors) == 0
        assert len(warnings) == 0
        filter_query = EvmTransactionsFilterQuery.make(chain_id=ChainID.ETHEREUM)
        returned_transactions = dbevmtx.get_evm_transactions(cursor, filter_query, True)
        assert returned_transactions == [tx1, tx2]

        # Add the last 2 transactions. Since tx2 already exists in the DB it should be
        # ignored (no errors shown for attempting to add already existing transaction)
        dbevmtx.add_evm_transactions(cursor, [tx2, tx3], relevant_address=ETH_ADDRESS3)
        errors = msg_aggregator.consume_errors()
        warnings = msg_aggregator.consume_warnings()
        assert len(errors) == 0
        assert len(warnings) == 0
        returned_transactions = dbevmtx.get_evm_transactions(cursor, filter_query, True)
        assert returned_transactions == [tx1, tx2, tx3]

        # Now add same transactions but with other relevant address
        dbevmtx.add_evm_transactions(cursor, [tx1, tx3], relevant_address=ETH_ADDRESS1)
        dbevmtx.add_evm_transactions(cursor, [tx2], relevant_address=ETH_ADDRESS2)

        # try transaction query by tx_hash
        result = dbevmtx.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(tx_hash=tx2_hash, chain_id=ChainID.ETHEREUM), has_premium=True)  # noqa: E501
        assert result == [tx2], 'querying transaction by hash in bytes failed'
        result = dbevmtx.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(tx_hash=b'dsadsad', chain_id=ChainID.ETHEREUM), has_premium=True)  # noqa: E501
        assert result == []

        # Now try transaction by relevant addresses
        result = dbevmtx.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(addresses=[ETH_ADDRESS1, make_ethereum_address()], chain_id=ChainID.ETHEREUM), has_premium=True)  # noqa: E501
        assert result == [tx1, tx3]


def test_query_also_internal_evm_transactions(data_dir, username, sql_vm_instructions_cb):
    """Test that querying transactions for an address also returns the parent
    transaction of any internal transactions the address was involved in.
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True)
    address_4 = make_ethereum_address()

    with data.db.user_write() as cursor:
        data.db.add_blockchain_accounts(
            cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            account_data=[
                BlockchainAccountData(address=ETH_ADDRESS1),
                BlockchainAccountData(address=ETH_ADDRESS2),
                BlockchainAccountData(address=ETH_ADDRESS3),
                BlockchainAccountData(address=address_4),
            ],
        )

    tx1 = EvmTransaction(
        tx_hash=make_evm_tx_hash(b'1'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1451606400),
        block_number=1,
        from_address=ETH_ADDRESS1,
        to_address=ETH_ADDRESS3,
        value=FVal('2000000'),
        gas=FVal('5000000'),
        gas_price=FVal('2000000000'),
        gas_used=FVal('25000000'),
        input_data=MOCK_INPUT_DATA,
        nonce=1,
    )
    tx2 = EvmTransaction(
        tx_hash=make_evm_tx_hash(b'2'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1451706400),
        block_number=3,
        from_address=ETH_ADDRESS2,
        to_address=make_ethereum_address(),
        value=FVal('4000000'),
        gas=FVal('5000000'),
        gas_price=FVal('2000000000'),
        gas_used=FVal('25000000'),
        input_data=MOCK_INPUT_DATA,
        nonce=1,
    )
    tx3 = EvmTransaction(
        tx_hash=make_evm_tx_hash(b'3'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1452806400),
        block_number=5,
        from_address=ETH_ADDRESS3,
        to_address=ETH_ADDRESS1,
        value=FVal('1000000'),
        gas=FVal('5000000'),
        gas_price=FVal('2000000000'),
        gas_used=FVal('25000000'),
        input_data=MOCK_INPUT_DATA,
        nonce=3,
    )
    tx4 = EvmTransaction(
        tx_hash=make_evm_tx_hash(b'4'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1628064001),
        block_number=6,
        from_address=ETH_ADDRESS1,
        to_address=make_ethereum_address(),
        value=FVal('1000000'),
        gas=FVal('5000000'),
        gas_price=FVal('2000000000'),
        gas_used=FVal('25000000'),
        input_data=MOCK_INPUT_DATA,
        nonce=55,
    )
    tx5 = EvmTransaction(
        tx_hash=make_evm_tx_hash(b'5'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1629064001),
        block_number=7,
        from_address=ETH_ADDRESS1,
        to_address=make_ethereum_address(),
        value=FVal('1000000'),
        gas=FVal('5000000'),
        gas_price=FVal('2000000000'),
        gas_used=FVal('25000000'),
        input_data=MOCK_INPUT_DATA,
        nonce=55,
    )
    internal_tx1 = EvmInternalTransaction(
        parent_tx_hash=make_evm_tx_hash(b'3'),
        chain_id=ChainID.ETHEREUM,
        trace_id=1,
        timestamp=Timestamp(1452806400),
        block_number=5,
        from_address=ETH_ADDRESS3,
        to_address=address_4,
        value=0,
    )
    internal_tx2 = EvmInternalTransaction(
        parent_tx_hash=make_evm_tx_hash(b'5'),
        chain_id=ChainID.ETHEREUM,
        trace_id=21,
        timestamp=Timestamp(1629064001),
        block_number=55,
        from_address=make_ethereum_address(),
        to_address=make_ethereum_address(),
        value=0,
    )
    internal_tx3 = EvmInternalTransaction(
        parent_tx_hash=make_evm_tx_hash(b'4'),
        chain_id=ChainID.ETHEREUM,
        trace_id=25,
        timestamp=Timestamp(1628064001),
        block_number=6,
        from_address=ETH_ADDRESS1,
        to_address=ETH_ADDRESS3,
        value=10,
    )
    internal_tx4 = EvmInternalTransaction(
        parent_tx_hash=make_evm_tx_hash(b'4'),
        chain_id=ChainID.ETHEREUM,
        trace_id=26,
        timestamp=Timestamp(1628064001),
        block_number=6,
        from_address=ETH_ADDRESS1,
        to_address=ETH_ADDRESS3,
        value=0,
    )

    dbevmtx = DBEvmTx(data.db)
    with data.db.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [tx1, tx3, tx4, tx5], relevant_address=ETH_ADDRESS1)  # noqa: E501
        dbevmtx.add_evm_transactions(cursor, [tx2], relevant_address=ETH_ADDRESS2)
        dbevmtx.add_evm_transactions(cursor, [tx1, tx3], relevant_address=ETH_ADDRESS3)
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx2, internal_tx3, internal_tx4], relevant_address=ETH_ADDRESS1)  # noqa: E501
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx1, internal_tx4], relevant_address=ETH_ADDRESS3)  # noqa: E501
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx1], relevant_address=address_4)  # noqa: E501
        errors = msg_aggregator.consume_errors()
        warnings = msg_aggregator.consume_warnings()
        assert len(errors) == 0
        assert len(warnings) == 0

        result, total_filter_count = dbevmtx.get_evm_transactions_and_limit_info(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(addresses=[ETH_ADDRESS3], chain_id=ChainID.ETHEREUM),  # noqa: E501
            has_premium=True,
        )
        assert {x.tx_hash for x in result} == {b'1', b'3', b'4'}
        assert total_filter_count == 3

        # Now try transaction query by relevant addresses and see we get more due to the
        # internal tx mappings
        result, total_filter_count = dbevmtx.get_evm_transactions_and_limit_info(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(addresses=[ETH_ADDRESS1], chain_id=ChainID.ETHEREUM),  # noqa: E501
            has_premium=True,
        )
        assert result == [tx1, tx3, tx4, tx5]
        assert total_filter_count == 4

        result = dbevmtx.get_evm_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(addresses=[address_4], chain_id=ChainID.ETHEREUM),  # noqa: E501
            has_premium=True,
        )
        assert result == [tx3]

        result = dbevmtx.get_evm_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(addresses=[ETH_ADDRESS3], chain_id=ChainID.ETHEREUM),  # noqa: E501
            has_premium=True,
        )
        assert result == [tx1, tx3, tx4]
