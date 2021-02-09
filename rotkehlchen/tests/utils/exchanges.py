import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.exchanges.binance import Binance, create_binance_symbols_to_pair
from rotkehlchen.exchanges.bitcoinde import Bitcoinde
from rotkehlchen.exchanges.bitfinex import Bitfinex
from rotkehlchen.exchanges.bitmex import Bitmex
from rotkehlchen.exchanges.bitstamp import Bitstamp
from rotkehlchen.exchanges.bittrex import Bittrex
from rotkehlchen.exchanges.coinbase import Coinbase
from rotkehlchen.exchanges.coinbasepro import Coinbasepro
from rotkehlchen.exchanges.gemini import Gemini
from rotkehlchen.exchanges.iconomi import Iconomi
from rotkehlchen.exchanges.kucoin import Kucoin
from rotkehlchen.exchanges.poloniex import Poloniex
from rotkehlchen.tests.utils.factories import (
    make_api_key,
    make_api_secret,
    make_random_uppercasenumeric_string,
)
from rotkehlchen.tests.utils.kraken import MockKraken
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import ApiKey, ApiSecret
from rotkehlchen.user_messages import MessagesAggregator

POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE = """{
  "withdrawals": [
    {
      "currency": "BTC",
      "address": "131rdg5Rzn6BFufnnQaHhVa5ZtRU1J2EZR",
      "status": "COMPLETE: 2d27ae26fa9c70d6709e27ac94d4ce2fde19b3986926e9f3bfcf3e2d68354ec5",
      "timestamp": 1458994442,
      "amount": "5.0",
      "fee": "0.5",
      "withdrawalNumber": 1
    }, {
      "currency": "ETH",
      "address": "0xb7e033598cb94ef5a35349316d3a2e4f95f308da",
      "status": "COMPLETE: 0xbd4da74e1a0b81c21d056c6f58a5b306de85d21ddf89992693b812bb117eace4",
      "timestamp": 1468994442,
      "amount": "10.0",
      "fee": "0.1",
      "withdrawalNumber": 2
    }, {
      "currency": "IDONTEXIST",
      "timestamp": 1478994442,
      "amount": "10.0",
      "fee": "0.1",
      "withdrawalNumber": 3,
      "status": "COMPLETE: 0xbd4da74e1a0b81c21d056c6f58a5b306de85d21ddf89992693b812bb117eace4"
    }, {
      "currency": "DIS",
      "timestamp": 1478994442,
      "amount": "10.0",
      "fee": "0.1",
      "status": "COMPLETE: 0xbd4da74e1a0b81c21d056c6f58a5b306de85d21ddf89992693b812bb117eace4",
      "withdrawalNumber": 4
  }],
  "deposits": [
    {
      "currency": "BTC",
      "timestamp": 1448994442,
      "address": "131rdg5Rzn6BFufnnQaHhVa5ZtRU1J2EZR",
      "txid": "b05bdec7430a56b5a5ed34af4a31a54859dda9b7c88a5586bc5d6540cdfbfc7a",
      "amount": "50.0",
      "depositNumber": 1
    }, {
      "currency": "ETH",
      "address": "0xb7e033598cb94ef5a35349316d3a2e4f95f308da",
      "txid": "0xf7e7eeb44edcad14c0f90a5fffb1cbb4b80e8f9652124a0838f6906ca939ccd2",
      "timestamp": 1438994442,
      "amount": "100.0",
      "depositNumber": 2
    }, {
      "currency": "IDONTEXIST",
      "address": "0xb7e033598cb94ef5a35349316d3a2e4f95f308da",
      "txid": "0xf7e7eeb44edcad14c0f90a5fffb1cbb4b80e8f9652124a0838f6906ca939ccd2",
      "timestamp": 1478994442,
      "amount": "10.0",
      "depositNumber": 3
    }, {
      "currency": "EBT",
      "address": "0xb7e033598cb94ef5a35349316d3a2e4f95f308da",
      "txid": "0xf7e7eeb44edcad14c0f90a5fffb1cbb4b80e8f9652124a0838f6906ca939ccd2",
      "timestamp": 1478994442,
      "amount": "10.0",
      "depositNumber": 4
  }]
}"""

