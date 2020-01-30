from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union
from unittest.mock import _patch, patch

from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.constants import (
    ETH_ADDRESS1,
    ETH_ADDRESS2,
    ETH_ADDRESS3,
    MOCK_INPUT_DATA,
    MOCK_INPUT_DATA_HEX,
    TX_HASH_STR1,
    TX_HASH_STR2,
    TX_HASH_STR3,
)
from rotkehlchen.tests.utils.exchanges import POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.transactions import EthereumTransaction
from rotkehlchen.typing import (
    AssetAmount,
    AssetMovementCategory,
    Location,
    SupportedBlockchain,
    Timestamp,
    TradeType,
)
from rotkehlchen.utils.misc import hexstring_to_bytes

TEST_END_TS = 1559427707


# Prices queried by cryptocompare
prices = {
    'BTC': {
        'EUR': {
            1428994442: FVal(210.865),
            1446979735: FVal(355.9),
            1448994442: FVal(338.805),
            1449809536: FVal(386.175),
            1458994442: FVal(373.295),
            1464393600: FVal(422.9),
            1473505138: FVal(556.435),
            1473897600: FVal(542.87),
            1475042230: FVal(537.805),
            1476536704: FVal(585.96),
            1476979735: FVal(578.505),
            1479200704: FVal(667.185),
            1480683904: FVal(723.505),
            1483314171: FVal(947.175),
            1484629704: FVal(810.49),
            1486299904: FVal(942.78),
            1487289600: FVal(979.39),
            1491177600: FVal(1039.935),
            1491231601: FVal(1062.67),
            1493650800: FVal(1259.295),
            1493737201: FVal(1310.735),
            1495551601: FVal(2030.01),
            1495969504: FVal(1964.685),
            1498694400: FVal(2244.465),
            1512561941: FVal(10929.925),
            1512693374: FVal(14415.365),
            1539713117: FVal(5626.17),
            1539713237: FVal(5626.17),
            1566572401: FVal(9367.55),
        },
    },
    'ETH': {
        'EUR': {
            1438994442: FVal(2.549),
            1439048640: FVal(1.13),
            1439048643: FVal(1.13),
            1439048645: FVal(1.13),
            1439994442: FVal(1.134),
            1446979735: FVal(0.8583),
            1448994442: FVal(0.83195),
            1463184190: FVal(9.187),
            1463508234: FVal(10.785),
            1468994442: FVal(10.80),
            1473505138: FVal(10.36),
            1475042230: FVal(11.925),
            1476536704: FVal(10.775),
            1479510304: FVal(8.9145),
            1483313925: FVal(7.764),
            1491062063: FVal(47.865),
            1493291104: FVal(53.175),
            1493737200: FVal(69.505),
            1511626623: FVal(396.56),
            1512561941: FVal(380.34),
            1512561942: FVal(380.34),
            1539713117: FVal(178.615),
            1539713237: FVal(178.615),
            1539713238: FVal(178.615),
        },
    },
    'RDN': {
        'EUR': {
            1512561942: ZERO,
        },
    },
    'LTC': {
        'EUR': {
            1493650800: FVal(14.07),
            1493737200: FVal(14.56),
        },
    },
    'XMR': {
        'EUR': {
            1449809536: FVal(0.39665),
            1539713238: FVal(91.86),
        },
    },
    'DASH': {
        'EUR': {
            1479200704: FVal(9.0015),
            1480683904: FVal(8.154),
            1483351504: FVal(11.115),
            1484629704: FVal(12.88),
            1485252304: FVal(13.48),
            1486299904: FVal(15.29),
            1487027104: FVal(16.08),
            1502715904: FVal(173.035),
        },
    },
}


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
            "transactID": "id1",
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
            "transactID": "id2",
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
            "transactID": "id3",
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
            "transactID": "id4",
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
            "transactID": "id5",
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

    # TODO: Turn this into a loop of all exchanges and return a list of patches
    poloniex = rotki.exchange_manager.connected_exchanges.get('poloniex', None)
    polo_patch = None
    if poloniex:
        polo_patch = patch.object(
            poloniex.session,
            'post',
            side_effect=mock_poloniex_api_queries,
        )

    binance = rotki.exchange_manager.connected_exchanges.get('binance', None)
    binance_patch = None
    if binance:
        binance_patch = patch.object(
            binance.session,
            'get',
            side_effect=mock_binance_api_queries,
        )

    bittrex = rotki.exchange_manager.connected_exchanges.get('bittrex', None)
    bittrex_patch = None
    if bittrex:
        bittrex_patch = patch.object(
            bittrex.session,
            'get',
            side_effect=mock_bittrex_api_queries,
        )

    bitmex = rotki.exchange_manager.connected_exchanges.get('bitmex', None)
    bitmex_patch = None
    if bitmex:
        bitmex_patch = patch.object(
            bitmex.session,
            'get',
            side_effect=mock_bitmex_api_queries,
        )

    return polo_patch, binance_patch, bittrex_patch, bitmex_patch


