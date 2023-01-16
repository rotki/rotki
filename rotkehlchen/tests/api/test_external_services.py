from http import HTTPStatus

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)


@pytest.mark.parametrize('include_etherscan_key', [False])
@pytest.mark.parametrize('include_cryptocompare_key', [False])
def test_add_get_external_service(rotkehlchen_api_server):
    """Tests that adding and retrieving external service credentials works"""
    # With no data an empty response should be returned
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
    )
    result = assert_proper_response_with_result(response)
    assert result == {}

    # Now add some data and see that the response shows they are added
    expected_result = {
        'etherscan': {'api_key': 'key1'},
        'cryptocompare': {'api_key': 'key2'},
    }
    data = {'services': [
        {'name': 'etherscan', 'api_key': 'key1'},
        {'name': 'cryptocompare', 'api_key': 'key2'},
    ]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    result = assert_proper_response_with_result(response)
    assert result == expected_result

    # Query again and see that the newly added services are returned
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
    )
    result = assert_proper_response_with_result(response)
    assert result == expected_result

    # Test that we can replace a value of an already existing service
    new_key = 'new_key'
    expected_result['cryptocompare']['api_key'] = new_key
    data = {'services': [{'name': 'cryptocompare', 'api_key': new_key}]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    result = assert_proper_response_with_result(response)
    assert result == expected_result

    # Query again and see that the modified services are returned
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
    )
    result = assert_proper_response_with_result(response)
    assert result == expected_result


@pytest.mark.parametrize('include_etherscan_key', [False])
def test_delete_external_service(rotkehlchen_api_server):
    """Tests that delete external service credentials works"""
    # Add some data and see that the response shows they are added
    expected_result = {
        'etherscan': {'api_key': 'key1'},
        'cryptocompare': {'api_key': 'key2'},
    }
    data = {'services': [
        {'name': 'etherscan', 'api_key': 'key1'},
        {'name': 'cryptocompare', 'api_key': 'key2'},
    ]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    result = assert_proper_response_with_result(response)
    assert result == expected_result

    # Now try to delete an entry and see the response shows it's deleted
    data = {'services': ['etherscan']}
    del expected_result['etherscan']
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    result = assert_proper_response_with_result(response)
    assert result == expected_result

    # Query again and see that the modified services are returned
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
    )
    result = assert_proper_response_with_result(response)
    assert result == expected_result

    # Now try to delete an existing and a non-existing service to make sure
    # that if the service is not in the DB, deletion is silently ignored
    data = {'services': ['etherscan', 'cryptocompare']}
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    result = assert_proper_response_with_result(response)
    assert result == {}

    # Query again and see that the modified services are returned
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
    )
    result = assert_proper_response_with_result(response)
    assert result == {}


def test_add_external_services_errors(rotkehlchen_api_server):
    """Tests that errors at adding external service credentials are handled properly"""
    # Missing data
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
    )
    assert_error_response(
        response=response,
        contained_in_msg='services": ["Missing data for required field.',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type for services
    data = {'services': 'foo'}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='"services": ["Not a valid list."',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type for services list element
    data = {'services': ['foo']}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='services": {"0": {"_schema": ["Invalid input type',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Missing api_key entry
    data = {'services': [{'name': 'etherscan'}]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='"api_key": ["Missing data for required field."',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Missing name entry
    data = {'services': [{'api_key': 'goookey'}]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='"name": ["Missing data for required field."',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Unsupported service name
    data = {'services': [{'name': 'unknown', 'api_key': 'goookey'}]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize ExternalService value unknown',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for service name
    data = {'services': [{'name': 23.2, 'api_key': 'goookey'}]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize ExternalService value from non string value: 23.2',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for api_key
    data = {'services': [{'name': 'etherscan', 'api_key': 53.2}]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='"api_key": ["Not a valid string."',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_remove_external_services_errors(rotkehlchen_api_server):
    """Tests that errors at removing external service credentials are handled properly"""
    # Missing data
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
    )
    assert_error_response(
        response=response,
        contained_in_msg='services": ["Missing data for required field.',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Wrong type for services
    data = {'services': 23.5}
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='"services": ["Not a valid list.',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Wrong type for services list element
    data = {'services': [55]}
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize ExternalService value from non string value: 55',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Unsupported service name in the list
    data = {'services': ['unknown', 'etherscan']}
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize ExternalService value unknown',
        status_code=HTTPStatus.BAD_REQUEST,
    )
