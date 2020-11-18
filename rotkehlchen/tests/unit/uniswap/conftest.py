from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.chain.ethereum.uniswap.uniswap import Uniswap
from rotkehlchen.premium.premium import Premium


@pytest.fixture
def uniswap_module(
        ethereum_manager,
        database,
        start_with_valid_premium,
        rotki_premium_credentials,
        function_scope_messages_aggregator,
        data_dir,
) -> Uniswap:
    premium = None

    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    uniswap = Uniswap(
        ethereum_manager=ethereum_manager,
        database=database,
        premium=premium,
        msg_aggregator=function_scope_messages_aggregator,
        data_directory=data_dir,
    )
    return uniswap


@pytest.fixture
def patch_graph_query_limit(graph_query_limit):
    with patch(
        'rotkehlchen.chain.ethereum.uniswap.uniswap.GRAPH_QUERY_LIMIT',
        new_callable=MagicMock(return_value=graph_query_limit),
    ):
        yield
