import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Literal, overload
from unittest.mock import _patch, patch

from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.exchanges.binance import BINANCE_BASE_URL, BINANCEUS_BASE_URL, Binance
from rotkehlchen.exchanges.bitcoinde import Bitcoinde
from rotkehlchen.exchanges.bitfinex import Bitfinex
from rotkehlchen.exchanges.bitmex import Bitmex
from rotkehlchen.exchanges.bitpanda import Bitpanda
from rotkehlchen.exchanges.bitstamp import Bitstamp
from rotkehlchen.exchanges.bybit import Bybit
from rotkehlchen.exchanges.coinbase import Coinbase
from rotkehlchen.exchanges.coinbaseprime import Coinbaseprime
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.exchanges.gemini import Gemini
from rotkehlchen.exchanges.htx import Htx
from rotkehlchen.exchanges.iconomi import Iconomi
from rotkehlchen.exchanges.independentreserve import Independentreserve
from rotkehlchen.exchanges.kucoin import Kucoin
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.exchanges.okx import Okx
from rotkehlchen.exchanges.poloniex import Poloniex
from rotkehlchen.exchanges.utils import create_binance_symbols_to_pair
from rotkehlchen.exchanges.woo import Woo
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.tests.utils.constants import A_XMR
from rotkehlchen.tests.utils.factories import (
    make_api_key,
    make_api_secret,
    make_random_uppercasenumeric_string,
)
from rotkehlchen.tests.utils.kraken import MockKraken
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    Fee,
    Location,
    Price,
    Timestamp,
    TimestampMS,
    TradeType,
)
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.exchanges.kraken import Kraken

POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE: Final = """{
  "adjustments": [],
  "withdrawals": [
    {
      "currency": "BTC",
      "address": "131rdg5Rzn6BFufnnQaHhVa5ZtRU1J2EZR",
      "status": "COMPLETE: 2d27ae26fa9c70d6709e27ac94d4ce2fde19b3986926e9f3bfcf3e2d68354ec5",
      "timestamp": 1458994442,
      "amount": "5.0",
      "fee": "0.5",
      "withdrawalRequestsId": 1
    }, {
      "currency": "ETH",
      "address": "0xb7e033598cb94ef5a35349316d3a2e4f95f308da",
      "status": "COMPLETE: 0xbd4da74e1a0b81c21d056c6f58a5b306de85d21ddf89992693b812bb117eace4",
      "timestamp": 1468994442,
      "amount": "10.0",
      "fee": "0.1",
      "withdrawalRequestsId": 2
    }, {
      "currency": "IDONTEXIST",
      "timestamp": 1478994442,
      "amount": "10.0",
      "fee": "0.1",
      "withdrawalRequestsId": 3,
      "status": "COMPLETE: 0xbd4da74e1a0b81c21d056c6f58a5b306de85d21ddf89992693b812bb117eace4"
    }, {
      "currency": "BALLS",
      "timestamp": 1478994442,
      "amount": "10.0",
      "fee": "0.1",
      "status": "COMPLETE: 0xbd4da74e1a0b81c21d056c6f58a5b306de85d21ddf89992693b812bb117eace4",
      "withdrawalRequestsId": 4
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

POLONIEX_BALANCES_RESPONSE: Final = """[{
    "accountId": 1337,
    "accountType": "SPOT",
    "balances": [{
        "available": "5.0", "currency": "BTC", "currencyId": "28", "hold": "0.5"
    }, {
        "available": "10.0", "currency": "ETH", "currencyId": "1", "hold": "1.0"
    }, {
        "available": "1.0", "currency": "IDONTEXIST", "currencyId": "42", "hold": "1.0"
    }, {
        "available": "2.0", "currency": "CNOTE", "currencyId": "44", "hold": "3.0"
    }]
}]
"""

POLONIEX_TRADES_RESPONSE: Final = """[{
    "symbol": "BCH_BTC",
    "id": 394131412,
    "createTime": 1539713117000,
    "price": "0.06935244",
    "quantity": "1.40308443",
    "feeAmount": "0.00009730732",
    "feeCurrency": "BTC",
    "side": "SELL",
    "type": "LIMIT",
    "accountType": "SPOT"
    }, {
    "symbol": "ETH_BTC",
    "id": 13536350,
    "createTime": 1539709423000,
    "price": "0.00003432",
    "quantity": "3600.53748129",
    "feeAmount": "7.20107496258",
    "feeCurrency": "ETH",
    "side": "BUY",
    "type": "MARKET",
    "accountType": "SPOT"
}]"""

BINANCE_BALANCES_RESPONSE: Final = """
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


