import random
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)

EXPECTED_8CB0_TXS = [{
    'tx_hash': '0x79d9e5a55a92429ef1f6d2fad116127306500fec341dd21826ef341ada0cc3f3',
    'timestamp': 1627300137,
    'block_number': 2775355,
    'from_address': '0x350f13c2c46acac8e44711f4bd87321304572a7d',
    'to_address': '0xb34fe8a87dfebd5ab0a03db73f2d49b903e63db6',
    'value': 0,
    'gas': 500000,
    'gas_price': 225000000000,
    'gas_used': 353674,
    'input_data': '0x',
    'nonce': 0,
}, {
    'tx_hash': '0x750504c9590d6af035bbd2e61a866c1264836155700e4f1c59d691f87a48ceb5',
    'timestamp': 1625920265,
    'block_number': 2626828,
    'from_address': '0x350f13c2c46acac8e44711f4bd87321304572a7d',
    'to_address': '0xe54ca86531e17ef3616d22ca28b0d458b6c89106',
    'value': 0,
    'gas': 180000,
    'gas_price': 225000000000,
    'gas_used': 141692,
    'input_data': '0x',
    'nonce': 0,
}, {
    'tx_hash': '0x7daa954a4ea7c8e8ece3b01857843abc0670938ead75d5f45b1356abb0e693df',
    'timestamp': 1625920188,
    'block_number': 2626819,
    'from_address': '0x350f13c2c46acac8e44711f4bd87321304572a7d',
    'to_address': '0xb34fe8a87dfebd5ab0a03db73f2d49b903e63db6',
    'value': 0,
    'gas': 500000,
    'gas_price': 225000000000,
    'gas_used': 353674,
    'input_data': '0x',
    'nonce': 0,
}]


@pytest.mark.parametrize('web3_mock_data', [{'covalent_transactions': 'test_avalanche/covalent_query_transactions.json'}])  # noqa: E501
def test_query_transactions(rotkehlchen_api_server):
    """Test that querying the avalanche transactions endpoint works as expected

    This test uses real data.
    """
    async_query = random.choice([False, True])
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'avalanchetransactionsresource',
        ), json={
            'address': '0x350f13c2C46AcaC8e44711F4bD87321304572A7D',
            'async_query': async_query,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)
    expected_result = EXPECTED_8CB0_TXS
    result_entries = result['entries']
    for entry in expected_result:
        assert entry in result_entries
    assert result['entries_found'] >= len(expected_result)


def test_query_transactions_errors(rotkehlchen_api_server):
    # Malformed address
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_address_avalanche_transactions_resource',
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
            'per_address_avalanche_transactions_resource',
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
            'per_address_avalanche_transactions_resource',
            address='0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
        ), json={'to_timestamp': 'foo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a timestamp entry from string foo',
        status_code=HTTPStatus.BAD_REQUEST,
    )
