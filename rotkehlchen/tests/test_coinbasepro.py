import json
import warnings as test_warnings
from enum import Enum
from unittest.mock import patch

from typing_extensions import Literal

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.exchanges.coinbasepro import Coinbasepro, coinbasepro_to_worldpair
from rotkehlchen.exchanges.data_structures import AssetMovement, Location, Trade, TradeType
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_BAT
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import AssetAmount, AssetMovementCategory, Fee, Price, Timestamp, TradePair

POST_REPORT_RESPONSE_TEMPLATE = """{{
"id": "{}",
"type": "fills",
"status": "pending",
"created_at": "2015-01-06T10:34:47.000Z",
"completed_at": null,
"expires_at": "2015-01-13T10:35:47.000Z",
"file_url": null,
"params": {{
"start_date": "2014-11-01T00:00:00.000Z",
"end_date": "2014-11-30T23:59:59.000Z"
}}}}"""

GET_REPORT_RESPONSE_TEMPLATE = """{{
"id": "{}",
"type": "fills",
"status": "ready",
"created_at": "2015-01-06T10:34:47.000Z",
"completed_at": "2015-01-06T10:34:47.000Z",
"expires_at": "2015-01-13T10:35:47.000Z",
"file_url": "{}",
"params": {{
"start_date": "2014-11-01T00:00:00.000Z",
"end_date": "2014-11-30T23:59:59.000Z"
}}}}"""

# Test fill report for the ETH-BAT product
ETH_BAT_REPORT_ID = '0328b97b-bec1-129e-a94c-69232926778d'
ETH_BAT_ROW = 'default,204623,BAT-ETH,SELL,2020-01-13T09:15:06.311Z,1.00000000,BAT,0.00131511,0.00000657555,0.00130853445,ETH'  # noqa: E501
ETH_BAT_REPORT = f"""portfolio,trade id,product,side,created at,size,size unit,price,fee,total,price/fee/total unit
{ETH_BAT_ROW}"""
FILL_REPORT_UNKNOWN_ASSET = f"""portfolio,trade id,product,side,created at,size,size unit,price,fee,total,price/fee/total unit
default,204623,UNKNOWN-ETH,SELL,2020-01-13T09:15:06.311Z,1.00000000,UNKNOWN,0.00131511,0.00000657555,0.00130853445,ETH
{ETH_BAT_ROW}"""
FILL_REPORT_KEY_ERROR = f"""portfolio,trade id,product,side,created at,size,size unit,price,fee,total,price/fee/total unit
2020-01-13T09:15:06.311Z,1.00000000,0.00131511,0.00000657555,0.00130853445,ETH
{ETH_BAT_ROW}"""

# Test account reports
ETH_ACCOUNT_REPORT_ID = '1328b97b-fec1-123e-b94c-69332926771d'
ETH_ACCOUNT_ROWS = """default,match,2020-01-13T09:15:06.315Z,0.0013151100000000,0.0013151100000000,ETH,,204623,5abf20fe-2b79-2315-57d3-c143dd291654
default,fee,2020-01-13T09:15:06.315Z,-0.0000065755500000,0.0013085344500000,ETH,,204623,5abf20fe-2b79-2315-57d3-c143dd291654
default,withdrawal,2020-01-15T23:51:26.478Z,-0.0011085300000000,0.0002000044500000,ETH,fcc61b23-4b51-43f8-da1e-def2d5a217ad,,"""  # noqa: E501
ETH_ACCOUNT_REPORT = f"""portfolio,type,time,amount,balance,amount/balance unit,transfer id,trade id,order id
{ETH_ACCOUNT_ROWS}"""
ETH_ACCOUNT_REPORT_UNKNOWN_ASSET = f"""portfolio,type,time,amount,balance,amount/balance unit,transfer id,trade id,order id
default,withdrawal,2020-01-15T23:54:26.478Z,-0.0011085300000000,0.0002000044500000,UNKNOWN,fcc61b23-3b51-13f8-da1e-def2d5a217ad,,
{ETH_ACCOUNT_ROWS}"""

