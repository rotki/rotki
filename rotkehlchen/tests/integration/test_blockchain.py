import operator
import os
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.tests.utils.blockchain import mock_etherscan_query
from rotkehlchen.typing import SupportedBlockchain


@pytest.mark.skipif(
    os.name == 'nt',
    reason='Not testing running with geth in windows at the moment',
)
@pytest.mark.parametrize('have_blockchain_backend', [True])
def test_eth_connection_initial_balances(
        blockchain,
        inquirer,  # pylint: disable=unused-argument
):
    """TODO for this test. Either:
    1. Not use own chain but use a normal open node for this test.
    2. If we use own chain, deploy the eth-scan contract there.

    But probably (1) makes more sense
    """
    assert blockchain.ethereum.web3 is not None, 'Should be connected to ethereum node'


def test_query_btc_balances(blockchain):
    blockchain.query_btc_balances()
    assert 'BTC' not in blockchain.totals

    account = '3BZU33iFcAiyVyu2M2GhEpLNuh81GymzJ7'
    blockchain.modify_btc_account(account, 'append', operator.add)

    blockchain.query_btc_balances()
    assert blockchain.totals[A_BTC].usd_value is not None
    assert blockchain.totals[A_BTC].amount is not None


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_remove_account_assure_all_balances_not_always_queried(blockchain):
    """Due to a programming mistake at addition and removal of blockchain accounts
    after the first time all balances were queried every time. That slowed
    everything down (https://github.com/rotki/rotki/issues/678).

    This is a regression test for that behaviour

    TODO: Is this still needed? Shouldn't it just be removed?
    Had to add lots of mocks to make it not be a slow test
    """
    addr1 = '0xe188c6BEBB81b96A65aa20dDB9e2aef62627fa4c'
    addr2 = '0x78a087fCf440315b843632cFd6FDE6E5adcCc2C2'
    etherscan_patch = mock_etherscan_query(
        eth_map={addr1: {'ETH': 1}, addr2: {'ETH': 2}},
        etherscan=blockchain.ethereum.etherscan,
        original_requests_get=requests.get,
        original_queries=[],
    )
    ethtokens_max_chunks_patch = patch(
        'rotkehlchen.chain.ethereum.tokens.ETHERSCAN_MAX_TOKEN_CHUNK_LENGTH',
        new=800,
    )
    with etherscan_patch, ethtokens_max_chunks_patch:
        blockchain.add_blockchain_accounts(
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[addr1],
        )
    assert addr1 in blockchain.accounts.eth

    with etherscan_patch, ethtokens_max_chunks_patch, patch.object(blockchain, 'query_balances') as mock:  # noqa: E501
        blockchain.remove_blockchain_accounts(
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[addr1],
        )

    assert addr1 not in blockchain.accounts.eth
    assert mock.call_count == 0, 'blockchain.query_balances() should not have been called'

    addr2 = '0x78a087fCf440315b843632cFd6FDE6E5adcCc2C2'
    with etherscan_patch, ethtokens_max_chunks_patch, patch.object(blockchain, 'query_balances') as mock:  # noqa: E501
        blockchain.add_blockchain_accounts(
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[addr2],
        )
