import warnings as test_warnings
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import (
    BINANCE_TO_WORLD,
    RENAMED_BINANCE_ASSETS,
    UNSUPPORTED_BINANCE_ASSETS,
    asset_from_binance,
)
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import RemoteError, UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.binance import Binance, trade_from_binance
from rotkehlchen.exchanges.data_structures import Exchange, Trade, TradeType
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_BNB, A_RDN, A_USDT, A_XMR
from rotkehlchen.tests.utils.exchanges import BINANCE_BALANCES_RESPONSE
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret
from rotkehlchen.tests.utils.history import TEST_END_TS
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.user_messages import MessagesAggregator


def test_trade_from_binance(function_scope_binance):
    binance = function_scope_binance
    binance_trades_list = [
        {
            'symbol': 'RDNETH',
            'id': 1,
            'orderId': 1,
            'price': FVal(0.0063213),
            'qty': FVal(5.0),
            'commission': FVal(0.005),
            'commissionAsset': 'RDN',
            'time': 1512561941000,
            'isBuyer': True,
            'isMaker': False,
            'isBestMatch': True,
        }, {
            'symbol': 'ETHUSDT',
            'id': 2,
            'orderId': 2,
            'price': FVal(481.0),
            'qty': FVal(0.505),
            'commission': FVal(0.242905),
            'commissionAsset': 'USDT',
            'time': 1531117990000,
            'isBuyer': False,
            'isMaker': True,
            'isBestMatch': True,
        }, {
            'symbol': 'BTCUSDT',
            'id': 3,
            'orderId': 3,
            'price': FVal(6376.39),
            'qty': FVal(0.051942),
            'commission': FVal(0.00005194),
            'commissionAsset': 'BTC',
            'time': 1531728338000,
            'isBuyer': True,
            'isMaker': False,
            'isBestMatch': True,
        }, {
            'symbol': 'ADAUSDT',
            'id': 4,
            'orderId': 4,
            'price': FVal(0.17442),
            'qty': FVal(285.2),
            'commission': FVal(0.00180015),
            'commissionAsset': 'BNB',
            'time': 1531871806000,
            'isBuyer': False,
            'isMaker': True,
            'isBestMatch': True,
        },
    ]
    our_expected_list = [
        Trade(
            timestamp=1512561941,
            location='binance',
            pair='RDN_ETH',
            trade_type=TradeType.BUY,
            amount=FVal(5.0),
            rate=FVal(0.0063213),
            fee=FVal(0.005),
            fee_currency=A_RDN,
            link='1',
        ),
        Trade(
            timestamp=1531117990,
            location='binance',
            pair='ETH_USDT',
            trade_type=TradeType.SELL,
            amount=FVal(0.505),
            rate=FVal(481.0),
            fee=FVal(0.242905),
            fee_currency=A_USDT,
            link='2',
        ),
        Trade(
            timestamp=1531728338,
            location='binance',
            pair='BTC_USDT',
            trade_type=TradeType.BUY,
            amount=FVal(0.051942),
            rate=FVal(6376.39),
            fee=FVal(0.00005194),
            fee_currency=A_BTC,
            link='3',
        ),
        Trade(
            timestamp=1531871806,
            location='binance',
            pair='ADA_USDT',
            trade_type=TradeType.SELL,
            amount=FVal(285.2),
            rate=FVal(0.17442),
            fee=FVal(0.00180015),
            fee_currency=A_BNB,
            link='4',
        ),
    ]

    for idx, binance_trade in enumerate(binance_trades_list):
        our_trade = trade_from_binance(binance_trade, binance.symbols_to_pair)
        assert our_trade == our_expected_list[idx]
        assert isinstance(our_trade.fee_currency, Asset)


