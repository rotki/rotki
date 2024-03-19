from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.tests.utils.api import api_url_for, assert_simple_ok_response

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('number_of_eth_accounts', [2])
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
