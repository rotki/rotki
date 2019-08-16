from typing import Any, Dict, List, Union
from unittest.mock import patch

from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.exchanges import POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.transactions import EthereumTransaction
from rotkehlchen.typing import AssetAmount, Exchange, Timestamp, TradeType

TEST_END_TS = 1559427707


# Prices queried by cryptocompare  @ 12/01/2019
prices = {
    'BTC': {
        'EUR': {
            1446979735: FVal(355.9),
            1449809536: FVal(386.175),
            1464393600: FVal(422.9),
            1473505138: FVal(556.435),
            1473897600: FVal(542.87),
            1475042230: FVal(537.805),
            1476536704: FVal(585.96),
            1476979735: FVal(578.505),
            1479200704: FVal(667.185),
            1480683904: FVal(723.505),
            1484629704: FVal(810.49),
            1486299904: FVal(942.78),
            1487289600: FVal(979.39),
            1491177600: FVal(1039.935),
            1495969504: FVal(1964.685),
            1498694400: FVal(2244.255),
            1512693374: FVal(14415.365),
        },
    },
    'ETH': {
        'EUR': {
            1446979735: FVal(0.8583),
            1463184190: FVal(9.185),
            1463508234: FVal(10.785),
            1473505138: FVal(10.365),
            1475042230: FVal(11.925),
            1476536704: FVal(10.775),
            1479510304: FVal(8.915),
            1491062063: FVal(47.5),
            1493291104: FVal(52.885),
            1511626623: FVal(393.955),
        },
    },
    'XMR': {
        'EUR': {
            1449809536: FVal(0.396987900),  # BTC adjusted price
        },
    },
    'DASH': {
        'EUR': {
            # TODO: Switch to the DASH non-usd adjusted prices since cryptocompare
            # starting returning correct results and adjust the tests accordingly
            # 1479200704: FVal(9),
            1479200704: FVal(8.9456),  # old USD adjusted price

            # 1480683904: FVal(8.155),
            1480683904: FVal(8.104679571509114828039),  # old USD adjusted price

            # 1483351504: FVal(11.115),
            1483351504: FVal(10.9698996),  # old USD adjusted price

            # 1484629704: FVal(12.89),  # found in historical hourly
            1484629704: FVal(12.4625608386372145),  # old USD adjusted price

            # 1485252304: FVal(13.48),
            1485252304: FVal(13.22106438),  # old USD adjusted price

            # 1486299904: FVal(15.29),
            1486299904: FVal(15.36169816590634019),  # old USD adjusted price

            # 1487027104: FVal(16.08)
            1487027104: FVal(15.73995672),  # old USD adjusted price

            # 1502715904: FVal(173.035),
            1502715904: FVal(173.77),  # old USD adjusted price
        },
    },
}


