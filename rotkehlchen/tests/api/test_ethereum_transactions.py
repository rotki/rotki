from http import HTTPStatus
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.mock import MockResponse

EXPECTED_AFB7_TXS = [{
    'tx_hash': '0x13684203a4bf07aaed0112983cb380db6004acac772af2a5d46cb2a28245fbad',
    'timestamp': 1439984408,
    'block_number': 111083,
    'from_address': '0xC47Aaa860008be6f65B58c6C6E02a84e666EfE31',
    'to_address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
    'value': '37451082560000003241',
    'gas': '90000',
    'gas_price': '58471444665',
    'gas_used': '21000',
    'input_data': '0x',
    'nonce': 100,
}, {
    'tx_hash': '0xe58af420fd8430c061303e4c5bd2668fafbc0fd41078fa6aa01d7781c1dadc7a',
    'timestamp': 1461221228,
    'block_number': 1375816,
    'from_address': '0x9e6316f44BaEeeE5d41A1070516cc5fA47BAF227',
    'to_address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
    'value': '389359660000000000',
    'gas': '250000',
    'gas_price': '20000000000',
    'gas_used': '21000',
    'input_data': '0x',
    'nonce': 326,
}, {
    'tx_hash': '0x0ae8b470b4a69c7f6905b9ec09f50c8772821080d11ba0acc83ac23a7ccb4ad8',
    'timestamp': 1461399856,
    'block_number': 1388248,
    'from_address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
    'to_address': '0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2',
    'value': '37840020860000003241',
    'gas': '21068',
    'gas_price': '20000000000',
    'gas_used': '21068',
    'input_data': '0x01',
    'nonce': 0,
}, {
    'tx_hash': '0x2f6f167e32e9cb1bef40b92e831c3f1d1cd0348bb72dcc723bde94f51944ebd6',
    'timestamp': 1494458609,
    'block_number': 3685519,
    'from_address': '0x4aD11d04CCd80A83d48096478b73D1E8e0ed49D6',
    'to_address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
    'value': '6000000000000000000',
    'gas': '21000',
    'gas_price': '21000000000',
    'gas_used': '21000',
    'input_data': '0x',
    'nonce': 1,
}, {
    'tx_hash': '0x5d81f937ad37349f89dc6e9926988855bb6c6e1e00c683ee3b7cb7d7b09b5567',
    'timestamp': 1494458861,
    'block_number': 3685532,
    'from_address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
    'to_address': '0xFa52274DD61E1643d2205169732f29114BC240b3',
    'value': '5999300000000000000',
    'gas': '35000',
    'gas_price': '20000000000',
    'gas_used': '30981',
    'input_data': '0xf7654176',
    'nonce': 1,
}]

EXPECTED_4193_TXS = [{
    'tx_hash': '0x2964f3a91408337b05aeb8f8f670f4107999be05376e630742404664c96a5c31',
    'timestamp': 1439979000,
    'block_number': 110763,
    'from_address': '0x976349705b839e2F5719387Fb27D2519d519da03',
    'to_address': '0x4193122032b38236825BBa166F42e54fc3F4A1EE',
    'value': '100000000000000000',
    'gas': '90000',
    'gas_price': '57080649960',
    'gas_used': '21000',
    'input_data': '0x',
    'nonce': 30,
}, {
    'tx_hash': '0xb99a6e0b40f38c4887617bc1df560fde1d0456b712cb2bb1b52fdb8880d3cd74',
    'timestamp': 1439984825,
    'block_number': 111111,
    'from_address': '0x4193122032b38236825BBa166F42e54fc3F4A1EE',
    'to_address': '0x1177848589133f5C4E69EdFcb18bBCd9cACE72D1',
    'value': '20000000000000000',
    'gas': '90000',
    'gas_price': '59819612547',
    'gas_used': '21000',
    'input_data': '0x',
    'nonce': 0,
}, {
    'tx_hash': '0xfadf1f12281ee2c0311055848b4ffc0046ac80afae4a9d3640b5f57bb8a7795a',
    'timestamp': 1507291254,
    'block_number': 4341870,
    'from_address': '0x4193122032b38236825BBa166F42e54fc3F4A1EE',
    'to_address': '0x2B06E2ea21e184589853225888C93b9b8e0642f6',
    'value': '78722788136513000',
    'gas': '21000',
    'gas_price': '1000000000',
    'gas_used': '21000',
    'input_data': '0x',
    'nonce': 1,
}]


@pytest.mark.parametrize('ethereum_accounts', [[
    '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
    '0x4193122032b38236825BBa166F42e54fc3F4A1EE',
]])
@pytest.mark.parametrize('async_query', [True, False])
def test_query_transactions(rotkehlchen_api_server, async_query):
    """Test that querying the ethereum transactions endpoint works as expected

    This test uses real data. Found an ethereum address that has very few transactions
    and hopefully won't have more. If it does we can adjust the test.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Check that we get all transactions
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)
    expected_result = EXPECTED_AFB7_TXS + EXPECTED_4193_TXS
    expected_result.sort(key=lambda x: x['timestamp'])
    assert result == expected_result

    # Check that transactions per address and in a specific time range can be
    # queried and that this is from the DB and not etherscan
    def mock_etherscan_get(url, *args, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, "{}")
    etherscan_patch = patch.object(rotki.etherscan.session, 'get', wraps=mock_etherscan_get)
    with etherscan_patch as mock_call:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'per_address_ethereum_transactions_resource',
                address='0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
            ), json={
                'async_query': async_query,
                "from_timestamp": 1461399856,
                "to_timestamp": 1494458860,
            },
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

        assert mock_call.call_count == 0

    assert result == EXPECTED_AFB7_TXS[2:-2]


def test_query_transactions_errors(rotkehlchen_api_server):
    # Malformed address
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_address_ethereum_transactions_resource',
            address='0xasdasd',
        ),
    )
    assert_error_response(
        response=response,
        contained_in_msg='address": ["Given value 0xasdasd is not an ethereum address',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Malformed from_timestamp
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_address_ethereum_transactions_resource',
            address='0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
        ), json={'from_timestamp': 'foo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a timestamp entry from string foo',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Malformed to_timestamp
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_address_ethereum_transactions_resource',
            address='0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
        ), json={'to_timestamp': 'foo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a timestamp entry from string foo',
        status_code=HTTPStatus.BAD_REQUEST,
    )
