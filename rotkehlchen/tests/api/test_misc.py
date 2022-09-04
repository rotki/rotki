from http import HTTPStatus
from typing import Any, Dict
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.ethereum.types import ETHERSCAN_NODE_NAME
from rotkehlchen.constants.misc import DEFAULT_MAX_LOG_BACKUP_FILES, DEFAULT_SQL_VM_INSTRUCTIONS_CB
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.types import SupportedBlockchain
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

    response = requests.get(api_url_for(rotkehlchen_api_server, 'pingresource'))
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
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    blockchain = SupportedBlockchain.ETHEREUM
    nodes_at_start = len(database.get_web3_nodes(blockchain=blockchain, only_active=True))
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    assert len(result) == 7
    for node in result:
        if node['name'] != ETHERSCAN_NODE_NAME:
            assert node['endpoint'] != ''
        else:
            assert node['identifier'] == 1
        if node['active']:
            assert node['weight'] != 0

    # try to delete a node
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
        json={'identifier': 5},
    )
    assert_proper_response(response)
    # check that is not anymore in the returned list
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    assert not any([node['name'] == '1inch' for node in result])

    # now try to add it again
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
        json={
            'name': '1inch',
            'endpoint': 'https://web3.1inch.exchange',
            'owned': False,
            'weight': '15',
            'active': True,
        },
    )
    assert_proper_response(response)
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    for node in result:
        if node['name'] == '1inch':
            assert FVal(node['weight']) == 15
            assert node['active'] is True
            assert node['endpoint'] == 'https://web3.1inch.exchange'
            assert node['owned'] is False
            assert node['blockchain'] == 'ETH'
            break

    # Try to add etherscan as node
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
        json={
            'name': 'etherscan',
            'endpoint': 'ewarwae',
            'owned': False,
            'weight': '0.3',
            'active': True,
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Name can\'t be empty or etherscan',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # try to edit an unknown node
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
        json={
            'identifier': 666,
            'name': '1inch',
            'endpoint': 'ewarwae',
            'owned': True,
            'weight': '40',
            'active': True,
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg="Node with identifier 666 doesn't exist",
        status_code=HTTPStatus.CONFLICT,
    )

    # try to edit a node's endpoint
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
        json={
            'identifier': 8,
            'name': '1inch',
            'endpoint': 'ewarwae',
            'owned': True,
            'weight': '40',
            'active': True,
        },
    )
    assert_proper_response(response)
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    for node in result:
        if node['identifier'] == 8:
            assert FVal(node['weight']) == 40
            assert node['name'] == '1inch'
            assert node['active'] is True
            assert node['endpoint'] == 'ewarwae'
            assert node['owned'] is True
            assert node['blockchain'] == 'ETH'
            break

    # try to edit a node's name
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
        json={
            'identifier': 8,
            'name': 'oneinch',
            'endpoint': 'ewarwae',
            'owned': True,
            'weight': '40',
            'active': True,
        },
    )
    assert_proper_response(response)
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    for node in result:
        if node['identifier'] == 8:
            assert FVal(node['weight']) == 40
            assert node['name'] == 'oneinch'
            assert node['active'] is True
            assert node['endpoint'] == 'ewarwae'
            assert node['owned'] is True
            assert node['blockchain'] == 'ETH'
            break

    result = assert_proper_response_with_result(response)
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
        json={
            'name': 'my_super_node',
            'endpoint': 'ewarwae',
            'owned': True,
            'weight': '0.3',
            'active': True,
        },
    )
    # set owned to false and see that we have the expected amount of nodes
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
        json={
            'identifier': 4,
            'name': 'avado pool',
            'endpoint': 'https://mainnet.eth.cloud.ava.do/',
            'owned': False,
            'weight': '0',
            'active': False,
        },
    )
    assert nodes_at_start - len(database.get_web3_nodes(blockchain=blockchain, only_active=True)) == 0  # noqa: E501
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    # Check that the rebalancing didn't get affected by the owned node
    for node in result:
        if node['name'] == '1inch':
            assert FVal(node['weight']) == 40
            break

    # Try to edit etherscan weight
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
        json={
            'identifier': 1,
            'name': 'etherscan',
            'endpoint': '',
            'owned': False,
            'weight': '20',
            'active': True,
        },
    )
    assert_proper_response_with_result(response)

    # and now let's replicate https://github.com/rotki/rotki/issues/4769 by
    # editing all nodes to have 0% weight.
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    for node in result:
        response = requests.patch(
            api_url_for(rotkehlchen_api_server, 'web3nodesresource', blockchain=node['blockchain']),  # noqa: E501
            json={
                'identifier': node['identifier'],
                'name': node['name'],
                'endpoint': node['endpoint'],
                'owned': node['owned'],
                'weight': '0',
                'active': node['active'],
            },
        )
        assert_proper_response(response)


@pytest.mark.parametrize('max_size_in_mb_all_logs', [659])
def test_configuration(rotkehlchen_api_server):
    """Test that the configuration endpoint returns the expected information"""
    response = requests.get(api_url_for(rotkehlchen_api_server, 'configurationsresource'))
    result = assert_proper_response_with_result(response)
    assert result['max_size_in_mb_all_logs']['value'] == 659
    assert result['max_size_in_mb_all_logs']['is_default'] is False
    assert result['max_logfiles_num']['is_default'] is True
    assert result['max_logfiles_num']['value'] == DEFAULT_MAX_LOG_BACKUP_FILES
    assert result['sqlite_instructions']['is_default'] is True
    assert result['sqlite_instructions']['value'] == DEFAULT_SQL_VM_INSTRUCTIONS_CB
