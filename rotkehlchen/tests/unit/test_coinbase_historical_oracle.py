from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_USD
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.price_oracles.coinbase import CoinbaseHistoricalPriceOracle
from rotkehlchen.history.types import DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER, HistoricalPriceOracle
from rotkehlchen.types import ChainID, Location, Price, Timestamp, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.db.updates import RotkiDataUpdater
    from rotkehlchen.exchanges.coinbase import Coinbase
    from rotkehlchen.history.price import PriceHistorian

QUERY_TIMESTAMP = Timestamp(1724661234)
CANDLE_START = Timestamp(1724659200)
pytestmark = pytest.mark.parametrize('use_clean_caching_directory', [True])


@pytest.fixture(name='coinbase_oracle')
def fixture_coinbase_oracle(
        data_updater: RotkiDataUpdater,
        exchange_manager,
        function_scope_coinbase: Coinbase,
) -> CoinbaseHistoricalPriceOracle:
    data_updater.update_location_asset_mappings(data={'additions': [
        {'asset': asset.identifier, 'location': 'coinbase', 'location_symbol': asset.identifier}
        for asset in (A_BTC, A_ETH, A_EUR, A_USD)
    ]}, version=17)
    function_scope_coinbase._spot_products = {
        ('BTC', 'USD'): 'BTC-USD',
        ('ETH', 'EUR'): 'ETH-EUR',
        ('ETH', 'USD'): 'ETH-USD',
        ('ETH', 'USDC'): 'ETH-USDC',
        ('ETH', 'USDT'): 'ETH-USDT',
    }
    exchange_manager.connected_exchanges[Location.COINBASE].append(function_scope_coinbase)
    return CoinbaseHistoricalPriceOracle(exchange_manager=exchange_manager)


def test_coinbase_is_not_a_default_historical_oracle() -> None:
    assert HistoricalPriceOracle.COINBASE not in DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER


def test_direct_eur_candle_and_covering_candle_selection(
        coinbase_oracle: CoinbaseHistoricalPriceOracle,
) -> None:
    coinbase = coinbase_oracle._get_coinbase()
    assert coinbase is not None
    with patch.object(coinbase, 'query_product_candles', return_value=[
        {'start': str(CANDLE_START + 3600), 'close': '9999'},
        {
            'start': str(CANDLE_START),
            'low': '2390.52',
            'high': '2466.15',
            'open': '2454.13',
            'close': '2401.77',
            'volume': '2092.23619856',
        },
    ]) as query_mock:
        price = coinbase_oracle.query_historical_price(A_ETH, A_EUR, QUERY_TIMESTAMP)

    assert price == FVal('2401.77')
    query_mock.assert_called_once_with(
        product_id='ETH-EUR',
        start=CANDLE_START,
        end=Timestamp(CANDLE_START + 3599),
        granularity='ONE_HOUR',
        limit=1,
    )


def test_stablecoin_quote_fallback(
        coinbase_oracle: CoinbaseHistoricalPriceOracle,
        price_historian: PriceHistorian,
) -> None:
    coinbase = coinbase_oracle._get_coinbase()
    assert coinbase is not None

    def query_candles(product_id: str, **kwargs) -> list[dict[str, str]]:  # pylint: disable=unused-argument
        if product_id == 'ETH-USDC':
            return [{'start': str(CANDLE_START), 'close': '2500'}]
        return []

    with (
        patch.object(coinbase, 'query_product_candles', side_effect=query_candles) as query_mock,
        patch.object(price_historian, 'query_historical_price', return_value=Price(FVal('0.92'))) as conversion_mock,  # noqa: E501
    ):
        price = coinbase_oracle.query_historical_price(A_ETH, A_EUR, QUERY_TIMESTAMP)

    assert price == FVal('2300')
    assert [call.kwargs['product_id'] for call in query_mock.call_args_list] == [
        'ETH-EUR',
        'ETH-USD',
        'ETH-USDC',
    ]
    conversion_mock.assert_called_once()


def test_missing_credentials(exchange_manager) -> None:
    oracle = CoinbaseHistoricalPriceOracle(exchange_manager=exchange_manager)
    assert oracle.can_query_history(A_BTC, A_USD, QUERY_TIMESTAMP) is False
    with pytest.raises(PriceQueryUnsupportedAsset):
        oracle.query_historical_price(A_BTC, A_USD, QUERY_TIMESTAMP)


