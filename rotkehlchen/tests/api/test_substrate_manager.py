import pytest
import requests
from flaky import flaky

from rotkehlchen.chain.substrate.types import KusamaNodeName
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result
from rotkehlchen.tests.utils.substrate import KUSAMA_TEST_NODES, SUBSTRATE_ACC1_KSM_ADDR


@flaky(max_runs=3, min_passes=1)  # Kusama open nodes some times time out
def test_set_own_rpc_endpoint(rotkehlchen_api_server):
    """Test that successfully setting an own node (via `ksm_rpc_endpoint` setting)
    updates the `available_node_attributes_map`, sorts `available_nodes_call_order`,
    and sets the `own_rpc_endpoint` property.

    NB: `set_rpc_endpoint()` is synchronous therefore no need to sleep/wait.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    kusama_manager = rotki.chains_aggregator.kusama

    # No nodes connected
    assert kusama_manager.own_rpc_endpoint is None  # from `ksm_rpc_endpoint` fixture
    assert len(kusama_manager.available_node_attributes_map) == 0
    assert len(kusama_manager.available_nodes_call_order) == 0

    # Set ksm_rpc_endpoint with a reliable endpoint (e.g. NOT Parity)
    test_node_endpoint = KUSAMA_TEST_NODES[1].endpoint()
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "settingsresource"),
        json={'settings': {'ksm_rpc_endpoint': test_node_endpoint}},
    )

    # Check settings response
    result = assert_proper_response_with_result(response)
    assert result['ksm_rpc_endpoint'] == test_node_endpoint

    # Check SubstrateManager instance
    assert kusama_manager.own_rpc_endpoint == test_node_endpoint
    assert len(kusama_manager.available_node_attributes_map) == 1
    assert len(kusama_manager.available_nodes_call_order) == 1
    assert KusamaNodeName.OWN in kusama_manager.available_node_attributes_map
    assert kusama_manager.available_nodes_call_order[0][0] == KusamaNodeName.OWN


@flaky(max_runs=3, min_passes=1)  # Kusama open nodes some times time out
@pytest.mark.parametrize('ksm_accounts', [[SUBSTRATE_ACC1_KSM_ADDR]])
@pytest.mark.parametrize('ksm_rpc_endpoint', [KUSAMA_TEST_NODES[1].endpoint()])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [[KusamaNodeName.OWN]])
def test_unset_own_rpc_endpoint(ksm_rpc_endpoint, rotkehlchen_api_server):
    """Test that unsetting the own node (via `ksm_rpc_endpoint` setting) removes
    it from `available_node_attributes_map` and `available_nodes_call_order`,
    and sets the `own_rpc_endpoint` property to empty string.

    NB: `set_rpc_endpoint()` is synchronous therefore no need to sleep/wait.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    kusama_manager = rotki.chains_aggregator.kusama

    # Property exists (own node connected)
    assert kusama_manager.own_rpc_endpoint == ksm_rpc_endpoint
    assert len(kusama_manager.available_node_attributes_map) == 1
    assert len(kusama_manager.available_nodes_call_order) == 1
    assert KusamaNodeName.OWN in kusama_manager.available_node_attributes_map
    assert kusama_manager.available_nodes_call_order[0][0] == KusamaNodeName.OWN

    # Unset ksm_rpc_endpoint
    response = requests.put(
        api_url_for(rotkehlchen_api_server, "settingsresource"),
        json={'settings': {'ksm_rpc_endpoint': ''}},
    )

    # Check settings response
    result = assert_proper_response_with_result(response)
    assert result['ksm_rpc_endpoint'] == ''

    # Check SubstrateManager instance
    assert kusama_manager.own_rpc_endpoint == ''
    assert len(kusama_manager.available_node_attributes_map) == 0
    assert len(kusama_manager.available_nodes_call_order) == 0
