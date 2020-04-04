import operator
import os
from unittest.mock import patch

import pytest

from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.tests.utils.blockchain import DEFAULT_BALANCE
from rotkehlchen.tests.utils.constants import A_GNO
from rotkehlchen.typing import SupportedBlockchain
from rotkehlchen.utils.misc import from_wei


@pytest.mark.skipif(
    os.name == 'nt',
    reason='Not testing running with geth in windows at the moment',
)
@pytest.mark.parametrize('have_blockchain_backend', [True])
def test_eth_connection_initial_balances(
        blockchain,
        number_of_eth_accounts,
        ethereum_accounts,
        inquirer,  # pylint: disable=unused-argument
):
    assert blockchain.ethereum.connected is True, 'Should be connected to ethereum node'
    result = blockchain.query_balances()

    per_eth_account = result.per_account.eth
    assert len(ethereum_accounts) == len(per_eth_account) == number_of_eth_accounts

    eth_default_balance = from_wei(DEFAULT_BALANCE)
    for acc, values in per_eth_account.items():
        assert acc in ethereum_accounts
        assert values.asset_balances['ETH'].amount == eth_default_balance
        assert values.asset_balances['ETH'].usd_value > ZERO
        assert values.total_usd_value > ZERO

    totals_eth = result.totals['ETH']
    assert totals_eth.amount == number_of_eth_accounts * eth_default_balance
    assert totals_eth.usd_value > ZERO


def test_query_btc_balances(blockchain):
    blockchain.query_btc_balances()
    assert 'BTC' not in blockchain.totals

    account = '3BZU33iFcAiyVyu2M2GhEpLNuh81GymzJ7'
    blockchain.modify_btc_account(account, 'append', operator.add)

    blockchain.query_btc_balances()
    assert blockchain.totals[A_BTC].usd_value is not None
    assert blockchain.totals[A_BTC].amount is not None


def test_add_remove_account_assure_all_balances_not_always_queried(blockchain):
    """Due to a programming mistake at addition and removal of blockchain accounts
    after the first time all balances were queried every time. That slowed
    everything down (https://github.com/rotki/rotki/issues/678).

    This is a regression test for that behaviour
    """
    addr1 = '0xe188c6BEBB81b96A65aa20dDB9e2aef62627fa4c'
    blockchain.add_blockchain_accounts(
        blockchain=SupportedBlockchain.ETHEREUM,
        accounts=[addr1],
    )
    assert addr1 in blockchain.accounts.eth

    with patch.object(blockchain, 'query_balances') as mock:
        blockchain.remove_blockchain_accounts(
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[addr1],
        )

    assert addr1 not in blockchain.accounts.eth
    assert mock.call_count == 0, 'blockchain.query_balances() should not have been called'

    addr2 = '0x78a087fCf440315b843632cFd6FDE6E5adcCc2C2'
    with patch.object(blockchain, 'query_balances') as mock:
        blockchain.add_blockchain_accounts(
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[addr2],
        )

    assert addr2 in blockchain.accounts.eth
    assert mock.call_count == 0, 'blockchain.query_balances() should not have been called'

    with patch.object(blockchain, 'query_balances') as mock:
        blockchain.track_new_tokens(new_tokens=[A_GNO])

    assert mock.call_count == 0, 'blockchain.query_balances() should not have been called'
    assert A_GNO in blockchain.owned_eth_tokens

    with patch.object(blockchain, 'query_balances') as mock:
        blockchain.remove_eth_tokens(tokens=[A_GNO])

    assert A_GNO not in blockchain.owned_eth_tokens
    assert mock.call_count == 0, 'blockchain.query_balances() should not have been called'
