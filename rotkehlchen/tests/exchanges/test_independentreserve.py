import warnings as test_warnings
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants.assets import A_BTC, A_ETC, A_ETH, A_OMG
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.exchanges.data_structures import Location
from rotkehlchen.exchanges.independentreserve import (
    Independentreserve,
    independentreserve_asset,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.tests.utils.constants import A_AUD
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Timestamp, TimestampMS


def test_location():
    exchange = Independentreserve('independentreserve1', 'a', b'a', object(), object())
    assert exchange.location == Location.INDEPENDENTRESERVE
    assert exchange.name == 'independentreserve1'


@pytest.mark.asset_test
def test_assets_are_known():
    exchange = Independentreserve('independentreserve1', 'a', b'a', object(), object())
    response = exchange._api_query('get', 'Public', 'GetValidPrimaryCurrencyCodes')
    for currency in response:
        try:
            independentreserve_asset(currency)
        except UnknownAsset:
            test_warnings.warn(UserWarning(
                f'Found unknown primary asset {currency} in IndependentReserve. '
                f'Support for it has to be added',
            ))

    response = exchange._api_query('get', 'Public', 'GetValidSecondaryCurrencyCodes')
    for currency in response:
        try:
            independentreserve_asset(currency)
        except UnknownAsset:
            test_warnings.warn(UserWarning(
                f'Found unknown secondary asset {currency} in IndependentReserve. '
                f'Support for it has to be added',
            ))


def test_missing_mapping_assets():
    """Regression test for #10602. TODO: @yabirgb remove in develop
    https://github.com/orgs/rotki/projects/11/views/3?pane=issue&itemId=128888662
    """
    assert independentreserve_asset('Xbt') == A_BTC
    assert independentreserve_asset('Omg') == A_OMG


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_balances(
        function_scope_independentreserve,
        inquirer,  # pylint: disable=unused-argument
):
    """Test all balances returned by IndependentReserve are processed properly"""
    exchange = function_scope_independentreserve

    def mock_api_return(method, url, **kwargs):    # pylint: disable=unused-argument
        assert method == 'post'
        response = """[{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Aud", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Usd", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Nzd", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Sgd", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Xbt", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Eth", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Xrp", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Ada", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Dot", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Uni", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Link", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Usdt", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Usdc", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Bch", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Ltc", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Mkr", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Dai", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Comp", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Snx", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Grt", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Eos", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Xlm", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Etc", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Bat", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Pmgt", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Yfi", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Aave", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Zrx", "TotalBalance": 150.55},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 150.55, "CurrencyCode": "Omg", "TotalBalance": 150.55}]"""  # noqa: E501
        return MockResponse(200, response)

    with patch.object(exchange.session, 'request', side_effect=mock_api_return):
        balances, msg = exchange.query_balances()

    assert msg == ''
    assets_seen = {0}
    for asset, balance in balances.items():
        assert asset not in assets_seen
        assets_seen.add(asset)
        assert balance.amount == FVal('150.55')


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_some_balances(
        function_scope_independentreserve,
        inquirer,  # pylint: disable=unused-argument
):
    """Just like test_query_balances but make sure 0 balances are skipped"""
    exchange = function_scope_independentreserve

    def mock_api_return(method, url, **kwargs):    # pylint: disable=unused-argument
        assert method == 'post'
        response = """[{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 1.2, "CurrencyCode": "Aud", "TotalBalance": 2.5},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Usd", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Nzd", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Sgd", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Xbt", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Eth", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Xrp", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Ada", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Dot", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Uni", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Link", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Usdt", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Usdc", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Bch", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Ltc", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Mkr", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Dai", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Comp", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Snx", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Grt", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Eos", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Xlm", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Etc", "TotalBalance": 100.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Bat", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Pmgt", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Yfi", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Aave", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Zrx", "TotalBalance": 0.0},
{"AccountGuid": "foo", "AccountStatus": "Active", "AvailableBalance": 0.0, "CurrencyCode": "Omg", "TotalBalance": 0.0}]"""  # noqa: E501
        return MockResponse(200, response)

    with patch.object(exchange.session, 'request', side_effect=mock_api_return):
        balances, msg = exchange.query_balances()

    assert msg == ''
    assert balances == {
        A_AUD: Balance(amount=FVal(2.5), usd_value=FVal(3.75)),
        A_ETC: Balance(amount=FVal(100), usd_value=FVal(150)),
    }


def test_query_trade_history(function_scope_independentreserve):
    """Happy path test for independentreserve trade history querying"""
    exchange = function_scope_independentreserve

    def mock_api_return(method, url, **kwargs):    # pylint: disable=unused-argument
        assert method == 'post'
        response = """{"Data": [
        {"TradeGuid": "foo1",
        "TradeTimestampUtc": "2017-11-22T22:54:40.3249401Z",
        "OrderType": "MarketOffer",
        "PrimaryCurrencyCode": "Eth",
        "SecondaryCurrencyCode": "Aud",
        "Price": 603.7,
        "VolumeTraded": 0.5,
        "Value": 301.85
        }, {
        "TradeGuid": "foo2",
        "TradeTimestampUtc": "2017-07-28T09:39:19.8799244Z",
        "OrderType": "MarketBid",
        "PrimaryCurrencyCode": "Eth",
        "SecondaryCurrencyCode": "Aud",
        "Price": 257.25,
        "VolumeTraded": 2.64117379,
        "Value": 679.44
        }],
 "PageSize": 50,
 "TotalItems": 2,
 "TotalPages": 1}
"""
        return MockResponse(200, response)

    with (
        patch.object(exchange.session, 'request', side_effect=mock_api_return),
        patch.object(exchange, '_query_asset_movements'),
    ):
        events, _ = exchange.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1565732120),
        )

    assert events == [SwapEvent(
        timestamp=(timestamp_1 := TimestampMS(1511391280000)),
        location=Location.INDEPENDENTRESERVE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal('0.5'),
        location_label=exchange.name,
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.INDEPENDENTRESERVE,
            unique_id=(unique_id_1 := 'foo1'),
        ),
    ), SwapEvent(
        timestamp=timestamp_1,
        location=Location.INDEPENDENTRESERVE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_AUD,
        amount=FVal('301.85'),
        location_label=exchange.name,
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.INDEPENDENTRESERVE,
            unique_id=unique_id_1,
        ),
    ), SwapEvent(
        timestamp=(timestamp_2 := TimestampMS(1501234760000)),
        location=Location.INDEPENDENTRESERVE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_AUD,
        amount=FVal('679.4419574775'),
        location_label=exchange.name,
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.INDEPENDENTRESERVE,
            unique_id=(unique_id_2 := 'foo2'),
        ),
    ), SwapEvent(
        timestamp=timestamp_2,
        location=Location.INDEPENDENTRESERVE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal('2.64117379'),
        location_label=exchange.name,
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.INDEPENDENTRESERVE,
            unique_id=unique_id_2,
        ),
    )]


# TODO: Make a test for asset movements.
# Would need more mocking as it would require mocking of multiple calls
