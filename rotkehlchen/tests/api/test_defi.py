import pytest
import requests

from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result


@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_query_defi_balances(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the defi balances endpoint works. Uses real data.

    TODO: Here we should use a test account for which we will know what balances
    it has and we never modify
    """
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "defibalancesresource",
    ))
    result = assert_proper_response_with_result(response)

    assert len(result) == 1
    # Since we can't really be sure of latest balance of a non-test account just check
    # for correctness of result if there is any balance
    if len(result['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']) != 0:
        first_entry = result['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'][0]
        assert first_entry['protocol'] is not None
        assert first_entry['balance_type'] in ('Asset', 'Debt')
        assert first_entry['base_balance'] is not None
        assert first_entry['underlying_balances'] is not None
