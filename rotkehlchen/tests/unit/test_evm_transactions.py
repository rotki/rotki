from unittest.mock import patch

from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
from rotkehlchen.chain.evm.types import EvmAccount
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import ChainID

ADDR_1, ADDR_2, ADDR_3 = make_evm_address(), make_evm_address(), make_evm_address()


def test_query_transactions_single_chain(eth_transactions: 'EthereumTransactions'):
    """
    Test that when querying transactions for a single chain, addresses only for that chain are
    queried. This tests passes several addresses for different chains to `EthereumTransactions`
    and checks that only ethereum addresses are queried.
    """
    queried_addresses = []

    def mock_single_address_query_transactions(address, **kwargs):  # pylint: disable=unused-argument  # noqa: E501
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