POLONIEX_BALANCES_RESPONSE = """
{
    "BTC": {"available": "5.0", "onOrders": "0.5"},
    "ETH": {"available": "10.0", "onOrders": "1.0"},
    "IDONTEXIST": {"available": "1.0", "onOrders": "2.0"},
    "CNOTE": {"available": "2.0", "onOrders": "3.0"}
}
"""

POLONIEX_TRADES_RESPONSE = """{ "BTC_BCH":
        [ { "globalTradeID": 394131412,
        "tradeID": "5455033",
        "date": "2018-10-16 18:05:17",
        "rate": "0.06935244",
        "amount": "1.40308443",
        "total": "0.09730732",
        "fee": "0.00100000",
        "orderNumber": "104768235081",
        "type": "sell",
        "category": "exchange" }],
        "BTC_ETH":
        [{ "globalTradeID": 394127361,
        "tradeID": "13536350",
        "date": "2018-10-16 17:03:43",
        "rate": "0.00003432",
        "amount": "3600.53748129",
        "total": "0.12357044",
        "fee": "0.00200000",
        "orderNumber": "96238912841",
        "type": "buy",
        "category": "exchange"}]}"""

BINANCE_BALANCES_RESPONSE = """
{
  "makerCommission": 15,
  "takerCommission": 15,
  "buyerCommission": 0,
  "sellerCommission": 0,
  "canTrade": true,
  "canWithdraw": true,
  "canDeposit": true,
  "updateTime": 123456789,
  "balances": [
    {
      "asset": "BTC",
      "free": "4723846.89208129",
      "locked": "0.00000000"
    }, {
      "asset": "ETH",
      "free": "4763368.68006011",
      "locked": "0.00000000"
    }, {
      "asset": "IDONTEXIST",
      "free": "5.0",
      "locked": "0.0"
    }, {
      "asset": "ETF",
      "free": "5.0",
      "locked": "0.0"
}]}"""


BINANCE_FUTURES_WALLET_RESPONSE = """{
    "totalCrossCollateral":"5.8238577133",
    "totalBorrowed":"5.07000000",
    "totalInterest":"0.0",
    "asset": "USDT",
    "crossCollaterals":[
        {
            "collateralCoin":"BUSD",
            "locked":"5.82211108",
            "loanAmount": "5.07",
            "currentCollateralRate": "0.87168984",
            "principalForInterest": "0.0",
            "interest": "0.0"
        }, {
            "collateralCoin":"BTC",
            "locked":"0",
            "loanAmount": "0",
            "currentCollateralRate": "0",
            "principalForInterest": "0.0",
            "interest": "0.0"
        }
    ]
}"""

BINANCE_USDT_FUTURES_BALANCES_RESPONSE = """[
{"accountAlias": "foo", "asset": "USDT", "availableBalance": "125.55", "balance": "125.55", "crossUnPnl": "0", "crossWalletBalance": "125.55", "maxWithdrawAmount": "125.55"},
 {"accountAlias": "foo", "asset": "BNB", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "maxWithdrawAmount": "0"},
 {"accountAlias": "foo", "asset": "BUSD", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "maxWithdrawAmount": "0"}
]"""  # noqa: E501