def mock_history_processing(
        rotki: Rotkehlchen,
        should_mock_history_processing: bool = True,
        remote_errors: bool = False,
        history_start_ts: Optional[Timestamp] = None,
        history_end_ts: Optional[Timestamp] = None,
):
    """ Patch away the processing of history """
    if remote_errors is True and should_mock_history_processing is False:
        raise AssertionError(
            'Checking for remote errors while not mocking history is not supported',
        )
    original_history_processing_function = rotki.accountant.process_history

    def check_result_of_history_creation(
            start_ts: Timestamp,
            end_ts: Timestamp,
            trade_history: List[Union[Trade, MarginPosition]],
            loan_history: Dict,
            asset_movements: List[AssetMovement],
            eth_transactions: List[EthereumTransaction],
    ) -> Dict[str, Any]:
        """This function offers some simple assertions on the result of the
        created history. The entire processing part of the history is mocked
        away by this checking function"""
        if history_start_ts is None:
            assert start_ts == 0, 'if no start_ts is given it should be zero'
        else:
            assert start_ts == history_start_ts, 'should be same as given to process_history'
        if history_end_ts is not None:
            assert end_ts == history_end_ts, 'should be same as given to process_history'

        # TODO: Add more assertions/check for each action
        # OR instead do it in tests for conversion of actions(trades, loans, deposits e.t.c.)
        # from exchange to our format for each exchange
        assert len(trade_history) == 11
        assert trade_history[0].location == Location.KRAKEN
        assert trade_history[0].pair == 'ETH_EUR'
        assert trade_history[0].trade_type == TradeType.BUY
        assert trade_history[1].location == Location.KRAKEN
        assert trade_history[1].pair == 'BTC_EUR'
        assert trade_history[1].trade_type == TradeType.BUY
        assert trade_history[2].location == Location.BITTREX
        assert trade_history[2].pair == 'LTC_BTC'
        assert trade_history[2].trade_type == TradeType.BUY
        assert trade_history[3].location == Location.BITTREX
        assert trade_history[3].pair == 'LTC_ETH'
        assert trade_history[3].trade_type == TradeType.SELL
        assert isinstance(trade_history[4], MarginPosition)
        assert trade_history[4].profit_loss == FVal('0.05')
        assert trade_history[5].location == Location.BINANCE
        assert trade_history[5].pair == 'ETH_BTC'
        assert trade_history[5].trade_type == TradeType.BUY
        assert trade_history[6].location == Location.BINANCE
        assert trade_history[6].pair == 'RDN_ETH'
        assert trade_history[6].trade_type == TradeType.SELL
        assert trade_history[7].location == Location.POLONIEX
        assert trade_history[7].pair == 'ETH_BTC'
        assert trade_history[7].trade_type == TradeType.SELL
        assert trade_history[8].location == Location.POLONIEX
        assert trade_history[8].pair == 'ETH_BTC'
        assert trade_history[8].trade_type == TradeType.BUY
        assert trade_history[9].location == Location.POLONIEX
        assert trade_history[9].pair == 'XMR_ETH'
        assert trade_history[9].trade_type == TradeType.BUY
        # TODO: investigate why this new bitmex position popped up
        assert isinstance(trade_history[10], MarginPosition)
        assert trade_history[10].profit_loss == FVal('5E-9')

        assert len(loan_history) == 2
        assert loan_history[0].currency == A_ETH
        assert loan_history[0].earned == AssetAmount(FVal('0.00000001'))
        assert loan_history[1].currency == A_BTC
        assert loan_history[1].earned == AssetAmount(FVal('0.00000005'))

        assert len(asset_movements) == 11
        assert asset_movements[0].location == Location.KRAKEN
        assert asset_movements[0].category == AssetMovementCategory.DEPOSIT
        assert asset_movements[0].asset == A_BTC
        assert asset_movements[1].location == Location.KRAKEN
        assert asset_movements[1].category == AssetMovementCategory.DEPOSIT
        assert asset_movements[1].asset == A_ETH
        assert asset_movements[2].location == Location.KRAKEN
        assert asset_movements[2].category == AssetMovementCategory.WITHDRAWAL
        assert asset_movements[2].asset == A_BTC
        assert asset_movements[3].location == Location.KRAKEN
        assert asset_movements[3].category == AssetMovementCategory.WITHDRAWAL
        assert asset_movements[3].asset == A_ETH
        assert asset_movements[4].location == Location.POLONIEX
        assert asset_movements[4].category == AssetMovementCategory.WITHDRAWAL
        assert asset_movements[4].asset == A_BTC
        assert asset_movements[5].location == Location.POLONIEX
        assert asset_movements[5].category == AssetMovementCategory.WITHDRAWAL
        assert asset_movements[5].asset == A_ETH
        assert asset_movements[6].location == Location.POLONIEX
        assert asset_movements[6].category == AssetMovementCategory.DEPOSIT
        assert asset_movements[6].asset == A_BTC
        assert asset_movements[7].location == Location.POLONIEX
        assert asset_movements[7].category == AssetMovementCategory.DEPOSIT
        assert asset_movements[7].asset == A_ETH
        assert asset_movements[8].location == Location.BITMEX
        assert asset_movements[8].category == AssetMovementCategory.DEPOSIT
        assert asset_movements[8].asset == A_BTC
        assert asset_movements[9].location == Location.BITMEX
        assert asset_movements[9].category == AssetMovementCategory.WITHDRAWAL
        assert asset_movements[9].asset == A_BTC
        # TODO: investigate why this new bitmex withdrawal popped up
        assert asset_movements[10].location == Location.BITMEX
        assert asset_movements[10].category == AssetMovementCategory.WITHDRAWAL
        assert asset_movements[10].asset == A_BTC

        # The history creation for these is not yet tested
        assert len(eth_transactions) == 3
        assert eth_transactions[0].block_number == 54092
        assert eth_transactions[0].tx_hash == hexstring_to_bytes(TX_HASH_STR1)
        assert eth_transactions[0].from_address == ETH_ADDRESS1
        assert eth_transactions[0].to_address == ''
        assert eth_transactions[0].value == FVal('11901464239480000000000000')
        assert eth_transactions[0].input_data == MOCK_INPUT_DATA
        assert eth_transactions[1].block_number == 54093
        assert eth_transactions[1].tx_hash == hexstring_to_bytes(TX_HASH_STR2)
        assert eth_transactions[1].from_address == ETH_ADDRESS2
        assert eth_transactions[1].to_address == ETH_ADDRESS1
        assert eth_transactions[1].value == FVal('40000300')
        assert eth_transactions[1].input_data == MOCK_INPUT_DATA
        assert eth_transactions[2].block_number == 54094
        assert eth_transactions[2].tx_hash == hexstring_to_bytes(TX_HASH_STR3)
        assert eth_transactions[2].from_address == ETH_ADDRESS3
        assert eth_transactions[2].to_address == ETH_ADDRESS1
        assert eth_transactions[2].value == FVal('500520300')
        assert eth_transactions[2].input_data == MOCK_INPUT_DATA

        return {}

    def check_result_of_history_creation_and_process_it(
            start_ts: Timestamp,
            end_ts: Timestamp,
            trade_history: List[Union[Trade, MarginPosition]],
            loan_history: Dict,
            asset_movements: List[AssetMovement],
            eth_transactions: List[EthereumTransaction],
    ) -> Dict[str, Any]:
        """Checks results of history creation but also proceeds to normal history processing"""
        check_result_of_history_creation(
            start_ts=start_ts,
            end_ts=end_ts,
            trade_history=trade_history,
            loan_history=loan_history,
            asset_movements=asset_movements,
            eth_transactions=eth_transactions,
        )
        return original_history_processing_function(
            start_ts,
            end_ts,
            trade_history,
            loan_history,
            asset_movements,
            eth_transactions,
        )

    if should_mock_history_processing is True:
        mock_function = check_result_of_history_creation
    else:
        mock_function = check_result_of_history_creation_and_process_it

    if remote_errors:
        mock_function = check_result_of_history_creation_for_remote_errors
    accountant_patch = patch.object(
        rotki.accountant,
        'process_history',
        side_effect=mock_function,
    )
    return accountant_patch


