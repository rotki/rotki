import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import Location, SupportedBlockchain
from rotkehlchen.utils.misc import ts_now


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_query_periodic(rotkehlchen_api_server_with_exchanges: APIServer) -> None:
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
    setup = setup_balances(rotki, ethereum_accounts=[], btc_accounts=[])
    start_ts = ts_now()
    assert setup.binance_patch is not None
    assert setup.poloniex_patch is not None
    # Query trades of an exchange to get them saved in the DB
    with setup.binance_patch, setup.poloniex_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ), json={'save_data': True},
        )
    assert_proper_response(response)

    response = requests.get(
        periodic_url := api_url_for(rotkehlchen_api_server_with_exchanges, 'periodicdataresource'),
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result) == 3
    assert result[DBCacheStatic.LAST_BALANCE_SAVE.value] >= start_ts
    assert 'failed_to_connect' not in result
    connected_nodes = result['connected_nodes']
    assert len(connected_nodes) == len(list(rotki.chains_aggregator.iterate_chain_managers_with_nodes()))  # noqa: E501
    for chain_manager in rotki.chains_aggregator.iterate_chain_managers_with_nodes():
        assert connected_nodes[chain_manager.node_inquirer.blockchain.serialize()] == []
    # Non -1 value tests for these exist in test_history.py::test_query_history_timerange
    assert result[DBCacheStatic.LAST_DATA_UPLOAD_TS.value] == 0

    rotki.data.db.add_rpc_node(WeightedNode(
        identifier=100,
        node_info=NodeName(
            name='rate_limited_node',
            endpoint='https://rate-limited.example.com',
            owned=False,
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
        weight=FVal('0.3'),
        active=True,
    ))
    rotki.chains_aggregator.ethereum.node_inquirer.invalidate_nodes_cache()
    rotki.chains_aggregator.ethereum.node_inquirer.failed_to_connect_nodes.add('custom node')
    rotki.chains_aggregator.ethereum.node_inquirer.mark_node_rate_limited(
        next(
            iter(rotki.chains_aggregator.ethereum.node_inquirer._get_configured_nodes()),
        ).node_info,
        '429',
    )
    response = requests.get(periodic_url)
    result = assert_proper_sync_response_with_result(response)
    assert result['failed_to_connect'] == {'eth': ['custom node']}
    assert len(result['cooling_down_nodes']['eth']) == 1
