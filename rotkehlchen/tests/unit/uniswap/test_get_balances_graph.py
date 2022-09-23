import pytest

from rotkehlchen.chain.ethereum.interfaces.ammswap.types import ProtocolBalance

from .utils import (
    EXP_KNOWN_ASSETS_1,
    EXP_KNOWN_ASSETS_2,
    EXP_UNKNOWN_ASSETS_1,
    EXP_UNKNOWN_ASSETS_2,
    LIQUIDITY_POSITION_1,
    LIQUIDITY_POSITION_2,
    TEST_ADDRESS_1,
    TEST_ADDRESS_2,
    TEST_ADDRESS_3,
    const_exp_liquidity_pool_1,
    const_exp_liquidity_pool_2,
    store_call_args,
)


def test_single_address_balance(mock_uniswap):
    """Test <ProtocolBalance> contains the following data:

        - TEST_ADDRESS_1: has 1 LP (LIQUIDITY_POSITION_1)
    """
    mock_uniswap.graph.query.return_value = {'liquidityPositions': [LIQUIDITY_POSITION_1]}
    addresses = [TEST_ADDRESS_1]

    protocol_balance = mock_uniswap._get_balances_graph(addresses=addresses)

    exp_protocol_balance = ProtocolBalance(
        address_balances={TEST_ADDRESS_1: [const_exp_liquidity_pool_1()]},
        known_assets=EXP_KNOWN_ASSETS_1,
        unknown_assets=EXP_UNKNOWN_ASSETS_1,
    )
    assert exp_protocol_balance == protocol_balance


def test_multiple_addresses_balances(mock_uniswap):
    """Test <ProtocolBalance> contains the following data:

        - TEST_ADDRESS_1: has 1 LP (LIQUIDITY_POSITION_1)
        - TEST_ADDRESS_2: has 1 LP (LIQUIDITY_POSITION_2)

    As TEST_ADDRESS_3 has no LPs is not included.
    """
    mock_uniswap.graph.query.return_value = {
        'liquidityPositions': [LIQUIDITY_POSITION_1, LIQUIDITY_POSITION_2],
    }
    addresses = [TEST_ADDRESS_1, TEST_ADDRESS_2, TEST_ADDRESS_3]

    protocol_balance = mock_uniswap._get_balances_graph(addresses=addresses)

    exp_protocol_balance = ProtocolBalance(
        address_balances={
            TEST_ADDRESS_1: [const_exp_liquidity_pool_1()],
            TEST_ADDRESS_2: [const_exp_liquidity_pool_2()],
        },
        known_assets=EXP_KNOWN_ASSETS_1.union(EXP_KNOWN_ASSETS_2),
        unknown_assets=EXP_UNKNOWN_ASSETS_1.union(EXP_UNKNOWN_ASSETS_2),
    )
    assert exp_protocol_balance == protocol_balance


@pytest.mark.parametrize('graph_query_limit, no_requests', [(2, 2), (3, 1)])
def test_pagination(
        mock_uniswap,
        graph_query_limit,
        no_requests,
        mock_graph_query_limit,  # pylint: disable=unused-argument
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
    def mock_response(
        *args,  # pylint: disable=unused-argument
        **kwargs,  # pylint: disable=unused-argument
    ):
        return next(get_response)

    get_response = get_graph_response()
    mock_uniswap.graph.query.side_effect = mock_response
    addresses = [TEST_ADDRESS_1, TEST_ADDRESS_2]

    mock_uniswap._get_balances_graph(addresses=addresses)

    assert len(mock_response.calls) == no_requests
    for idx, call_args in enumerate(mock_response.calls):
        param_values = call_args['kwargs']['param_values']
        assert param_values['limit'] == graph_query_limit
        assert param_values['offset'] == idx * graph_query_limit