exchange_info_mock_text = '''{
  "timezone": "UTC",
  "serverTime": 1508631584636,
  "symbols": [{
    "symbol": "ETHBTC",
    "status": "TRADING",
    "baseAsset": "ETH",
    "baseAssetPrecision": 8,
    "quoteAsset": "BTC",
    "quotePrecision": 8,
    "icebergAllowed": false
    }]
}'''


def test_binance_backoff_after_429(function_scope_binance):
    count = 0
    binance = function_scope_binance

    def mock_429(url):  # pylint: disable=unused-argument
        nonlocal count
        if count < 2:
            response = MockResponse(429, '{"code": -1103, "msg": "Too many requests"}')
        else:
            response = MockResponse(200, exchange_info_mock_text)
        count += 1
        return response

    binance.initial_backoff = 0.5
    binance.backoff_limit = 2
    with patch.object(binance.session, 'get', side_effect=mock_429):
        # test that after 2 429 cals we finally succeed in the API call
        result = binance.api_query('exchangeInfo')
        assert 'timezone' in result

        # Test the backoff_limit properly returns an error when hit
        count = -9999999
        with pytest.raises(RemoteError):
            binance.api_query('exchangeInfo')


def analyze_binance_assets(sorted_assets):
    """Go through all binance assets and print info whether or not Rotkehlchen
    supports each asset or not.

    This function should be used when wanting to analyze/categorize new Binance assets
    """
    length = len(sorted_assets)
    for idx, binance_asset in enumerate(sorted_assets):
        if binance_asset in RENAMED_BINANCE_ASSETS:
            continue

        binance_asset = BINANCE_TO_WORLD.get(binance_asset, binance_asset)

        if not AssetResolver().is_identifier_canonical(binance_asset):
            raise AssertionError(
                f'{idx}/{length} - {binance_asset} is not known.',
            )
        else:
            asset = Asset(binance_asset)
            print(
                f'{idx}/{length} - {binance_asset} with name {asset.name} is known',
            )


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
                f'Found unknown asset {e.asset_name} in Binance. Support for it has to be added',
            ))


def test_binance_query_balances_unknown_asset(function_scope_binance):
    """Test that if a binance balance query returns unknown asset no exception
    is raised and a warning is generated. Same for unsupported asset."""
    binance = function_scope_binance

    def mock_unknown_asset_return(url):  # pylint: disable=unused-argument
        return MockResponse(200, BINANCE_BALANCES_RESPONSE)

    with patch.object(binance.session, 'get', side_effect=mock_unknown_asset_return):
        # Test that after querying the assets only ETH and BTC are there
        balances, msg = binance.query_balances()

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_BTC]['amount'] == FVal('4723846.89208129')
    assert balances[A_ETH]['amount'] == FVal('4763368.68006011')

    warnings = binance.msg_aggregator.consume_warnings()
    assert len(warnings) == 2
    assert 'unknown binance asset IDONTEXIST' in warnings[0]
    assert 'unsupported binance asset ETF' in warnings[1]


BINANCE_MYTRADES_RESPONSE = """
[
    {
    "symbol": "BNBBTC",
    "id": 28457,
    "orderId": 100234,
    "price": "4.00000100",
    "qty": "12.00000000",
    "quoteQty": "48.000012",
    "commission": "10.10000000",
    "commissionAsset": "BNB",
    "time": 1499865549590,
    "isBuyer": true,
    "isMaker": false,
    "isBestMatch": true
    }]"""


def test_binance_query_trade_history(function_scope_binance):
    """Test that turning a binance trade as returned by the server to our format works"""
    binance = function_scope_binance
    binance.cache_ttl_secs = 0

    def mock_my_trades(url):  # pylint: disable=unused-argument
        if 'symbol=BNBBTC' in url:
            text = BINANCE_MYTRADES_RESPONSE
        else:
            text = '[]'

        return MockResponse(200, text)

    with patch.object(binance.session, 'get', side_effect=mock_my_trades):
        trades = binance.query_trade_history(start_ts=0, end_ts=1564301134)

    expected_trade = Trade(
        timestamp=1499865549,
        location='binance',
        pair='BNB_BTC',
        trade_type=TradeType.BUY,
        amount=FVal('12'),
        rate=FVal('4.00000100'),
        fee=FVal('10.10000000'),
        fee_currency=A_BNB,
        link='28457',
    )

    assert len(trades) == 1
    assert trades[0] == expected_trade


def test_binance_query_trade_history_unexpected_data(function_scope_binance):
    """Test that turning a binance trade that contains unexpected data is handled gracefully"""
    binance = function_scope_binance
    binance.cache_ttl_secs = 0

    def mock_my_trades(url):  # pylint: disable=unused-argument
        if 'symbol=BNBBTC' in url or 'symbol=BTCBBTC' in url:
            text = BINANCE_MYTRADES_RESPONSE
        else:
            text = '[]'

        return MockResponse(200, text)

    def query_binance_and_test(
            input_trade_str,
            expected_warnings_num,
            expected_errors_num,
            warning_str_test=None,
            error_str_test=None,
            query_specific_markets=None,
    ):
        patch_get = patch.object(binance.session, 'get', side_effect=mock_my_trades)
        patch_response = patch(
            'rotkehlchen.tests.test_binance.BINANCE_MYTRADES_RESPONSE',
            new=input_trade_str,
        )
        with patch_get, patch_response:
            trades = binance.query_online_trade_history(
                start_ts=0,
                end_ts=1564301134,
                markets=query_specific_markets,
            )

        assert len(trades) == 0
        errors = binance.msg_aggregator.consume_errors()
        warnings = binance.msg_aggregator.consume_warnings()
        assert len(errors) == expected_errors_num
        assert len(warnings) == expected_warnings_num
        if warning_str_test:
            assert warning_str_test in warnings[0]
        if error_str_test:
            assert error_str_test in errors[0]

    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"qty": "12.00000000"',
        '"qty": "dsadsad"',
    )
    query_binance_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"price": "4.00000100"',
        '"price": null',
    )
    query_binance_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"symbol": "BNBBTC"',
        '"symbol": "nonexistingmarket"',
    )
    query_binance_and_test(
        input_str,
        expected_warnings_num=0,
        expected_errors_num=1,
        query_specific_markets=['BTCBBTC'],
    )

    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"time": 1499865549590',
        '"time": "sadsad"',
    )
    query_binance_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    # Delete an entry
    input_str = BINANCE_MYTRADES_RESPONSE.replace('"isBuyer": true,', '')
    query_binance_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"commission": "10.10000000"',
        '"commission": "fdfdfdsf"',
    )
    query_binance_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    # unsupported fee currency
    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"commissionAsset": "BNB"',
        '"commissionAsset": "BTCB"',
    )
    query_binance_and_test(
        input_str,
        expected_warnings_num=1,
        expected_errors_num=0,
        warning_str_test='Found binance trade with unsupported asset BTCB',
    )

    # unknown fee currency
    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"commissionAsset": "BNB"',
        '"commissionAsset": "DSDSDS"',
    )
    query_binance_and_test(
        input_str,
        expected_warnings_num=1,
        expected_errors_num=0,
        warning_str_test='Found binance trade with unknown asset DSDSDS',
    )


BINANCE_DEPOSITS_HISTORY_RESPONSE = """{
    "depositList": [
        {
            "insertTime": 1508198532000,
            "amount": 0.04670582,
            "asset": "ETH",
            "address": "0x6915f16f8791d0a1cc2bf47c13a6b2a92000504b",
            "txId": "0xdf33b22bdb2b28b1f75ccd201a4a4m6e7g83jy5fc5d5a9d1340961598cfcb0a1",
            "status": 1
        },
        {
            "insertTime": 1508398632000,
            "amount": 1000,
            "asset": "XMR",
            "address": "463tWEBn5XZJSxLU34r6g7h8jtxuNcDbjLSjkn3XAXHCbLrTTErJrBWYgHJQyrCwkNgYvV38",
            "addressTag": "342341222",
            "txId": "b3c6219639c8ae3f9cf010cdc24fw7f7yt8j1e063f9b4bd1a05cb44c4b6e2509",
            "status": 1
        }
    ],
    "success": true
}"""

