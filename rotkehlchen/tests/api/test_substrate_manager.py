import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.substrate.types import KusamaNodeName
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.substrate import KUSAMA_TEST_RPC_ENDPOINT


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2025-11-09 17:00:00 GMT')
def test_set_unset_own_rpc_endpoint(rotkehlchen_api_server: APIServer) -> None:
    """Test that successfully setting/unsetting an own node (via `ksm_rpc_endpoint` setting)
    updates the `available_node_attributes_map`, sorts `available_nodes_call_order`,
    and sets the `own_rpc_endpoint` property.

    NB: `set_rpc_endpoint()` is synchronous therefore no need to sleep/wait.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    kusama_manager = rotki.chains_aggregator.kusama

    # No nodes connected
    assert kusama_manager.own_rpc_endpoint is None  # from `ksm_rpc_endpoint` fixture
    assert len(kusama_manager.available_node_attributes_map) == 0  # type: ignore
    assert len(kusama_manager.available_nodes_call_order) == 0

    # Set ksm_rpc_endpoint with a reliable endpoint (e.g. NOT Parity)
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'settingsresource'),
        json={'settings': {'ksm_rpc_endpoint': KUSAMA_TEST_RPC_ENDPOINT}},
    )

    # Check settings response
    result = assert_proper_sync_response_with_result(response)
    assert result['ksm_rpc_endpoint'] == KUSAMA_TEST_RPC_ENDPOINT

    # Check SubstrateManager instance
    assert kusama_manager.own_rpc_endpoint == KUSAMA_TEST_RPC_ENDPOINT
    assert len(kusama_manager.available_node_attributes_map) == 1
    assert len(kusama_manager.available_nodes_call_order) == 1
    assert KusamaNodeName.OWN in kusama_manager.available_node_attributes_map
    assert kusama_manager.available_nodes_call_order[0][0] == KusamaNodeName.OWN

    # Unset ksm_rpc_endpoint
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'settingsresource'),
        json={'settings': {'ksm_rpc_endpoint': ''}},
    )

    # Check settings response
    result = assert_proper_sync_response_with_result(response)
    assert result['ksm_rpc_endpoint'] == ''

    # Check SubstrateManager instance
    assert kusama_manager.own_rpc_endpoint == ''
    assert len(kusama_manager.available_node_attributes_map) == 0
    assert len(kusama_manager.available_nodes_call_order) == 0
