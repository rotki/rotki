import warnings as test_warnings
from typing import Optional, Set
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import UNSUPPORTED_FTX_ASSETS, asset_from_ftx
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_1INCH, A_ETH, A_USD, A_USDC
from rotkehlchen.errors import UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.exchanges.ftx import Ftx
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import AssetMovementCategory, Fee, Location, Timestamp, TradeType

TEST_END_TS = Timestamp(1617382780)


def test_name(database):
    exchange = Ftx('ftx1', 'a', b'a', database, object(), None)
    assert exchange.location == Location.FTX
    assert exchange.name == 'ftx1'


def test_ftx_exchange_assets_are_known(mock_ftx: Ftx):

    unknown_assets: Set[str] = set()
    unsupported_assets = set(UNSUPPORTED_FTX_ASSETS)

    def process_currency(currency: Optional[str]):
        """Check if a currency is known for the FTX exchange"""
        if currency is None:
            return
        try:
            if currency not in unknown_assets:
                asset_from_ftx(base_currency)
        except UnsupportedAsset:
            assert base_currency in unsupported_assets
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.asset_name} in FTX. '
                f'Support for it has to be added',
            ))
            unknown_assets.add(base_currency)

    response = mock_ftx._api_query(endpoint='markets', paginate=False)

    # Extract the unique symbols from the exchange pairs
    for entry in response:
        if entry['type'] == 'future':
            continue

        base_currency = entry.get('baseCurrency', None)
        quote_currency = entry.get('quoteCurrency', None)
        process_currency(base_currency)
        process_currency(quote_currency)


FILLS_RESPONSE = """{
"success": true,
"result": [
    {
        "id": 1,
        "market": "ETH/USD",
        "future": null,
        "baseCurrency": "ETH",
        "quoteCurrency": "USD",
        "type": "order",
        "side": "sell",
        "price": 2000,
        "size": 1,
        "orderId": 1,
        "time": "2021-02-27T01:01:01.662266+00:00",
        "tradeId": 1,
        "feeRate": 0.0002,
        "fee": 4,
        "feeCurrency": "USD",
        "liquidity": "taker"
    },
    {
        "id": 2,
        "market": "1INCH/ETH",
        "future": null,
        "baseCurrency": "1INCH",
        "quoteCurrency": "ETH",
        "type": "order",
        "side": "buy",
        "price": 0.005,
        "size": 400,
        "orderId": 2,
        "time": "2021-03-10T01:01:01.662266+00:00",
        "tradeId": 2,
        "feeRate": 0.0002,
        "fee": 0.0004,
        "feeCurrency": "ETH",
        "liquidity": "taker"
    },
    {
        "id": 3,
        "market": "1INCH/ETH",
        "future": null,
        "baseCurrency": "1INCH",
        "quoteCurrency": "ETH",
        "type": "order",
        "side": "sell",
        "price": 0.006,
        "size": 200,
        "orderId": 3,
        "time": "2021-03-11T01:01:01.662266+00:00",
        "tradeId": 3,
        "feeRate": 0.5,
        "fee": 0.6,
        "feeCurrency": "BTC",
        "liquidity": "taker"
    }
]
}
"""

BALANCES_RESPONSE = """{
"result": {
    "iron": [
        {
            "coin": "USDC",
            "total": 10000.0,
            "free": 10000.0,
            "availableWithoutBorrow": 10000.0,
            "usdValue": 10000.0,
            "spotBorrow": 0.0
        },
        {
            "coin": "ETH",
            "total": 10.0,
            "free": 10.0,
            "availableWithoutBorrow": 10.0,
            "usdValue": 20000.0,
            "spotBorrow": 0.0
        }
    ],
    "hacks": [
        {
            "coin": "ETH",
            "total": 10000.0,
            "free": 10000.0,
            "availableWithoutBorrow": 10000.0,
            "usdValue": 20000000.0,
            "spotBorrow": 0.0
        }
    ]
} }
"""

