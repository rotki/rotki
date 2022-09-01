from unittest.mock import patch

import pytest

from rotkehlchen.chain.ethereum.modules.uniswap.uniswap import Uniswap
from rotkehlchen.premium.premium import Premium


@pytest.fixture(name='mock_graph')
def fixture_graph():
    with patch('rotkehlchen.chain.ethereum.modules.uniswap.uniswap.Graph'):
        yield


@pytest.fixture(name='mock_graph_query_limit')
def fixture_graph_query_limit(graph_query_limit):
    with patch(
        'rotkehlchen.chain.ethereum.interfaces.ammswap.ammswap.GRAPH_QUERY_LIMIT',
        new=graph_query_limit,
    ):
        yield


@pytest.fixture
def mock_uniswap(
        ethereum_manager,
        database,
        start_with_valid_premium,
        rotki_premium_credentials,
        function_scope_messages_aggregator,
        mock_graph,  # pylint: disable=unused-argument
) -> Uniswap:
    premium = None

    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    uniswap = Uniswap(
        ethereum_manager=ethereum_manager,
        database=database,
        premium=premium,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return uniswap
