import warnings as test_warnings
from unittest.mock import patch

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import UNSUPPORTED_BITTREX_ASSETS, asset_from_bittrex
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_LTC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.bittrex import Bittrex
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_timestamp_from_date
from rotkehlchen.tests.utils.history import TEST_END_TS
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import AssetMovementCategory, Location, TradeType


def test_deserialize_timestamp_from_bittrex_date():
    """Test for deserialize_timestamp_from_bittrex_date() and regression for #1151

    In https://github.com/rotki/rotki/issues/1151 a user encountered an error with
    the following date: 2017-07-08T07:57:12
    """
    assert deserialize_timestamp_from_date('2014-02-13T00:00:00.00Z', 'iso8601', '') == 1392249600
    assert deserialize_timestamp_from_date('2015-06-15T07:38:53.883Z', 'iso8601', '') == 1434353934
    assert deserialize_timestamp_from_date('2015-08-19T04:24:47.217Z', 'iso8601', '') == 1439958287
    assert deserialize_timestamp_from_date('2017-07-08T07:57:12Z', 'iso8601', '') == 1499500632


def test_name():
    exchange = Bittrex('bittrex1', 'a', b'a', object(), object())
    assert exchange.location == Location.BITTREX
    assert exchange.name == 'bittrex1'


def test_bittrex_assets_are_known(bittrex):
    currencies = bittrex.get_currencies()
    for bittrex_asset in currencies:
        symbol = bittrex_asset['symbol']
        try:
            _ = asset_from_bittrex(symbol)
        except UnsupportedAsset:
            assert symbol in UNSUPPORTED_BITTREX_ASSETS
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.asset_name} in Bittrex. Support for it has to be added',
            ))


def test_bittrex_query_balances_unknown_asset(bittrex):
    def mock_unknown_asset_return(method, url, json, **kwargs):  # pylint: disable=unused-argument
        response = MockResponse(
            200,
            """
[
    {
      "currencySymbol": "BTC",
      "total": "5.0",
      "available": "5.0"
    },
    {
      "currencySymbol": "ETH",
      "total": "10.0",
      "available": "10.0"
    },
    {
      "currencySymbol": "IDONTEXIST",
      "total": "15.0",
      "available": "15.0"
    },
    {
      "currencySymbol": "PTON",
      "total": "15.0",
      "available": "15.0"
    }
]
            """,
        )
        return response

    with patch.object(bittrex.session, 'request', side_effect=mock_unknown_asset_return):
        # Test that after querying the assets only ETH and BTC are there
        balances, msg = bittrex.query_balances()

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_BTC].amount == FVal('5.0')
    assert balances[A_ETH].amount == FVal('10.0')

    warnings = bittrex.msg_aggregator.consume_warnings()
    assert len(warnings) == 2
    assert 'unknown bittrex asset IDONTEXIST' in warnings[0]
    assert 'unsupported bittrex asset PTON' in warnings[1]


BITTREX_LIMIT_TRADE = """
    {
      "id": "fd97d393-e9b9-4dd1-9dbf-f288fc72a185",
      "marketSymbol": "LTC-BTC",
      "direction": "BUY",
      "type": "LIMIT",
      "fillQuantity": 667.03644955,
      "limit": 0.0000295,
      "proceeds": 0.0196775752617,
      "commission": 0.00004921,
      "closedAt": "2014-02-13T00:00:00.00Z"
    }"""

BITTREX_MARKET_TRADE = """
    {
      "id": "ad97d393-19b9-6dd1-9dbf-f288fc72a185",
      "marketSymbol": "ETH-BTC",
      "direction": "SELL",
      "type": "MARKET",
      "fillQuantity": 2,
      "proceeds": 10,
      "commission": 0.00001,
      "closedAt": "2014-02-13T00:00:00.00Z"
    }"""
BITTREX_ORDER_HISTORY_RESPONSE = f'[{BITTREX_LIMIT_TRADE}, {BITTREX_MARKET_TRADE}]'