BINANCE_COIN_FUTURES_BALANCES_RESPONSE = """[{"accountAlias": "boo", "asset": "ETC", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "updateTime": 1608764079532, "withdrawAvailable": "0"},
 {"accountAlias": "boo", "asset": "BTC", "availableBalance": "0.5", "balance": "0.5", "crossUnPnl": "0", "crossWalletBalance": "0.5", "updateTime": 1608764079532, "withdrawAvailable": "0.5"},
 {"accountAlias": "boo", "asset": "ADA", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "updateTime": 1608764079532, "withdrawAvailable": "0"},
 {"accountAlias": "boo", "asset": "FIL", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "updateTime": 1608764079532, "withdrawAvailable": "0"},
 {"accountAlias": "boo", "asset": "LINK", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "updateTime": 1608764079532, "withdrawAvailable": "0"},
 {"accountAlias": "boo", "asset": "ETH", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "updateTime": 1608764079532, "withdrawAvailable": "0"},
 {"accountAlias": "boo", "asset": "BNB", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "updateTime": 1608764079532, "withdrawAvailable": "0"},
 {"accountAlias": "boo", "asset": "TRX", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "updateTime": 1608764079532, "withdrawAvailable": "0"},
 {"accountAlias": "boo", "asset": "DOT", "availableBalance": "500.55", "balance": "500.55", "crossUnPnl": "0", "crossWalletBalance": "500.55", "updateTime": 1608764079532, "withdrawAvailable": "500.55"},
 {"accountAlias": "boo", "asset": "EOS", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "updateTime": 1608764079532, "withdrawAvailable": "0"},
 {"accountAlias": "boo", "asset": "LTC", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "updateTime": 1608764079532, "withdrawAvailable": "0"},
 {"accountAlias": "boo", "asset": "BCH", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "updateTime": 1608764079532, "withdrawAvailable": "0"},
 {"accountAlias": "boo", "asset": "XRP", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "updateTime": 1608764079532, "withdrawAvailable": "0"},
 {"accountAlias": "boo", "asset": "EGLD", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "updateTime": 1608764079532, "withdrawAvailable": "0"}
 ]"""  # noqa: E501

BINANCE_LENDING_WALLET_RESPONSE = """{
    "positionAmountVos": [
        {
            "amount": "75.46000000",
            "amountInBTC": "0.01044819",
            "amountInUSDT": "75.46000000",
            "asset": "USDT"
        },
        {
            "amount": "1.67072036",
            "amountInBTC": "0.00023163",
            "amountInUSDT": "1.67289230",
            "asset": "BUSD"
        }
    ],
    "totalAmountInBTC": "0.01067982",
    "totalAmountInUSDT": "77.13289230",
    "totalFixedAmountInBTC": "0.00000000",
    "totalFixedAmountInUSDT": "0.00000000",
    "totalFlexibleInBTC": "0.01067982",
    "totalFlexibleInUSDT": "77.13289230"
}"""

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


def assert_binance_balances_result(balances: Dict[str, Any]) -> None:
    assert balances['BTC']['amount'] == '4723846.89208129'
    assert balances['BTC']['usd_value'] is not None
    assert balances['ETH']['amount'] == '4763368.68006011'
    assert balances['ETH']['usd_value'] is not None


def assert_poloniex_balances_result(balances: Dict[str, Any]) -> None:
    assert balances['BTC']['amount'] == '5.5'
    assert balances['BTC']['usd_value'] is not None
    assert balances['ETH']['amount'] == '11.0'
    assert balances['ETH']['usd_value'] is not None


def mock_binance_balance_response(url):
    if 'futures' in url:
        return MockResponse(200, BINANCE_FUTURES_WALLET_RESPONSE)
    if 'lending' in url:
        return MockResponse(200, BINANCE_LENDING_WALLET_RESPONSE)
    if 'https://fapi' in url:
        return MockResponse(200, BINANCE_USDT_FUTURES_BALANCES_RESPONSE)
    if 'https://dapi' in url:
        return MockResponse(200, BINANCE_COIN_FUTURES_BALANCES_RESPONSE)

    # else
    return MockResponse(200, BINANCE_BALANCES_RESPONSE)


