import pytest

from rotkehlchen.fval import FVal
from rotkehlchen.typing import Price

from .utils import A_CAR, A_SHL, TOKEN_DAY_DATA_CAR, TOKEN_DAY_DATA_SHL, store_call_args


def test_unknown_asset_does_not_have_usd_price(mock_uniswap):
    """Test returned `asset_price` is empty when the unknown asset price is
    not found via subgraph.
    """
    mock_uniswap.graph.query.return_value = {'tokenDayDatas': []}
    unknown_assets = {A_CAR}

    asset_price = mock_uniswap._get_unknown_asset_price_graph(unknown_assets=unknown_assets)

    assert asset_price == {}


def test_unknown_asset_has_usd_price(mock_uniswap):
    """Test returned `asset_price` contains the unknown token address and
    its USD price when the price is found via subgraph.
    """
    mock_uniswap.graph.query.return_value = {'tokenDayDatas': [TOKEN_DAY_DATA_CAR]}
    unknown_assets = {A_CAR}

    asset_price = mock_uniswap._get_unknown_asset_price_graph(unknown_assets=unknown_assets)

    exp_asset_price = {
        A_CAR.ethereum_address: Price(FVal(TOKEN_DAY_DATA_CAR['priceUSD'])),
    }
    assert asset_price == exp_asset_price


@pytest.mark.parametrize("graph_query_limit, no_requests", [(2, 2), (3, 1)])
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
            {'tokenDayDatas': [TOKEN_DAY_DATA_CAR, TOKEN_DAY_DATA_SHL]},
            # Second response
            {'tokenDayDatas': []},
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
    unknown_assets = {A_CAR, A_SHL}

    mock_uniswap._get_unknown_asset_price_graph(unknown_assets=unknown_assets)

    assert len(mock_response.calls) == no_requests
    for idx, call_args in enumerate(mock_response.calls):
        param_values = call_args['kwargs']['param_values']
        assert param_values['limit'] == graph_query_limit
        assert param_values['offset'] == idx * graph_query_limit