def test_bittrex_query_trade_history(bittrex):
    """Test that turning a bittrex trade to our format works"""

    def mock_order_history(url, method, json):  # pylint: disable=unused-argument
        response = MockResponse(200, BITTREX_ORDER_HISTORY_RESPONSE)
        return response

    with patch.object(bittrex.session, 'request', side_effect=mock_order_history):
        trades = bittrex.query_trade_history(start_ts=0, end_ts=1564301134, only_cache=False)

    expected_trades = [Trade(
        timestamp=1392249600,
        location=Location.BITTREX,
        base_asset=A_LTC,
        quote_asset=A_BTC,
        trade_type=TradeType.BUY,
        amount=FVal('667.03644955'),
        rate=FVal('0.0000295'),
        fee=FVal('0.00004921'),
        fee_currency=A_BTC,
        link='fd97d393-e9b9-4dd1-9dbf-f288fc72a185',
    ), Trade(
        timestamp=1392249600,
        location=Location.BITTREX,
        base_asset=A_ETH,
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=FVal('2'),
        rate=FVal('5'),
        fee=FVal('0.00001'),
        fee_currency=A_BTC,
        link='ad97d393-19b9-6dd1-9dbf-f288fc72a185',
    )]
    assert expected_trades == trades


def test_bittrex_query_trade_history_unexpected_data(bittrex):
    """Test that turning a bittrex trade that contains unexpected data is handled gracefully"""
    # turn caching off
    bittrex.cache_ttl_secs = 0

    def mock_order_history(url, method, json):  # pylint: disable=unused-argument
        response = MockResponse(200, BITTREX_ORDER_HISTORY_RESPONSE)
        return response

    def query_bittrex_and_test(
            input_trade_str,
            expected_warnings_num,
            expected_errors_num,
            warning_str_test=None,
            error_str_test=None,
    ):
        patch_get = patch.object(bittrex.session, 'request', side_effect=mock_order_history)
        patch_response = patch(
            'rotkehlchen.tests.exchanges.test_bittrex.BITTREX_ORDER_HISTORY_RESPONSE',
            new=input_trade_str,
        )
        with patch_get, patch_response:
            # Test that after querying the assets only ETH and BTC are there
            trades = bittrex.query_online_trade_history(start_ts=0, end_ts=1564301134)

        assert len(trades) == 0
        errors = bittrex.msg_aggregator.consume_errors()
        warnings = bittrex.msg_aggregator.consume_warnings()
        assert len(errors) == expected_errors_num
        assert len(warnings) == expected_warnings_num
        if warning_str_test:
            assert warning_str_test in warnings[0]
        if error_str_test:
            assert error_str_test in errors[0]

    history = f'[{BITTREX_LIMIT_TRADE}]'
    input_str = history.replace(
        '"fillQuantity": 667.03644955',
        '"fillQuantity": "fdfdsf"',
    )
    query_bittrex_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    input_str = history.replace(
        '"closedAt": "2014-02-13T00:00:00.00Z"',
        '"closedAt": null',
    )
    query_bittrex_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    input_str = history.replace(
        '"limit": 0.0000295',
        '"limit": "sdad"',
    )
    query_bittrex_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    input_str = history.replace(
        '"direction": "BUY"',
        '"direction": "dsadsd"',
    )
    query_bittrex_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    input_str = history.replace(
        '"commission": 0.00004921',
        '"commission": "dasdsad"',
    )
    query_bittrex_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    # Check that for non-string pairs we give a graceful error
    input_str = history.replace(
        '"marketSymbol": "LTC-BTC"',
        '"marketSymbol": 4324234',
    )
    query_bittrex_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    # Check that for unsupported assets in the pair are caught
    input_str = history.replace(
        '"marketSymbol": "LTC-BTC"',
        '"marketSymbol": "BTC-PTON"',
    )
    query_bittrex_and_test(
        input_str,
        expected_warnings_num=1,
        expected_errors_num=0,
        warning_str_test='Found bittrex trade with unsupported asset PTON',
    )

    # Check that unprocessable pair is caught
    input_str = history.replace(
        '"marketSymbol": "LTC-BTC"',
        '"marketSymbol": "SSSS"',
    )
    query_bittrex_and_test(
        input_str,
        expected_warnings_num=0,
        expected_errors_num=1,
        error_str_test='Found bittrex trade with unprocessable pair SSSS',
    )


