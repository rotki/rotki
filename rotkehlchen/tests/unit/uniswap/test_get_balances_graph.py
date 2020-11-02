import pytest

from rotkehlchen.chain.ethereum.uniswap.typing import ProtocolBalance

from .utils import (
    EXP_LIQUIDITY_POOL_1,
    EXP_LIQUIDITY_POOL_2,
    EXP_KNOWN_ASSETS_1,
    EXP_KNOWN_ASSETS_2,
    EXP_UNKNOWN_ASSETS_1,
    EXP_UNKNOWN_ASSETS_2,
    LIQUIDITY_POSITION_1,
    LIQUIDITY_POSITION_2,
    TEST_ADDRESS_1,
    TEST_ADDRESS_2,
    TEST_ADDRESS_3,
    store_call_args,
)


def test_single_address_balance(uniswap_module):
    """Test <ProtocolBalance> contains the following data:

        - TEST_ADDRESS_1: has 1 LP (LIQUIDITY_POSITION_1)
    """
    def fake_graph_query(
        *args,  # pylint: disable=unused-argument
        **kwargs,  # pylint: disable=unused-argument
    ):
        return {'liquidityPositions': [LIQUIDITY_POSITION_1]}

    addresses = [TEST_ADDRESS_1]

    # Main call
    protocol_balance = uniswap_module._get_balances_graph(
        addresses=addresses,
        graph_query=fake_graph_query,
    )

    exp_protocol_balance = ProtocolBalance(
        address_balances={TEST_ADDRESS_1: [EXP_LIQUIDITY_POOL_1]},
        known_assets=EXP_KNOWN_ASSETS_1,
        unknown_assets=EXP_UNKNOWN_ASSETS_1,
    )
    assert exp_protocol_balance == protocol_balance


def test_multiple_addresses_balances(uniswap_module):
    """Test <ProtocolBalance> contains the following data:

        - TEST_ADDRESS_1: has 1 LP (LIQUIDITY_POSITION_1)
        - TEST_ADDRESS_2: has 1 LP (LIQUIDITY_POSITION_2)
        - TEST_ADDRESS_3: has no LP ([])
    """
    def fake_graph_query(
        *args,  # pylint: disable=unused-argument
        **kwargs,  # pylint: disable=unused-argument
    ):
        return {
            'liquidityPositions': [LIQUIDITY_POSITION_1, LIQUIDITY_POSITION_2],
        }

    addresses = [TEST_ADDRESS_1, TEST_ADDRESS_2, TEST_ADDRESS_3]

    # Main call
    protocol_balance = uniswap_module._get_balances_graph(
        addresses=addresses,
        graph_query=fake_graph_query,
    )

    exp_protocol_balance = ProtocolBalance(
        address_balances={
            TEST_ADDRESS_1: [EXP_LIQUIDITY_POOL_1],
            TEST_ADDRESS_2: [EXP_LIQUIDITY_POOL_2],
            TEST_ADDRESS_3: [],
        },
        known_assets=EXP_KNOWN_ASSETS_1.union(EXP_KNOWN_ASSETS_2),
        unknown_assets=EXP_UNKNOWN_ASSETS_1.union(EXP_UNKNOWN_ASSETS_2),
    )
    assert exp_protocol_balance == protocol_balance


@pytest.mark.parametrize("graph_query_limit, no_requests", [(2, 2), (3, 1)])
def test_pagination(
        uniswap_module,
        graph_query_limit,
        no_requests,
        patch_graph_query_limit,  # pylint: disable=unused-argument
):
    """Test an extra graph request is done when the number of items in the
    response equals GRAPH_QUERY_LIMIT.
    """
    def get_graph_response():
        responses = [
            # First response
            {'liquidityPositions': [LIQUIDITY_POSITION_1, LIQUIDITY_POSITION_2]},
            # Second response
            {'liquidityPositions': []},
        ]
        for response in responses:
            yield response

    @store_call_args
    def fake_graph_query(
        *args,  # pylint: disable=unused-argument
        **kwargs,  # pylint: disable=unused-argument
    ):
        return next(get_response)

    addresses = [TEST_ADDRESS_1, TEST_ADDRESS_2]
    get_response = get_graph_response()

    # Main call
    uniswap_module._get_balances_graph(
        addresses=addresses,
        graph_query=fake_graph_query,
    )

    assert len(fake_graph_query.calls) == no_requests

    # Check limit and offset
    for idx, call_args in enumerate(fake_graph_query.calls):
        param_values = call_args['kwargs']['param_values']
        assert param_values['limit'] == graph_query_limit
        assert param_values['offset'] == idx * graph_query_limit
