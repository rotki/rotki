
import json
import warnings as test_warnings
from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_htx
from rotkehlchen.constants.assets import A_CRV, A_DAI, A_DOGE, A_USDT, A_ZRX
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.htx import Htx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.globaldb import is_asset_symbol_unsupported
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location, Timestamp, TimestampMS


def htx_account_mock(
        calls: dict[str, list[tuple[dict[str, str | int], dict[str, Any]]]],
) -> Callable[[str, dict[str, Any]], dict[str, Any]]:
    """
    Mock call to the HTX API.
    - calls is a map of a URL to a list of call outputs consumed in the order provided.
    """
    iterators = {key: iter(val) for key, val in calls.items()}

    def _mock_authenticated_query(absolute_path: str, options: dict[str, Any] | None = None) -> dict[str, Any]:  # pylint: disable=unused-argument  # noqa: E501
        for expected_options, response in iterators[absolute_path]:
            if options == expected_options:
                return response
        return {}

    return _mock_authenticated_query


def test_accounts(htx_exchange: Htx):
    def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, """{"status": "ok", "data": [{"id": 50, "type": "spot", "subtype": "", "state": "working"}, {"id": 292, "type": "point", "subtype": "", "state": "working"}]}""")  # noqa: E501

    with patch.object(htx_exchange.session, 'get', side_effect=mock_api_return):
        accounts = htx_exchange.get_accounts()

    assert {account['type'] for account in accounts} == {'spot', 'point'}


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_balances(htx_exchange: Htx):
    balance_response = """
    {
        "status": "ok",
        "data": {"id": 50, "type": "spot", "state": "working", "list": [
            {"currency": "atom", "type": "trade", "balance": "1.100000007177861711", "available": "1.100000007177861711", "debt": "0", "seq-num": "11"},
            {"currency": "ksm", "type": "frozen", "balance": "0", "debt": "0", "seq-num": "0"},
            {"currency": "crv", "type": "trade", "balance": "0.100000007177861711", "available": "0.100000007177861711", "debt": "0", "seq-num": "0"}
        ]}
    }"""  # noqa: E501

    def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
        if 'balance' in url:
            return MockResponse(200, balance_response)
        else:
            return MockResponse(200, """{"status": "ok", "data": [{"id": 50, "type": "spot", "subtype": "", "state": "working"}]}""")  # noqa: E501

    with patch.object(htx_exchange.session, 'get', side_effect=mock_api_return):
        balances, _ = htx_exchange.query_balances()

    assert balances == {
        Asset('ATOM'): Balance(amount=FVal('1.100000007177861711'), usd_value=FVal('1.6500000107667925665')),  # noqa: E501
        A_CRV: Balance(amount=FVal('0.100000007177861711'), usd_value=FVal('0.1500000107667925665')),  # noqa: E501
    }


def test_assets_are_known(htx_exchange: Htx, globaldb):
    with patch('rotkehlchen.exchanges.htx.Htx._sign_request', return_value={}):
        tickers = htx_exchange._query('/v2/settings/common/symbols')
    for ticker in tickers:
        if ticker['te'] is False:  # skip if trade disabled
            continue
        try:
            asset_from_htx(ticker['bcdn'])
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.identifier} in HTX. '
                f'Support for it has to be added',
            ))
        except UnsupportedAsset as e:
            if is_asset_symbol_unsupported(globaldb, Location.HTX, ticker['bcdn']) is False:
                test_warnings.warn(UserWarning(
                    f'Found unsupported asset {e.identifier} in HTX. '
                    f'Support for it has to be added',
                ))