BITTREX_DEPOSIT_HISTORY_RESPONSE = """
[
    {
      "id": 1,
      "status": "COMPLETED",
      "quantity": 2.12345678,
      "currencySymbol": "BTC",
      "confirmations": 2,
      "completedAt": "2014-02-13T07:38:53.883Z",
      "txId": "e26d3b33fcfc2cb0c74d0938034956ea590339170bf4102f080eab4b85da9bde",
      "cryptoAddress": "15VyEAT4uf7ycrNWZVb1eGMzrs21BH95Va",
      "source": "foo"
    }, {
      "id": 2,
      "status": "COMPLETED",
      "quantity": 50.81,
      "currencySymbol": "ETH",
      "confirmations": 5,
      "completedAt": "2015-06-15T07:38:53.883Z",
      "txId": "e26d3b33fcfc2cb0cd4d0938034956ea590339170bf4102f080eab4s85da9bde",
      "cryptoAddress": "0x717E2De923A6377Fbd7e3c937491f71ad370e9A8",
      "source": "foo"
    }
]
"""

BITTREX_WITHDRAWAL_HISTORY_RESPONSE = """
[
    {
      "id": "b52c7a5c-90c6-4c6e-835c-e16df12708b1",
      "status": "COMPLETED",
      "currencySymbol": "BTC",
      "quantity": 17,
      "cryptoAddress": "1DeaaFBdbB5nrHj87x3NHS4onvw1GPNyAu",
      "completedAt": "2014-07-09T04:24:47.217Z",
      "txCost": 0.0002,
      "txId": "b4a575c2a71c7e56d02ab8e26bb1ef0a2f6cf2094f6ca2116476a569c1e84f6e"
    }, {
      "id": "b52c7a5c-90c6-4c6e-835c-e16df12708b1",
      "status": "COMPLETED",
      "currencySymbol": "ETH",
      "quantity": 55,
      "cryptoAddress": "0x717E2De923A6377Fbd7e3c937491f71ad370e9A8",
      "completedAt": "2015-08-19T04:24:47.217Z",
      "txCost": 0.0015,
      "txId": "0xc65d3391739c96a04b868b205b34069f0bbd7ab7f62d1f59be02f29e77b59247"
    }
]
"""