BINANCE_FUTURES_WALLET_RESPONSE: Final = """{
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

BINANCE_POOL_BALANCES_RESPONSE: Final = """[
    {
        "poolId": 2,
        "poolName": "BUSD/USDT",
        "updateTime": 2,
        "liquidity": {
            "USDT": "80",
            "BUSD": "80"
        },
        "share": {
            "shareAmount": "0",
            "sharePercentage": "0",
            "asset": {
                "BUSD": "0",
                "USDT": "0"
            }
        }
    },
    {
        "poolId": 15,
        "poolName": "BTC/WBTC",
        "updateTime": 2,
        "liquidity": {
            "BTC": "80",
            "WBTC": "80"
        },
        "share": {
            "shareAmount": "0",
            "sharePercentage": "0",
            "asset": {
                "BTC": "2",
                "WBTC": "2.1"
            }
        }
    }
]"""

BINANCE_USDT_FUTURES_BALANCES_RESPONSE: Final = """[
{"accountAlias": "foo", "asset": "USDT", "availableBalance": "125.55", "balance": "125.55", "crossUnPnl": "0", "crossWalletBalance": "125.55", "maxWithdrawAmount": "125.55"},
 {"accountAlias": "foo", "asset": "BNB", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "maxWithdrawAmount": "0"},
 {"accountAlias": "foo", "asset": "BUSD", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "maxWithdrawAmount": "0"}
]"""  # noqa: E501

BINANCE_COIN_FUTURES_BALANCES_RESPONSE: Final = """[{"accountAlias": "boo", "asset": "ETC", "availableBalance": "0", "balance": "0", "crossUnPnl": "0", "crossWalletBalance": "0", "updateTime": 1608764079532, "withdrawAvailable": "0"},
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


BINANCE_MYTRADES_RESPONSE: Final = """
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


BINANCE_FIATBUY_RESPONSE: Final = """{
   "code": "000000",
   "message": "success",
   "data": [{
      "orderNo": "353fca443f06466db0c4dc89f94f027a",
      "sourceAmount": "20.0",
      "fiatCurrency": "EUR",
      "obtainAmount": "4.462",
      "cryptoCurrency": "LUNA",
      "totalFee": "0.2",
      "price": "4.437472",
      "status": "Completed",
      "createTime": 1624529919000,
      "updateTime": 1624529919000
   }],
   "total": 1,
   "success": true
}"""


BINANCE_FIATSELL_RESPONSE: Final = """{
   "code": "000000",
   "message": "success",
   "data": [{
      "orderNo": "463fca443f06466db0c4dc89f94f027a",
      "sourceAmount": "20.0",
      "fiatCurrency": "EUR",
      "obtainAmount": "4.462",
      "cryptoCurrency": "ETH",
      "totalFee": "0.2",
      "price": "4.437472",
      "status": "Completed",
      "createTime": 1628529919000,
      "updateTime": 1628529919000
   }],
   "total": 1,
   "success": true
}"""


BINANCE_DEPOSITS_HISTORY_RESPONSE: Final = """[
    {
        "insertTime": 1508198532000,
        "amount": 0.04670582,
        "coin": "ETH",
        "address": "0x6915f16f8791d0a1cc2bf47c13a6b2a92000504b",
        "txId": "0xef33b22bdb2b28b1f75ccd201a4a4m6e7g83jy5fc5d5a9d1340961598cfcb0a1",
        "status": 1
    }, {
        "insertTime": 1508398632000,
        "amount": 1000,
        "coin": "XMR",
        "address": "463tWEBn5XZJSxLU34r6g7h8jtxuNcDbjLSjkn3XAXHCbLrTTErJrBWYgHJQyrCwkNgYvV38",
        "addressTag": "342341222",
        "txId": "c3c6219639c8ae3f9cf010cdc24fw7f7yt8j1e063f9b4bd1a05cb44c4b6e2509",
        "status": 1
    }
]"""

BINANCE_WITHDRAWALS_HISTORY_RESPONSE: Final = """[
        {
        "id":"7213fea8e94b4a5593d507237e5a555b",
        "withdrawOrderId": null,
        "amount": 0.99,
        "transactionFee": 0.01,
        "address": "0x6915f16f8791d0a1cc2bf47c13a6b2a92000504b",
        "coin": "ETH",
        "txId": "0xdf33b22bdb2b28b1f75ccd201a4a4m6e7g83jy5fc5d5a9d1340961598cfcb0a1",
        "applyTime": "2017-10-17 00:02:12",
        "status": 4
    }, {
        "id":"7213fea8e94b4a5534ggsd237e5a555b",
        "withdrawOrderId": "withdrawtest",
        "amount": 999.9999,
        "transactionFee": 0.0001,
        "address": "463tWEBn5XZJSxLU34r6g7h8jtxuNcDbjLSjkn3XAXHCbLrTTErJrBWYgHJQyrCwkNgYvyV3z8zctJLPCZy24jvb3NiTcTJ",
        "addressTag": "342341222",
        "txId": "b3c6219639c8ae3f9cf010cdc24fw7f7yt8j1e063f9b4bd1a05cb44c4b6e2509",
        "coin": "XMR",
        "applyTime": "2017-10-17 00:02:12",
        "status": 4
    }
]"""  # noqa: E501


BINANCE_FIATDEPOSITS_RESPONSE: Final = """{
   "code": "000000",
   "message": "success",
   "data": [
   {
      "orderNo":"7d76d611-0568-4f43-afb6-24cac7767365",
      "fiatCurrency": "EUR",
      "indicatedAmount": "10.00",
      "amount": "10.00",
      "totalFee": "0.00",
      "method": "BankAccount",
      "status": "Successful",
      "createTime": 1626144956000,
      "updateTime": 1626400907000
   }
   ],
   "total": 1,
   "success": true
}"""


BINANCE_FIATWITHDRAWS_RESPONSE: Final = """{
   "code": "000000",
   "message": "success",
   "data": [
   {
      "orderNo":"8e76d611-0568-4f43-afb6-24cac7767365",
      "fiatCurrency": "EUR",
      "indicatedAmount": "10.00",
      "amount": "10.00",
      "totalFee": "0.02",
      "method": "BankAccount",
      "status": "Finished",
      "createTime": 1636144956000,
      "updateTime": 1636400907000
   }
   ],
   "total": 1,
   "success": true
}"""


BINANCE_SIMPLE_EARN_FLEXIBLE_POSITION: Final = """{
    "rows":[{
        "totalAmount": "75.46000000",
        "tierAnnualPercentageRate": {
            "0-5BTC": 0.05,
            "5-10BTC": 0.03
        },
        "latestAnnualPercentageRate": "0.02599895",
        "yesterdayAirdropPercentageRate": "0.02599895",
        "asset": "USDT",
        "airDropAsset": "BETH",
        "canRedeem": true,
        "collateralAmount": "232.23123213",
        "productId": "USDT001",
        "yesterdayRealTimeRewards": "0.10293829",
        "cumulativeBonusRewards": "0.22759183",
        "cumulativeRealTimeRewards": "0.22759183",
        "cumulativeTotalRewards": "0.45459183",
        "autoSubscribe": true
    }],
    "total": 1
}"""


BINANCE_SIMPLE_EARN_LOCKED_POSITION: Final = """{
    "rows":[{
        "positionId": "123123",
        "projectId": "Axs*90",
        "asset": "AXS",
        "amount": "122.09202928",
        "purchaseTime": "1646182276000",
        "duration": "60",
        "accrualDays": "4",
        "rewardAsset": "AXS",
        "APY": "0.23",
        "isRenewable": true,
        "isAutoRenew": true,
        "redeemDate": "1732182276000"
    }],
    "total": 1
}"""


BINANCE_FUNDING_WALLET_BALANCES_RESPONSE: Final = """[{
    "asset": "USDT",
    "free": "1",
    "locked": "0",
    "freeze": "0",
    "withdrawing": "0",
    "btcValuation": "0.00000091"
}]"""


def assert_binance_balances_result(balances: dict[str, Any]) -> None:
    assert balances['BTC']['amount'] == '4723846.89208129'
    assert balances['BTC']['usd_value'] is not None
    assert balances['ETH']['amount'] == '4763368.68006011'
    assert balances['ETH']['usd_value'] is not None


def assert_binance_asset_movements_result(
        movements: list[AssetMovement],
        location: Location,
        got_fiat: bool,
) -> None:
    for movement in movements:
        movement.event_identifier = 'x'  # reset event_identifier since its different depending on location.  # noqa: E501

    location_label = 'binance'
    assert movements[:6] == [AssetMovement(
            event_identifier='x',
            timestamp=TimestampMS(1508198532000),
            location=location,
            location_label=location_label,
            event_type=HistoryEventType.DEPOSIT,
            asset=A_ETH,
            amount=FVal('0.04670582'),
            extra_data={
                'address': '0x6915f16F8791d0A1CC2BF47c13a6B2A92000504B',
                'transaction_id': '0xef33b22bdb2b28b1f75ccd201a4a4m6e7g83jy5fc5d5a9d1340961598cfcb0a1',  # noqa: E501
            },
        ), AssetMovement(
            event_identifier='x',
            timestamp=TimestampMS(1508398632000),
            location=location,
            location_label=location_label,
            event_type=HistoryEventType.DEPOSIT,
            asset=A_XMR,
            amount=FVal('1000'),
            extra_data={
                'address': '463tWEBn5XZJSxLU34r6g7h8jtxuNcDbjLSjkn3XAXHCbLrTTErJrBWYgHJQyrCwkNgYvV38',  # noqa: E501
                'transaction_id': 'c3c6219639c8ae3f9cf010cdc24fw7f7yt8j1e063f9b4bd1a05cb44c4b6e2509',  # noqa: E501
            },
        ), AssetMovement(
            event_identifier='x',
            timestamp=TimestampMS(1508198532000),
            location=location,
            location_label=location_label,
            event_type=HistoryEventType.WITHDRAWAL,
            asset=A_ETH,
            amount=FVal('0.99'),
            extra_data={
                'address': '0x6915f16F8791d0A1CC2BF47c13a6B2A92000504B',
                'transaction_id': '0xdf33b22bdb2b28b1f75ccd201a4a4m6e7g83jy5fc5d5a9d1340961598cfcb0a1',  # noqa: E501
            },
        ), AssetMovement(
            event_identifier='x',
            timestamp=TimestampMS(1508198532000),
            location=location,
            location_label=location_label,
            event_type=HistoryEventType.WITHDRAWAL,
            asset=A_ETH,
            amount=FVal('0.01'),
            is_fee=True,
        ), AssetMovement(
            event_identifier='x',
            timestamp=TimestampMS(1508198532000),
            location=location,
            location_label=location_label,
            event_type=HistoryEventType.WITHDRAWAL,
            asset=A_XMR,
            amount=FVal('999.9999'),
            extra_data={
                'address': '463tWEBn5XZJSxLU34r6g7h8jtxuNcDbjLSjkn3XAXHCbLrTTErJrBWYgHJQyrCwkNgYvyV3z8zctJLPCZy24jvb3NiTcTJ',  # noqa: E501
                'transaction_id': 'b3c6219639c8ae3f9cf010cdc24fw7f7yt8j1e063f9b4bd1a05cb44c4b6e2509',  # noqa: E501
            },
        ), AssetMovement(
            event_identifier='x',
            timestamp=TimestampMS(1508198532000),
            location=location,
            location_label=location_label,
            event_type=HistoryEventType.WITHDRAWAL,
            asset=A_XMR,
            amount=FVal('0.0001'),
            is_fee=True,
        ),
    ]

    if got_fiat is False:
        return

    assert movements[6:] == [AssetMovement(
        event_identifier='x',
        timestamp=TimestampMS(1626144956000),
        location=location,
        location_label=location_label,
        event_type=HistoryEventType.DEPOSIT,
        asset=A_EUR,
        amount=FVal('10.00'),
        extra_data={'transaction_id': '7d76d611-0568-4f43-afb6-24cac7767365'},
    ), AssetMovement(
        event_identifier='x',
        timestamp=TimestampMS(1636144956000),
        location=location,
        location_label=location_label,
        event_type=HistoryEventType.WITHDRAWAL,
        asset=A_EUR,
        amount=FVal('10.00'),
        extra_data={'transaction_id': '8e76d611-0568-4f43-afb6-24cac7767365'},
    ), AssetMovement(
        event_identifier='x',
        timestamp=TimestampMS(1636144956000),
        location=location,
        location_label=location_label,
        event_type=HistoryEventType.WITHDRAWAL,
        asset=A_EUR,
        amount=FVal('0.02'),
        is_fee=True,
    )]


def assert_poloniex_balances_result(balances: dict[str, Any]) -> None:
    assert balances['BTC']['amount'] == '5.5'
    assert balances['BTC']['usd_value'] is not None
    assert balances['ETH']['amount'] == '11.0'
    assert balances['ETH']['usd_value'] is not None


def mock_binance_balance_response(url, **kwargs):  # pylint: disable=unused-argument
    if 'futures' in url:
        return MockResponse(200, BINANCE_FUTURES_WALLET_RESPONSE)
    if 'https://fapi' in url:
        return MockResponse(200, BINANCE_USDT_FUTURES_BALANCES_RESPONSE)
    if 'https://dapi' in url:
        return MockResponse(200, BINANCE_COIN_FUTURES_BALANCES_RESPONSE)
    if 'bswap/liquidity' in url:
        return MockResponse(200, BINANCE_POOL_BALANCES_RESPONSE)
    if 'simple-earn/flexible/position' in url:
        if kwargs.get('params', {}).get('current') == 1:
            return MockResponse(200, BINANCE_SIMPLE_EARN_FLEXIBLE_POSITION)
        else:
            return MockResponse(200, '{"rows":[], "total": 1}')
    if 'simple-earn/locked/position' in url:
        if kwargs.get('params', {}).get('current') == 1:
            return MockResponse(200, BINANCE_SIMPLE_EARN_LOCKED_POSITION)
        else:
            return MockResponse(200, '{"rows":[], "total": 1}')
    if 'asset/get-funding-asset' in url:
        return MockResponse(200, BINANCE_FUNDING_WALLET_BALANCES_RESPONSE)

    # else
    return MockResponse(200, BINANCE_BALANCES_RESPONSE)


def patch_binance_balances_query(binance: 'Binance') -> _patch:
    def mock_binance_asset_return(url, *args, **kwargs):  # pylint: disable=unused-argument
        if 'futures' in url:
            response = '{"crossCollaterals":[]}'
        elif 'lending' in url:
            response = '{"positionAmountVos":[]}'
        elif (
                'https://fapi' in url or
                'https://dapi' in url or
                'bswap/liquidity' in url
        ):
            response = '[]'
        else:
            response = BINANCE_BALANCES_RESPONSE
        return MockResponse(200, response)

    return patch.object(binance.session, 'request', side_effect=mock_binance_asset_return)


def patch_poloniex_balances_query(poloniex: 'Poloniex') -> _patch:
    def mock_poloniex_asset_return(url, *args, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, POLONIEX_BALANCES_RESPONSE)

    return patch.object(poloniex.session, 'get', side_effect=mock_poloniex_asset_return)

# # -- Test Exchange Objects creation --


def create_test_coinbase(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        name: str = 'coinbase',
) -> Coinbase:
    return Coinbase(
        name=name,
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_coinbaseprime(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        passphrase: str,
        name: str = 'coinbaseprime',
) -> Coinbaseprime:
    return Coinbaseprime(
        name=name,
        api_key=make_api_key(),
        secret=make_api_secret(),
        passphrase=passphrase,
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_binance(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        location: Location = Location.BINANCE,
        name: str = 'binance',
) -> Binance:
    if location == Location.BINANCE:
        uri = BINANCE_BASE_URL
    elif location == Location.BINANCEUS:
        uri = BINANCEUS_BASE_URL
    else:
        raise AssertionError(f'Tried to create binance exchange with location {location}')
    binance = Binance(
        name=name,
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
        uri=uri,
    )
    this_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = Path(this_dir) / 'data' / 'binance_exchange_info.json'
    with json_path.open('r') as f:
        json_data = json.loads(f.read())

    binance._symbols_to_pair = create_binance_symbols_to_pair(json_data, location)
    binance.first_connection_made = True
    return binance


def create_test_bitfinex(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        api_key: ApiKey | None = None,
        secret: ApiSecret | None = None,
) -> Bitfinex:
    if api_key is None:
        api_key = make_api_key()
    if secret is None:
        secret = make_api_secret()

    return Bitfinex(
        name='bitfinex',
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
        name='bitmex',
        api_key=ApiKey('LAqUlngMIQkIUjXMUreyu3qn'),
        secret=ApiSecret(b'chNOOS4KvNXR_Xq4k4c9qsfoKWvnDecLATCRlcBwyKDYnWgO'),
        database=database,
        msg_aggregator=msg_aggregator,
    )
    bitmex.first_connection_made = True
    bitmex.asset_to_decimals = {'XBt': 8, 'USDt': 6}
    return bitmex


def create_test_bitstamp(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        api_key: ApiKey | None = None,
        secret: ApiSecret | None = None,
) -> Bitstamp:
    if api_key is None:
        api_key = make_api_key()
    if secret is None:
        secret = make_api_secret()

    return Bitstamp(
        name='bitstamp',
        api_key=api_key,
        secret=secret,
        database=database,
        msg_aggregator=msg_aggregator,
    )


# This function is dynamically used in rotkehlchen_api_server_with_exchanges
def create_test_gemini(
        api_key,
        api_secret,
        database,
        msg_aggregator,
        base_uri,
):
    return Gemini(
        name='gemini',
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
        name='mockkraken',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_bybit(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> Bybit:
    return Bybit(
        name='bybit',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_htx(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> Htx:
    return Htx(
        name='htx',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_kucoin(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        api_key: ApiKey | None = None,
        secret: ApiSecret | None = None,
        passphrase: str | None = None,
) -> Kucoin:
    if api_key is None:
        api_key = make_api_key()
    if secret is None:
        secret = make_api_secret()
    if passphrase is None:
        passphrase = make_random_uppercasenumeric_string(size=6)

    return Kucoin(
        name='kucoin',
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
        name='iconomi',
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
        name='bitcoinde',
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
        name='poloniex',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_independentreserve(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> Independentreserve:
    return Independentreserve(
        name='independentreserve',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_bitpanda(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        api_key: ApiKey | None = None,
        secret: ApiSecret | None = None,
) -> Bitpanda:
    if api_key is None:
        api_key = make_api_key()
    if secret is None:
        secret = make_api_secret()
    return Bitpanda(
        name='bitpanda',
        api_key=api_key,
        secret=secret,
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_okx(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        api_key: ApiKey,
        secret: ApiSecret,
        passphrase: str,
) -> Okx:
    return Okx(
        name='okx',
        api_key=api_key,
        secret=secret,
        passphrase=passphrase,
        database=database,
        msg_aggregator=msg_aggregator,
    )


def create_test_woo(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
        api_key: ApiKey | None = None,
        secret: ApiSecret | None = None,
) -> Woo:
    return Woo(
        name='woo',
        api_key=make_api_key() if api_key is None else api_key,
        secret=make_api_secret() if secret is None else secret,
        database=database,
        msg_aggregator=msg_aggregator,
    )


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.BINANCE, Location.BINANCEUS],
) -> Binance | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.BITPANDA],
) -> Bitpanda | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.BITCOINDE],
) -> Bitcoinde | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.BITFINEX],
) -> Bitfinex | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.BITMEX],
) -> Bitmex | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.BITSTAMP],
) -> Bitstamp | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.BYBIT],
) -> Bybit | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.COINBASE],
) -> Coinbase | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.COINBASEPRIME],
) -> Coinbaseprime | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.GEMINI],
) -> Gemini | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.HTX],
) -> Htx | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.ICONOMI],
) -> Iconomi | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.INDEPENDENTRESERVE],
) -> Independentreserve | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.KRAKEN],
) -> 'Kraken | None':
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.OKX],
) -> Okx | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.POLONIEX],
) -> Poloniex | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.WOO],
) -> Woo | None:
    ...


@overload
def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Literal[Location.KUCOIN],
) -> 'Kucoin | None':
    ...


def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Location,
) -> ExchangeInterface | None:
    """Tries to get the first exchange of a given type from the exchange manager

    If no such exchange exists returns None.

    It's not part of exchange manager itself since it's not used in production but only in tests.
    If this changes we should move this to the exchange manager
    """
    exchanges_list = exchange_manager.connected_exchanges.get(location)
    if exchanges_list is None:
        return None

    return exchanges_list[0]


def mock_exchange_data_in_db(exchange_locations, rotki) -> None:
    db = rotki.data.db
    with db.user_write() as cursor:
        for exchange_location in exchange_locations:
            db.add_trades(
                write_cursor=cursor,
                trades=[Trade(
                    timestamp=Timestamp(1),
                    location=exchange_location,
                    base_asset=A_BTC,
                    quote_asset=A_ETH,
                    trade_type=TradeType.BUY,
                    amount=AssetAmount(ONE),
                    rate=Price(ONE),
                    fee=Fee(FVal('0.1')),
                    fee_currency=A_ETH,
                    link='foo',
                    notes='boo',
                )])
            db.update_used_query_range(write_cursor=cursor, name=f'{exchange_location!s}_trades_{exchange_location!s}', start_ts=0, end_ts=9999)  # noqa: E501
            db.update_used_query_range(write_cursor=cursor, name=f'{exchange_location!s}_margins_{exchange_location!s}', start_ts=0, end_ts=9999)  # noqa: E501
            db.update_used_query_range(write_cursor=cursor, name=f'{exchange_location!s}_asset_movements_{exchange_location!s}', start_ts=0, end_ts=9999)  # noqa: E501


def check_saved_events_for_exchange(
        exchange_location: Location,
        db: DBHandler,
        should_exist: bool,
        queryrange_formatstr: str = '{exchange}_{type}_{exchange}',
) -> None:
    """Check that an exchange has saved events"""
    with db.conn.read_ctx() as cursor:
        trades = cursor.execute('SELECT * FROM trades where location=?;', (exchange_location.serialize_for_db(),)).fetchall()  # noqa: E501
        trades_range = db.get_used_query_range(cursor, queryrange_formatstr.format(exchange=exchange_location, type='trades'))  # noqa: E501
        margins_range = db.get_used_query_range(cursor, queryrange_formatstr.format(exchange=exchange_location, type='margins'))  # noqa: E501
        movements_range = db.get_used_query_range(cursor, queryrange_formatstr.format(exchange=exchange_location, type='asset_movements'))  # noqa: E501
    if should_exist:
        assert trades_range is not None
        assert margins_range is not None
        assert movements_range is not None
        assert len(trades) != 0
    else:
        assert trades_range is None
        assert margins_range is None
        assert movements_range is None
        assert len(trades) == 0


TRANSACTIONS_RESPONSE = """{
"pagination": {
    "ending_before": null,
    "starting_after": null,
    "limit": 25,
    "order": "desc",
    "previous_uri": null,
    "next_uri": null
},
"data": [{
  "id": "id1",
  "type": "send",
  "status": "completed",
  "amount": {
    "amount": "-0.05770427",
    "currency": "ETH"
  },
  "native_amount": {
    "amount": "-9.83",
    "currency": "EUR"
  },
  "description": null,
  "created_at": "2019-08-25T09:42:06Z",
  "updated_at": "2019-08-25T09:43:42Z",
  "resource": "transaction",
  "resource_path": "/v2/accounts/foo/transactions/boo",
  "instant_exchange": false,
  "network": {
    "status": "confirmed",
    "hash": "0x558bfa4d2a4ef598ddb92233459c00eda9e6c14cda75e6773b90208cb6938169",
    "transaction_url": "https://etherscan.io/tx/bbb",
    "transaction_fee": {"amount": "0.00021", "currency": "ETH"},
    "transaction_amount": {"amount": "0.05749427", "currency": "ETH"},
    "confirmations": 86
   },
    "to": {
      "resource": "evm_address",
      "address": "0x6dcd6449dbca615e40d696328209686ea95327b2",
      "currency": "ETH",
      "address_info": {"address": "0xboo"}
    },
    "idem": "zzzz",
    "details": {"title": "Sent Ethereum", "subtitle": "To Ethereum address"}
},{
  "amount": {
    "amount": "-10.482180",
    "currency": "USDC"
  },
  "created_at": "2024-12-02T14:46:23Z",
  "id": "5a1a32dc-bfda-5cbf-b625-1a197e699829",
  "native_amount": {
    "amount": "-9.98",
    "currency": "EUR"
  },
  "resource": "transaction",
  "resource_path": "/v2/accounts/40e03599-5601-534c-95c2-0db5f5c5e652/transactions/5a1a32dc-bfda-5cbf-b625-1a197e699829",
  "status": "completed",
  "trade": {
    "fee": {
      "amount": "0.099839",
      "currency": "USDC"
    },
    "id": "id9",
    "payment_method_name": "billetera de USDC"
  },
  "type": "trade"
}, {
  "id": "id2",
  "type": "send",
  "status": "completed",
  "amount": {
    "amount": "-0.05770427",
    "currency": "ETH"
  },
  "native_amount": {
    "amount": "-9.83",
    "currency": "EUR"
  },
  "description": null,
  "created_at": "2019-08-25T09:42:06Z",
  "updated_at": "2019-08-25T09:43:42Z",
  "resource": "transaction",
  "resource_path": "/v2/accounts/foo/transactions/coo",
  "instant_exchange": false,
    "to": {
      "resource": "evm_address",
      "address": "0x6dcd6449dbca615e40d696328209686ea95327b2",
      "currency": "ETH",
      "address_info": {"address": "0xboo"}
    },
    "idem": "zzzz",
    "details": {"title": "Sent Ethereum", "subtitle": "To Ethereum address"}
}, {
  "id": "id3",
  "type": "send",
  "status": "completed",
  "amount": {
    "amount": "0.10181673",
    "currency": "BTC"
  },
  "native_amount": {
    "amount": "410.24",
    "currency": "USD"
  },
  "description": null,
  "created_at": "2017-08-12T16:11:44Z",
  "updated_at": "2017-08-12T16:21:41Z",
  "resource": "transaction",
  "resource_path": "/v2/accounts/boo",
  "instant_exchange": false,
  "network": {
    "status": "confirmed",
    "status_description": null,
    "hash": "ccc",
    "transaction_url":
    "https://blockchain.info/tx/ccc"
  },
  "from": {
    "resource": "bitcoin_network",
    "currency": "BTC"
  },
  "details": {
    "title": "Received Bitcoin",
    "subtitle": "From Bitcoin address",
    "header": "Received 0.10181673 BTC ($410.24)",
    "health": "positive"
  },
  "hide_native_amount": false

},{
  "id": "id4",
  "type": "send",
  "status": "completed",
  "amount": {
    "amount": "0.02762431",
    "currency": "NMR"
  },
  "native_amount": {
    "amount": "1.01",
    "currency": "USD"
  },
  "description": null,
  "created_at": "2021-01-05T20:11:54Z",
  "updated_at": "2021-01-05T20:11:54Z",
  "resource": "transaction",
  "resource_path": "/v2/accounts/boo",
  "instant_exchange": false,
  "off_chain_status": "completed",
  "network": {"status": "off_blockchain", "status_description": null},
  "from": {
    "id": "idc",
    "resource": "user",
    "resource_path": "/v2/users/idc",
    "currency": "NMR"
  },
  "details": {
    "title": "Received Numeraire",
    "subtitle": "From Coinbase Earn",
    "header": "Received 0.02762431 NMR ($1.01)",
    "health": "positive"
  },
  "hide_native_amount": false
},{
  "id": "id5",
  "type": "inflation_reward",
  "status": "completed",
  "amount": {
    "amount": "0.000076",
    "currency": "ALGO"
  },
  "native_amount": {
    "amount": "0.00",
    "currency": "USD"
  },
  "description": null,
  "created_at": "2021-01-23T18:23:53Z",
  "updated_at": "2021-01-23T18:23:53Z",
  "resource": "transaction",
  "resource_path": "/v2/accounts/boo",
  "instant_exchange": false,
  "from": {
    "id": "idc",
    "resource": "user",
    "resource_path": "/v2/users/idd",
    "currency": "ALGO"
  },
  "details": {
    "title": "Algorand reward",
    "subtitle": "From Coinbase",
    "header": "Received 0.000076 ALGO ($0.00)",
    "health": "positive"
  },
  "hide_native_amount": false
},{
  "id": "id6",
  "type": "send",
  "status": "completed",
  "amount": {
    "amount": "-0.00100000",
    "currency": "BTC"
  },
  "native_amount": {
    "amount": "-0.01",
    "currency": "USD"
  },
  "description": null,
  "created_at": "2021-03-11T13:13:35-07:00",
  "updated_at": "2021-03-26T15:55:43-07:00",
  "resource": "transaction",
  "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/transactions/57ffb4ae-0c59-5430-bcd3-3f98f797a66c",
  "network": {
    "status": "off_blockchain",
    "name": "bitcoin"
  },
  "to": {
    "id": "a6b4c2df-a62c-5d68-822a-dd4e2102e703",
    "resource": "user",
    "resource_path": "/v2/users/a6b4c2df-a62c-5d68-822a-dd4e2102e703"
  },
  "details": {
    "title": "Send bitcoin",
    "subtitle": "to User 2"
  }
},{
"amount": {"amount": "0.05772716", "currency": "ETH"},
 "buy": {"id": "testid-1", "resource": "buy", "resource_path": "/v2/accounts/accountid-1/buys/testid-1"},
 "created_at": "2019-08-24T23:01:35Z",
 "description": null,
 "details": {"header": "Bought 0.05772716 ETH (€10.99)", "health": "positive", "payment_method_name": "1234********7890", "subtitle": "Using 1234********7890", "title": "Bought Ethereum"},
 "hide_native_amount": false,
 "id": "txid-1",
 "instant_exchange": false,
 "native_amount": {"amount": "10.99", "currency": "EUR"},
 "resource": "transaction",
 "resource_path": "/v2/accounts/accountid-1/transactions/txid-1",
 "status": "completed",
 "type": "buy",
 "updated_at": "2021-11-08T01:18:26Z"
},{
"amount": {"amount": "0.05772715", "currency": "ETH"},
 "buy": {"id": "testid-2", "resource": "buy", "resource_path": "/v2/accounts/accountid-1/sells/testid-2"},
 "created_at": "2019-09-24T23:01:35Z",
 "description": null,
 "details": {"header": "Sold 0.05772715 ETH (€10.98)", "health": "positive", "payment_method_name": "1234********7890", "subtitle": "Using 1234********7890", "title": "Sold Ethereum"},
 "hide_native_amount": false,
 "id": "txid-2",
 "instant_exchange": false,
 "native_amount": {"amount": "10.98", "currency": "EUR"},
 "resource": "transaction",
 "resource_path": "/v2/accounts/accountid-1/transactions/txid-2",
 "status": "completed",
 "type": "sell",
 "updated_at": "2021-12-08T01:18:26Z"
},{
 "amount": {"amount": "0.025412", "currency": "SOL"},
 "created_at": "2021-01-24T18:23:53Z",
 "updated_at": "2021-01-24T18:23:53Z",
 "id": "id6",
 "native_amount": {"amount": "0.31", "currency": "EUR"},
 "resource": "transaction",
 "resource_path": "/v2/accounts/accountid-1/transactions/id6",
 "status": "completed",
 "type": "staking_reward"
}]}"""  # noqa: E501


def mock_normal_coinbase_query(url, **kwargs):  # pylint: disable=unused-argument
    if 'transactions' in url:
        return MockResponse(200, TRANSACTIONS_RESPONSE)
    if 'accounts' in url:
        # keep it simple just return a single ID and ignore the rest of the fields
        return MockResponse(200, '{"data": [{"id": "5fs23", "updated_at": "2020-06-08T02:32:16Z"}]}')  # noqa: E501
    # else
    raise AssertionError(f'Unexpected url {url} for test')


def get_exchange_asset_symbols(
        exchange: Location,
        query_suffix: Literal[' OR location IS NULL;', ';'] = ' OR location IS NULL;',
) -> set[str]:
    """Get all asset symbols for an exchange from the global database.

    Using ';' returns only symbols specific to the exchange, while the default
    ' OR location IS NULL;' includes exchange-specific and generic symbols.
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        querystr = 'SELECT exchange_symbol FROM location_asset_mappings WHERE location IS ?' + query_suffix  # noqa: E501
        return {asset[0] for asset in cursor.execute(querystr, (exchange.serialize_for_db(),))}
