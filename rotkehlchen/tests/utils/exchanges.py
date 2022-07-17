import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import TradesFilterQuery
from rotkehlchen.exchanges.binance import BINANCE_BASE_URL, BINANCEUS_BASE_URL, Binance
from rotkehlchen.exchanges.bitcoinde import Bitcoinde
from rotkehlchen.exchanges.bitfinex import Bitfinex
from rotkehlchen.exchanges.bitmex import Bitmex
from rotkehlchen.exchanges.bitpanda import Bitpanda
from rotkehlchen.exchanges.bitstamp import Bitstamp
from rotkehlchen.exchanges.bittrex import Bittrex
from rotkehlchen.exchanges.coinbase import Coinbase
from rotkehlchen.exchanges.coinbasepro import Coinbasepro
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.exchanges.ftx import Ftx
from rotkehlchen.exchanges.gemini import Gemini
from rotkehlchen.exchanges.iconomi import Iconomi
from rotkehlchen.exchanges.independentreserve import Independentreserve
from rotkehlchen.exchanges.kucoin import Kucoin
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.exchanges.poloniex import Poloniex
from rotkehlchen.exchanges.utils import create_binance_symbols_to_pair
from rotkehlchen.fval import FVal
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
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
)
from rotkehlchen.user_messages import MessagesAggregator

POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE = """{
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
      "currency": "DIS",
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

POLONIEX_BALANCES_RESPONSE = """[{
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

POLONIEX_TRADES_RESPONSE = """[{
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

BINANCE_POOL_BALANCES_RESPONSE = """[
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


BINANCE_FIATBUY_RESPONSE = """{
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


BINANCE_FIATSELL_RESPONSE = """{
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


BINANCE_DEPOSITS_HISTORY_RESPONSE = """[
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

BINANCE_WITHDRAWALS_HISTORY_RESPONSE = """[
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


BINANCE_FIATDEPOSITS_RESPONSE = """{
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


BINANCE_FIATWITHDRAWS_RESPONSE = """{
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


def assert_binance_balances_result(balances: Dict[str, Any]) -> None:
    assert balances['BTC']['amount'] == '4723846.89208129'
    assert balances['BTC']['usd_value'] is not None
    assert balances['ETH']['amount'] == '4763368.68006011'
    assert balances['ETH']['usd_value'] is not None


def assert_binance_asset_movements_result(
        movements: List[AssetMovement],
        location: Location,
        got_fiat: bool,
) -> None:
    assert len(movements) == 6 if got_fiat else 4
    assert movements[0].location == location
    assert movements[0].category == AssetMovementCategory.DEPOSIT
    assert movements[0].timestamp == 1508198532
    assert isinstance(movements[0].asset, Asset)
    assert movements[0].asset == A_ETH
    assert movements[0].amount == FVal('0.04670582')
    assert movements[0].fee == ZERO

    assert movements[1].location == location
    assert movements[1].category == AssetMovementCategory.DEPOSIT
    assert movements[1].timestamp == 1508398632
    assert isinstance(movements[1].asset, Asset)
    assert movements[1].asset == A_XMR
    assert movements[1].amount == FVal('1000')
    assert movements[1].fee == ZERO

    assert movements[2].location == location
    assert movements[2].category == AssetMovementCategory.WITHDRAWAL
    assert movements[2].timestamp == 1508198532
    assert isinstance(movements[2].asset, Asset)
    assert movements[2].asset == A_ETH
    assert movements[2].amount == FVal('0.99')
    assert movements[2].fee == FVal('0.01')

    assert movements[3].location == location
    assert movements[3].category == AssetMovementCategory.WITHDRAWAL
    assert movements[3].timestamp == 1508198532
    assert isinstance(movements[3].asset, Asset)
    assert movements[3].asset == A_XMR
    assert movements[3].amount == FVal('999.9999')
    assert movements[3].fee == FVal('0.0001')

    if got_fiat:
        assert movements[4].location == location
        assert movements[4].category == AssetMovementCategory.DEPOSIT
        assert movements[4].timestamp == 1626144956
        assert isinstance(movements[4].asset, Asset)
        assert movements[4].asset == A_EUR
        assert movements[4].amount == FVal('10')
        assert movements[4].fee == FVal('0')

        assert movements[5].location == location
        assert movements[5].category == AssetMovementCategory.WITHDRAWAL
        assert movements[5].timestamp == 1636144956
        assert isinstance(movements[5].asset, Asset)
        assert movements[5].asset == A_EUR
        assert movements[5].amount == FVal('10')
        assert movements[5].fee == FVal('0.02')


def assert_poloniex_balances_result(balances: Dict[str, Any]) -> None:
    assert balances['BTC']['amount'] == '5.5'
    assert balances['BTC']['usd_value'] is not None
    assert balances['ETH']['amount'] == '11.0'
    assert balances['ETH']['usd_value'] is not None


def mock_binance_balance_response(url, **kwargs):  # pylint: disable=unused-argument
    if 'futures' in url:
        return MockResponse(200, BINANCE_FUTURES_WALLET_RESPONSE)
    if 'lending' in url:
        return MockResponse(200, BINANCE_LENDING_WALLET_RESPONSE)
    if 'https://fapi' in url:
        return MockResponse(200, BINANCE_USDT_FUTURES_BALANCES_RESPONSE)
    if 'https://dapi' in url:
        return MockResponse(200, BINANCE_COIN_FUTURES_BALANCES_RESPONSE)
    if 'bswap/liquidity' in url:
        return MockResponse(200, BINANCE_POOL_BALANCES_RESPONSE)

    # else
    return MockResponse(200, BINANCE_BALANCES_RESPONSE)


def patch_binance_balances_query(binance: 'Binance'):
    def mock_binance_asset_return(url, timeout, *args):  # pylint: disable=unused-argument
        if 'futures' in url:
            response = '{"crossCollaterals":[]}'
        elif 'lending' in url:
            response = '{"positionAmountVos":[]}'
        elif 'https://fapi' in url:
            response = '[]'
        elif 'https://dapi' in url:
            response = '[]'
        elif 'bswap/liquidity' in url:
            response = '[]'
        else:
            response = BINANCE_BALANCES_RESPONSE
        return MockResponse(200, response)

    binance_patch = patch.object(binance.session, 'get', side_effect=mock_binance_asset_return)
    return binance_patch


def patch_poloniex_balances_query(poloniex: 'Poloniex'):
    def mock_poloniex_asset_return(url, *args, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, POLONIEX_BALANCES_RESPONSE)

    poloniex_patch = patch.object(poloniex.session, 'get', side_effect=mock_poloniex_asset_return)
    return poloniex_patch

# # -- Test Exchange Objects creation --


def create_test_coinbase(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> Coinbase:
    mock = Coinbase(
        name='coinbase',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
    )
    return mock


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
        api_key: Optional[ApiKey] = None,
        secret: Optional[ApiSecret] = None,
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
        name='bitstamp',
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
        name='bittrex',
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
        name='coinbasepro',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
        passphrase=passphrase,
    )
    return coinbasepro


def create_test_ftx(
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> Ftx:
    mock = Ftx(
        name='ftx',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=msg_aggregator,
        ftx_subaccount=None,
    )
    return mock


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
        api_key: Optional[ApiKey] = None,
        secret: Optional[ApiSecret] = None,
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


def try_get_first_exchange(
        exchange_manager: ExchangeManager,
        location: Location,
) -> Optional[ExchangeInterface]:
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
            db.update_used_query_range(write_cursor=cursor, name=f'{str(exchange_location)}_trades_{str(exchange_location)}', start_ts=0, end_ts=9999)  # noqa: E501
            db.update_used_query_range(write_cursor=cursor, name=f'{str(exchange_location)}_margins_{str(exchange_location)}', start_ts=0, end_ts=9999)  # noqa: E501
            db.update_used_query_range(write_cursor=cursor, name=f'{str(exchange_location)}_asset_movements_{str(exchange_location)}', start_ts=0, end_ts=9999)  # noqa: E501


def check_saved_events_for_exchange(
        exchange_location: Location,
        db: DBHandler,
        should_exist: bool,
        queryrange_formatstr: str = '{exchange}_{type}_{exchange}',
) -> None:
    with db.conn.read_ctx() as cursor:
        trades = db.get_trades(
            cursor,
            filter_query=TradesFilterQuery.make(location=exchange_location),
            has_premium=True,
        )
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


BUYS_RESPONSE = """{
"pagination": {
    "ending_before": null,
    "starting_after": null,
    "limit": 25,
    "order": "desc",
    "previous_uri": null,
    "next_uri": null
},
"data": [{
  "id": "9e14d574-30fa-5d85-b02c-6be0d851d61d",
  "status": "completed",
  "payment_method": {
    "id": "83562370-3e5c-51db-87da-752af5ab9559",
    "resource": "payment_method",
    "resource_path": "/v2/payment-methods/83562370-3e5c-51db-87da-752af5ab9559"
  },
  "transaction": {
    "id": "4117f7d6-5694-5b36-bc8f-847509850ea4",
    "resource": "transaction",
    "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/transactions/441b9494"
  },
  "amount": {
    "amount": "486.34313725",
    "currency": "BTC"
  },
  "total": {
    "amount": "4863.43",
    "currency": "USD"
  },
  "subtotal": {
    "amount": "4862.42",
    "currency": "USD"
  },
  "created_at": "2017-07-21T23:43:59-07:00",
  "updated_at": "2017-07-21T23:43:59-07:00",
  "resource": "buy",
  "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/buys/9e14d574",
  "committed": true,
  "instant": false,
  "fee": {
    "amount": "1.01",
    "currency": "USD"
  },
  "payout_at": "2017-07-23T23:44:08Z"
}]}"""


SELLS_RESPONSE = """{
"pagination": {
    "ending_before": null,
    "starting_after": null,
    "limit": 25,
    "order": "desc",
    "previous_uri": null,
    "next_uri": null
},
"data": [{
  "id": "1e14d574-30fa-5d85-b02c-6be0d851d61d",
  "status": "completed",
  "payment_method": {
    "id": "23562370-3e5c-51db-87da-752af5ab9559",
    "resource": "payment_method",
    "resource_path": "/v2/payment-methods/83562370-3e5c-51db-87da-752af5ab9559"
  },
  "transaction": {
    "id": "3117f7d6-5694-5b36-bc8f-847509850ea4",
    "resource": "transaction",
    "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/transactions/4117f7d6"
  },
  "amount": {
    "amount": "100.45",
    "currency": "ETH"
  },
  "total": {
    "amount": "8940.12",
    "currency": "USD"
  },
  "subtotal": {
    "amount": "8930.02",
    "currency": "USD"
  },
  "created_at": "2016-03-26T13:42:00-07:00",
  "updated_at": "2016-03-26T13:42:00-07:00",
  "resource": "sell",
  "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/sells/9e14d574",
  "committed": true,
  "instant": true,
  "fee": {
    "amount": "10.1",
    "currency": "USD"
  },
  "payout_at": "2016-04-01T23:43:59-07:00"
}]}"""

DEPOSITS_RESPONSE = """{
"pagination": {
    "ending_before": null,
    "starting_after": null,
    "limit": 25,
    "order": "desc",
    "previous_uri": null,
    "next_uri": null
},
"data": [{
      "id": "1130eaec-07d7-54c4-a72c-2e92826897df",
      "status": "completed",
      "payment_method": {
        "id": "83562370-3e5c-51db-87da-752af5ab9559",
        "resource": "payment_method",
        "resource_path": "/v2/payment-methods/83562370-3e5c-51db-87da-752af5ab9559"
      },
      "transaction": {
        "id": "441b9494-b3f0-5b98-b9b0-4d82c21c252a",
        "resource": "transaction",
        "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/transactions/441b9494"
      },
      "amount": {
        "amount": "55.00",
        "currency": "USD"
      },
      "subtotal": {
        "amount": "54.95",
        "currency": "USD"
      },
      "created_at": "2015-01-31T20:49:02Z",
      "updated_at": "2015-02-11T16:54:02-08:00",
      "resource": "deposit",
      "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/deposits/67e0eaec",
      "committed": true,
      "fee": {
        "amount": "0.05",
        "currency": "USD"
      },
      "payout_at": "2018-02-18T16:54:00-08:00"
}]}"""


WITHDRAWALS_RESPONSE = """{
"pagination": {
    "ending_before": null,
    "starting_after": null,
    "limit": 25,
    "order": "desc",
    "previous_uri": null,
    "next_uri": null
},
"data": [{
      "id": "146eaec-07d7-54c4-a72c-2e92826897df",
      "status": "completed",
      "payment_method": {
        "id": "85562970-3e5c-51db-87da-752af5ab9559",
        "resource": "payment_method",
        "resource_path": "/v2/payment-methods/83562370-3e5c-51db-87da-752af5ab9559"
      },
      "transaction": {
        "id": "441b9454-b3f0-5b98-b9b0-4d82c21c252a",
        "resource": "transaction",
        "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/transactions/441b9494"
      },
      "amount": {
        "amount": "10.00",
        "currency": "USD"
      },
      "subtotal": {
        "amount": "9.99",
        "currency": "USD"
      },
      "created_at": "2017-01-31T20:49:02Z",
      "updated_at": "2017-01-31T20:49:02Z",
      "resource": "withdrawal",
      "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/withdrawals/67e0eaec",
      "committed": true,
      "fee": {
        "amount": "0.01",
        "currency": "USD"
      },
      "payout_at": null
}]}"""

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
}]}"""


def mock_normal_coinbase_query(url, **kwargs):  # pylint: disable=unused-argument
    if 'buys' in url:
        return MockResponse(200, BUYS_RESPONSE)
    if 'sells' in url:
        return MockResponse(200, SELLS_RESPONSE)
    if 'deposits' in url:
        return MockResponse(200, DEPOSITS_RESPONSE)
    if 'withdrawals' in url:
        return MockResponse(200, WITHDRAWALS_RESPONSE)
    if 'transactions' in url:
        return MockResponse(200, TRANSACTIONS_RESPONSE)
    if 'accounts' in url:
        # keep it simple just return a single ID and ignore the rest of the fields
        return MockResponse(200, '{"data": [{"id": "5fs23"}]}')
    # else
    raise AssertionError(f'Unexpected url {url} for test')