def mock_etherscan_transaction_response(etherscan: Etherscan, remote_errors: bool):
    def mocked_request_dict(url, *args, **kwargs):
        if remote_errors:
            return MockResponse(200, "[{")

        addr1_tx = f"""{{"blockNumber":"54092","timeStamp":"1439048640","hash":"{TX_HASH_STR1}","nonce":"0","blockHash":"0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159","transactionIndex":"0","from":"{ETH_ADDRESS1}","to":"","value":"11901464239480000000000000","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"{MOCK_INPUT_DATA_HEX}","contractAddress":"0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"8569454"}}
        """
        addr2_tx = f"""{{"blockNumber":"54093","timeStamp":"1439048643","hash":"{TX_HASH_STR2}","nonce":"0","blockHash":"0xf3cabad6adab0b52eb632c386ea194036805713682c62cb589b5abcd76df2159","transactionIndex":"0","from":"{ETH_ADDRESS2}","to":"{ETH_ADDRESS1}","value":"40000300","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"{MOCK_INPUT_DATA_HEX}","contractAddress":"0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"8569454"}}
        """
        addr3_tx = f"""{{"blockNumber":"54094","timeStamp":"1439048645","hash":"{TX_HASH_STR3}","nonce":"0","blockHash":"0xe3cabad6adab0b52eb632c3165a194036805713682c62cb589b5abcd76de2159","transactionIndex":"0","from":"{ETH_ADDRESS3}","to":"{ETH_ADDRESS1}","value":"500520300","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"{MOCK_INPUT_DATA_HEX}","contractAddress":"0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"8569454"}}
        """
        if 'txlistinternal' in url:
            # don't return any internal transactions
            payload = '{"status":"1","message":"OK","result":[]}'
        else:
            # And depending on the given query return corresponding mock transactions for address
            if ETH_ADDRESS1 in url:
                tx_str = addr1_tx
            elif ETH_ADDRESS2 in url:
                tx_str = addr2_tx
            elif ETH_ADDRESS3 in url:
                tx_str = addr3_tx
            else:
                raise AssertionError(
                    'Requested etherscan transactions for unknown address in tests',
                )

            payload = f'{{"status":"1","message":"OK","result":[{tx_str}]}}'
        return MockResponse(200, payload)

    return patch.object(etherscan.session, 'get', wraps=mocked_request_dict)