def check_result_of_history_creation(
        start_ts: Timestamp,
        end_ts: Timestamp,
        trade_history: List[Union[Trade, MarginPosition]],
        loan_history: Dict,
        asset_movements: List[AssetMovement],
        eth_transactions: List[EthereumTransaction],
) -> Dict[str, Any]:
    """This function offers Some simple assertions on the result of the
    created history. The entire processing part of the history is mocked
    away by this checking function"""
    assert start_ts == 0, 'should be same as given to process_history'
    assert end_ts == TEST_END_TS, 'should be same as given to process_history'

    # TODO: Add more assertions/check for each action
    # OR instead do it in tests for conversion of actions(trades, loans, deposits e.t.c.)
    # from exchange to our format for each exchange
    assert len(trade_history) == 10
    assert trade_history[0].location == 'kraken'
    assert trade_history[0].pair == 'ETH_EUR'
    assert trade_history[0].trade_type == TradeType.BUY
    assert trade_history[1].location == 'kraken'
    assert trade_history[1].pair == 'BTC_EUR'
    assert trade_history[1].trade_type == TradeType.BUY
    assert trade_history[2].location == 'bittrex'
    assert trade_history[2].pair == 'LTC_BTC'
    assert trade_history[2].trade_type == TradeType.BUY
    assert trade_history[3].location == 'bittrex'
    assert trade_history[3].pair == 'LTC_ETH'
    assert trade_history[3].trade_type == TradeType.SELL
    assert isinstance(trade_history[4], MarginPosition)
    assert trade_history[4].profit_loss == FVal('0.05')
    assert trade_history[5].location == 'binance'
    assert trade_history[5].pair == 'ETH_BTC'
    assert trade_history[5].trade_type == TradeType.BUY
    assert trade_history[6].location == 'binance'
    assert trade_history[6].pair == 'RDN_ETH'
    assert trade_history[6].trade_type == TradeType.SELL
    assert trade_history[7].location == 'poloniex'
    assert trade_history[7].pair == 'ETH_BTC'
    assert trade_history[7].trade_type == TradeType.SELL
    assert trade_history[8].location == 'poloniex'
    assert trade_history[8].pair == 'ETH_BTC'
    assert trade_history[8].trade_type == TradeType.BUY
    assert trade_history[9].location == 'poloniex'
    assert trade_history[9].pair == 'XMR_ETH'
    assert trade_history[9].trade_type == TradeType.BUY

    assert len(loan_history) == 2
    assert loan_history[0].currency == A_ETH
    assert loan_history[0].earned == AssetAmount(FVal('0.00000001'))
    assert loan_history[1].currency == A_BTC
    assert loan_history[1].earned == AssetAmount(FVal('0.00000005'))

    assert len(asset_movements) == 10
    assert asset_movements[0].exchange == Exchange.KRAKEN
    assert asset_movements[0].category == 'deposit'
    assert asset_movements[0].asset == A_BTC
    assert asset_movements[1].exchange == Exchange.KRAKEN
    assert asset_movements[1].category == 'deposit'
    assert asset_movements[1].asset == A_ETH
    assert asset_movements[2].exchange == Exchange.KRAKEN
    assert asset_movements[2].category == 'withdrawal'
    assert asset_movements[2].asset == A_BTC
    assert asset_movements[3].exchange == Exchange.KRAKEN
    assert asset_movements[3].category == 'withdrawal'
    assert asset_movements[3].asset == A_ETH
    assert asset_movements[4].exchange == Exchange.POLONIEX
    assert asset_movements[4].category == 'withdrawal'
    assert asset_movements[4].asset == A_BTC
    assert asset_movements[5].exchange == Exchange.POLONIEX
    assert asset_movements[5].category == 'withdrawal'
    assert asset_movements[5].asset == A_ETH
    assert asset_movements[6].exchange == Exchange.POLONIEX
    assert asset_movements[6].category == 'deposit'
    assert asset_movements[6].asset == A_BTC
    assert asset_movements[7].exchange == Exchange.POLONIEX
    assert asset_movements[7].category == 'deposit'
    assert asset_movements[7].asset == A_ETH
    assert asset_movements[8].exchange == Exchange.BITMEX
    assert asset_movements[8].category == 'deposit'
    assert asset_movements[8].asset == A_BTC
    assert asset_movements[9].exchange == Exchange.BITMEX
    assert asset_movements[9].category == 'withdrawal'
    assert asset_movements[9].asset == A_BTC

    # The history creation for these is not yet tested
    assert len(eth_transactions) == 0

    return {}


def check_result_of_history_creation_for_remote_errors(
        start_ts: Timestamp,
        end_ts: Timestamp,
        trade_history: List[Trade],
        loan_history: Dict,
        asset_movements: List[AssetMovement],
        eth_transactions: List[EthereumTransaction],
) -> Dict[str, Any]:
    assert len(trade_history) == 0
    assert len(loan_history) == 0
    assert len(asset_movements) == 0
    assert len(eth_transactions) == 0
    return {}