def test_bittrex_query_deposits_withdrawals(bittrex):
    """Test the happy case of bittrex deposit withdrawal query"""

    def mock_get_deposit_withdrawal(
        url,
        method,
        json,
        **kwargs,
    ):  # pylint: disable=unused-argument
        if 'deposit' in url:
            response_str = BITTREX_DEPOSIT_HISTORY_RESPONSE
        else:
            response_str = BITTREX_WITHDRAWAL_HISTORY_RESPONSE

        return MockResponse(200, response_str)

    with patch.object(bittrex.session, 'request', side_effect=mock_get_deposit_withdrawal):
        movements = bittrex.query_online_deposits_withdrawals(start_ts=0, end_ts=TEST_END_TS)

    errors = bittrex.msg_aggregator.consume_errors()
    warnings = bittrex.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0

    assert len(movements) == 4

    assert movements[0].location == Location.BITTREX
    assert movements[0].category == AssetMovementCategory.DEPOSIT
    assert movements[0].timestamp == 1392277134
    assert isinstance(movements[0].asset, Asset)
    assert movements[0].asset == A_BTC
    assert movements[0].amount == FVal('2.12345678')
    assert movements[0].fee == ZERO

    assert movements[1].location == Location.BITTREX
    assert movements[1].category == AssetMovementCategory.DEPOSIT
    assert movements[1].timestamp == 1434353934
    assert isinstance(movements[1].asset, Asset)
    assert movements[1].asset == A_ETH
    assert movements[1].amount == FVal('50.81')
    assert movements[1].fee == ZERO

    assert movements[2].location == Location.BITTREX
    assert movements[2].category == AssetMovementCategory.WITHDRAWAL
    assert movements[2].timestamp == 1404879887
    assert isinstance(movements[2].asset, Asset)
    assert movements[2].asset == A_BTC
    assert movements[2].amount == FVal('17')
    assert movements[2].fee == FVal('0.0002')

    assert movements[3].location == Location.BITTREX
    assert movements[3].category == AssetMovementCategory.WITHDRAWAL
    assert movements[3].timestamp == 1439958287
    assert isinstance(movements[3].asset, Asset)
    assert movements[3].asset == A_ETH
    assert movements[3].amount == FVal('55')
    assert movements[3].fee == FVal('0.0015')


def test_bittrex_query_asset_movement_int_transaction_id(bittrex):
    """Test that if an integer is returned for bittrex transaction id we handle it properly

    Bittrex deposit withdrawals SHOULD NOT return an integer for transaction id
    according to their docs https://bittrex.github.io/api/v3#definition-Order
    but as we saw in practise they sometimes can.

    Regression test for https://github.com/rotki/rotki/issues/2175
    """

    problematic_deposit = """
[
    {
      "id": 1,
      "status": "COMPLETED",
      "quantity": 2.12345678,
      "currencySymbol": "RISE",
      "confirmations": 2,
      "completedAt": "2014-02-13T07:38:53.883Z",
      "txId": 9875231951530679373,
      "cryptoAddress": "15VyEAT4uf7ycrNWZVb1eGMzrs21BH95Va",
      "source": "foo"
    }
]
"""

    def mock_get_deposit_withdrawal(
        url,
        method,
        json,
        **kwargs,
    ):  # pylint: disable=unused-argument
        if 'deposit' in url:
            response_str = problematic_deposit
        else:
            response_str = '[]'

        return MockResponse(200, response_str)

    with patch.object(bittrex.session, 'request', side_effect=mock_get_deposit_withdrawal):
        movements = bittrex.query_deposits_withdrawals(
            start_ts=0,
            end_ts=TEST_END_TS,
            only_cache=False,
        )

    errors = bittrex.msg_aggregator.consume_errors()
    warnings = bittrex.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0

    assert len(movements) == 1

    assert movements[0].location == Location.BITTREX
    assert movements[0].category == AssetMovementCategory.DEPOSIT
    assert movements[0].timestamp == 1392277134
    assert isinstance(movements[0].asset, Asset)
    assert movements[0].asset == Asset('RISE')
    assert movements[0].amount == FVal('2.12345678')
    assert movements[0].fee == ZERO
    assert movements[0].transaction_id == '9875231951530679373'

    # also make sure they are written in the db
    db_movements = bittrex.db.get_asset_movements(from_ts=0, to_ts=TEST_END_TS)
    assert len(db_movements) == 1
    assert db_movements[0] == movements[0]


