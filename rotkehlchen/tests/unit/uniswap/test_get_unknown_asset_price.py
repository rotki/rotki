import pytest

from rotkehlchen.fval import FVal
from rotkehlchen.typing import Price

from .utils import ASSET_SHUF, ASSET_TGX, TOKEN_DAY_DATA_SHUF, TOKEN_DAY_DATA_TGX, store_call_args


def test_unknown_asset_does_not_have_usd_price(uniswap_module):
    """Test returned `asset_price` is empty when the unknown asset price is
    not found via subgraph.
    """
    def fake_graph_query(
        *args,  # pylint: disable=unused-argument
        **kwargs,  # pylint: disable=unused-argument
    ):
        return {'tokenDayDatas': []}

    unknown_assets = {ASSET_TGX}

    # Main call
    asset_price = uniswap_module._get_unknown_asset_price_graph(
        unknown_assets=unknown_assets,
        graph_query=fake_graph_query,
    )

    assert asset_price == {}


def test_unknown_asset_has_usd_price(uniswap_module):
    """Test returned `asset_price` contains the unknown token address and
    its USD price when the price is found via subgraph.
    """
    def fake_graph_query(
        *args,  # pylint: disable=unused-argument
        **kwargs,  # pylint: disable=unused-argument
    ):
        return {'tokenDayDatas': [TOKEN_DAY_DATA_TGX]}

    unknown_assets = {ASSET_TGX}

    # Main call
    asset_price = uniswap_module._get_unknown_asset_price_graph(
        unknown_assets=unknown_assets,
        graph_query=fake_graph_query,
    )

    exp_asset_price = {
        ASSET_TGX.ethereum_address: Price(FVal(TOKEN_DAY_DATA_TGX['priceUSD'])),
    }
    assert asset_price == exp_asset_price


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
            {'tokenDayDatas': [TOKEN_DAY_DATA_TGX, TOKEN_DAY_DATA_SHUF]},
            # Second response
            {'tokenDayDatas': []},
        ]
        for response in responses:
            yield response

    @store_call_args
    def fake_graph_query(
        *args,  # pylint: disable=unused-argument
        **kwargs,  # pylint: disable=unused-argument
    ):
        return next(get_response)

    unknown_assets = {ASSET_TGX, ASSET_SHUF}
    get_response = get_graph_response()

    # Main call
    uniswap_module._get_unknown_asset_price_graph(
        unknown_assets=unknown_assets,
        graph_query=fake_graph_query,
    )

    assert len(fake_graph_query.calls) == no_requests

    # Check limit and offset
    for idx, call_args in enumerate(fake_graph_query.calls):
        param_values = call_args['kwargs']['param_values']
        assert param_values['limit'] == graph_query_limit
        assert param_values['offset'] == idx * graph_query_limit
