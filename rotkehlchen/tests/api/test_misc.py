import logging
import os
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.chain.ethereum.constants import ETHEREUM_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.evm.types import NodeName
from rotkehlchen.constants.misc import DEFAULT_MAX_LOG_BACKUP_FILES, DEFAULT_SQL_VM_INSTRUCTIONS_CB
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import ChainID, Location, SupportedBlockchain
from rotkehlchen.utils.misc import get_system_spec

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def generate_expected_info(
        expected_version: str,
        data_dir: Path,
        latest_version: str | None = None,
        accept_docker_risk: bool = False,
        download_url: str | None = None,
) -> dict[str, Any]:
    return {
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


def test_query_info_version_when_up_to_date(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that endpoint to query the rotki version works if no new version is available"""
    expected_version = '1.1.0'
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    def patched_get_system_spec() -> dict[str, Any]:
        return {'rotkehlchen': f'v{expected_version}'}

    def patched_get_latest_release(_klass: Any) -> tuple[str, str]:
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

    result = assert_proper_sync_response_with_result(response)
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

    result = assert_proper_sync_response_with_result(response)
    assert result == generate_expected_info(expected_version, rotki.data_dir, latest_version=expected_version)  # noqa: E501

    with version_patch, release_patch, patch.dict(os.environ, {'ROTKI_ACCEPT_DOCKER_RISK': 'whatever'}):  # noqa: E501
        response = requests.get(
            url=api_url_for(
                rotkehlchen_api_server,
                'inforesource',
            ),
        )

    result = assert_proper_sync_response_with_result(response)
    assert result == generate_expected_info(
        expected_version=expected_version,
        data_dir=rotki.data_dir,
        accept_docker_risk=True,
    )


def test_query_ping(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that the ping endpoint works"""
    expected_result = True
    expected_message = ''

    response = requests.get(api_url_for(rotkehlchen_api_server, 'pingresource'))
    assert_proper_response(response)
    response_json = response.json()
    assert len(response_json) == 2
    assert response_json['result'] == expected_result
    assert response_json['message'] == expected_message


def test_query_version_when_update_required(rotkehlchen_api_server: 'APIServer') -> None:
    """
    Test that endpoint to query app version and available updates works
    when a new version is available.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    def patched_get_latest_release(_klass: Any) -> tuple[str, str]:
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

    result = assert_proper_sync_response_with_result(response)
    our_version = get_system_spec()['rotkehlchen']
    assert result == generate_expected_info(
        expected_version=our_version,
        data_dir=rotki.data_dir,
        latest_version='99.99.99',
        download_url='https://github.com/rotki/rotki/releases/tag/v99.99.99',
    )


@pytest.mark.parametrize('ethereum_manager_connect_at_start', ['DEFAULT'])
def test_manage_nodes(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that list of nodes can be correctly updated and queried"""
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    blockchain = SupportedBlockchain.ETHEREUM
    blockchain_key = blockchain.serialize()
    nodes_at_start = len(database.get_rpc_nodes(blockchain=blockchain, only_active=True))
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result) == 7
    for node in result:
        if node['name'] != ETHEREUM_ETHERSCAN_NODE_NAME:
            assert node['endpoint'] != ''
        else:
            assert node['identifier'] == 1
        if node['active']:
            assert node['weight'] != 0

    # try to delete a node
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
        json={'identifier': 1},
    )
    assert_proper_response(response)
    # check that is not anymore in the returned list
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
    )
    result = assert_proper_sync_response_with_result(response)
    assert not any(node['name'] == 'cloudflare' for node in result)

    # now try to add it again
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
        json={
            'name': 'cloudflare',
            'endpoint': 'https://cloudflare-eth.com/',
            'owned': False,
            'weight': '20',
            'active': True,
        },
    )
    assert_proper_response(response)
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
    )
    result = assert_proper_sync_response_with_result(response)
    for node in result:
        if node['name'] == 'cloudflare':
            assert FVal(node['weight']) == 20
            assert node['active'] is True
            assert node['endpoint'] == 'https://cloudflare-eth.com/'
            assert node['owned'] is False
            assert node['blockchain'] == blockchain_key
            break

    # Try to add an empty name
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
        json={
            'name': '',
            'endpoint': '1inch.io',
            'owned': False,
            'weight': '0.3',
            'active': True,
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg="Name can't be empty",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # try to edit an unknown node
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
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
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
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
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
    )
    result = assert_proper_sync_response_with_result(response)
    for node in result:
        if node['identifier'] == 4:
            assert FVal(node['weight']) == 20
            assert node['name'] == 'ankr'
            assert node['active'] is True
            assert node['endpoint'] == 'ewarwae'
            assert node['owned'] is True
            assert node['blockchain'] == blockchain_key
            break

    # try to edit a node's name
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
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
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
    )
    result = assert_proper_sync_response_with_result(response)
    for node in result:
        if node['identifier'] == 4:
            assert FVal(node['weight']) == 20
            assert node['name'] == 'anchor'
            assert node['active'] is True
            assert node['endpoint'] == 'ewarwae'
            assert node['owned'] is True
            assert node['blockchain'] == blockchain_key
            break

    # add a new node with duplicated endpoint/chain, should fail due to constraint in the db
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
        json={
            'name': 'my_super_node',
            'endpoint': 'ewarwae',
            'owned': True,
            'weight': '0.3',
            'active': True,
        },
    )
    result = assert_error_response(
        response=response,
        contained_in_msg='Node for ethereum with endpoint ewarwae already exists in db',
        status_code=HTTPStatus.CONFLICT,
    )
    # add a new node that should be correct
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
        json={
            'name': 'my_super_node',
            'endpoint': 'ewarwae.com',
            'owned': True,
            'weight': '0.3',
            'active': True,
        },
    )
    result = assert_proper_sync_response_with_result(response)

    # set active to false and see that we have the expected amount of nodes
    with database.conn.read_ctx() as cursor:
        target_id = cursor.execute(
            "SELECT identifier from rpc_nodes WHERE name='my_super_node'",
        ).fetchone()[0]

    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
        json={
            'identifier': target_id,
            'name': 'myetherwallet',
            'endpoint': 'https://https://nodes.mewapi.io/rpc/eth.cloud.ava.do/',
            'owned': False,
            'weight': '10',
            'active': False,
        },
    )
    assert nodes_at_start - len(database.get_rpc_nodes(blockchain=blockchain, only_active=True)) == 0  # noqa: E501
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
    )
    result = assert_proper_sync_response_with_result(response)
    # Check that the rebalancing didn't get affected by the owned node
    for node in result:
        if node['name'] == 'anchor':
            assert FVal(node['weight']) == 20
            break

    # and now let's replicate https://github.com/rotki/rotki/issues/4769 by
    # editing all nodes to have 0% weight.
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=blockchain_key),
    )
    result = assert_proper_sync_response_with_result(response)
    for node in result:
        response = requests.patch(
            api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain=node['blockchain']),
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
def test_configuration(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that the configuration endpoint returns the expected information"""
    response = requests.get(api_url_for(rotkehlchen_api_server, 'configurationsresource'))
    result = assert_proper_sync_response_with_result(response)
    assert result['max_size_in_mb_all_logs']['value'] == 659
    assert result['max_size_in_mb_all_logs']['is_default'] is False
    assert result['max_logfiles_num']['is_default'] is True
    assert result['max_logfiles_num']['value'] == DEFAULT_MAX_LOG_BACKUP_FILES
    assert result['sqlite_instructions']['is_default'] is True
    assert result['sqlite_instructions']['value'] == DEFAULT_SQL_VM_INSTRUCTIONS_CB
    assert result['loglevel']['value'] == 'DEBUG'
    assert result['loglevel']['is_default'] is True


def test_update_log_level(
        rotkehlchen_api_server: 'APIServer',
        caplog: pytest.LogCaptureFixture,
) -> None:
    """Test updating log level via configuration endpoint"""
    assert_error_response(  # Test invalid log level
        response=requests.put(
            api_url_for(rotkehlchen_api_server, 'configurationsresource'),
            json={'loglevel': 'invalid'},
        ),
        contained_in_msg='Invalid log level',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    assert assert_proper_sync_response_with_result(requests.put(  # Switch to trace level
        api_url_for(rotkehlchen_api_server, 'configurationsresource'),
        json={'loglevel': (given_loglevel := 'TRACE')},
    ))['loglevel']['value'] == given_loglevel

    logger = logging.getLogger('rotkehlchen.test')
    logger.trace('Test trace message')  # type: ignore[attr-defined]
    assert 'Test trace message' in caplog.text


def test_query_all_chain_ids(rotkehlchen_api_server: 'APIServer') -> None:
    response = requests.get(api_url_for(rotkehlchen_api_server, 'allevmchainsresource'))
    result = assert_proper_sync_response_with_result(response)
    for chain in ChainID:
        name, label = chain.name_and_label()
        assert {'id': chain.value, 'name': name, 'label': label} in result
    assert len(ChainID) == len(result)


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('added_exchanges', [(Location.KRAKEN, Location.BINANCE)])
def test_events_mappings(rotkehlchen_api_server_with_exchanges: 'APIServer') -> None:
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
    result = assert_proper_sync_response_with_result(response)
    assert 'global_mappings' in result
    assert result['entry_type_mappings'] == {
        'eth withdrawal event': {
            'staking': {
                'remove asset': {
                    'is_exit': 'stake exit',
                    'not_exit': 'withdraw',
                },
            },
        },
    }
    assert 'event_category_details' in result
    assert 'accounting_events_icons' in result
    received_accounting_event_types = {
        AccountingEventType.deserialize(event_type)
        for event_type in result['accounting_events_icons']
    }
    assert received_accounting_event_types == set(AccountingEventType)

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'locationresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    excluded_locations = {Location.TOTAL}
    valid_locations = {location.serialize() for location in Location if location not in excluded_locations}  # noqa: E501
    assert set(result['locations'].keys()) == valid_locations
    for detail in result['locations'].values():
        assert 'icon' in detail or 'image' in detail


@pytest.mark.parametrize('have_decoders', [True])
def test_counterparties(rotkehlchen_api_server_with_exchanges: 'APIServer') -> None:
    """Test serialization of the counterparties"""
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'counterpartiesresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    for counterparty_details in result:
        assert 'identifier' in counterparty_details
        assert 'label' in counterparty_details
        assert 'icon' in counterparty_details or 'image' in counterparty_details
        if counterparty_details['identifier'] == 'gas':
            assert counterparty_details['icon'] == 'lu-flame'
        elif counterparty_details['identifier'] == 'jupiter':
            assert counterparty_details['label'] == 'Jupiter'


@pytest.mark.parametrize('base_manager_connect_at_start', ['DEFAULT'])
@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address()]])
def test_connecting_to_node(rotkehlchen_api_server: 'APIServer') -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    base = rotki.chains_aggregator.base
    patched_connection = patch.object(
        base.node_inquirer,
        'attempt_connect',
        lambda *args, **kwargs: (True, ''),
    )
    assert len(base.node_inquirer.get_connected_nodes()) == 0

    with patched_connection:
        rpc_url = api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='base')
        response = requests.post(url=rpc_url, json={'identifier': 28})
        assert_proper_sync_response_with_result(response)

        # check case of a bad identifier
        response = requests.post(url=rpc_url, json={'identifier': 999})
        assert_error_response(
            response=response,
            contained_in_msg='RPC node not found',
            status_code=HTTPStatus.BAD_REQUEST,
        )

        # check connecting to a non evm node
        response = requests.post(
            url=api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='ksm'),
            json={'identifier': 999},
        )
        assert_error_response(
            response=response,
            contained_in_msg='kusama nodes are connected at login',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    connected_nodes = []

    def custom_connect(node: NodeName) -> tuple[bool, str]:
        connected_nodes.append(node.name)
        return True, ''

    with patch.object(
        base.node_inquirer,
        'attempt_connect',
        custom_connect,
    ):  # connect to all the nodes
        rpc_url = api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='base')
        response = requests.post(url=rpc_url)
        assert_proper_sync_response_with_result(response)
        assert len(connected_nodes) >= 4

    with patch.object(
        base.node_inquirer,
        'attempt_connect',
        lambda *args, **kwargs: (False, 'Custom error'),
    ):
        # check error during connection
        rpc_url = api_url_for(rotkehlchen_api_server, 'rpcnodesresource', blockchain='base')
        response = requests.post(url=rpc_url, json={'identifier': 28})
        assert response.json()['result'] == {
            'errors': [{'name': 'dRPC', 'error': 'Custom error'}],
        }
        assert response.status_code == HTTPStatus.OK