class TradesTestSetup(NamedTuple):
    polo_patch: _patch
    binance_patch: _patch
    bittrex_patch: _patch
    bitmex_patch: _patch
    accountant_patch: _patch
    etherscan_patch: _patch


def mock_history_processing_and_exchanges(
        rotki: Rotkehlchen,
        should_mock_history_processing: bool = True,
        history_start_ts: Optional[Timestamp] = None,
        history_end_ts: Optional[Timestamp] = None,
        remote_errors: bool = False,
) -> TradesTestSetup:
    """Prepare patches to mock querying of trade history from various locations for testing

    If should_mock_history_processing is True then the history is only created and checked
    by a special test function but it is not processed to generate tax report.

    If remote_errors is True then all the mocked exchange remotes return remote errors
    """
    accountant_patch = mock_history_processing(
        rotki,
        should_mock_history_processing=should_mock_history_processing,
        history_start_ts=history_start_ts,
        history_end_ts=history_end_ts,
        remote_errors=remote_errors,
    )

    polo_patch, binance_patch, bittrex_patch, bitmex_patch = mock_exchange_responses(
        rotki,
        remote_errors,
    )
    etherscan_patch = mock_etherscan_transaction_response(
        etherscan=rotki.etherscan,
        remote_errors=remote_errors,
    )
    return TradesTestSetup(
        polo_patch=polo_patch,
        binance_patch=binance_patch,
        bittrex_patch=bittrex_patch,
        bitmex_patch=bitmex_patch,
        accountant_patch=accountant_patch,
        etherscan_patch=etherscan_patch,
    )


def prepare_rotki_for_history_processing_test(
        rotki: Rotkehlchen,
        should_mock_history_processing: bool = True,
        history_start_ts: Optional[Timestamp] = None,
        history_end_ts: Optional[Timestamp] = None,
        remote_errors: bool = False,
) -> TradesTestSetup:
    """Prepares rotki for the history processing tests

    Makes sure blockchain accounts are loaded, kraken does not generate random trades
    and that all mocks are ready.
    """
    kraken = rotki.exchange_manager.connected_exchanges['kraken']
    kraken.random_trade_data = False
    kraken.random_ledgers_data = False
    kraken.remote_errors = remote_errors
    # Let's add 3 blockchain accounts
    rotki.data.db.add_blockchain_accounts(
        SupportedBlockchain.ETHEREUM,
        [ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3],
    )
    setup = mock_history_processing_and_exchanges(
        rotki=rotki,
        should_mock_history_processing=should_mock_history_processing,
        history_start_ts=history_start_ts,
        history_end_ts=history_end_ts,
        remote_errors=remote_errors,
    )
    return setup


