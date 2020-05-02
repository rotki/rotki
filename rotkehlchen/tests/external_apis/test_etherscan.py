import os
from unittest.mock import patch

import pytest

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import ExternalService, ExternalServiceApiCredentials


@pytest.fixture(scope='function')
def temp_etherscan(function_scope_messages_aggregator, tmpdir_factory):
    directory = tmpdir_factory.mktemp('data')
    db = DBHandler(
        user_data_dir=directory,
        password='123',
        msg_aggregator=function_scope_messages_aggregator,
    )

    # Test with etherscan API key
    api_key = os.environ.get('ETHERSCAN_API_KEY', None)
    if api_key:
        db.add_external_service_credentials(credentials=[
            ExternalServiceApiCredentials(service=ExternalService.ETHERSCAN, api_key=api_key),
        ])
    etherscan = Etherscan(database=db, msg_aggregator=function_scope_messages_aggregator)
    return etherscan


def patch_etherscan(etherscan):
    count = 0

    def mock_requests_get(_url):
        nonlocal count
        if count == 0:
            response = (
                '{"status":"0","message":"NOTOK",'
                '"result":"Max rate limit reached, please use API Key for higher rate limit"}'
            )
        else:
            response = '{"jsonrpc":"2.0","id":1,"result":"0x1337"}'

        count += 1
        return MockResponse(200, response)

    return patch.object(etherscan.session, 'get', wraps=mock_requests_get)


def test_maximum_rate_limit_reached(temp_etherscan):
    """
    Test that we can handle etherscan's rate limit repsponse properly

    Regression test for https://github.com/rotki/rotki/issues/772"
    """
    etherscan = temp_etherscan

    etherscan_patch = patch_etherscan(etherscan)

    with etherscan_patch:
        result = etherscan.eth_call(
            '0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4',
            '0xc455279100000000000000000000000027a2eaaa8bebea8d23db486fb49627c165baacb5',
        )

    assert result == '0x1337'