@pytest.mark.parametrize('status_code', [
    HTTPStatus.UNAUTHORIZED,
    HTTPStatus.FORBIDDEN,
    HTTPStatus.TOO_MANY_REQUESTS,
])
def test_auth_permission_and_rate_limit_errors_fall_through(
        coinbase_oracle: CoinbaseHistoricalPriceOracle,
        status_code: HTTPStatus,
) -> None:
    coinbase = coinbase_oracle._get_coinbase()
    assert coinbase is not None
    with (
        patch.object(
            coinbase,
            'query_product_candles',
            side_effect=RemoteError('request failed', error_code=status_code),
        ),
        pytest.raises(RemoteError) as exc_info,
    ):
        coinbase_oracle.query_historical_price(A_BTC, A_USD, QUERY_TIMESTAMP)

    assert exc_info.value.error_code == status_code


def test_unknown_product_and_malformed_candles(
        coinbase_oracle: CoinbaseHistoricalPriceOracle,
) -> None:
    coinbase = coinbase_oracle._get_coinbase()
    assert coinbase is not None
    with (
        patch.object(coinbase, 'query_product_candles', return_value=[
            {'start': 'not-a-timestamp', 'close': '1'},
            {'start': str(CANDLE_START), 'close': 'not-a-price'},
            {'start': str(CANDLE_START)},
        ]),
        pytest.raises(NoPriceForGivenTimestamp),
    ):
        coinbase_oracle.query_historical_price(A_BTC, A_USD, QUERY_TIMESTAMP)


def test_coinbase_only_queries_mapping_backed_assets(
        coinbase_oracle: CoinbaseHistoricalPriceOracle,
) -> None:
    """A token cannot impersonate a Coinbase-listed asset by copying its symbol."""
    fake_eth = EvmToken.initialize(
        address=string_to_evm_address('0x0000000000000000000000000000000000000001'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        name='Fake Ether',
        symbol='ETH',
        decimals=18,
    )
    coinbase = coinbase_oracle._get_coinbase()
    assert coinbase is not None
    with (
        patch.object(coinbase, 'query_spot_products') as products_mock,
        patch.object(coinbase, 'query_product_candles') as candles_mock,
        pytest.raises(PriceQueryUnsupportedAsset),
    ):
        coinbase_oracle.query_historical_price(fake_eth, A_USD, QUERY_TIMESTAMP)

    products_mock.assert_not_called()
    candles_mock.assert_not_called()


def test_cached_coinbase_price_avoids_second_request(
        price_historian: PriceHistorian,
        coinbase_oracle: CoinbaseHistoricalPriceOracle,
) -> None:
    coinbase = coinbase_oracle._get_coinbase()
    assert coinbase is not None
    price_historian.__dict__.pop('query_historical_price', None)
    price_historian._coinbase = coinbase_oracle
    price_historian.set_oracles_order([HistoricalPriceOracle.COINBASE])
    with patch.object(coinbase, 'query_product_candles', return_value=[
        {'start': str(CANDLE_START), 'close': '2401.77'},
    ]) as query_mock:
        assert price_historian.query_historical_price(A_ETH, A_EUR, QUERY_TIMESTAMP) == FVal('2401.77')  # noqa: E501
        assert price_historian.query_historical_price(A_ETH, A_EUR, QUERY_TIMESTAMP) == FVal('2401.77')  # noqa: E501

    assert query_mock.call_count == 1


def test_historian_falls_back_after_coinbase_error(price_historian: PriceHistorian) -> None:
    coinbase = MagicMock(spec=CoinbaseHistoricalPriceOracle)
    coinbase.can_query_history.return_value = True
    coinbase.query_historical_price.side_effect = RemoteError('Coinbase unavailable')
    coingecko = price_historian._coingecko
    price_historian.__dict__.pop('query_historical_price', None)
    price_historian._coinbase = coinbase
    price_historian.set_oracles_order([
        HistoricalPriceOracle.COINBASE,
        HistoricalPriceOracle.COINGECKO,
    ])

    with (
        patch.object(coingecko, 'can_query_history', return_value=True),
        patch.object(coingecko, 'query_historical_price', return_value=Price(FVal('1234'))) as coingecko_query,  # noqa: E501
    ):
        assert price_historian.query_historical_price(A_BTC, A_USD, Timestamp(1724662345)) == FVal('1234')  # noqa: E501

    coinbase.query_historical_price.assert_called_once()
    coingecko_query.assert_called_once()