def test_bittrex_query_deposits_withdrawals_unexpected_data(bittrex):
    """Test that we handle unexpected bittrex deposit withdrawal data gracefully"""

    def mock_bittrex_and_query(deposits, withdrawals, expected_warnings_num, expected_errors_num):

        def mock_get_deposit_withdrawal(
            url,
            method,
            json,
            **kwargs,
        ):  # pylint: disable=unused-argument
            if 'deposit' in url:
                response_str = deposits
            else:
                response_str = withdrawals

            return MockResponse(200, response_str)

        with patch.object(bittrex.session, 'request', side_effect=mock_get_deposit_withdrawal):
            movements = bittrex.query_online_deposits_withdrawals(start_ts=0, end_ts=TEST_END_TS)

        if expected_errors_num == 0 and expected_warnings_num == 0:
            assert len(movements) == 1
        else:
            assert len(movements) == 0
            warnings = bittrex.msg_aggregator.consume_warnings()
            assert len(warnings) == expected_warnings_num
            errors = bittrex.msg_aggregator.consume_errors()
            assert len(errors) == expected_errors_num

    def check_permutations_of_input_invalid_data(deposits, withdrawals):
        # First make sure it works with normal data
        mock_bittrex_and_query(
            deposits,
            withdrawals,
            expected_warnings_num=0,
            expected_errors_num=0,
        )
        testing_deposits = 'source' in deposits

        # From here and on test unexpected data
        # invalid timestamp
        if testing_deposits:
            new_deposits = deposits.replace('"2014-07-09T04:24:47.217Z"', '"dsadasd"')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"2014-07-09T04:24:47.217Z"', '"dsadasd"')
        mock_bittrex_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

        # invalid currency
        if testing_deposits:
            new_deposits = deposits.replace('"BTC"', '[]')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"BTC"', '[]')
        mock_bittrex_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

        # Unknown asset
        if testing_deposits:
            new_deposits = deposits.replace('"BTC"', '"dasdsDSDSAD"')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"BTC"', '"dasdsDSDSAD"')
        mock_bittrex_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=1,
            expected_errors_num=0,
        )

        # Unsupported Asset
        if testing_deposits:
            new_deposits = deposits.replace('"BTC"', '"OGO"')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"BTC"', '"OGO"')
        mock_bittrex_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=1,
            expected_errors_num=0,
        )

        # Invalid amount
        if testing_deposits:
            new_deposits = deposits.replace('17', 'null')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('17', 'null')
        mock_bittrex_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

        # Invalid fee, only for withdrawals
        if testing_deposits:
            new_withdrawals = withdrawals.replace('0.0002', '"dsadsda"')
            mock_bittrex_and_query(
                new_deposits,
                new_withdrawals,
                expected_warnings_num=0,
                expected_errors_num=1,
            )

        # Missing Key Error
        if testing_deposits:
            new_deposits = deposits.replace('"currencySymbol": "BTC",', '')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"currencySymbol": "BTC",', '')
        mock_bittrex_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

    # To make the test easy to write the values for deposit/withdrawal attributes
    # are the same in the two examples below
    empty_response = '[]'
    input_withdrawals = """[{
      "id": "b52c7a5c-90c6-4c6e-835c-e16df12708b1",
      "status": "COMPLETED",
      "currencySymbol": "BTC",
      "quantity": 17,
      "cryptoAddress": "1DeaaFBdbB5nrHj87x3NHS4onvw1GPNyAu",
      "completedAt": "2014-07-09T04:24:47.217Z",
      "txCost": 0.0002,
      "txId": "b4a575c2a71c7e56d02ab8e26bb1ef0a2f6cf2094f6ca2116476a569c1e84f6e"
    }]"""
    check_permutations_of_input_invalid_data(
        deposits=empty_response,
        withdrawals=input_withdrawals,
    )

    input_deposits = """[{
      "id": 1,
      "status": "COMPLETED",
      "quantity": 17,
      "currencySymbol": "BTC",
      "confirmations": 2,
      "completedAt": "2014-07-09T04:24:47.217Z",
      "txId": "e26d3b33fcfc2cb0c74d0938034956ea590339170bf4102f080eab4b85da9bde",
      "cryptoAddress": "1DeaaFBdbB5nrHj87x3NHS4onvw1GPNyAu",
      "source": "foo"
    }]"""
    check_permutations_of_input_invalid_data(
        deposits=input_deposits,
        withdrawals=empty_response,
    )