def test_deposit_withdrawals(htx_exchange: Htx) -> None:
    """Test that withdrawals and deposits get correctly processed"""
    mock_fn = htx_account_mock(calls={
        '/v1/query/deposit-withdraw': [
            ({'type': 'deposit', 'size': 500, 'direct': 'next'}, json.loads('[{"id": 59781355, "type": "deposit", "sub-type": "NORMAL", "request-id": "zrx-da9752c57c3c5e7b847b69f4e7bc2b7bc40beca0f47b4c4d73e9e166eb46d1a6-276", "currency": "zrx", "chain": "zrx", "tx-hash": "0xda9752c57c3c5e7b847b69f4e7bc2b7bc40beca0f47b4c4d73e9e166eb46d1a6", "amount": 597.0018, "from-addr-tag": "", "address-id": 0, "address": "0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97", "address-tag": "", "fee": 0, "state": "safe", "wallet-confirm": 12, "created-at": 1612820394594, "updated-at": 1612492580193}, {"id": 131331249, "type": "deposit", "sub-type": "NORMAL", "request-id": "dai-efc9ea1f3cf1ed581d75a43eecb1dc17b6f4fd96440f1c0d880f1e9c86e6c179-259", "currency": "dai", "chain": "dai", "tx-hash": "0xefc9ea1f3cf1ed581d75a43eecb1dc17b6f4fd96440f1c0d880f1e9c86e6c179", "amount": 1064.437, "from-addr-tag": "", "address-id": 0, "address": "0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97", "address-tag": "", "fee": 0, "state": "safe", "wallet-confirm": 93, "created-at": 1710153143454, "updated-at": 1710154218916}]')),  # noqa: E501
            ({'type': 'withdraw', 'size': 500, 'direct': 'next'}, json.loads('[{"id": 52360978, "type": "withdraw", "sub-type": "NORMAL", "currency": "zrx", "chain": "zrx", "tx-hash": "0xd41ab5afa0e19c84ffa388bbfc60623e4936af2232861e1cf365b2f8725cbd2c", "amount": 1174.49047, "from-addr-tag": "", "address-id": 30777398, "address": "0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97", "address-tag": "", "fee": 13.778201, "state": "confirmed", "created-at": 1631140110655, "updated-at": 1631140245190}]')),  # noqa: E501
        ],
    })
    with (
        patch.object(htx_exchange, '_query', side_effect=mock_fn),
        patch.object(htx_exchange, '_query_trades'),
    ):
        movements, _ = htx_exchange.query_online_history_events(
            start_ts=Timestamp(1612492580),
            end_ts=Timestamp(1714746851),
        )
    expected_movements = [
        AssetMovement(
            location=Location.HTX,
            location_label=htx_exchange.name,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1612820394000),
            asset=A_ZRX,
            amount=FVal('597.0018'),
            unique_id='59781355',
            extra_data={
                'address': '0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97',
                'transaction_id': '0xda9752c57c3c5e7b847b69f4e7bc2b7bc40beca0f47b4c4d73e9e166eb46d1a6',  # noqa: E501
            },
        ), AssetMovement(
            location=Location.HTX,
            location_label=htx_exchange.name,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1710153143000),
            asset=A_DAI,
            amount=FVal('1064.437'),
            unique_id='131331249',
            extra_data={
                'address': '0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97',
                'transaction_id': '0xefc9ea1f3cf1ed581d75a43eecb1dc17b6f4fd96440f1c0d880f1e9c86e6c179',  # noqa: E501
            },
        ), AssetMovement(
            location=Location.HTX,
            location_label=htx_exchange.name,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1631140110000),
            asset=A_ZRX,
            amount=FVal('1174.49047'),
            unique_id='52360978',
            extra_data={
                'address': '0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97',
                'transaction_id': '0xd41ab5afa0e19c84ffa388bbfc60623e4936af2232861e1cf365b2f8725cbd2c',  # noqa: E501
            },
        ), AssetMovement(
            location=Location.HTX,
            location_label=htx_exchange.name,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1631140110000),
            asset=A_ZRX,
            amount=FVal('13.778201'),
            unique_id='52360978',
            is_fee=True,
        ),
    ]
    assert movements == expected_movements


