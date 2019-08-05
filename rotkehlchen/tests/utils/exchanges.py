POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE = """{
"withdrawals": [
{"currency": "BTC", "timestamp": 1458994442, "amount": "5.0", "fee": "0.5"},
{"currency": "ETH", "timestamp": 1468994442, "amount": "10.0", "fee": "0.1"},
{"currency": "IDONTEXIST", "timestamp": 1478994442, "amount": "10.0", "fee": "0.1"},
{"currency": "DIS", "timestamp": 1478994442, "amount": "10.0", "fee": "0.1"}],
"deposits": [
{"currency": "BTC", "timestamp": 1448994442, "amount": "50.0"},
{"currency": "ETH", "timestamp": 1438994442, "amount": "100.0"},
{"currency": "IDONTEXIST", "timestamp": 1478994442, "amount": "10.0"},
{"currency": "EBT", "timestamp": 1478994442, "amount": "10.0"}]
}"""


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
