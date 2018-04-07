from rotkehlchen.utils import from_wei

from rotkehlchen.tests.utils.blockchain import DEFAULT_BALANCE


def test_eth_connection_initial_balances(
        blockchain,
        number_of_accounts,
        ethereum_accounts,
        inquirer,
):
    res = blockchain.query_balances()
    assert 'per_account' in res
    assert 'totals' in res

    eth_usd_price = inquirer.find_usd_price('ETH')
    per_eth_account = res['per_account']['ETH']
    assert len(ethereum_accounts) == len(per_eth_account) == number_of_accounts

    eth_default_balance = from_wei(DEFAULT_BALANCE)
    for acc, values in per_eth_account.items():
        assert acc in ethereum_accounts
        assert values['ETH'] == eth_default_balance
        assert values['usd_value'] == eth_default_balance * eth_usd_price

    totals_eth = res['totals']['ETH']
    assert totals_eth['amount'] == number_of_accounts * eth_default_balance
    assert totals_eth['usd_value'] == number_of_accounts * eth_default_balance * eth_usd_price