BAT_ACCOUNT_REPORT_ID = '9321b97c-fac2-224e-a94d-69332916772d'
BAT_ACCOUNT_ROWS = """default,deposit,2020-01-12T23:26:44.073Z,14.2500000000000000,14.2500000000000000,BAT,dfdd574b-25ca-de01-asce-edc3c1f2e987,,
default,deposit,2020-01-12T23:38:29.433Z,160.8000000000000000,175.0500000000000000,BAT,489f76g2-4dda-4ab8-3eac-6dffadaa57ba7,,
default,deposit,2020-01-12T23:57:12.306Z,8.6500000000000000,183.7000000000000000,BAT,34c6d26c-d27d-4218-3d14-1493120543e9,,
default,match,2020-01-13T09:15:06.315Z,-1.0000000000000000,182.7000000000000000,BAT,,204623,5abf20fe-2b79-2315-57d3-c143dd291654"""  # noqa: E501
BAT_ACCOUNT_REPORT = f"""portfolio,type,time,amount,balance,amount/balance unit,transfer id,trade id,order id
{BAT_ACCOUNT_ROWS}"""
BAT_ACCOUNT_REPORT_WRONG_FORMAT = f"""portfolio,type,time,amount,balance,amount/balance unit,transfer id,trade id,order id
default,deposit,2020-01-12T23:57:12.306Z,,foo,BAT,34c6d26c-d27d-4218-3d14-1493120543e9,,
{BAT_ACCOUNT_ROWS}"""

PRODUCTS_RESPONSE = """[{
"id": "BAT-ETH",
 "base_currency": "BAT",
 "quote_currency": "ETH",
 "base_min_size": "1.0",
 "base_max_size": "2500000.0",
 "quote_increment": "0.000001",
 "base_increment": "1.0",
 "display_name": "BAT/ETH",
 "min_market_funds": "0.1",
 "max_market_funds": "100000.0",
 "margin_enabled": false,
 "post_only": false,
 "limit_only": true,
 "cancel_only": false,
 "status": "online",
 "status_message": ""}]"""

ETH_ACCOUNT_ID = 'e316cb9a-0808-4fd7-8914-97829c1925de'
BAT_ACCOUNT_ID = '71452118-efc7-4cc4-8780-a5e22d4baa53'

ETH_ACCOUNTS = f"""{{
"id": "{ETH_ACCOUNT_ID}",
"currency": "ETH",
"balance": "2.5",
"available": "2.15",
"hold": "0.35",
"profile_id": "75da88c5-05bf-4f54-bc85-5c775bd68254"
}}"""

ACCOUNTS_RESPONSE = f"""[{{
"id": "{BAT_ACCOUNT_ID}",
"currency": "BAT",
"balance": "10.5000000000",
"available": "10.00000000",
"hold": "0.5000000000000000",
"profile_id": "75da88c5-05bf-4f54-bc85-5c775bd68254"
}},{ETH_ACCOUNTS}]"""


UNKNOWN_ASSET_ACCOUNTS_RESPONSE = f"""[{{
"id": "71452118-efc7-4cc4-8780-a5e22d4baa53",
"currency": "UNKNOWN",
"balance": "10.5000000000",
"available": "10.00000000",
"hold": "0.5000000000000000",
"profile_id": "75da88c5-05bf-4f54-bc85-5c775bd68254"
}},{ETH_ACCOUNTS}]"""

INVALID_ACCOUNTS_RESPONSE = '[{"id": "71452118-efc7-4cc4-8780-a5e22d4baa53",,,}]'
KEYERROR_ACCOUNTS_RESPONSE = f'[{{"id": "foo"}}, {ETH_ACCOUNTS}]'


class ErrorEmulation(Enum):
    NONE = 0
    UNKNOWN_ASSET = 1
    INVALID_RESPONSE = 2
    KEY_ERROR = 3
    INVALID_RESPONSE_POST_REPORT = 4
    INVALID_RESPONSE_GET_REPORT = 5
    ASSET_MOVEMENTS_WRONG_FORMAT = 6


