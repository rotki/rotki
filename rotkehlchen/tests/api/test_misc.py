import os
from http import HTTPStatus
from pathlib import Path
from typing import Any, Optional
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.ethereum.constants import ETHEREUM_ETHERSCAN_NODE_NAME
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import DEFAULT_MAX_LOG_BACKUP_FILES, DEFAULT_SQL_VM_INSTRUCTIONS_CB
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.types import ChainID, Location, SupportedBlockchain
from rotkehlchen.utils.misc import get_system_spec


def generate_expected_info(
        expected_version: str,
        data_dir: Path,
        latest_version: Optional[str] = None,
        accept_docker_risk: bool = False,
        download_url: Optional[str] = None,
):
    result = {
        'version': {
            'our_version': expected_version,
            'latest_version': latest_version,
            'download_url': download_url,
        },
        'data_directory': str(data_dir),
        'log_level': 'DEBUG',
        'accept_docker_risk': accept_docker_risk,
        'backend_default_arguments': {
            'max_logfiles_num': 3,
            'max_size_in_mb_all_logs': 300,
            'sqlite_instructions': 5000,
        },
    }
    return result


def test_query_info_version_when_up_to_date(rotkehlchen_api_server):
    """Test that endpoint to query the rotki version works if no new version is available"""
    expected_version = 'v1.1.0'
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    def patched_get_system_spec() -> dict[str, Any]:
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
    assert result == generate_expected_info(expected_version, rotki.data_dir)

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
    assert result == generate_expected_info(expected_version, rotki.data_dir, latest_version=expected_version)  # noqa: E501

    with version_patch, release_patch, patch.dict(os.environ, {'ROTKI_ACCEPT_DOCKER_RISK': 'whatever'}):  # noqa: E501
        response = requests.get(
            url=api_url_for(
                rotkehlchen_api_server,
                'inforesource',
            ),
        )

    result = assert_proper_response_with_result(response)
    assert result == generate_expected_info(
        expected_version=expected_version,
        data_dir=rotki.data_dir,
        accept_docker_risk=True,
    )


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
    assert result == generate_expected_info(
        expected_version=our_version,
        data_dir=rotki.data_dir,
        latest_version='v99.99.99',
        download_url='https://github.com/rotki/rotki/releases/tag/v99.99.99',
    )


