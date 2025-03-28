import warnings as test_warnings
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.constants.assets import A_BNB, A_BTC
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.binance import BINANCEUS_BASE_URL, Binance
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.tests.utils.exchanges import (
    BINANCE_DEPOSITS_HISTORY_RESPONSE,
    BINANCE_MYTRADES_RESPONSE,
    BINANCE_WITHDRAWALS_HISTORY_RESPONSE,
    assert_binance_asset_movements_result,
)
from rotkehlchen.tests.utils.globaldb import is_asset_symbol_unsupported
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location, Timestamp, TimestampMS


def test_name():
    exchange = Binance('binanceus1', 'a', b'a', object(), object(), uri=BINANCEUS_BASE_URL)
    assert exchange.location == Location.BINANCEUS
    assert exchange.name == 'binanceus1'


def test_binance_assets_are_known(inquirer, globaldb):  # pylint: disable=unused-argument
    exchange_data = requests.get('https://api.binance.us/api/v3/exchangeInfo').json()
    binance_assets = set()
    for pair_symbol in exchange_data['symbols']:
        binance_assets.add(pair_symbol['baseAsset'])
        binance_assets.add(pair_symbol['quoteAsset'])

    sorted_assets = sorted(binance_assets)
    for binance_asset in sorted_assets:
        try:
            _ = asset_from_binance(binance_asset)
        except UnsupportedAsset:
            assert is_asset_symbol_unsupported(globaldb, Location.BINANCE, binance_asset)
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.identifier} in binanceus. '
                f'Support for it has to be added',
            ))


@pytest.mark.parametrize('binance_location', [Location.BINANCEUS])
def test_binanceus_trades_location(function_scope_binance):
    """Test that trades from binance US have the right location.

    Regression test for https://github.com/rotki/rotki/issues/2837
    """
    binance = function_scope_binance

    def mock_my_trades(url, params, **kwargs):  # pylint: disable=unused-argument
        if params.get('symbol') == 'BNBBTC':
            text = BINANCE_MYTRADES_RESPONSE
        else:
            text = '[]'

        return MockResponse(200, text)

    with patch.object(binance.session, 'request', side_effect=mock_my_trades):
        events, _ = binance.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1564301134),
        )
        assert events == [SwapEvent(
            timestamp=TimestampMS(1499865549590),
            location=Location.BINANCEUS,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_BTC,
            amount=FVal('48.0000120000000000'),
            unique_id='28457',
        ), SwapEvent(
            timestamp=TimestampMS(1499865549590),
            location=Location.BINANCEUS,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_BNB,
            amount=FVal('12.00000000'),
            unique_id='28457',
        ), SwapEvent(
            timestamp=TimestampMS(1499865549590),
            location=Location.BINANCEUS,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BNB,
            amount=FVal('10.10000000'),
            unique_id='28457',
        )]


@pytest.mark.parametrize('binance_location', [Location.BINANCEUS])
def test_binanceus_deposits_withdrawals_location(function_scope_binance):
    """Test deposits/withdrawls of binance US have the right location.

    Regression test for https://github.com/rotki/rotki/issues/2837
    """
    start_ts = 1508022000  # 2017-10-15
    end_ts = 1508540400  # 2017-10-21 (less than 90 days since `start_ts`)
    binance = function_scope_binance

    def mock_get_history_events(url, **kwargs):  # pylint: disable=unused-argument
        if 'deposit' in url:
            response_str = BINANCE_DEPOSITS_HISTORY_RESPONSE
        else:
            response_str = BINANCE_WITHDRAWALS_HISTORY_RESPONSE

        return MockResponse(200, response_str)

    with patch.object(binance.session, 'request', side_effect=mock_get_history_events):
        movements, _ = binance.query_online_history_events(
            start_ts=Timestamp(start_ts),
            end_ts=Timestamp(end_ts),
        )

    errors = binance.msg_aggregator.consume_errors()
    warnings = binance.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0

    assert len(movements) == 6
    assert_binance_asset_movements_result(
        movements=movements,
        location=Location.BINANCEUS,
        got_fiat=False,
    )
