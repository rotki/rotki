import json
import os
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.exchanges.binance import Binance, create_binance_symbols_to_pair
from rotkehlchen.exchanges.bitmex import Bitmex
from rotkehlchen.exchanges.bittrex import Bittrex
from rotkehlchen.exchanges.coinbase import Coinbase
from rotkehlchen.exchanges.coinbasepro import Coinbasepro
from rotkehlchen.exchanges.gemini import Gemini
from rotkehlchen.exchanges.poloniex import Poloniex
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret
from rotkehlchen.tests.utils.kraken import MockKraken
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import ApiKey, ApiSecret
from rotkehlchen.user_messages import MessagesAggregator

POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE = """{
  "withdrawals": [
    {
      "currency": "BTC",
      "timestamp": 1458994442,
      "amount": "5.0",
      "fee": "0.5",
      "withdrawalNumber": 1
    }, {
      "currency": "ETH",
      "timestamp": 1468994442,
      "amount": "10.0",
      "fee": "0.1",
      "withdrawalNumber": 2
    }, {
      "currency": "IDONTEXIST",
      "timestamp": 1478994442,
      "amount": "10.0",
      "fee": "0.1",
      "withdrawalNumber": 3
    }, {
      "currency": "DIS",
      "timestamp": 1478994442,
      "amount": "10.0",
      "fee": "0.1",
      "withdrawalNumber": 4
  }],
  "deposits": [
    {
      "currency": "BTC",
      "timestamp": 1448994442,
      "amount": "50.0",
      "depositNumber": 1
    }, {
      "currency": "ETH",
      "timestamp": 1438994442,
      "amount": "100.0",
      "depositNumber": 2
    }, {
      "currency": "IDONTEXIST",
      "timestamp": 1478994442,
      "amount": "10.0",
      "depositNumber": 3
    }, {
      "currency": "EBT",
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


def patch_binance_balances_query(binance: 'Binance'):
    def mock_binance_asset_return(url, *args):  # pylint: disable=unused-argument
        return MockResponse(200, BINANCE_BALANCES_RESPONSE)

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