def create_coinbasepro_query_mock(
        cb: Coinbasepro,
        emulate_errors: ErrorEmulation = ErrorEmulation.NONE,
):

    def mock_coinbasepro_request(
            request_method: Literal['get', 'post'],
            url: str,
            data: str = '',
            allow_redirects: bool = True,  # pylint: disable=unused-argument
    ) -> MockResponse:
        if 'products' in url:
            # just return one product so not too many requests happen during tests
            text = PRODUCTS_RESPONSE
        elif 'accounts' in url:
            if emulate_errors == ErrorEmulation.UNKNOWN_ASSET:
                text = UNKNOWN_ASSET_ACCOUNTS_RESPONSE
            elif emulate_errors == ErrorEmulation.INVALID_RESPONSE:
                text = INVALID_ACCOUNTS_RESPONSE
            elif emulate_errors == ErrorEmulation.KEY_ERROR:
                text = KEYERROR_ACCOUNTS_RESPONSE
            else:
                text = ACCOUNTS_RESPONSE
        elif request_method == 'post' and 'reports' in url:
            if emulate_errors == ErrorEmulation.INVALID_RESPONSE_POST_REPORT:
                text = '{"foo": 5,,]'
            else:
                response_data = json.loads(data)
                assert response_data['format'] == 'csv'
                assert response_data['email'] == 'some@invalidemail.com'
                if response_data['type'] == 'fills':
                    assert 'account_id' not in response_data
                    if response_data['product_id'] == 'BAT-ETH':
                        text = POST_REPORT_RESPONSE_TEMPLATE.format(ETH_BAT_REPORT_ID)
                    else:
                        raise AssertionError(
                            f'Unimplemented coinbasepro product_id '
                            f'{response_data["product_id"]} in tests mock',
                        )
                elif response_data['type'] == 'account':
                    assert 'product_id' not in response_data
                    if response_data['account_id'] == ETH_ACCOUNT_ID:
                        text = POST_REPORT_RESPONSE_TEMPLATE.format(ETH_ACCOUNT_REPORT_ID)
                    elif response_data['account_id'] == BAT_ACCOUNT_ID:
                        text = POST_REPORT_RESPONSE_TEMPLATE.format(BAT_ACCOUNT_REPORT_ID)
                    else:
                        raise AssertionError(
                            f'Unimplemented coinbasepro account_id '
                            f'{response_data["account_id"]} in tests mock',
                        )
                else:
                    raise AssertionError(
                        f'Unknown report type {response_data["type"]} '
                        f'given to coinbasepro endpoint',
                    )
        elif request_method == 'get' and 'reports' in url:
            if emulate_errors == ErrorEmulation.INVALID_RESPONSE_GET_REPORT:
                text = '{"foo": 5,,]'
            else:
                parts = url.split('reports/')
                assert len(parts) == 2
                report_id = parts[1]
                text = GET_REPORT_RESPONSE_TEMPLATE.format(
                    report_id,
                    f'http://download_report/{report_id}',
                )
        elif 'download_report/' in url:
            parts = url.split('download_report/')
            assert len(parts) == 2
            report_id = parts[1]
            if report_id == ETH_ACCOUNT_REPORT_ID:
                if emulate_errors == ErrorEmulation.UNKNOWN_ASSET:
                    text = ETH_ACCOUNT_REPORT_UNKNOWN_ASSET
                else:
                    text = ETH_ACCOUNT_REPORT
            elif report_id == BAT_ACCOUNT_REPORT_ID:
                if emulate_errors == ErrorEmulation.ASSET_MOVEMENTS_WRONG_FORMAT:
                    text = BAT_ACCOUNT_REPORT_WRONG_FORMAT
                else:
                    text = BAT_ACCOUNT_REPORT
            elif report_id == ETH_BAT_REPORT_ID:
                if emulate_errors == ErrorEmulation.UNKNOWN_ASSET:
                    text = FILL_REPORT_UNKNOWN_ASSET
                elif emulate_errors == ErrorEmulation.KEY_ERROR:
                    text = FILL_REPORT_KEY_ERROR
                else:
                    text = ETH_BAT_REPORT
            else:
                raise AssertionError(
                    f'Tried to download invalid coinbasepro report during tests',
                )
        else:
            raise AssertionError(f'Unknown url: {url} encountered during CoinbasePro mocking')
        return MockResponse(200, text)

    return patch.object(cb.session, 'request', side_effect=mock_coinbasepro_request)


def test_name():
    exchange = Coinbasepro('a', b'a', object(), object())
    assert exchange.name == 'coinbasepro'


def test_coverage_of_products():
    """Test that we can process all pairs and assets of the offered coinbasepro products"""
    exchange = Coinbasepro('a', b'a', object(), object())
    products = exchange._api_query('products', request_method='GET')
    for product in products:
        try:
            # Make sure all products can be processed
            coinbasepro_to_worldpair(product['id'])
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.asset_name} in Coinbase Pro. '
                f'Support for it has to be added',
            ))


def test_query_balances(function_scope_coinbasepro):
    """Test that querying balances from coinbasepro works fine"""
    cb = function_scope_coinbasepro

    with create_coinbasepro_query_mock(cb):
        balances, message = cb.query_balances()

    assert message == ''
    assert len(balances) == 2
    assert balances[A_BAT]['amount'] == FVal('10.5')
    assert balances[A_BAT]['usd_value'] is not None
    assert balances[A_ETH]['amount'] == FVal('2.5')
    assert balances[A_ETH]['usd_value'] is not None