WITHDRAWALS_RESPONSE = """
{
    "result": [
        {
            "id": 1,
            "coin": "ETH",
            "txid": "0xbb27f24c2a348526fc23767d3d8bb303099e90f253ef9fdbb28ce38c1635d116",
            "address": {
                "address": "0x903d12bf2c57a29f32365917c706ce0e1a84cce3",
                "tag": null,
                "method": "eth",
                "coin": null
            },
            "size": 11.0,
            "fee": 0.0,
            "status": "confirmed",
            "time": "2021-02-01T06:06:06.300000+00:00",
            "sentTime": "2021-02-01T06:06:06.300000+00:00",
            "confirmedTime": "2021-02-01T06:06:06.300000+00:00",
            "confirmations": 200
        },
        {
            "id": 2,
            "coin": "USD",
            "size": 21.0,
            "time": "2021-02-01T06:06:06.300000+00:00",
            "notes": "Super sercret",
            "status": "complete"
        }
    ]
}
"""

DEPOSITS_RESPONSE = """
{
    "result": [
        {
            "id": 3,
            "coin": "ETH",
            "txid": "0xf787fa6b62edf1c97fb3f73f80a5eb7550bbf3dcf4269b9bfb9e8c1c0a3bc1a9",
            "address": {
                "address": "0x541163adf0a2e830d9f940763e912807d1a359f5",
                "tag": null,
                "method": "eth",
                "coin": null
            },
            "size": 20.0,
            "fee": 0.0,
            "status": "confirmed",
            "time": "2021-02-01T06:06:06.300000+00:00",
            "sentTime": "2021-02-01T06:06:06.300000+00:00",
            "confirmedTime": "2021-02-01T06:06:06.300000+00:00",
            "confirmations": 333
        }
    ]
}
"""


def mock_normal_ftx_query(url: str, **kwargs):  # pylint: disable=unused-argument
    if 'fills' in url:
        return MockResponse(200, FILLS_RESPONSE)
    if 'deposits' in url:
        return MockResponse(200, DEPOSITS_RESPONSE)
    if 'withdrawals' in url:
        return MockResponse(200, WITHDRAWALS_RESPONSE)
    if 'balances' in url:
        return MockResponse(200, BALANCES_RESPONSE)
    # else
    raise AssertionError(f'Unexpected url {url} for test')


def query_ftx_and_test(
        ftx: Ftx,
        query_fn_name: str,
        fills_response: str = FILLS_RESPONSE,
        deposits_response: str = DEPOSITS_RESPONSE,
        withdrawals_response: str = WITHDRAWALS_RESPONSE,
        expected_warnings_num: int = 0,
        expected_errors_num: int = 0,
        # Since this test only mocks as breaking only one of the two actions by default
        expected_actions_num: int = 1,
):
    def mock_ftx_query(url, **kwargs):  # pylint: disable=unused-argument
        if 'fills' in url:
            return MockResponse(200, fills_response)
        if 'deposits' in url:
            return MockResponse(200, deposits_response)
        if 'withdrawals' in url:
            return MockResponse(200, withdrawals_response)
        # else
        raise AssertionError(f'Unexpected url {url} for test')

    query_fn = getattr(ftx, query_fn_name)
    with patch.object(ftx.session, 'get', side_effect=mock_ftx_query):
        actions = query_fn(
            start_ts=Timestamp(0),
            end_ts=TEST_END_TS,
        )

    errors = ftx.msg_aggregator.consume_errors()
    warnings = ftx.msg_aggregator.consume_warnings()
    assert len(actions) == expected_actions_num
    assert len(errors) == expected_errors_num
    assert len(warnings) == expected_warnings_num


def test_ftx_trade_history(mock_ftx):
    """Test the happy path when querying trades"""
    with patch.object(mock_ftx.session, 'get', side_effect=mock_normal_ftx_query):
        trades = mock_ftx.query_online_trade_history(
            start_ts=0,
            end_ts=TEST_END_TS,
        )
    warnings = mock_ftx.msg_aggregator.consume_warnings()
    errors = mock_ftx.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(trades) == 3

    expected_trades = [Trade(
        timestamp=Timestamp(1614387662),
        location=Location.FTX,
        base_asset=A_ETH,
        quote_asset=A_USD,
        trade_type=TradeType.SELL,
        amount=FVal('1'),
        rate=FVal('2000'),
        fee=FVal('4'),
        fee_currency=A_USD,
        link='1',
    ), Trade(
        timestamp=Timestamp(1615338062),
        location=Location.FTX,
        base_asset=A_1INCH,
        quote_asset=A_ETH,
        trade_type=TradeType.BUY,
        amount=FVal('400'),
        rate=FVal('0.005'),
        fee=FVal('0.0004'),
        fee_currency=A_ETH,
        link='2',
    ), Trade(
        timestamp=Timestamp(1615424462),
        location=Location.FTX,
        base_asset=A_1INCH,
        quote_asset=A_ETH,
        trade_type=TradeType.SELL,
        amount=FVal('200'),
        rate=FVal('0.006'),
        fee=FVal('0.6'),
        fee_currency=Asset('BTC'),
        link='3',
    )]

    assert trades == expected_trades


