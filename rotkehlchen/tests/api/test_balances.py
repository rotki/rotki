import pytest
import requests

from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response
from rotkehlchen.tests.utils.blockchain import (
    assert_btc_balances_result,
    assert_eth_balances_result,
    mock_etherscan_balances_query,
)
from rotkehlchen.tests.utils.constants import A_RDN
from rotkehlchen.tests.utils.exchanges import (
    patch_binance_balances_query,
    patch_poloniex_balances_query,
)
from rotkehlchen.tests.utils.factories import (
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    make_ethereum_address,
)
from rotkehlchen.utils.misc import from_wei, satoshis_to_btc


def assert_all_balances(
        data,
        eth_balances,
        btc_balances,
        rdn_balances,
        fiat_balances,
        binance_balances,
        poloniex_balances,
) -> None:
    result = data['result']

    total_eth = ZERO
    total_eth += sum(from_wei(FVal(b)) for b in eth_balances)
    total_eth += binance_balances.get('ETH', ZERO)
    total_eth += poloniex_balances.get('ETH', ZERO)

    total_rdn = ZERO
    total_rdn += sum(from_wei(FVal(b)) for b in rdn_balances)
    total_rdn += binance_balances.get('RDN', ZERO)
    total_rdn += poloniex_balances.get('RDN', ZERO)

    total_btc = ZERO
    total_btc += sum(satoshis_to_btc(FVal(b)) for b in btc_balances)
    total_btc += binance_balances.get('BTC', ZERO)
    total_btc += poloniex_balances.get('BTC', ZERO)

    assert FVal(result['ETH']['amount']) == total_eth
    assert result['ETH']['usd_value'] is not None
    assert result['ETH']['percentage_of_net_value'] is not None
    assert FVal(result['RDN']['amount']) == total_rdn
    assert result['RDN']['usd_value'] is not None
    assert result['RDN']['percentage_of_net_value'] is not None
    assert FVal(result['BTC']['amount']) == total_btc
    assert result['BTC']['usd_value'] is not None
    assert result['BTC']['percentage_of_net_value'] is not None
    assert FVal(result['EUR']['amount']) == fiat_balances['EUR']
    assert result['BTC']['usd_value'] is not None
    assert result['EUR']['percentage_of_net_value'] is not None

    assert result['net_usd'] is not None
    # Check that the 4 locations are there
    assert len(result['location']) == 4
    assert result['location']['binance']['usd_value'] is not None
    assert result['location']['binance']['percentage_of_net_value'] is not None
    assert result['location']['poloniex']['usd_value'] is not None
    assert result['location']['poloniex']['percentage_of_net_value'] is not None
    assert result['location']['blockchain']['usd_value'] is not None
    assert result['location']['blockchain']['percentage_of_net_value'] is not None
    assert result['location']['banks']['usd_value'] is not None
    assert result['location']['banks']['percentage_of_net_value'] is not None
    assert len(result) == 6  # 4 assets + location + net_usd


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN]])
@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_query_all_balances(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
        number_of_eth_accounts,
):
    """Test that using the query all balances endpoint works

    Test that balances from various sources are returned. Such as exchanges,
    blockchain and FIAT"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.blockchain.cache_ttl_secs = 0

    eth_acc1 = ethereum_accounts[0]
    eth_acc2 = ethereum_accounts[1]
    eth_balance1 = '1000000'
    eth_balance2 = '2000000'
    eth_balances = [eth_balance1, eth_balance2]
    btc_balance1 = '3000000'
    btc_balance2 = '5000000'
    btc_balances = [btc_balance1, btc_balance2]
    rdn_balance = '4000000'
    eur_balance = FVal('1550')

    rotki.data.db.add_fiat_balance(A_EUR, eur_balance)
    binance = rotki.exchange_manager.connected_exchanges['binance']
    poloniex = rotki.exchange_manager.connected_exchanges['poloniex']
    poloniex_patch = patch_poloniex_balances_query(poloniex)
    binance_patch = patch_binance_balances_query(binance)
    blockchain_patch = mock_etherscan_balances_query(
        eth_map={
            eth_acc1: {'ETH': eth_balance1},
            eth_acc2: {'ETH': eth_balance2, 'RDN': rdn_balance},
        },
        btc_map={btc_accounts[0]: btc_balance1, btc_accounts[1]: btc_balance2},
        original_requests_get=requests.get,
    )

    with poloniex_patch, binance_patch, blockchain_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "allbalancesresource",
            ), json={'save_data': False}
        )

    assert_proper_response(response)
    json_data = response.json()
    assert_all_balances(
        data=json_data,
        eth_balances=eth_balances,
        btc_balances=btc_balances,
        rdn_balances=[rdn_balance],
        fiat_balances={A_EUR: eur_balance},
        # Taken from BINANCE_BALANCES_RESPONSE from tests.utils.exchanges
        binance_balances={'ETH': FVal('4763368.68006011'), 'BTC': FVal('4723846.89208129')},
        # Taken from POLONIEX_BALANCES_RESPONSE from tests.utils.exchanges
        poloniex_balances={'ETH': FVal('11.0'), 'BTC': FVal('5.5')},
    )