def test_query_balances_unknown_asset(function_scope_coinbasepro):
    """Test that unknown assets are handled when querying balances from coinbasepro"""
    cb = function_scope_coinbasepro

    with create_coinbasepro_query_mock(cb, emulate_errors=ErrorEmulation.UNKNOWN_ASSET):
        balances, message = cb.query_balances()

    assert message == ''
    assert len(balances) == 1
    assert balances[A_ETH]['amount'] == FVal('2.5')
    assert balances[A_ETH]['usd_value'] is not None

    warnings = cb.msg_aggregator.consume_warnings()
    assert len(warnings) == 1
    assert 'Found coinbase pro balance result with unknown asset UNKNOWN' in warnings[0]
    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 0


def test_query_balances_invalid_response(function_scope_coinbasepro):
    """Test that an invalid response is handled when querying balances from coinbasepro"""
    cb = function_scope_coinbasepro

    cb_query_mock = create_coinbasepro_query_mock(
        cb,
        emulate_errors=ErrorEmulation.INVALID_RESPONSE,
    )
    with cb_query_mock:
        balances, message = cb.query_balances()

    assert balances is None
    assert 'returned invalid JSON response' in message

    warnings = cb.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 0


def test_query_balances_keyerror_response(function_scope_coinbasepro):
    """Test that a key error is handled when querying balances from coinbasepro"""
    cb = function_scope_coinbasepro

    cb_query_mock = create_coinbasepro_query_mock(
        cb,
        emulate_errors=ErrorEmulation.KEY_ERROR,
    )
    with cb_query_mock:
        balances, message = cb.query_balances()

    assert message == ''
    assert len(balances) == 1
    assert balances[A_ETH]['amount'] == FVal('2.5')
    assert balances[A_ETH]['usd_value'] is not None

    warnings = cb.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 1
    assert 'Error processing a coinbase pro account balance' in errors[0]


EXPECTED_TRADE = Trade(
    timestamp=Timestamp(1578906906),
    location=Location.COINBASEPRO,
    pair=TradePair('BAT_ETH'),
    trade_type=TradeType.SELL,
    amount=AssetAmount(FVal('1')),
    rate=Price(FVal('0.00131511')),
    fee=Fee(FVal('0.00000657555')),
    fee_currency=A_ETH,
    link='204623',
)


def test_query_trade_history(function_scope_coinbasepro):
    """Test that querying trade data from coinbase pro works"""
    cb = function_scope_coinbasepro

    with create_coinbasepro_query_mock(cb):
        trades = cb.query_trade_history(start_ts=0, end_ts=1579449769)

    assert len(trades) == 1
    assert trades[0] == EXPECTED_TRADE
    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 0


def test_query_trade_history_unknown_assets(function_scope_coinbasepro):
    """Test that unknown assets are handled when querying trade data from coinbase pro"""
    cb = function_scope_coinbasepro
    cb_query_mock = create_coinbasepro_query_mock(
        cb,
        emulate_errors=ErrorEmulation.UNKNOWN_ASSET,
    )
    with cb_query_mock:
        trades = cb.query_trade_history(start_ts=0, end_ts=1579449769)

    assert len(trades) == 1
    assert trades[0] == EXPECTED_TRADE

    warnings = cb.msg_aggregator.consume_warnings()
    assert len(warnings) == 1
    assert 'Found unknown Coinbasepro asset UNKNOWN. Ignoring the trade' in warnings[0]
    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 0


def test_query_trade_history_wrong_format(function_scope_coinbasepro):
    """Test that wrong data format are handled when querying trade data from coinbase pro"""
    cb = function_scope_coinbasepro
    cb_query_mock = create_coinbasepro_query_mock(
        cb,
        emulate_errors=ErrorEmulation.KEY_ERROR,
    )
    with cb_query_mock:
        trades = cb.query_trade_history(start_ts=0, end_ts=1579449769)

    assert len(trades) == 1
    assert trades[0] == EXPECTED_TRADE

    warnings = cb.msg_aggregator.consume_warnings()
    assert len(warnings) == 0

    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 1
    assert 'Failed to deserialize a coinbasepro trade. Check logs for details' in errors[0]


