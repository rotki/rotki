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
                    "time": "1418994442",
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
