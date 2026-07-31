from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_3CRV,
    A_BTC,
    A_DAI,
    A_ETH,
    A_EUR,
    A_GNO,
    A_USD,
    A_USDC,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.externalapis.kraken import Kraken
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChainID, Price, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.defillama import Defillama


@pytest.mark.vcr
def test_kraken_query_single_current_price():
    """A single current price query returns the last trade price from Kraken."""
    kraken = Kraken()
    price = kraken.query_current_price(
        from_asset=A_BTC.resolve_to_asset_with_oracles(),
        to_asset=A_USD.resolve_to_asset_with_oracles(),
    )
    assert price != ZERO_PRICE
    assert price > Price(FVal(1000))


@pytest.mark.vcr
def test_kraken_query_multiple_current_prices():
    """Multiple assets are resolved from a single all-tickers response.

    GNO is listed on Kraken and is expected to return a price, while INDEX
    (Index Cooperative) is not listed on Kraken and is expected to be absent
    from the result.
    """
    kraken = Kraken()
    prices = kraken.query_multiple_current_prices(
        from_assets=[
            A_BTC.resolve_to_asset_with_oracles(),
            A_ETH.resolve_to_asset_with_oracles(),
            A_GNO.resolve_to_asset_with_oracles(),
            A_3CRV.resolve_to_asset_with_oracles(),
        ],
        to_asset=A_USD.resolve_to_asset_with_oracles(),
    )
    assert A_BTC in prices
    assert prices[A_BTC] == Price(FVal('60934.90000'))
    assert A_ETH in prices
    assert prices[A_ETH] == Price(FVal('1643.01000'))
    # GNO is listed on Kraken and should get a price
    assert A_GNO in prices
    assert prices[A_GNO] == Price(FVal('106.340000'))
    # INDEX is not listed on Kraken, so no price is returned for it
    assert A_3CRV not in prices


def test_kraken_mapping_lookup_is_batched() -> None:
    """A 100-asset uncached batch and its target must use one mapping query, not 101."""
    kraken = Kraken()
    btc = A_BTC.resolve_to_asset_with_oracles()
    eth = A_ETH.resolve_to_asset_with_oracles()
    usd = A_USD.resolve_to_asset_with_oracles()
    with (
        patch.object(
            Kraken,
            '_assets_to_kraken_symbols',
            wraps=Kraken._assets_to_kraken_symbols,
        ) as mapping_query,
        patch.object(
            Kraken,
            '_asset_to_kraken_symbols',
            side_effect=AssertionError('used scalar Kraken mapping lookup'),
        ),
        patch.object(kraken, '_get_tickers', return_value={
            'BTC/USD': {'c': ['100000']},
            'ETH/USD': {'c': ['4000']},
        }),
    ):
        prices = kraken.query_multiple_current_prices(
            from_assets=[btc, eth] * 50,
            to_asset=usd,
        )

    assert prices == {btc: Price(FVal(100000)), eth: Price(FVal(4000))}
    assert mapping_query.call_count == 1


@pytest.mark.vcr
def test_kraken_tickers_cache_avoids_repeated_requests():
    """A second query within the cache window must not trigger another HTTP call.

    The cassette for this test only contains a single ticker request; if the
    cache didn't work the second query would raise a VCR "can't overwrite
    existing cassette" error.
    """
    kraken = Kraken()
    first = kraken.query_current_price(
        from_asset=A_BTC.resolve_to_asset_with_oracles(),
        to_asset=A_USD.resolve_to_asset_with_oracles(),
    )
    second = kraken.query_current_price(
        from_asset=A_ETH.resolve_to_asset_with_oracles(),
        to_asset=A_USD.resolve_to_asset_with_oracles(),
    )
    assert first != ZERO_PRICE
    assert second != ZERO_PRICE


@pytest.mark.vcr
def test_kraken_unsupported_asset_returns_zero_price():
    """An asset not listed on Kraken yields no price (ZERO_PRICE) without raising."""
    kraken = Kraken()
    price = kraken.query_current_price(
        from_asset=A_3CRV.resolve_to_asset_with_oracles(),
        to_asset=A_USD.resolve_to_asset_with_oracles(),
    )
    assert price == ZERO_PRICE