def test_query_trade_history_invalid_response(function_scope_coinbasepro):
    """Test that invalid response is handled when querying trade data from coinbase pro

    We make the invalid response be in the POST report query in this test.
"""
    cb = function_scope_coinbasepro
    cb_query_mock = create_coinbasepro_query_mock(
        cb,
        emulate_errors=ErrorEmulation.INVALID_RESPONSE_POST_REPORT,
    )
    with cb_query_mock:
        trades = cb.query_trade_history(start_ts=0, end_ts=1579449769)

    assert len(trades) == 0

    warnings = cb.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 1
    assert 'returned invalid JSON response' in errors[0]


EXPECTED_MOVEMENTS = [AssetMovement(
    location=Location.COINBASEPRO,
    category=AssetMovementCategory.DEPOSIT,
    timestamp=Timestamp(1578871604),
    asset=A_BAT,
    amount=FVal('14.25'),
    fee_asset=A_BAT,
    fee=Fee(ZERO),
    link='dfdd574b-25ca-de01-asce-edc3c1f2e987',
), AssetMovement(
    location=Location.COINBASEPRO,
    category=AssetMovementCategory.DEPOSIT,
    timestamp=Timestamp(1578872309),
    asset=A_BAT,
    amount=FVal('160.8'),
    fee_asset=A_BAT,
    fee=Fee(ZERO),
    link='489f76g2-4dda-4ab8-3eac-6dffadaa57ba7',
), AssetMovement(
    location=Location.COINBASEPRO,
    category=AssetMovementCategory.DEPOSIT,
    timestamp=Timestamp(1578873432),
    asset=A_BAT,
    amount=FVal('8.65'),
    fee_asset=A_BAT,
    fee=Fee(ZERO),
    link='34c6d26c-d27d-4218-3d14-1493120543e9',
), AssetMovement(
    location=Location.COINBASEPRO,
    category=AssetMovementCategory.WITHDRAWAL,
    timestamp=Timestamp(1579132286),
    asset=A_ETH,
    amount=FVal('0.0011085300000000'),
    fee_asset=A_ETH,
    fee=Fee(ZERO),
    link='fcc61b23-4b51-43f8-da1e-def2d5a217ad',
)]


def test_query_asset_movements(function_scope_coinbasepro):
    """Test that querying deposits/withdrawals from coinbase pro works"""
    cb = function_scope_coinbasepro

    with create_coinbasepro_query_mock(cb):
        movements = cb.query_deposits_withdrawals(start_ts=0, end_ts=1579449769)

    assert movements == EXPECTED_MOVEMENTS
    warnings = cb.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 0


def test_query_asset_movements_unknown_assets(function_scope_coinbasepro):
    """Test that unknown assets are handled in querying deposits/withdrawals from coinbase pro"""
    cb = function_scope_coinbasepro
    cb_query_mock = create_coinbasepro_query_mock(
        cb,
        emulate_errors=ErrorEmulation.UNKNOWN_ASSET,
    )
    with cb_query_mock:
        movements = cb.query_deposits_withdrawals(start_ts=0, end_ts=1579449769)

    assert movements == EXPECTED_MOVEMENTS
    warnings = cb.msg_aggregator.consume_warnings()
    assert len(warnings) == 1
    msg = 'Found unknown Coinbasepro asset UNKNOWN. Ignoring its deposit/withdrawal'
    assert msg in warnings[0]
    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 0


def test_query_asset_movements_wrong_format(function_scope_coinbasepro):
    """Test that invalid data are handled in querying deposits/withdrawals from coinbase pro"""
    cb = function_scope_coinbasepro
    cb_query_mock = create_coinbasepro_query_mock(
        cb,
        emulate_errors=ErrorEmulation.ASSET_MOVEMENTS_WRONG_FORMAT,
    )
    with cb_query_mock:
        movements = cb.query_deposits_withdrawals(start_ts=0, end_ts=1579449769)

    assert movements == EXPECTED_MOVEMENTS
    warnings = cb.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 1
    assert 'Failed to deserialize a Coinbasepro deposit/withdrawal' in errors[0]


def test_query_asset_movements_invalid_response(function_scope_coinbasepro):
    """Test that invalid response is handled when querying deposits/withdrals from coinbase pro

    We make the invalid response be in the GET report query in this test.
"""
    cb = function_scope_coinbasepro
    cb_query_mock = create_coinbasepro_query_mock(
        cb,
        emulate_errors=ErrorEmulation.INVALID_RESPONSE_GET_REPORT,
    )
    with cb_query_mock:
        movements = cb.query_deposits_withdrawals(start_ts=0, end_ts=1579449769)

    assert movements == []
    warnings = cb.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 1
    assert 'returned invalid JSON response' in errors[0]
