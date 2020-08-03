import pytest
import requests

from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response
from rotkehlchen.tests.utils.constants import A_GNO, A_RDN


@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN, A_GNO]])
def test_query_ethereum_tokens_info(rotkehlchen_api_server):
    """Test that the rest api endpoint to query information about ethereum tokens works fine"""
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ))

    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    # There should be 2 keys in the result dict
    assert len(data['result']) == 2
    all_tokens = data['result']['all_eth_tokens']
    assert isinstance(all_tokens, list)
    for entry in all_tokens:
        assert len(entry) == 4
        assert entry['address'] is not None
        assert entry['symbol'] is not None
        assert entry['name'] is not None
        assert entry['decimal'] >= 0 and entry['decimal'] <= 18

    assert data['result']['owned_eth_tokens'] == ['RDN', 'GNO']
