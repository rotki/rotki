import pytest
import os

from rotkehlchen.utils import from_wei
from rotkehlchen.tests.utils.blockchain import DEFAULT_BALANCE


@pytest.mark.skip(
    os.name == 'nt',
    reason='Not testing running with geth in windows at the moment',
)
@pytest.mark.parametrize('have_blockchain_backend', [True])
def test_eth_connection_initial_balances(
        blockchain,
        number_of_accounts,
        ethereum_accounts,
        inquirer,
):
    res, empty_or_error = blockchain.query_balances()
    assert empty_or_error == ''
    assert 'per_account' in res
    assert 'totals' in res

    per_eth_account = res['per_account']['ETH']
    assert len(ethereum_accounts) == len(per_eth_account) == number_of_accounts

    eth_default_balance = from_wei(DEFAULT_BALANCE)
    for acc, values in per_eth_account.items():
        assert acc in ethereum_accounts
        assert values['ETH'] == eth_default_balance
        assert 'usd_value' in values

    totals_eth = res['totals']['ETH']
    assert totals_eth['amount'] == number_of_accounts * eth_default_balance
    assert 'usd_value' in totals_eth
