from typing import TYPE_CHECKING, Any, Dict
from unittest.mock import patch

from rotkehlchen.tests.utils.mock import MockResponse

if TYPE_CHECKING:
    from rotkehlchen.exchanges.binance import Binance, Poloniex

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


KRAKEN_SPECIFIC_TRADES_HISTORY_RESPONSE = """{
    "trades": {
        "1": {
            "ordertxid": "1",
            "postxid": 1,
            "pair": "XXBTZEUR",
            "time": "1458994442.0000",
            "type": "buy",
            "ordertype": "market",
            "price": "100",
            "vol": "1",
            "fee": "0.1",
            "cost": "100",
            "margin": "0.0",
            "misc": ""},
        "2": {
            "ordertxid": "2",
            "postxid": 2,
            "pair": "XETHZEUR",
            "time": "1456994442.0000",
            "type": "buy",
            "ordertype": "market",
            "price": "100",
            "vol": "1",
            "fee": "0.1",
            "cost": "100",
            "margin": "0.0",
            "misc": ""},
        "3": {
            "ordertxid": "3",
            "postxid": 3,
            "pair": "IDONTEXISTZEUR",
            "time": "1458994442.0000",
            "type": "buy",
            "ordertype": "market",
            "price": "100",
            "vol": "1",
            "fee": "0.1",
            "cost": "100",
            "margin": "0.0",
            "misc": ""
        },
        "4": {
            "ordertxid": "4",
            "postxid": 4,
            "pair": "XETHIDONTEXISTTOO",
            "time": "1458994442.0000",
            "type": "buy",
            "ordertype": "market",
            "price": "100",
            "vol": "1",
            "fee": "0.1",
            "cost": "100",
            "margin": "0.0",
            "misc": ""
        },
        "5": {
            "ordertxid": "5",
            "postxid": 5,
            "pair": "%$#%$#%$#%$#%$#%",
            "time": "1458994442.0000",
            "type": "buy",
            "ordertype": "market",
            "price": "100",
            "vol": "1",
            "fee": "0.1",
            "cost": "100",
            "margin": "0.0",
            "misc": ""
        }},
    "count": 5
}"""

KRAKEN_SPECIFIC_DEPOSITS_RESPONSE = """
      {
            "ledger": {
                "1": {
                    "refid": "1",
                    "time": "1458994442",
                    "type": "deposit",
                    "aclass": "currency",
                    "asset": "BTC",
                    "amount": "5.0",
                    "balance": "10.0",
                    "fee": "0.1"
                },
                "2": {
                    "refid": "2",
                    "time": "1448994442",
                    "type": "deposit",
                    "aclass": "currency",
                    "asset": "ETH",
                    "amount": "10.0",
                    "balance": "100.0",
                    "fee": "0.11"
                },
                "3": {
                    "refid": "3",
                    "time": "1438994442",
                    "type": "deposit",
                    "aclass": "currency",
                    "asset": "IDONTEXIST",
                    "amount": "10.0",
                    "balance": "100.0",
                    "fee": "0.11"
                }
            },
            "count": 3
}"""

KRAKEN_SPECIFIC_WITHDRAWALS_RESPONSE = """
{
            "ledger": {
                "4": {
                    "refid": "4",
                    "time": "1428994442",
                    "type": "withdrawal",
                    "aclass": "currency",
                    "asset": "BTC",
                    "amount": "5.0",
                    "balance": "10.0",
                    "fee": "0.1"
                },
                "5": {
                    "refid": "5",
                    "time": "1439994442",
                    "type": "withdrawal",
                    "aclass": "currency",
                    "asset": "ETH",
                    "amount": "10.0",
                    "balance": "100.0",
                    "fee": "0.11"
                },
                "6": {
                    "refid": "6",
                    "time": "1408994442",
                    "type": "withdrawal",
                    "aclass": "currency",
                    "asset": "IDONTEXISTEITHER",
                    "amount": "10.0",
                    "balance": "100.0",
                    "fee": "0.11"
                }
            },
            "count": 3
}"""


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