def test_ftx_trade_history_unexpected_data(mock_ftx):
    """Test that the trade history handles invalid data"""
    query_ftx_and_test(
        ftx=mock_ftx,
        query_fn_name='query_online_trade_history',
        expected_warnings_num=0,
        expected_errors_num=0,
        expected_actions_num=3,
    )

    # missing key
    broken_response = FILLS_RESPONSE.replace('size', 'ides')
    query_ftx_and_test(
        ftx=mock_ftx,
        fills_response=broken_response,
        query_fn_name='query_online_trade_history',
        expected_warnings_num=0,
        expected_errors_num=3,
        expected_actions_num=0,
    )

    # Invalid time
    broken_response = FILLS_RESPONSE.replace('2021-03-11T01:01:01.662266+00:00', 'true')
    query_ftx_and_test(
        ftx=mock_ftx,
        fills_response=broken_response,
        query_fn_name='query_online_trade_history',
        expected_warnings_num=0,
        expected_errors_num=1,
        expected_actions_num=2,
    )

    # Unknown assets
    broken_response = FILLS_RESPONSE.replace('USD', 'oldmoney')
    query_ftx_and_test(
        ftx=mock_ftx,
        fills_response=broken_response,
        query_fn_name='query_online_trade_history',
        expected_warnings_num=1,
        expected_errors_num=0,
        expected_actions_num=2,
    )

    # Invalid asset format
    broken_response = FILLS_RESPONSE.replace('USD', '123')
    query_ftx_and_test(
        ftx=mock_ftx,
        fills_response=broken_response,
        query_fn_name='query_online_trade_history',
        expected_warnings_num=1,
        expected_errors_num=0,
        expected_actions_num=2,
    )

    # Invalid trade types
    broken_response = FILLS_RESPONSE.replace('buy', 'investmentss')
    query_ftx_and_test(
        ftx=mock_ftx,
        fills_response=broken_response,
        query_fn_name='query_online_trade_history',
        expected_warnings_num=0,
        expected_errors_num=1,
        expected_actions_num=2,
    )

    # Invalid amount
    broken_response = FILLS_RESPONSE.replace('400', '"four hundred"')
    query_ftx_and_test(
        ftx=mock_ftx,
        fills_response=broken_response,
        query_fn_name='query_online_trade_history',
        expected_warnings_num=0,
        expected_errors_num=1,
        expected_actions_num=2,
    )

    # Invalid fee amount
    broken_response = FILLS_RESPONSE.replace('0.6', '"zero dot six"')
    query_ftx_and_test(
        ftx=mock_ftx,
        fills_response=broken_response,
        query_fn_name='query_online_trade_history',
        expected_warnings_num=0,
        expected_errors_num=1,
        expected_actions_num=2,
    )

    # Unknown fee asset
    broken_response = FILLS_RESPONSE.replace('BTC', 'AUGMENTED')
    query_ftx_and_test(
        ftx=mock_ftx,
        fills_response=broken_response,
        query_fn_name='query_online_trade_history',
        expected_warnings_num=1,
        expected_errors_num=0,
        expected_actions_num=2,
    )


@pytest.mark.parametrize('mocked_current_prices', [{
    A_USDC: FVal(1),
    "ETH": FVal(2000),
}])
def test_balances(mock_ftx: Ftx):
    """Test that balances are correctly extracted"""

    with patch.object(mock_ftx.session, 'get', side_effect=mock_normal_ftx_query):
        balances, msg = mock_ftx.query_balances()

    warnings = mock_ftx.msg_aggregator.consume_warnings()
    errors = mock_ftx.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_USDC].amount == FVal('10000.0')
    assert balances[A_ETH].amount == FVal('10010.0')
    assert balances[A_USDC].usd_value == FVal('10000.0')
    assert balances[A_ETH].usd_value == FVal('20020000.0')