def mock_exchange_responses(rotki: Rotkehlchen, remote_errors: bool):
    invalid_payload = "[{"

    def mock_binance_api_queries(url):
        if remote_errors:
            payload = invalid_payload
        elif 'myTrades' in url:
            # Can't mock unknown assets in binance trade query since
            # only all known pairs are queried
            payload = '[]'
            if 'symbol=ETHBTC' in url:
                payload = """[{
                "symbol": "ETHBTC",
                "id": 1,
                "orderId": 1,
                "price": "0.0063213",
                "qty": "5.0",
                "commission": "0.005",
                "commissionAsset": "ETH",
                "time": 1512561941000,
                "isBuyer": true,
                "isMaker": false,
                "isBestMatch": true
                }]"""
            elif 'symbol=RDNETH' in url:
                payload = """[{
                "symbol": "RDNETH",
                "id": 2,
                "orderId": 2,
                "price": "0.0063213",
                "qty": "5.0",
                "commission": "0.005",
                "commissionAsset": "RDN",
                "time": 1512561942000,
                "isBuyer": false,
                "isMaker": false,
                "isBestMatch": true
                }]"""
        elif 'depositHistory.html' in url:
            payload = '{"success": true, "depositList": []}'
        elif 'withdrawHistory.html' in url:
            payload = '{"success": true, "withdrawList": []}'
        else:
            raise RuntimeError(f'Binance test mock got unexpected/unmocked url {url}')

        return MockResponse(200, payload)

    def mock_poloniex_api_queries(url, req):  # pylint: disable=unused-argument
        payload = ''
        if remote_errors:
            payload = invalid_payload
        elif 'returnTradeHistory' == req['command']:
            payload = """{
                "BTC_ETH": [{
                    "globalTradeID": 394131412,
                    "tradeID": "5455033",
                    "date": "2018-10-16 18:05:17",
                    "rate": "0.06935244",
                    "amount": "1.40308443",
                    "total": "0.09730732",
                    "fee": "0.00100000",
                    "orderNumber": "104768235081",
                    "type": "sell",
                    "category": "exchange"
                }, {
                    "globalTradeID": 394131413,
                    "tradeID": "5455034",
                    "date": "2018-10-16 18:07:17",
                    "rate": "0.06935244",
                    "amount": "1.40308443",
                    "total": "0.09730732",
                    "fee": "0.00100000",
                    "orderNumber": "104768235081",
                    "type": "buy",
                    "category": "exchange"
                }],
                "ETH_XMR": [{
                    "globalTradeID": 394131415,
                    "tradeID": "5455036",
                    "date": "2018-10-16 18:07:18",
                    "rate": "0.06935244",
                    "amount": "1.40308443",
                    "total": "0.09730732",
                    "fee": "0.00100000",
                    "orderNumber": "104768235081",
                    "type": "buy",
                    "category": "exchange"
                }],
                "ETH_NOEXISTINGASSET": [{
                    "globalTradeID": 394131416,
                    "tradeID": "5455036",
                    "date": "2018-10-16 18:07:17",
                    "rate": "0.06935244",
                    "amount": "1.40308443",
                    "total": "0.09730732",
                    "fee": "0.00100000",
                    "orderNumber": "104768235081",
                    "type": "buy",
                    "category": "exchange"
                }],
                "ETH_BALLS": [{
                    "globalTradeID": 394131417,
                    "tradeID": "5455036",
                    "date": "2018-10-16 18:07:17",
                    "rate": "0.06935244",
                    "amount": "1.40308443",
                    "total": "0.09730732",
                    "fee": "0.00100000",
                    "orderNumber": "104768235081",
                    "type": "buy",
                    "category": "exchange"
                }]
            }"""

        elif 'returnLendingHistory' == req['command']:
            payload = """[{
                "id": 246300115,
                "currency": "BTC",
                "rate": "0.00013890",
                "amount": "0.33714830",
                "duration": "0.00090000",
                "interest": "0.00000005",
                "fee": "0.00000000",
                "earned": "0.00000005",
                "open": "2017-01-01 23:41:37",
                "close": "2017-01-01 23:42:51"
            }, {
                "id": 246294775,
                "currency": "ETH",
                "rate": "0.00013890",
                "amount": "0.03764586",
                "duration": "0.00150000",
                "interest": "0.00000001",
                "fee": "0.00000000",
                "earned": "0.00000001",
                "open": "2017-01-01 23:36:32",
                "close": "2017-01-01 23:38:45"
            }, {
                "id": 246294776,
                "currency": "NOTEXISTINGASSET",
                "rate": "0.00013890",
                "amount": "0.03764586",
                "duration": "0.00150000",
                "interest": "0.00000001",
                "fee": "0.00000000",
                "earned": "0.00000001",
                "open": "2017-01-01 23:36:32",
                "close": "2017-01-01 23:38:45"
            }, {
                "id": 246294777,
                "currency": "BDC",
                "rate": "0.00013890",
                "amount": "0.03764586",
                "duration": "0.00150000",
                "interest": "0.00000001",
                "fee": "0.00000000",
                "earned": "0.00000001",
                "open": "2017-01-01 23:36:32",
                "close": "2017-01-01 23:38:45"
            }]"""
        elif 'returnDepositsWithdrawals' == req['command']:
            payload = POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE
        else:
            raise RuntimeError(
                f'Poloniex test mock got unexpected/unmocked command {req["command"]}',
            )
        return MockResponse(200, payload)

    def mock_bittrex_api_queries(url):
        if remote_errors:
            payload = invalid_payload
        elif 'getorderhistory' in url:
            payload = """
{
  "success": true,
  "message": "''",
  "result": [{
      "OrderUuid": "fd97d393-e9b9-4dd1-9dbf-f288fc72a185",
      "Exchange": "BTC-LTC",
      "TimeStamp": "2017-05-01T15:00:00.00",
      "OrderType": "LIMIT_BUY",
      "Limit": 1e-8,
      "Quantity": 667.03644955,
      "QuantityRemaining": 0,
      "Commission": 0.00004921,
      "Price": 0.01968424,
      "PricePerUnit": 0.0000295,
      "IsConditional": false,
      "ImmediateOrCancel": false
    }, {
      "OrderUuid": "ad97d393-e9b9-4dd1-9dbf-f288fc72a185",
      "Exchange": "ETH-LTC",
      "TimeStamp": "2017-05-02T15:00:00.00",
      "OrderType": "LIMIT_SELL",
      "Limit": 1e-8,
      "Quantity": 667.03644955,
      "QuantityRemaining": 0,
      "Commission": 0.00004921,
      "Price": 0.01968424,
      "PricePerUnit": 0.0000295,
      "IsConditional": false,
      "ImmediateOrCancel": false
    }, {
      "OrderUuid": "ed97d393-e9b9-4dd1-9dbf-f288fc72a185",
      "Exchange": "PTON-ETH",
      "TimeStamp": "2017-05-02T15:00:00.00",
      "OrderType": "LIMIT_SELL",
      "Limit": 1e-8,
      "Quantity": 667.03644955,
      "QuantityRemaining": 0,
      "Commission": 0.00004921,
      "Price": 0.01968424,
      "PricePerUnit": 0.0000295,
      "IsConditional": false,
      "ImmediateOrCancel": false
    }, {
      "OrderUuid": "1d97d393-e9b9-4dd1-9dbf-f288fc72a185",
      "Exchange": "ETH-IDONTEXIST",
      "TimeStamp": "2017-05-02T15:00:00.00",
      "OrderType": "LIMIT_SELL",
      "Limit": 1e-8,
      "Quantity": 667.03644955,
      "QuantityRemaining": 0,
      "Commission": 0.00004921,
      "Price": 0.01968424,
      "PricePerUnit": 0.0000295,
      "IsConditional": false,
      "ImmediateOrCancel": false
    }, {
      "OrderUuid": "2d97d393-e9b9-4dd1-9dbf-f288fc72a185",
      "Exchange": "%$#%$#%#$%",
      "TimeStamp": "2017-05-02T15:00:00.00",
      "OrderType": "LIMIT_BUY",
      "Limit": 1e-8,
      "Quantity": 667.03644955,
      "QuantityRemaining": 0,
      "Commission": 0.00004921,
      "Price": 0.01968424,
      "PricePerUnit": 0.0000295,
      "IsConditional": false,
      "ImmediateOrCancel": false
}]
}
"""
        elif 'getdeposithistory' in url or 'getwithdrawalhistory' in url:
            # For now no deposits or withdrawals for bittrex in the big history test
            payload = '{"success": true, "message": "''", "result": []}'
        else:
            raise RuntimeError(f'Bittrex test mock got unexpected/unmocked url {url}')

        return MockResponse(200, payload)

    def mock_bitmex_api_queries(url, data):
        if remote_errors:
            payload = invalid_payload
        elif 'user/walletHistory' in url:
            payload = """[{
            "transactID": "foo",
            "account": 0,
            "currency": "XBt",
            "transactType": "Deposit",
            "amount": 15000000,
            "fee": 0,
            "transactStatus": "foo",
            "address": "foo",
            "tx": "foo",
            "text": "foo",
            "transactTime": "2017-04-03T15:00:00.929Z",
            "timestamp": "2017-04-03T15:00:00.929Z"
            },{
            "transactID": "foo",
            "account": 0,
            "currency": "XBt",
            "transactType": "RealisedPNL",
            "amount": 5000000,
            "fee": 0.01,
            "transactStatus": "foo",
            "address": "foo",
            "tx": "foo",
            "text": "foo",
            "transactTime": "2017-05-02T15:00:00.929Z",
            "timestamp": "2017-05-02T15:00:00.929Z"
            },{
            "transactID": "foo",
            "account": 0,
            "currency": "XBt",
            "transactType": "Withdrawal",
            "amount": 1000000,
            "fee": 0.001,
            "transactStatus": "foo",
            "address": "foo",
            "tx": "foo",
            "text": "foo",
            "transactTime": "2017-05-23T15:00:00.00.929Z",
            "timestamp": "2017-05-23T15:00:00.929Z"
            },{
            "transactID": "foo",
            "account": 0,
            "currency": "XBt",
            "transactType": "Withdrawal",
            "amount": 0.5,
            "fee": 0.001,
            "transactStatus": "foo",
            "address": "foo",
            "tx": "foo",
            "text": "foo",
            "transactTime": "2019-08-23T15:00:00.00.929Z",
            "timestamp": "2019-08-23T15:00:00.929Z"
            },{
            "transactID": "foo",
            "account": 0,
            "currency": "XBt",
            "transactType": "RealisedPNL",
            "amount": 0.5,
            "fee": 0.001,
            "transactStatus": "foo",
            "address": "foo",
            "tx": "foo",
            "text": "foo",
            "transactTime": "2019-08-23T15:00:00.929Z",
            "timestamp": "2019-08-23T15:00:00.929Z"
            }]"""
        else:
            raise RuntimeError(f'Bitmex test mock got unexpected/unmocked url {url}')

        return MockResponse(200, payload)

    polo_patch = patch.object(
        rotki.poloniex.session,
        'post',
        side_effect=mock_poloniex_api_queries,
    )
    binance_patch = patch.object(
        rotki.binance.session,
        'get',
        side_effect=mock_binance_api_queries,
    )
    bittrex_patch = patch.object(
        rotki.bittrex.session,
        'get',
        side_effect=mock_bittrex_api_queries,
    )
    bitmex_patch = patch.object(
        rotki.bitmex.session,
        'get',
        side_effect=mock_bitmex_api_queries,
    )

    return polo_patch, binance_patch, bittrex_patch, bitmex_patch


def mock_history_processing(rotki: Rotkehlchen, remote_errors=False):
    """ Patch away the processing of history """
    mock_function = check_result_of_history_creation
    if remote_errors:
        mock_function = check_result_of_history_creation_for_remote_errors
    accountant_patch = patch.object(
        rotki.accountant,
        'process_history',
        side_effect=mock_function,
    )
    return accountant_patch


def mock_history_processing_and_exchanges(rotki: Rotkehlchen, remote_errors=False):
    accountant_patch = mock_history_processing(rotki, remote_errors=remote_errors)
    polo_patch, binance_patch, bittrex_patch, bitmex_patch = mock_exchange_responses(
        rotki,
        remote_errors,
    )
    return (
        accountant_patch,
        polo_patch,
        binance_patch,
        bittrex_patch,
        bitmex_patch,
    )
