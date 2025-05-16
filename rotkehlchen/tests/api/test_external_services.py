from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


EMPTY_RESULT = {
    'blockscout': {'ethereum': None, 'optimism': None, 'polygon_pos': None, 'arbitrum_one': None, 'base': None, 'gnosis': None},  # noqa: E501
}


@pytest.mark.parametrize('include_etherscan_key', [False])
@pytest.mark.parametrize('include_cryptocompare_key', [False])
@pytest.mark.parametrize('start_with_valid_premium', [True])  # for monerium
def test_add_get_external_service(rotkehlchen_api_server: 'APIServer') -> None:
    """Tests that adding and retrieving external service credentials works"""
    # With no data an empty response should be returned
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == EMPTY_RESULT

    # Now add some data and see that the response shows they are added
    expected_result: dict[str, Any] = {
        'etherscan': {'api_key': 'key1'},
        'blockscout': {'ethereum': None, 'optimism': None, 'polygon_pos': None, 'arbitrum_one': None, 'base': None, 'gnosis': None},  # noqa: E501
        'cryptocompare': {'api_key': 'key2'},
        'monerium': {'username': 'Ben', 'password': 'supersafepassword'},
    }
    data = {'services': [
        {'name': 'etherscan', 'api_key': 'key1'},
        {'name': 'cryptocompare', 'api_key': 'key2'},
        {'name': 'monerium', 'username': 'Ben', 'password': 'supersafepassword'},
    ]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == expected_result

    # Query again and see that the newly added services are returned
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == expected_result

    # Test that we can replace a value of an already existing service
    new_key = 'new_key'
    expected_result['cryptocompare']['api_key'] = new_key
    data = {'services': [{'name': 'cryptocompare', 'api_key': new_key}]}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json=data,
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == expected_result

    # Query again and see that the modified services are returned
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == expected_result


@pytest.mark.parametrize('include_etherscan_key', [False])
def test_delete_external_service(rotkehlchen_api_server: 'APIServer') -> None:
    """Tests that delete external service credentials works"""
    # Add some data and see that the response shows they are added
    expected_result: dict[str, Any] = {
        'etherscan': {'api_key': 'key1'},
        'blockscout': {'ethereum': None, 'optimism': None, 'polygon_pos': None, 'arbitrum_one': None, 'base': None, 'gnosis': None},  # noqa: E501
        'cryptocompare': {'api_key': 'key2'},
    }
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': [
            {'name': 'etherscan', 'api_key': 'key1'},
            {'name': 'cryptocompare', 'api_key': 'key2'},
        ]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == expected_result

    expected_result.pop('etherscan')
    # Now try to delete an entry and see the response shows it's deleted
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': ['etherscan']},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == expected_result

    # Query again and see that the modified services are returned
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == expected_result

    # Now try to delete an existing and a non-existing service to make sure
    # that if the service is not in the DB, deletion is silently ignored
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': ['etherscan', 'cryptocompare']},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == EMPTY_RESULT

    # Query again and see that the modified services are returned
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == EMPTY_RESULT


def test_add_external_services_errors(rotkehlchen_api_server: 'APIServer') -> None:
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
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': 'foo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='"services": ["Not a valid list."',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type for services list element
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': ['foo']},
    )
    assert_error_response(
        response=response,
        contained_in_msg='services": {"0": {"_schema": ["Invalid input type',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Missing api_key entry
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': [{'name': 'etherscan'}]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='"api_key": ["an api key is needed for etherscan"',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Missing name entry
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': [{'api_key': 'goookey'}]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='"name": ["Missing data for required field."',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Unsupported service name
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': [{'name': 'unknown', 'api_key': 'goookey'}]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize ExternalService value unknown',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for service name
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': [{'name': 23.2, 'api_key': 'goookey'}]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize ExternalService value from non string value: 23.2',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for api_key
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': [{'name': 'etherscan', 'api_key': 53.2}]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='"api_key": ["Not a valid string."',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # monerium without username
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': [{'name': 'monerium', 'api_key': 'aaa'}]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='monerium needs a username and password"',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # monerium without password
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': [{'name': 'monerium', 'username': 'Ben'}]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='monerium needs a username and password"',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # monerium without premium
    rotkehlchen_api_server.rest_api.rotkehlchen.premium = None
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': [{'name': 'monerium', 'username': 'Ben', 'password': 'secure'}]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='You can only use monerium with rotki premium',
        status_code=HTTPStatus.FORBIDDEN,
    )


def test_remove_external_services_errors(rotkehlchen_api_server: 'APIServer') -> None:
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
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': 23.5},
    )
    assert_error_response(
        response=response,
        contained_in_msg='"services": ["Not a valid list.',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Wrong type for services list element
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': [55]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize ExternalService value from non string value: 55',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Unsupported service name in the list
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'externalservicesresource'),
        json={'services': ['unknown', 'etherscan']},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize ExternalService value unknown',
        status_code=HTTPStatus.BAD_REQUEST,
    )
