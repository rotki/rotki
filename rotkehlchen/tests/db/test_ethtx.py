from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
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
    EvmInternalTransaction,
    EvmTransaction,
    SupportedBlockchain,
    Timestamp,
    make_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator


def test_add_get_ethereum_transactions(data_dir, username, sql_vm_instructions_cb):
    """Test that adding and retrieving ethereum transactions from the DB works fine.

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
        dbethtx = DBEthTx(data.db)
        dbethtx.add_ethereum_transactions(cursor, [tx1, tx2], relevant_address=ETH_ADDRESS3)
        errors = msg_aggregator.consume_errors()
        warnings = msg_aggregator.consume_warnings()
        assert len(errors) == 0
        assert len(warnings) == 0
        filter_query = ETHTransactionsFilterQuery.make()
        returned_transactions = dbethtx.get_ethereum_transactions(cursor, filter_query, True)
        assert returned_transactions == [tx1, tx2]

        # Add the last 2 transactions. Since tx2 already exists in the DB it should be
        # ignored (no errors shown for attempting to add already existing transaction)
        dbethtx.add_ethereum_transactions(cursor, [tx2, tx3], relevant_address=ETH_ADDRESS3)
        errors = msg_aggregator.consume_errors()
        warnings = msg_aggregator.consume_warnings()
        assert len(errors) == 0
        assert len(warnings) == 0
        returned_transactions = dbethtx.get_ethereum_transactions(cursor, filter_query, True)
        assert returned_transactions == [tx1, tx2, tx3]

        # Now add same transactions but with other relevant address
        dbethtx.add_ethereum_transactions(cursor, [tx1, tx3], relevant_address=ETH_ADDRESS1)
        dbethtx.add_ethereum_transactions(cursor, [tx2], relevant_address=ETH_ADDRESS2)

        # try transaction query by tx_hash
        result = dbethtx.get_ethereum_transactions(cursor, ETHTransactionsFilterQuery.make(tx_hash=tx2_hash), has_premium=True)  # noqa: E501
        assert result == [tx2], 'querying transaction by hash in bytes failed'
        result = dbethtx.get_ethereum_transactions(cursor, ETHTransactionsFilterQuery.make(tx_hash=b'dsadsad'), has_premium=True)  # noqa: E501
        assert result == []

        # Now try transaction by relevant addresses
        result = dbethtx.get_ethereum_transactions(cursor, ETHTransactionsFilterQuery.make(addresses=[ETH_ADDRESS1, make_ethereum_address()]), has_premium=True)  # noqa: E501
        assert result == [tx1, tx3]


def test_query_also_internal_ethereum_transactions(data_dir, username, sql_vm_instructions_cb):
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
        trace_id=1,
        timestamp=Timestamp(1452806400),
        block_number=5,
        from_address=ETH_ADDRESS3,
        to_address=address_4,
        value=0,
    )
    internal_tx2 = EvmInternalTransaction(
        parent_tx_hash=make_evm_tx_hash(b'5'),
        trace_id=21,
        timestamp=Timestamp(1629064001),
        block_number=55,
        from_address=make_ethereum_address(),
        to_address=make_ethereum_address(),
        value=0,
    )
    internal_tx3 = EvmInternalTransaction(
        parent_tx_hash=make_evm_tx_hash(b'4'),
        trace_id=25,
        timestamp=Timestamp(1628064001),
        block_number=6,
        from_address=ETH_ADDRESS1,
        to_address=ETH_ADDRESS3,
        value=10,
    )
    internal_tx4 = EvmInternalTransaction(
        parent_tx_hash=make_evm_tx_hash(b'4'),
        trace_id=26,
        timestamp=Timestamp(1628064001),
        block_number=6,
        from_address=ETH_ADDRESS1,
        to_address=ETH_ADDRESS3,
        value=0,
    )

    dbethtx = DBEthTx(data.db)
    with data.db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [tx1, tx3, tx4, tx5], relevant_address=ETH_ADDRESS1)  # noqa: E501
        dbethtx.add_ethereum_transactions(cursor, [tx2], relevant_address=ETH_ADDRESS2)
        dbethtx.add_ethereum_transactions(cursor, [tx1, tx3], relevant_address=ETH_ADDRESS3)
        dbethtx.add_ethereum_internal_transactions(cursor, [internal_tx2, internal_tx3, internal_tx4], relevant_address=ETH_ADDRESS1)  # noqa: E501
        dbethtx.add_ethereum_internal_transactions(cursor, [internal_tx1, internal_tx4], relevant_address=ETH_ADDRESS3)  # noqa: E501
        dbethtx.add_ethereum_internal_transactions(cursor, [internal_tx1], relevant_address=address_4)  # noqa: E501
        errors = msg_aggregator.consume_errors()
        warnings = msg_aggregator.consume_warnings()
        assert len(errors) == 0
        assert len(warnings) == 0

        result, total_filter_count = dbethtx.get_ethereum_transactions_and_limit_info(
            cursor=cursor,
            filter_=ETHTransactionsFilterQuery.make(addresses=[ETH_ADDRESS3]),
            has_premium=True,
        )
        assert {x.tx_hash for x in result} == {b'1', b'3', b'4'}
        assert total_filter_count == 3

        # Now try transaction query by relevant addresses and see we get more due to the
        # internal tx mappings
        result, total_filter_count = dbethtx.get_ethereum_transactions_and_limit_info(
            cursor=cursor,
            filter_=ETHTransactionsFilterQuery.make(addresses=[ETH_ADDRESS1]),
            has_premium=True,
        )
        assert result == [tx1, tx3, tx4, tx5]
        assert total_filter_count == 4

        result = dbethtx.get_ethereum_transactions(
            cursor=cursor,
            filter_=ETHTransactionsFilterQuery.make(addresses=[address_4]),
            has_premium=True,
        )
        assert result == [tx3]

        result = dbethtx.get_ethereum_transactions(
            cursor=cursor,
            filter_=ETHTransactionsFilterQuery.make(addresses=[ETH_ADDRESS3]),
            has_premium=True,
        )
        assert result == [tx1, tx3, tx4]
