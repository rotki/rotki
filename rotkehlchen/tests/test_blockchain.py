import operator
import os

import pytest
from eth_utils.address import to_checksum_address

from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.tests.utils.blockchain import DEFAULT_BALANCE
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
    res, empty_or_error = blockchain.query_balances()
    assert empty_or_error == ''
    assert 'per_account' in res
    assert 'totals' in res

    per_eth_account = res['per_account']['ETH']
    assert len(ethereum_accounts) == len(per_eth_account) == number_of_eth_accounts

    eth_default_balance = from_wei(DEFAULT_BALANCE)
    for acc, values in per_eth_account.items():
        assert acc in ethereum_accounts
        assert values['ETH'] == eth_default_balance
        assert 'usd_value' in values

    totals_eth = res['totals']['ETH']
    assert totals_eth['amount'] == number_of_eth_accounts * eth_default_balance
    assert 'usd_value' in totals_eth


def test_query_btc_balances(blockchain):
    blockchain.query_btc_balances()
    assert blockchain.totals[A_BTC] == {}
    assert blockchain.balances[A_BTC] == {}

    account = '3BZU33iFcAiyVyu2M2GhEpLNuh81GymzJ7'
    blockchain.modify_btc_account(account, 'append', operator.add)

    blockchain.query_btc_balances()
    assert 'usd_value' in blockchain.totals[A_BTC]
    assert 'amount' in blockchain.totals[A_BTC]


def test_add_remove_ethereum_account_saved_as_checksummed(blockchain):
    """Provide a non-checksummed ethereum account and make sure it's saved as checksummed
    And then try to remove it as non checksummed and make sure removal also works
    """
    blockchain.add_blockchain_accounts(
        blockchain=SupportedBlockchain.ETHEREUM,
        accounts=['0xe188c6bebb81b96a65aa20ddb9e2aef62627fa4c'],
    )
    checksummed_addr = to_checksum_address('0xe188c6bebb81b96a65aa20ddb9e2aef62627fa4c')
    assert checksummed_addr in blockchain.accounts.eth

    blockchain.remove_blockchain_accounts(
        blockchain=SupportedBlockchain.ETHEREUM,
        accounts=['0xe188c6bebb81b96a65aa20ddb9e2aef62627fa4c'],
    )

    assert checksummed_addr not in blockchain.accounts.eth