def patch_binance_balances_query(binance: 'Binance'):
    def mock_binance_asset_return(url, *args):  # pylint: disable=unused-argument
        if 'futures' in url:
            response = '{"crossCollaterals":[]}'
        elif 'lending' in url:
            response = '{"positionAmountVos":[]}'
        elif 'https://fapi' in url:
            response = '[]'
        elif 'https://dapi' in url:
            response = '[]'
        else:
            response = BINANCE_BALANCES_RESPONSE
        return MockResponse(200, response)

    binance_patch = patch.object(binance.session, 'get', side_effect=mock_binance_asset_return)
    return binance_patch


def patch_poloniex_balances_query(poloniex: 'Poloniex'):
    def mock_poloniex_asset_return(url, *args):  # pylint: disable=unused-argument
        return MockResponse(200, POLONIEX_BALANCES_RESPONSE)

    poloniex_patch = patch.object(poloniex.session, 'post', side_effect=mock_poloniex_asset_return)
    return poloniex_patch

# # -- Test Exchange Objects creation --


def create_test_coinbase(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> Coinbase:
    mock = Coinbase(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )
    return mock


def create_test_binance(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> Binance:
    binance = Binance(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )
    this_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = Path(this_dir) / 'data' / 'binance_exchange_info.json'
    with json_path.open('r') as f:
        json_data = json.loads(f.read())

    binance._symbols_to_pair = create_binance_symbols_to_pair(json_data)
    binance.first_connection_made = True
    return binance


def create_test_bitfinex(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        api_key: Optional[ApiKey] = None,
        secret: Optional[ApiSecret] = None,
) -> Bitfinex:
    if api_key is None:
        api_key = make_api_key()
    if secret is None:
        secret = make_api_secret()

    return Bitfinex(
        api_key=api_key,
        secret=secret,
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_bitmex(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> Bitmex:
    # API key/secret from tests cases here: https://www.bitmex.com/app/apiKeysUsage
    bitmex = Bitmex(
        api_key=ApiKey('LAqUlngMIQkIUjXMUreyu3qn'),
        secret=ApiSecret(b'chNOOS4KvNXR_Xq4k4c9qsfoKWvnDecLATCRlcBwyKDYnWgO'),
        database=database,
        msg_aggregator=msg_aggregator,
    )
    bitmex.first_connection_made = True
    return bitmex


def create_test_bitstamp(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        api_key: Optional[ApiKey] = None,
        secret: Optional[ApiSecret] = None,
) -> Bitstamp:
    if api_key is None:
        api_key = make_api_key()
    if secret is None:
        secret = make_api_secret()

    return Bitstamp(
        api_key=api_key,
        secret=secret,
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_bittrex(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> Bittrex:
    bittrex = Bittrex(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )
    return bittrex


def create_test_coinbasepro(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        passphrase: str,
) -> Coinbasepro:
    coinbasepro = Coinbasepro(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
        passphrase=passphrase,
    )
    return coinbasepro


def create_test_gemini(
        api_key,
        api_secret,
        database,
        msg_aggregator,
        base_uri,
):
    return Gemini(
        api_key=api_key,
        secret=api_secret,
        database=database,
        msg_aggregator=msg_aggregator,
        base_uri=base_uri,
    )


def create_test_kraken(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> MockKraken:
    return MockKraken(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_kucoin(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        api_key: Optional[ApiKey] = None,
        secret: Optional[ApiSecret] = None,
        passphrase: Optional[str] = None,
) -> Kucoin:
    if api_key is None:
        api_key = make_api_key()
    if secret is None:
        secret = make_api_secret()
    if passphrase is None:
        passphrase = make_random_uppercasenumeric_string(size=6)

    return Kucoin(
        api_key=api_key,
        secret=secret,
        database=database,
        msg_aggregator=msg_aggregator,
        passphrase=passphrase,
    )


def create_test_iconomi(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> Iconomi:
    return Iconomi(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_bitcoinde(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> Bitcoinde:
    return Bitcoinde(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_poloniex(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> Poloniex:
    return Poloniex(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )
