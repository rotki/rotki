import warnings as test_warnings

from rotkehlchen.assets.converters import UNSUPPORTED_BINANCE_ASSETS, asset_from_binance
from rotkehlchen.constants.misc import BINANCE_US_BASE_URL
from rotkehlchen.errors import UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.binance import Binance
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret
from rotkehlchen.user_messages import MessagesAggregator


def test_name():
    exchange = Binance('a', b'a', object(), object(), uri=BINANCE_US_BASE_URL)
    assert exchange.name == 'binance_us'


def test_binance_assets_are_known(
        database,
        inquirer,  # pylint: disable=unused-argument
):
    # use a real binance instance so that we always get the latest data
    binance = Binance(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=MessagesAggregator(),
        uri=BINANCE_US_BASE_URL,
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
                f'Found unknown asset {e.asset_name} in binance_us. '
                f'Support for it has to be added',
            ))