def test_query_deposits_withdrawals(mock_ftx: Ftx):
    """Test happy path of deposits/withdrawls"""
    with patch.object(mock_ftx.session, 'get', side_effect=mock_normal_ftx_query):
        movements = mock_ftx.query_online_deposits_withdrawals(
            start_ts=Timestamp(0),
            end_ts=TEST_END_TS,
        )
    warnings = mock_ftx.msg_aggregator.consume_warnings()
    errors = mock_ftx.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0

    expected_movements = [AssetMovement(
        location=Location.FTX,
        category=AssetMovementCategory.DEPOSIT,
        address='0x541163adf0a2e830d9f940763e912807d1a359f5',
        transaction_id='0xf787fa6b62edf1c97fb3f73f80a5eb7550bbf3dcf4269b9bfb9e8c1c0a3bc1a9',
        timestamp=Timestamp(1612159566),
        asset=A_ETH,
        amount=FVal('20'),
        fee_asset=A_ETH,
        fee=Fee(ZERO),
        link='3',
    ), AssetMovement(
        location=Location.FTX,
        category=AssetMovementCategory.WITHDRAWAL,
        timestamp=Timestamp(1612159566),
        address='0x903d12bf2c57a29f32365917c706ce0e1a84cce3',
        transaction_id='0xbb27f24c2a348526fc23767d3d8bb303099e90f253ef9fdbb28ce38c1635d116',
        asset=A_ETH,
        amount=FVal('11.0'),
        fee_asset=A_ETH,
        fee=Fee(ZERO),
        link='1',
    ), AssetMovement(
        location=Location.FTX,
        category=AssetMovementCategory.WITHDRAWAL,
        address=None,
        transaction_id=None,
        timestamp=Timestamp(1612159566),
        asset=A_USD,
        amount=FVal('21.0'),
        fee_asset=A_USD,
        fee=Fee(ZERO),
        link='2',
    )]

    assert len(movements) == 3
    assert movements == expected_movements


def test_query_deposits_withdrawals_unexpected_data(mock_ftx: Ftx):
    """Test that ftx deposit/withdrawals query handles unexpected data properly"""
    # first query with proper data and expect no errors
    query_ftx_and_test(
        ftx=mock_ftx,
        query_fn_name='query_online_deposits_withdrawals',
        expected_warnings_num=0,
        expected_errors_num=0,
        expected_actions_num=3,
    )

    # invalid payout_at timestamp
    # Here the number of errors is 1 more since it tries pagination
    # but since the result is the same no new entries are added.
    broken_response = DEPOSITS_RESPONSE.replace('"2021-02-01T06:06:06.300000+00:00"', '"dadas"')
    query_ftx_and_test(
        ftx=mock_ftx,
        query_fn_name='query_online_deposits_withdrawals',
        deposits_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=2,
        expected_actions_num=2,
    )

    # unknown asset
    broken_response = WITHDRAWALS_RESPONSE.replace('"USD"', '"dasdad"')
    query_ftx_and_test(
        ftx=mock_ftx,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=1,
        expected_errors_num=0,
        expected_actions_num=2,
    )

    # invalid asset
    broken_response = WITHDRAWALS_RESPONSE.replace('"USD"', '{}')
    query_ftx_and_test(
        ftx=mock_ftx,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
        expected_actions_num=2,
    )

    # invalid amount
    broken_response = WITHDRAWALS_RESPONSE.replace('21.0', 'true')
    query_ftx_and_test(
        ftx=mock_ftx,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
        expected_actions_num=2,
    )

    # invalid fee
    broken_response = WITHDRAWALS_RESPONSE.replace('0.0', '"dasd"')
    query_ftx_and_test(
        ftx=mock_ftx,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
        expected_actions_num=2,
    )


def test_pagination(mock_ftx: Ftx):
    """Test pagination in the eth/eur market (public endpoint)"""
    # Try pagination good path
    response = mock_ftx._api_query(
        endpoint='markets/eth/eur/trades',
        limit=3,
        start_time=Timestamp(1617716695),
        end_time=Timestamp(1617724135),
    )

    assert len(response) == 24

    # Try with a page size divisor of the total orders
    response = mock_ftx._api_query(
        endpoint='markets/eth/eur/trades',
        limit=3,
        start_time=Timestamp(1617716695),
        end_time=Timestamp(1617724135),
    )

    assert len(response) == 24

    # Try pagination with same dates. Should return empty list
    response = mock_ftx._api_query(
        endpoint='markets/eth/eur/trades',
        limit=3,
        start_time=Timestamp(1617716695),
        end_time=Timestamp(1617716695),
    )

    assert len(response) == 0
