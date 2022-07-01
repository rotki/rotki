from http import HTTPStatus
from typing import Any, Dict
from unittest.mock import patch

import requests
from rotkehlchen.chain.ethereum.constants import WEIGHTED_ETHEREUM_NODES
from rotkehlchen.chain.ethereum.types import ETHERSCAN_NODE_NAME

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.utils.misc import get_system_spec


def test_query_info_version_when_up_to_date(rotkehlchen_api_server):
    """Test that endpoint to query the rotki version works if no new version is available"""
    expected_version = 'v1.1.0'
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    def patched_get_system_spec() -> Dict[str, Any]:
        return {'rotkehlchen': expected_version}

    def patched_get_latest_release(_klass):
        return expected_version, f'https://github.com/rotki/rotki/releases/tag/{expected_version}'
    release_patch = patch(
        'rotkehlchen.externalapis.github.Github.get_latest_release',
        patched_get_latest_release,
    )
    version_patch = patch(
        'rotkehlchen.utils.version_check.get_system_spec',
        patched_get_system_spec,
    )

    with version_patch, release_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'inforesource',
            ),
        )

    result = assert_proper_response_with_result(response)
    assert result == {
        'version': {
            'our_version': expected_version,
            'latest_version': None,
            'download_url': None,
        },
        'data_directory': str(rotki.data_dir),
        'log_level': 'DEBUG',
    }

    with version_patch, release_patch:
        response = requests.get(
            url=api_url_for(
                rotkehlchen_api_server,
                'inforesource',
            ),
            params={
                'check_for_updates': True,
            },
        )

    result = assert_proper_response_with_result(response)
    assert result == {
        'version': {
            'our_version': expected_version,
            'latest_version': expected_version,
            'download_url': None,
        },
        'data_directory': str(rotki.data_dir),
        'log_level': 'DEBUG',
    }


def test_query_ping(rotkehlchen_api_server):
    """Test that the ping endpoint works"""
    expected_result = True
    expected_message = ''

    response = requests.get(api_url_for(rotkehlchen_api_server, "pingresource"))
    assert_proper_response(response)
    response_json = response.json()
    assert len(response_json) == 2
    assert response_json['result'] == expected_result
    assert response_json['message'] == expected_message


def test_query_version_when_update_required(rotkehlchen_api_server):
    """
    Test that endpoint to query app version and available updates works
    when a new version is available.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    def patched_get_latest_release(_klass):
        new_latest = 'v99.99.99'
        return new_latest, f'https://github.com/rotki/rotki/releases/tag/{new_latest}'

    release_patch = patch(
        'rotkehlchen.externalapis.github.Github.get_latest_release',
        patched_get_latest_release,
    )
    with release_patch:
        response = requests.get(
            url=api_url_for(
                rotkehlchen_api_server,
                'inforesource',
            ),
            params={
                'check_for_updates': True,
            },
        )

    result = assert_proper_response_with_result(response)
    our_version = get_system_spec()['rotkehlchen']
    assert result == {
        'version': {
            'our_version': our_version,
            'latest_version': 'v99.99.99',
            'download_url': 'https://github.com/rotki/rotki/releases/tag/v99.99.99',
        },
        'data_directory': str(rotki.data_dir),
        'log_level': 'DEBUG',
    }


def test_manage_ethereum_nodes(rotkehlchen_api_server):
    """Test that list of nodes can be correctly updated and queried"""
    expected_message = ''
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "ethereumnodesresource"),
        json={'nodes': [
            {
                'name': node.node_info.name,
                'endpoint': node.node_info.endpoint,
                'owned': node.node_info.owned,
            }
            for node in WEIGHTED_ETHEREUM_NODES if node.node_info.name != ETHERSCAN_NODE_NAME
        ]},
    )
    assert_proper_response(response)
    response = requests.get(api_url_for(rotkehlchen_api_server, "ethereumnodesresource"))
    assert_proper_response(response)
    response_json = response.json()
    assert len(response_json['result']) == len(WEIGHTED_ETHEREUM_NODES)
    assert response_json['result'] == [node.node_info.serialize() for node in WEIGHTED_ETHEREUM_NODES]  # noqa: E501
    assert response_json['message'] == expected_message

    # Try to add etherscan as node
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "ethereumnodesresource"),
        json={'nodes': [
            {
                'name': 'etherscan',
                'endpoint': 'ewarwae',
                'owned': False,
            },
        ]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='name can\'t be etherscan',
        status_code=HTTPStatus.BAD_REQUEST,
    )
