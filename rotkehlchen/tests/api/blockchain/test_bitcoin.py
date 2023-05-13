import random

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.ens import ENS_BRUNO, ENS_BRUNO_BTC_ADDR
from rotkehlchen.types import SupportedBlockchain


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_btc_blockchain_account_ens_domain(rotkehlchen_api_server):
    """Test adding a Bitcoin blockchain account via ENS domain when there is none
    in the db works as expected.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    async_query = random.choice([False, True])
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=SupportedBlockchain.BITCOIN.value,
        ),
        json={
            'accounts': [{'address': ENS_BRUNO}],
            'async_query': async_query,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert result == [ENS_BRUNO_BTC_ADDR]
    assert set(rotki.chains_aggregator.accounts.btc) == {ENS_BRUNO_BTC_ADDR}