def assert_binance_trades_result(
        trades: List[Dict[str, Any]],
        trades_to_check: Optional[Tuple[int]] = None,
) -> None:
    """Convenience function to assert on the trades returned by binance's mock

    'trades_to_check' is a tuple of indexes indicating which trades should be checked.
    For example (1, 2) would mean that we have given two trades for checking and that
    they corresponse to the second and third of the normally expected trades.
    So the first trade is skipped.
    The mock trade data are set in tests/utils/history.py
    """
    if trades_to_check is None:
        assert len(trades) == 2
        trades_to_check = (0, 1)
    else:
        assert len(trades) == len(trades_to_check)

    for given_idx, idx in enumerate(trades_to_check):
        trade = trades[given_idx]
        expected_id = Trade(
            **{k: v for k, v in trades[given_idx].items() if k != 'trade_id'},
        ).identifier

        assert trade['trade_id'] == expected_id
        if idx == 0:
            assert trade['timestamp'] == 1512561941
            assert trade['location'] == 'binance'
            assert trade['pair'] == 'ETH_BTC'
            assert trade['trade_type'] == 'buy'
            assert trade['amount'] == '5.0'
            assert trade['rate'] == '0.0063213'
            assert trade['fee'] == '0.005'
            assert trade['fee_currency'] == 'ETH'
            assert trade['link'] == '1'
            assert trade['notes'] == ''
        elif idx == 1:
            assert trade['timestamp'] == 1512561942
            assert trade['location'] == 'binance'
            assert trade['pair'] == 'RDN_ETH'
            assert trade['trade_type'] == 'sell'
            assert trade['amount'] == '5.0'
            assert trade['rate'] == '0.0063213'
            assert trade['fee'] == '0.005'
            assert trade['fee_currency'] == 'RDN'
            assert trade['link'] == '2'
            assert trade['notes'] == ''
        else:
            raise AssertionError('index out of range')


def assert_poloniex_trades_result(
        trades: List[Dict[str, Any]],
        trades_to_check: Optional[Tuple[int]] = None,
) -> None:
    """Convenience function to assert on the trades returned by poloniex's mock

    'trades_to_check' is a tuple of indexes indicating which trades should be checked.
    For example (1, 2) would mean that we have given two trades for checking and that
    they corresponse to the second and third of the normally expected trades.
    So the first trade is skipped.

    The mock trade data are set in tests/utils/history.py
    """
    if trades_to_check is None:
        assert len(trades) == 3
        trades_to_check = (0, 1, 2)
    else:
        assert len(trades) == len(trades_to_check)

    for given_idx, idx in enumerate(trades_to_check):
        trade = trades[given_idx]
        expected_id = Trade(
            **{k: v for k, v in trades[given_idx].items() if k != 'trade_id'},
        ).identifier

        assert trade['trade_id'] == expected_id
        if idx == 0:
            assert trade['timestamp'] == 1539713117
            assert trade['location'] == 'poloniex'
            assert trade['pair'] == 'ETH_BTC'
            assert trade['trade_type'] == 'sell'
            assert trade['amount'] == '1.40308443'
            assert trade['rate'] == '0.06935244'
            assert trade['fee'] == '0.0000973073287465092'
            assert trade['fee_currency'] == 'BTC'
            assert trade['link'] == '394131412'
            assert trade['notes'] == ''
        elif idx == 1:
            assert trade['timestamp'] == 1539713237
            assert trade['location'] == 'poloniex'
            assert trade['pair'] == 'ETH_BTC'
            assert trade['trade_type'] == 'buy'
            assert trade['amount'] == '1.40308443'
            assert trade['rate'] == '0.06935244'
            assert trade['fee'] == '0.00140308443'
            assert trade['fee_currency'] == 'ETH'
            assert trade['link'] == '394131413'
            assert trade['notes'] == ''
        elif idx == 2:
            assert trade['timestamp'] == 1539713238
            assert trade['location'] == 'poloniex'
            assert trade['pair'] == 'XMR_ETH'
            assert trade['trade_type'] == 'buy'
            assert trade['amount'] == '1.40308443'
            assert trade['rate'] == '0.06935244'
            assert trade['fee'] == '0.00140308443'
            assert trade['fee_currency'] == 'XMR'
            assert trade['link'] == '394131415'
            assert trade['notes'] == ''
        else:
            raise AssertionError('index out of range')