@pytest.mark.vcr
def test_kraken_only_prices_mapped_assets_and_their_collections(globaldb):
    """A token cannot impersonate a Kraken-listed asset by copying its symbol."""
    optimism_dai = EvmToken('eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1')
    fake_dai = EvmToken.initialize(
        address=string_to_evm_address('0x0000000000000000000000000000000000000001'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        name='Fake Dai',
        symbol='DAI',
        decimals=18,
    )
    with globaldb.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'UPDATE location_asset_mappings SET local_id=? '
            'WHERE location IS NULL AND exchange_symbol=?',
            (optimism_dai.identifier, 'DAI'),
        )

    prices = Kraken().query_multiple_current_prices(
        from_assets=[
            A_DAI.resolve_to_asset_with_oracles(),
            optimism_dai,
            fake_dai,
            A_USDC.resolve_to_asset_with_oracles(),
        ],
        to_asset=A_USD.resolve_to_asset_with_oracles(),
    )

    assert A_DAI in prices
    assert optimism_dai in prices
    assert prices[A_DAI] == prices[optimism_dai]
    assert fake_dai not in prices
    assert prices[A_USDC] != ZERO_PRICE


@pytest.mark.vcr
@pytest.mark.freeze_time('2026-06-24 12:00:00 GMT')
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_kraken_eur_price_close_to_defillama(inquirer, session_defillama: Defillama):
    """Kraken EUR prices for BTC and ETH stay within 0.5% of Defillama's.

    Both oracles are queried for BTC -> EUR and ETH -> EUR. Defillama only
    exposes USD prices, so the EUR rate is obtained through the real
    (unmocked) Inquirer fiat-pair query against xrates.com. The relative
    difference between the two oracles is asserted to stay under 0.5%.
    """
    kraken = Kraken()
    assets = [
        A_BTC.resolve_to_asset_with_oracles(),
        A_ETH.resolve_to_asset_with_oracles(),
    ]
    kraken_prices = kraken.query_multiple_current_prices(
        from_assets=assets,
        to_asset=A_EUR.resolve_to_asset_with_oracles(),
    )
    defillama_prices = session_defillama.query_multiple_current_prices(
        from_assets=assets,
        to_asset=A_EUR.resolve_to_asset_with_oracles(),
    )

    for asset in assets:
        assert asset in kraken_prices, f'Kraken returned no EUR price for {asset}'
        assert asset in defillama_prices, f'Defillama returned no EUR price for {asset}'
        relative_diff = (
            abs(kraken_prices[asset] - defillama_prices[asset]) / defillama_prices[asset]
        )
        assert relative_diff < FVal('0.005'), (
            f'{asset} EUR price differs too much: kraken={kraken_prices[asset]} '
            f'defillama={defillama_prices[asset]} relative_diff={relative_diff}'
        )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_kraken_price_close_to_coingecko(session_coingecko: Coingecko):
    """The Kraken BTC/USD price should be in the same ballpark as CoinGecko's.

    Both oracles are queried for BTC -> USD and the results are compared with a
    generous tolerance to account for the last-trade vs. volume-weighted
    differences and the slight time gap between the two recorded requests.
    """
    kraken = Kraken()
    kraken_price = kraken.query_current_price(
        from_asset=A_BTC.resolve_to_asset_with_oracles(),
        to_asset=A_USD.resolve_to_asset_with_oracles(),
    )
    coingecko_price = session_coingecko.query_current_price(
        from_asset=A_BTC.resolve_to_asset_with_oracles(),
        to_asset=A_USD.resolve_to_asset_with_oracles(),
    )

    assert kraken_price > ZERO_PRICE
    assert coingecko_price > ZERO_PRICE
    # allow up to 0.1% divergence between the two oracles
    relative_diff = abs(kraken_price - coingecko_price) / coingecko_price
    assert relative_diff < FVal('0.001')
