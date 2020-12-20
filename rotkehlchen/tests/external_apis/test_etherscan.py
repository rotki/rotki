import os
from unittest.mock import patch

import pytest

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.externalapis.etherscan import Etherscan, deserialize_transaction_from_etherscan
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import EthereumTransaction, ExternalService, ExternalServiceApiCredentials


@pytest.fixture(scope='function', name='temp_etherscan')
def fixture_temp_etherscan(function_scope_messages_aggregator, tmpdir_factory):
    directory = tmpdir_factory.mktemp('data')
    db = DBHandler(
        user_data_dir=directory,
        password='123',
        msg_aggregator=function_scope_messages_aggregator,
        initial_settings=None,
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


def test_deserialize_transaction_from_etherscan():
    # Make sure that a missing to address due to contract creation is handled
    data = {'blockNumber': 54092, 'timeStamp': 1439048640, 'hash': '0x9c81f44c29ff0226f835cd0a8a2f2a7eca6db52a711f8211b566fd15d3e0e8d4', 'nonce': 0, 'blockHash': '0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159', 'transactionIndex': 0, 'from': '0x5153493bB1E1642A63A098A65dD3913daBB6AE24', 'to': '', 'value': 11901464239480000000000000, 'gas': 2000000, 'gasPrice': 10000000000000, 'isError': 0, 'txreceipt_status': '', 'input': '0x313233', 'contractAddress': '0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae', 'cumulativeGasUsed': 1436963, 'gasUsed': 1436963, 'confirmations': 8569454}  # noqa: E501
    transaction = deserialize_transaction_from_etherscan(data, internal=False)
    assert transaction == EthereumTransaction(
        tx_hash=bytes.fromhex(data['hash'][2:]),
        timestamp=1439048640,
        block_number=54092,
        from_address='0x5153493bB1E1642A63A098A65dD3913daBB6AE24',
        to_address=None,
        value=11901464239480000000000000,
        gas=2000000,
        gas_price=10000000000000,
        gas_used=1436963,
        input_data=bytes.fromhex(data['input'][2:]),
        nonce=0,
    )
