import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.ens import ENS_BRUNO, ENS_BRUNO_BTC_ADDR
from rotkehlchen.types import SupportedBlockchain


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.freeze_time('2023-11-05 11:40:00 GMT')
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_btc_blockchain_account_ens_domain(rotkehlchen_api_server):
    """Test adding a Bitcoin blockchain account via ENS domain when there is none
    in the db works as expected.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=SupportedBlockchain.BITCOIN.value,
        ),
        json={
            'accounts': [{'address': ENS_BRUNO}],
            'async_query': True,
        },
    )
    task_id = assert_ok_async_response(response)
    result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)

    assert result == [ENS_BRUNO_BTC_ADDR]
    assert set(rotki.chains_aggregator.accounts.btc) == {ENS_BRUNO_BTC_ADDR}