@pytest.mark.freeze_time('2024-03-12 00:00:00 GMT')
def test_trades(htx_exchange: Htx) -> None:
    mock_fn = htx_account_mock(calls={
        '/v1/order/matchresults': [
            ({'start-time': '1709997318000', 'end-time': '1710170118000', 'size': 500}, json.loads('[{"symbol": "dogeusdt", "fee-currency": "doge", "source": "spot-web", "filled-amount": "0.587616346289181345", "filled-fees": "0.62254395", "filled-points": "0.0", "role": "taker", "updated-at": null, "price": "0.69042", "created-at": 1792370117673, "fee-deduct-currency": "", "fee-deduct-state": "done", "order-id": 10505067, "match-id": 612882223, "trade-id": 708313429, "id": 8208887641319065, "type": "buy-market"}, {"symbol": "dogeusdt", "fee-currency": "doge", "source": "spot-web", "filled-amount": "8.1662", "filled-fees": "0.006007", "filled-points": "0.0", "role": "taker", "updated-at": null, "price": "0.69042", "created-at": 1792370117673, "fee-deduct-currency": "", "fee-deduct-state": "done", "order-id": 10505067, "match-id": 612882223, "trade-id": 708313428, "id": 1836658935934866, "type": "buy-market"}, {"symbol": "dogeusdt", "fee-currency": "doge", "source": "spot-web", "filled-amount": "1.537", "filled-fees": "0.003074", "filled-points": "0.0", "role": "taker", "updated-at": null, "price": "38.8718", "created-at": 1792370117672, "fee-deduct-currency": "", "fee-deduct-state": "done", "order-id": 10505067, "match-id": 612882223, "trade-id": 708313427, "id": 2186266790953303, "type": "buy-market"}, {"symbol": "daiusdt", "fee-currency": "usdt", "source": "spot-web", "filled-amount": "1038.18", "filled-fees": "2.07532182", "filled-points": "0.0", "role": "taker", "updated-at": null, "price": "0.9995", "created-at": 1710354800452, "fee-deduct-currency": "", "fee-deduct-state": "done", "order-id": 1020938404315, "match-id": 100304520643, "trade-id": 73831300, "id": 1552611026239689, "type": "sell-market"}, {"symbol": "daiusdt", "fee-currency": "usdt", "source": "spot-web", "filled-amount": "26.3", "filled-fees": "0.05257896", "filled-points": "0.0", "role": "taker", "updated-at": null, "price": "0.9996", "created-at": 1710354800451, "fee-deduct-currency": "", "fee-deduct-state": "done", "order-id": 1020938404315, "match-id": 100304520643, "trade-id": 73831399, "id": 3409716930791340, "type": "sell-market"}]')),  # noqa: E501
        ],
    })
    with (
        patch.object(htx_exchange, '_query', side_effect=mock_fn),
        patch.object(htx_exchange, '_query_deposits_withdrawals'),
    ):
        events, _ = htx_exchange.query_online_history_events(
            start_ts=Timestamp(1710354800),
            end_ts=Timestamp(1710170118),
        )

    assert events == [SwapEvent(
        timestamp=TimestampMS(1792370117673),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal('0.40570207780497658421490'),
        location_label='htx',
        unique_id='8208887641319065',
    ), SwapEvent(
        timestamp=TimestampMS(1792370117673),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_DOGE,
        amount=FVal('0.587616346289181345'),
        location_label='htx',
        unique_id='8208887641319065',
    ), SwapEvent(
        timestamp=TimestampMS(1792370117673),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_DOGE,
        amount=FVal('0.62254395'),
        location_label='htx',
        unique_id='8208887641319065',
    ), SwapEvent(
        timestamp=TimestampMS(1792370117673),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal('5.638107804'),
        location_label='htx',
        unique_id='1836658935934866',
    ), SwapEvent(
        timestamp=TimestampMS(1792370117673),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_DOGE,
        amount=FVal('8.1662'),
        location_label='htx',
        unique_id='1836658935934866',
    ), SwapEvent(
        timestamp=TimestampMS(1792370117673),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_DOGE,
        amount=FVal('0.006007'),
        location_label='htx',
        unique_id='1836658935934866',
    ), SwapEvent(
        timestamp=TimestampMS(1792370117672),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal('59.7459566'),
        location_label='htx',
        unique_id='2186266790953303',
    ), SwapEvent(
        timestamp=TimestampMS(1792370117672),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_DOGE,
        amount=FVal('1.537'),
        location_label='htx',
        unique_id='2186266790953303',
    ), SwapEvent(
        timestamp=TimestampMS(1792370117672),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_DOGE,
        amount=FVal('0.003074'),
        location_label='htx',
        unique_id='2186266790953303',
    ), SwapEvent(
        timestamp=TimestampMS(1710354800452),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_DAI,
        amount=FVal('1038.18'),
        location_label='htx',
        unique_id='1552611026239689',
    ), SwapEvent(
        timestamp=TimestampMS(1710354800452),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        amount=FVal('1037.660910'),
        location_label='htx',
        unique_id='1552611026239689',
    ), SwapEvent(
        timestamp=TimestampMS(1710354800452),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDT,
        amount=FVal('2.07532182'),
        location_label='htx',
        unique_id='1552611026239689',
    ), SwapEvent(
        timestamp=TimestampMS(1710354800451),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_DAI,
        amount=FVal('26.3'),
        location_label='htx',
        unique_id='3409716930791340',
    ), SwapEvent(
        timestamp=TimestampMS(1710354800451),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        amount=FVal('26.28948'),
        location_label='htx',
        unique_id='3409716930791340',
    ), SwapEvent(
        timestamp=TimestampMS(1710354800451),
        location=Location.HTX,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDT,
        amount=FVal('0.05257896'),
        location_label='htx',
        unique_id='3409716930791340',
    )]
