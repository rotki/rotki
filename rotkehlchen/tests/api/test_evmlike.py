from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_GNO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.factories import make_evm_address

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('ethereum_modules', [['zksync_lite']])
def test_evmlike_transactions_refresh(
        rotkehlchen_api_server: 'APIServer',
        number_of_eth_accounts: int,
) -> None:
    """Just tests the api part of refreshing evmlike transactions. Since at the moment
    this only concerns zksynclite, actual data check is in
    integration/test_zksynclite.py::test_get_transactions"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert (zksync_lite := rotki.chains_aggregator.get_module('zksync_lite')) is not None
    with patch.object(
            zksync_lite,
            'get_transactions',
            wraps=zksync_lite.get_transactions,
    ) as tx_query:
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'evmliketransactionsresource',
            ), json={'async_query': False},
        )
        assert_simple_ok_response(response)
        assert tx_query.call_count == number_of_eth_accounts


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('zksync_lite_accounts', [[make_evm_address(), make_evm_address()]])
@pytest.mark.parametrize('ethereum_modules', [['zksync_lite']])
def test_evmlike_blockchain_balances(
        rotkehlchen_api_server: 'APIServer',
        zksync_lite_accounts,
) -> None:
    """Just tests the api part of refreshing evmlike transactions. Since at the moment
    this only concerns zksynclite, actual data check is in
    integration/test_zksynclite.py::test_balances"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    addy_0_balances = {
        A_ETH: Balance(amount=FVal(10), usd_value=FVal(1000)),
        A_DAI: Balance(amount=FVal(100), usd_value=FVal(100)),
    }
    addy_1_balances = {
        A_ETH: Balance(amount=FVal(5), usd_value=FVal(500)),
        A_GNO: Balance(amount=FVal(50), usd_value=FVal(25)),
    }

    def serialize_balances(value) -> dict[str, dict]:
        return {asset.identifier: balance.serialize() for asset, balance in value.items()}

    def mocked_get_balances(addresses):
        return {
            addresses[0]: addy_0_balances,
            addresses[1]: addy_1_balances,
        }

    assert (zksync_lite := rotki.chains_aggregator.get_module('zksync_lite')) is not None
    with patch.object(
            zksync_lite,
            'get_balances',
            wraps=mocked_get_balances,
    ) as balance_query:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'blockchainbalancesresource',
            ), json={'async_query': False},
        )
        result = assert_proper_response_with_result(response)
        assert balance_query.call_count == 1
        assert result == {
            'per_account': {
                'zksync_lite': {
                    zksync_lite_accounts[0]: {
                        'assets': serialize_balances(addy_0_balances),
                        'liabilities': {},
                    },
                    zksync_lite_accounts[1]: {
                        'assets': serialize_balances(addy_1_balances),
                        'liabilities': {},
                    },
                },
            },
            'totals': {
                'assets': {
                    A_ETH.identifier: (addy_0_balances[A_ETH] + addy_1_balances[A_ETH]).serialize(),  # noqa: E501
                    A_GNO.identifier: addy_1_balances[A_GNO].serialize(),
                    A_DAI.identifier: addy_0_balances[A_DAI].serialize(),
                },
                'liabilities': {},
            },
        }