BINANCE_WITHDRAWALS_HISTORY_RESPONSE = """{
    "withdrawList": [
        {
            "id":"7213fea8e94b4a5593d507237e5a555b",
            "amount": 1,
            "address": "0x6915f16f8791d0a1cc2bf47c13a6b2a92000504b",
            "asset": "ETH",
            "txId": "0xdf33b22bdb2b28b1f75ccd201a4a4m6e7g83jy5fc5d5a9d1340961598cfcb0a1",
            "applyTime": 1518192542000,
            "status": 4
        },
        {
            "id":"7213fea8e94b4a5534ggsd237e5a555b",
            "amount": 850.1,
            "address": "463tWEBn5XZJSxLU34r6g7h8jtxuNcDbjLSjkn3XAXHCbLrTTErJrBWYgHJQyrCwkNgYvyVz8",
            "addressTag": "342341222",
            "txId": "b3c6219639c8ae3f9cf010cdc24fw7f7yt8j1e063f9b4bd1a05cb44c4b6e2509",
            "asset": "XMR",
            "applyTime": 1529198732000,
            "status": 4
        }
    ],
    "success": true
}"""


def test_binance_query_deposits_withdrawals(function_scope_binance):
    """Test the happy case of binance deposit withdrawal query"""
    binance = function_scope_binance
    binance.cache_ttl_secs = 0

    def mock_get_deposit_withdrawal(url):  # pylint: disable=unused-argument
        if 'deposit' in url:
            response_str = BINANCE_DEPOSITS_HISTORY_RESPONSE
        else:
            response_str = BINANCE_WITHDRAWALS_HISTORY_RESPONSE

        return MockResponse(200, response_str)

    with patch.object(binance.session, 'get', side_effect=mock_get_deposit_withdrawal):
        movements = binance.query_deposits_withdrawals(start_ts=0, end_ts=TEST_END_TS)

    errors = binance.msg_aggregator.consume_errors()
    warnings = binance.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0

    assert len(movements) == 4

    assert movements[0].exchange == Exchange.BINANCE
    assert movements[0].category == 'deposit'
    assert movements[0].timestamp == 1508198532
    assert isinstance(movements[0].asset, Asset)
    assert movements[0].asset == A_ETH
    assert movements[0].amount == FVal('0.04670582')
    assert movements[0].fee == ZERO

    assert movements[1].exchange == Exchange.BINANCE
    assert movements[1].category == 'deposit'
    assert movements[1].timestamp == 1508398632
    assert isinstance(movements[1].asset, Asset)
    assert movements[1].asset == A_XMR
    assert movements[1].amount == FVal('1000')
    assert movements[1].fee == ZERO

    assert movements[2].exchange == Exchange.BINANCE
    assert movements[2].category == 'withdrawal'
    assert movements[2].timestamp == 1518192542
    assert isinstance(movements[2].asset, Asset)
    assert movements[2].asset == A_ETH
    assert movements[2].amount == FVal('1')
    assert movements[2].fee == ZERO

    assert movements[3].exchange == Exchange.BINANCE
    assert movements[3].category == 'withdrawal'
    assert movements[3].timestamp == 1529198732
    assert isinstance(movements[3].asset, Asset)
    assert movements[3].asset == A_XMR
    assert movements[3].amount == FVal('850.1')
    assert movements[3].fee == ZERO