def test_manage_ethereum_nodes(rotkehlchen_api_server):
    """Test that list of nodes can be correctly updated and queried"""
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    blockchain = SupportedBlockchain.ETHEREUM
    nodes_at_start = len(database.get_rpc_nodes(blockchain=blockchain, only_active=True))
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    assert len(result) == 5
    for node in result:
        if node['name'] != ETHEREUM_ETHERSCAN_NODE_NAME:
            assert node['endpoint'] != ''
        else:
            assert node['identifier'] == 1
        if node['active']:
            assert node['weight'] != 0

    # try to delete a node
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
        json={'identifier': 2},
    )
    assert_proper_response(response)
    # check that is not anymore in the returned list
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    assert not any(node['name'] == 'cloudflare' for node in result)

    # now try to add it again
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
        json={
            'name': 'cloudflae',
            'endpoint': 'https://cloudflare-eth.com/',
            'owned': False,
            'weight': '20',
            'active': True,
        },
    )
    assert_proper_response(response)
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    for node in result:
        if node['name'] == 'cloudflare':
            assert FVal(node['weight']) == 20
            assert node['active'] is True
            assert node['endpoint'] == 'https://cloudflare-eth.com/'
            assert node['owned'] is False
            assert node['blockchain'] == 'ETH'
            break

    # Try to add etherscan as node
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
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
        contained_in_msg="Name can't be empty or etherscan",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # try to edit an unknown node
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
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
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
        json={
            'identifier': 4,
            'name': 'ankr',
            'endpoint': 'ewarwae',
            'owned': True,
            'weight': '20',
            'active': True,
        },
    )
    assert_proper_response(response)
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    for node in result:
        if node['identifier'] == 4:
            assert FVal(node['weight']) == 20
            assert node['name'] == 'ankr'
            assert node['active'] is True
            assert node['endpoint'] == 'ewarwae'
            assert node['owned'] is True
            assert node['blockchain'] == 'ETH'
            break

    # try to edit a node's name
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
        json={
            'identifier': 4,
            'name': 'anchor',
            'endpoint': 'ewarwae',
            'owned': True,
            'weight': '20',
            'active': True,
        },
    )
    assert_proper_response(response)
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    for node in result:
        if node['identifier'] == 4:
            assert FVal(node['weight']) == 20
            assert node['name'] == 'anchor'
            assert node['active'] is True
            assert node['endpoint'] == 'ewarwae'
            assert node['owned'] is True
            assert node['blockchain'] == 'ETH'
            break

    # add a new node
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
        json={
            'name': 'my_super_node',
            'endpoint': 'ewarwae',
            'owned': True,
            'weight': '0.3',
            'active': True,
        },
    )
    result = assert_proper_response_with_result(response)
    # set owned to false and see that we have the expected amount of nodes
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
        json={
            'identifier': 5,
            'name': 'myetherwallet',
            'endpoint': 'https://https://nodes.mewapi.io/rpc/eth.cloud.ava.do/',
            'owned': False,
            'weight': '10',
            'active': False,
        },
    )
    assert nodes_at_start - len(database.get_rpc_nodes(blockchain=blockchain, only_active=True)) == 0  # noqa: E501
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    # Check that the rebalancing didn't get affected by the owned node
    for node in result:
        if node['name'] == 'anchor':
            assert FVal(node['weight']) == 20
            break

    # Try to edit etherscan weight
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
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
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ETH'),
    )
    result = assert_proper_response_with_result(response)
    for node in result:
        response = requests.patch(
            api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=node['blockchain']),  # noqa: E501
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


def test_query_supported_chains(rotkehlchen_api_server):
    response = requests.get(api_url_for(rotkehlchen_api_server, 'supportedchainsresource'))
    result = assert_proper_response_with_result(response)
    for entry in SupportedBlockchain:
        for result_entry in result:
            if (
                entry.value == result_entry['id'] and
                str(entry) == result_entry['name'] and
                entry.get_chain_type() == result_entry['type']
            ):
                if entry.is_evm() is True:
                    assert result_entry['evm_chain_name'] == entry.to_chain_id().to_name()
                if entry == SupportedBlockchain.OPTIMISM:
                    assert result_entry['native_asset'] == A_ETH.serialize()
                else:
                    assert 'native_asset' not in result_entry

                break  # found
        else:  # internal for loop found nothing
            raise AssertionError(f'Did not find {entry} in the supported chains result')


def test_query_all_chain_ids(rotkehlchen_api_server):
    response = requests.get(api_url_for(rotkehlchen_api_server, 'allevmchainsresource'))
    result = assert_proper_response_with_result(response)
    assert result == [{'id': chain.value, 'name': chain.to_name()} for chain in ChainID]


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('added_exchanges', [(Location.KRAKEN, Location.BINANCE)])
def test_events_mappings(rotkehlchen_api_server_with_exchanges):
    """
    Test different mappings and information that we provide for rendering events information
    - Test that the structure for types mappings is correctly generated
    - Test that the valid locations are correctly provided to the frontend
    """
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'typesmappingsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert 'per_protocol_mappings' in result
    assert 'global_mappings' in result
    assert 'event_category_details' in result
    assert result['exchange_mappings'].keys() == {'kraken'}
    assert {'trade', 'spend'}.issubset(result['exchange_mappings']['kraken'].keys())

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'locationresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    excluded_locations = {Location.TOTAL}
    valid_locations = {location.serialize() for location in Location if location not in excluded_locations}  # noqa: E501
    assert set(result['locations'].keys()) == valid_locations
    for detail in result['locations'].values():
        assert 'icon' in detail or 'image' in detail
