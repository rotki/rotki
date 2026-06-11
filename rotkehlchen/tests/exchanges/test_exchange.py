from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USDC
from rotkehlchen.exchanges.exchange import ExchangeWithoutApiSecret
from rotkehlchen.fval import FVal
from rotkehlchen.types import Price


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_balances_from_amounts_batches_and_uses_cache(inquirer):
    """Test that the exchange pricing helper queries all asset prices in a single
    batched oracle query and that subsequent calls (e.g. from the next exchange in
    a balance refresh) get the already priced assets from the price cache, querying
    the oracle only for the new ones"""
    oracle_queries = []

    def mock_oracle_batch(from_assets, to_asset):
        oracle_queries.append(set(from_assets))
        return {from_asset: Price(FVal(100)) for from_asset in from_assets}

    eth, btc, usdc = (x.resolve_to_asset_with_oracles() for x in (A_ETH, A_BTC, A_USDC))
    with patch.object(
        inquirer._coingecko,
        'query_multiple_current_prices',
        side_effect=mock_oracle_batch,
    ):
        balances = ExchangeWithoutApiSecret.balances_from_amounts({eth: FVal(2), btc: ONE})
        assert oracle_queries == [{eth, btc}]  # one batched query for all assets
        assert balances == {
            eth: Balance(amount=FVal(2), value=FVal(200)),
            btc: Balance(amount=ONE, value=FVal(100)),
        }

        balances = ExchangeWithoutApiSecret.balances_from_amounts({btc: FVal(3), usdc: FVal(4)})
        assert oracle_queries == [{eth, btc}, {usdc}]  # btc was served from the cache
        assert balances == {
            btc: Balance(amount=FVal(3), value=FVal(300)),
            usdc: Balance(amount=FVal(4), value=FVal(400)),
        }