def test_binance_query_deposits_withdrawals_unexpected_data(function_scope_binance):
    """Test that we handle unexpected deposit withdrawal query data gracefully"""
    binance = function_scope_binance
    binance.cache_ttl_secs = 0

    def mock_binance_and_query(deposits, withdrawals, expected_warnings_num, expected_errors_num):

        def mock_get_deposit_withdrawal(url):  # pylint: disable=unused-argument
            if 'deposit' in url:
                response_str = deposits
            else:
                response_str = withdrawals

            return MockResponse(200, response_str)

        with patch.object(binance.session, 'get', side_effect=mock_get_deposit_withdrawal):
            movements = binance.query_deposits_withdrawals(start_ts=0, end_ts=TEST_END_TS)

        if expected_errors_num == 0 and expected_warnings_num == 0:
            assert len(movements) == 1
        else:
            assert len(movements) == 0
            warnings = binance.msg_aggregator.consume_warnings()
            assert len(warnings) == expected_warnings_num
            errors = binance.msg_aggregator.consume_errors()
            assert len(errors) == expected_errors_num

    def check_permutations_of_input_invalid_data(deposits, withdrawals):
        # First make sure it works with normal data
        mock_binance_and_query(
            deposits,
            withdrawals,
            expected_warnings_num=0,
            expected_errors_num=0,
        )
        testing_deposits = "amount" in deposits

        # From here and on test unexpected data
        # invalid timestamp
        if testing_deposits:
            new_deposits = deposits.replace('1508198532000', '"dasdd"')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('1508198532000', '"dasdd"')
        mock_binance_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

        # invalid asset
        if testing_deposits:
            new_deposits = deposits.replace('"ETH"', '[]')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"ETH"', '[]')
        mock_binance_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

        # Unknown asset
        if testing_deposits:
            new_deposits = deposits.replace('"ETH"', '"dasdsDSDSAD"')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"ETH"', '"dasdsDSDSAD"')
        mock_binance_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=1,
            expected_errors_num=0,
        )

        # Unsupported Asset
        if testing_deposits:
            new_deposits = deposits.replace('"ETH"', '"BTCB"')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"ETH"', '"BTCB"')
        mock_binance_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=1,
            expected_errors_num=0,
        )

        # Invalid amount
        if testing_deposits:
            new_deposits = deposits.replace('0.04670582', 'null')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('0.04670582', 'null')
        mock_binance_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

        # Missing Key Error
        if testing_deposits:
            new_deposits = deposits.replace('"amount": 0.04670582,', '')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"amount": 0.04670582,', '')
        mock_binance_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

    # To make the test easy to write the values for deposit/withdrawal attributes
    # are the same in the two examples below
    empty_deposits = '{"success": true, "depositList": []}'
    empty_withdrawals = '{"success": true, "withdrawList": []}'
    input_withdrawals = """{
    "success": true,
    "withdrawList": [
        {
            "id":"7213fea8e94b4a5593d507237e5a555b",
            "amount": 0.04670582,
            "address": "0x6915f16f8791d0a1cc2bf47c13a6b2a92000504b",
            "asset": "ETH",
            "txId": "0xdf33b22bdb2b28b1f75ccd201a4a4m6e7g83jy5fc5d5a9d1340961598cfcb0a1",
            "applyTime": 1508198532000,
            "status": 4
        }]}"""
    check_permutations_of_input_invalid_data(
        deposits=empty_deposits,
        withdrawals=input_withdrawals,
    )

    input_deposits = """{
    "success": true,
    "depositList": [
        {
            "insertTime": 1508198532000,
            "amount": 0.04670582,
            "asset": "ETH",
            "address": "0x6915f16f8791d0a1cc2bf47c13a6b2a92000504b",
            "txId": "0xdf33b22bdb2b28b1f75ccd201a4a4m6e7g83jy5fc5d5a9d1340961598cfcb0a1",
            "status": 1
        }]}"""
    check_permutations_of_input_invalid_data(
        deposits=input_deposits,
        withdrawals=empty_withdrawals,
    )
