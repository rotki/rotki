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
from rotkehlchen.typing import EthereumInternalTransaction, EthereumTransaction, Timestamp
from rotkehlchen.user_messages import MessagesAggregator


def test_add_ethereum_transactions(data_dir, username):
    """Test that adding and retrieving ethereum transactions from the DB works fine.

    Also duplicates should be ignored and an error returned
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    tx2_hash_b = b'.h\xdd\x82\x85\x94\xeaq\xfe\n\xfc\xcf\xadwH\xc9\x0f\xfc\xd0\xf1\xad\xd4M\r$\x9b\xf7\x98\x87\xda\x93\x18'  # noqa: E501
    tx2_hash = '0x2e68dd828594ea71fe0afccfad7748c90ffcd0f1add44d0d249bf79887da9318'

    tx1 = EthereumTransaction(
        tx_hash=b'1',
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
    tx2 = EthereumTransaction(
        tx_hash=tx2_hash_b,
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
    tx3 = EthereumTransaction(
        tx_hash=b'3',
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

    # Add and retrieve the first 2 trades. All should be fine.
    dbethtx = DBEthTx(data.db)
    dbethtx.add_ethereum_transactions([tx1, tx2])
    errors = msg_aggregator.consume_errors()
    warnings = msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0
    filter_query = ETHTransactionsFilterQuery.make()
    returned_transactions, _ = dbethtx.get_ethereum_transactions(filter_query)
    assert returned_transactions == [tx1, tx2]

    # Add the last 2 transactions. Since tx2 already exists in the DB it should be
    # ignored (no errors shown for attempting to add already existing transaction)
    dbethtx.add_ethereum_transactions([tx2, tx3])
    errors = msg_aggregator.consume_errors()
    warnings = msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0
    returned_transactions, _ = dbethtx.get_ethereum_transactions(filter_query)
    assert returned_transactions == [tx1, tx2, tx3]

    # try transaction query by tx_hash
    result, _ = dbethtx.get_ethereum_transactions(ETHTransactionsFilterQuery.make(tx_hash=tx2_hash_b))  # noqa: E501
    assert result == [tx2], 'querying transaction by hash in bytes failed'
    result, _ = dbethtx.get_ethereum_transactions(ETHTransactionsFilterQuery.make(tx_hash=tx2_hash))  # noqa: E501
    assert result == [tx2], 'querying transaction by hash string failed'
    result, _ = dbethtx.get_ethereum_transactions(ETHTransactionsFilterQuery.make(tx_hash=b'dsadsad'))  # noqa: E501
    assert result == []


def test_query_also_internal_ethereum_transactions(data_dir, username):
    """Test that querying transactions for an address also returns the parent
    transaction of any internal transactions the address was involved in.
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    address_4 = make_ethereum_address()

    tx1 = EthereumTransaction(
        tx_hash=b'1',
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
    tx2 = EthereumTransaction(
        tx_hash=b'2',
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
    tx3 = EthereumTransaction(
        tx_hash=b'3',
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
    tx4 = EthereumTransaction(
        tx_hash=b'4',
        timestamp=Timestamp(162806400),
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
    tx5 = EthereumTransaction(
        tx_hash=b'5',
        timestamp=Timestamp(162806400),
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
    internal_tx1 = EthereumInternalTransaction(
        parent_tx_hash=b'3',
        trace_id=1,
        timestamp=Timestamp(1452806400),
        block_number=5,
        from_address=ETH_ADDRESS3,
        to_address=address_4,
        value=0,
    )
    internal_tx2 = EthereumInternalTransaction(
        parent_tx_hash=b'5',
        trace_id=21,
        timestamp=Timestamp(1552806400),
        block_number=55,
        from_address=make_ethereum_address(),
        to_address=make_ethereum_address(),
        value=0,
    )
    internal_tx3 = EthereumInternalTransaction(
        parent_tx_hash=b'4',
        trace_id=25,
        timestamp=Timestamp(162806400),
        block_number=6,
        from_address=ETH_ADDRESS1,
        to_address=ETH_ADDRESS3,
        value=10,
    )
    internal_tx4 = EthereumInternalTransaction(
        parent_tx_hash=b'4',
        trace_id=26,
        timestamp=Timestamp(162806400),
        block_number=6,
        from_address=ETH_ADDRESS1,
        to_address=ETH_ADDRESS3,
        value=0,
    )

    dbethtx = DBEthTx(data.db)
    dbethtx.add_ethereum_transactions([tx1, tx2, tx3, tx4, tx5])
    dbethtx.add_ethereum_internal_transactions([
        internal_tx1,
        internal_tx2,
        internal_tx3,
        internal_tx4,
    ])
    errors = msg_aggregator.consume_errors()
    warnings = msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0

    result = dbethtx.get_ethereum_transactions(
        ETHTransactionsFilterQuery.make(addresses=[ETH_ADDRESS3]),
    )
    assert {x.tx_hash for x in result} == {b'1', b'3', b'4'}
