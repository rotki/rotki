import warnings as test_warnings

from rotkehlchen.assets.converters import UNSUPPORTED_BINANCE_ASSETS, asset_from_binance
from rotkehlchen.constants.misc import BINANCEUS_BASE_URL
from rotkehlchen.errors import UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.binance import Binance
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret
from rotkehlchen.typing import Location
from rotkehlchen.user_messages import MessagesAggregator


def test_name():
    exchange = Binance('binanceus1', 'a', b'a', object(), object(), uri=BINANCEUS_BASE_URL)
    assert exchange.location == Location.BINANCEUS
    assert exchange.name == 'binanceus1'


def test_binance_assets_are_known(
        database,
        inquirer,  # pylint: disable=unused-argument
):
    # use a real binance instance so that we always get the latest data
    binance = Binance(
        name='binance1',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=MessagesAggregator(),
        uri=BINANCEUS_BASE_URL,
    )

    mapping = binance.symbols_to_pair
    binance_assets = set()
    for _, pair in mapping.items():
        binance_assets.add(pair.binance_base_asset)
        binance_assets.add(pair.binance_quote_asset)

    sorted_assets = sorted(binance_assets)
    for binance_asset in sorted_assets:
        try:
            _ = asset_from_binance(binance_asset)
        except UnsupportedAsset:
            assert binance_asset in UNSUPPORTED_BINANCE_ASSETS
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.asset_name} in binanceus. '
                f'Support for it has to be added',
            ))
