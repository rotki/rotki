import warnings as test_warnings
from unittest.mock import patch

import pytest

from rotkehlchen.assets.converters import UNSUPPORTED_BINANCE_ASSETS, asset_from_binance
from rotkehlchen.constants.assets import A_BNB, A_BTC
from rotkehlchen.errors import UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.binance import Binance, BINANCEUS_BASE_URL
from rotkehlchen.exchanges.data_structures import Trade, TradeType
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.exchanges import (
    BINANCE_DEPOSITS_HISTORY_RESPONSE,
    BINANCE_MYTRADES_RESPONSE,
    BINANCE_WITHDRAWALS_HISTORY_RESPONSE,
    assert_binance_asset_movements_result,
)
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import Location, Timestamp
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


@pytest.mark.parametrize('binance_location', [Location.BINANCEUS])
def test_binanceus_trades_location(function_scope_binance):
    """Test that trades from binance US have the right location.

    Regression test for https://github.com/rotki/rotki/issues/2837
    """
    binance = function_scope_binance

    def mock_my_trades(url, **kwargs):  # pylint: disable=unused-argument
        if 'symbol=BNBBTC' in url:
            text = BINANCE_MYTRADES_RESPONSE
        else:
            text = '[]'

        return MockResponse(200, text)

    with patch.object(binance.session, 'get', side_effect=mock_my_trades):
        trades = binance.query_trade_history(start_ts=0, end_ts=1564301134, only_cache=False)

    expected_trade = Trade(
        timestamp=1499865549,
        location=Location.BINANCEUS,
        base_asset=A_BNB,
        quote_asset=A_BTC,
        trade_type=TradeType.BUY,
        amount=FVal('12'),
        rate=FVal('4.00000100'),
        fee=FVal('10.10000000'),
        fee_currency=A_BNB,
        link='28457',
    )

    assert len(trades) == 1
    assert trades[0] == expected_trade


@pytest.mark.parametrize('binance_location', [Location.BINANCEUS])
def test_binanceus_deposits_withdrawals_location(function_scope_binance):
    """Test deposits/withdrawls of binance US have the right location.

    Regression test for https://github.com/rotki/rotki/issues/2837
    """
    start_ts = 1508022000  # 2017-10-15
    end_ts = 1508540400  # 2017-10-21 (less than 90 days since `start_ts`)
    binance = function_scope_binance

    def mock_get_deposit_withdrawal(url, **kwargs):  # pylint: disable=unused-argument
        if 'deposit' in url:
            response_str = BINANCE_DEPOSITS_HISTORY_RESPONSE
        else:
            response_str = BINANCE_WITHDRAWALS_HISTORY_RESPONSE

        return MockResponse(200, response_str)

    with patch.object(binance.session, 'get', side_effect=mock_get_deposit_withdrawal):
        movements = binance.query_online_deposits_withdrawals(
            start_ts=Timestamp(start_ts),
            end_ts=Timestamp(end_ts),
        )

    errors = binance.msg_aggregator.consume_errors()
    warnings = binance.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0

    assert len(movements) == 4
    assert_binance_asset_movements_result(movements=movements, location=Location.BINANCEUS)
