import pytest
import requests

from rotkehlchen.chain.substrate.typing import SubstrateOwnNodeName
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response
from rotkehlchen.tests.utils.substrate import TEST_KUSAMA_NODES


def test_set_own_rpc_endpoint(rotkehlchen_api_server):
    """Test that successfully setting an own node (via `ksm_rpc_endpoint` setting)
    updates the `available_node_attributes_map` with the own node item, and
    sets the `own_rpc_endpoint` property.

    NB: `set_rpc_endpoint()` is synchronous therefore no need to sleep/wait.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    kusama_manager = rotki.chain_manager.kusama

    # Property does not exist if own node is not connected
    assert not hasattr(kusama_manager, 'own_rpc_endpoint')
    assert len(kusama_manager.available_node_attributes_map) == 0

    # Set ksm_rpc_endpoint with a reliable endpoint (e.g. Parity)
    test_node_endpoint = TEST_KUSAMA_NODES[0].endpoint()
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "settingsresource"),
        json={'settings': {'ksm_rpc_endpoint': test_node_endpoint}},
    )

    # Check settings response
    assert_proper_response(response)
    json_data = response.json()
    result = json_data['result']
    assert result['ksm_rpc_endpoint'] == test_node_endpoint

    # Check SubstrateManager instance
    assert kusama_manager.own_rpc_endpoint == test_node_endpoint
    assert len(kusama_manager.available_node_attributes_map) == 1
    assert SubstrateOwnNodeName.OWN in kusama_manager.available_node_attributes_map


@pytest.mark.parametrize('ksm_rpc_endpoint', [TEST_KUSAMA_NODES[0].endpoint()])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [[SubstrateOwnNodeName.OWN]])
def test_unset_own_rpc_endpoint(ksm_rpc_endpoint, rotkehlchen_api_server):
    """Test that unsetting the own node (via `ksm_rpc_endpoint` setting) removes
    it from `available_node_attributes_map`, and sets the `own_rpc_endpoint`
    property to empty string.

    NB: `set_rpc_endpoint()` is synchronous therefore no need to sleep/wait.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    kusama_manager = rotki.chain_manager.kusama

    # Property exists (own node connected)
    assert kusama_manager.own_rpc_endpoint == ksm_rpc_endpoint
    assert len(kusama_manager.available_node_attributes_map) == 1
    assert SubstrateOwnNodeName.OWN in kusama_manager.available_node_attributes_map

    # Unset ksm_rpc_endpoint
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "settingsresource"),
        json={'settings': {'ksm_rpc_endpoint': ''}},
    )

    # Check settings response
    assert_proper_response(response)
    json_data = response.json()
    result = json_data['result']
    assert result['ksm_rpc_endpoint'] == ''

    # Check SubstrateManager instance
    assert kusama_manager.own_rpc_endpoint == ''
    assert len(kusama_manager.available_node_attributes_map) == 0
