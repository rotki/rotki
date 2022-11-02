import warnings as test_warnings

import pytest
import requests
from flaky import flaky

from rotkehlchen.tests.utils.aave import AAVE_TEST_ACC_1
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result


@flaky(max_runs=3, min_passes=1)  # failed in a flaky way sometimes in the CI due to etherscan
@pytest.mark.parametrize('ethereum_accounts', [[AAVE_TEST_ACC_1]])
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

    # Since we can't really be sure of latest balance of a non-test account just check
    # for correctness of result if there is any balance
    if len(result[AAVE_TEST_ACC_1]) != 0:
        first_entry = result[AAVE_TEST_ACC_1][0]
        assert first_entry['protocol'] is not None
        assert first_entry['protocol']['name'] is not None
        assert first_entry['balance_type'] in ('Asset', 'Debt')
        assert first_entry['base_balance'] is not None
        assert first_entry['underlying_balances'] is not None
    else:
        test_warnings.warn(UserWarning(f'Test account {AAVE_TEST_ACC_1} has no DeFi balances'))
