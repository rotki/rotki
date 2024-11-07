from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.tests.utils.aave import AAVE_TEST_ACC_1
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_sync_response_with_result

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[AAVE_TEST_ACC_1]])
def test_query_defi_balances(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],   # pylint: disable=unused-argument
) -> None:
    """Check querying the defi balances endpoint works. Uses real data.

    TODO: Here we should use a test account for which we will know what balances
    it has and we never modify
    """
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'defibalancesresource',
    ))
    result = assert_proper_sync_response_with_result(response)

    # assert some defi balances were detected
    first_entry = result[AAVE_TEST_ACC_1][0]
    assert first_entry['protocol'] is not None
    assert first_entry['protocol']['name'] is not None
    assert first_entry['balance_type'] in {'Asset', 'Debt'}
    assert first_entry['base_balance'] is not None
    assert first_entry['underlying_balances'] is not None
