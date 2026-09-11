from typing import TYPE_CHECKING, Final

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USD
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.externalapis.birdeye import Birdeye

A_SOLANA_USDC: Final = Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')
A_BONK: Final = Asset('solana/token:DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263')
# A timestamp for which Birdeye should have Solana USDC price data (2023-11-14).
USDC_TIMESTAMP: Final = Timestamp(1700000000)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_birdeye_current_prices(birdeye: Birdeye) -> None:
    """Query Birdeye for current prices of Solana and Ethereum tokens in one call. The
    tokens are grouped per chain and queried one token at a time, the free Standard
    package path. The batched probe is skipped because a free key answers it with a
    401, which the cassette recorder drops, so on replay the request would be unmatched."""
    birdeye._batching_supported = False
    prices = birdeye.query_multiple_current_prices(
        from_assets=[
            (usdc := A_SOLANA_USDC.resolve_to_asset_with_oracles()),
            (bonk := A_BONK.resolve_to_asset_with_oracles()),
            (dai := A_DAI.resolve_to_asset_with_oracles()),
        ],
        to_asset=A_USD.resolve_to_asset_with_oracles(),
    )
    assert FVal('0.9') < prices[usdc] < FVal('1.1'), f'unexpected Solana USDC price {prices[usdc]}'
    assert FVal('0.9') < prices[dai] < FVal('1.1'), f'unexpected DAI price {prices[dai]}'
    assert ZERO_PRICE < prices[bonk] < FVal('0.01'), f'unexpected BONK price {prices[bonk]}'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_birdeye_historical_price(birdeye: Birdeye) -> None:
    """Query Birdeye for a historical Solana USDC/USD price (a USD stablecoin, so the
    value should sit close to 1)."""
    price = birdeye.query_historical_price(
        from_asset=A_SOLANA_USDC,
        to_asset=A_USD,
        timestamp=USDC_TIMESTAMP,
    )
    assert FVal('0.9') < price < FVal('1.1'), f'unexpected Solana USDC historical price {price}'


def test_birdeye_unsupported_asset(birdeye: Birdeye) -> None:
    """Native ETH is neither a Solana nor an EVM token, so Birdeye cannot price it. This
    is resolved locally before any network call."""
    eth = A_ETH.resolve_to_asset_with_oracles()
    usd = A_USD.resolve_to_asset_with_oracles()

    assert birdeye.query_current_price(from_asset=eth, to_asset=usd) == ZERO_PRICE
    assert birdeye.query_multiple_current_prices(from_assets=[eth], to_asset=usd) == {}
    with pytest.raises(NoPriceForGivenTimestamp):
        birdeye.query_historical_price(
            from_asset=eth,
            to_asset=usd,
            timestamp=USDC_TIMESTAMP,
        )
