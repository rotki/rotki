import pytest

from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.types import ChainID, deserialize_evm_tx_hash


@pytest.mark.parametrize('optimism_accounts', [['0xd6Ade875eEC93a7aAb7EfB7DBF13d1457443f95B']])
def test_query_transactions_no_fee(optimism_transactions, optimism_accounts):
    """Test to query an optimism transaction with and without l1_fee existing in the DB.
    Make sure that if l1_fee is missing in the DB nothing breaks, but it's just seen as 0.
    """
    address = optimism_accounts[0]
    dbevmtx = optimism_transactions.dbevmtx
    tx_hash = deserialize_evm_tx_hash('0x6eb136db4d36cf695f4026da16f602ed4a2583b2420dbbcbd4f436943190b665')  # noqa: E501

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
        assert transactions[0].to_address == '0xDEF1ABE32c034e558Cdd535791643C58a13aCC10'

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
