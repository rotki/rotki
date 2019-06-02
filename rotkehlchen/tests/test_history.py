from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history import limit_trade_list_to_period
from rotkehlchen.order_formatting import AssetMovement, Trade
from rotkehlchen.tests.utils.exchanges import POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.transactions import EthereumTransaction
from rotkehlchen.typing import Timestamp, TradeType

TEST_END_TS = 1559427707


def check_result_of_history_creation(
        start_ts: Timestamp,
        end_ts: Timestamp,
        trade_history: List[Trade],
        margin_history: List[Trade],
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
    assert len(trade_history) == 9
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
    assert trade_history[4].location == 'binance'
    assert trade_history[4].pair == 'ETH_BTC'
    assert trade_history[4].trade_type == TradeType.BUY
    assert trade_history[5].location == 'binance'
    assert trade_history[5].pair == 'RDN_ETH'
    assert trade_history[5].trade_type == TradeType.SELL
    assert trade_history[6].location == 'poloniex'
    assert trade_history[6].pair == 'ETH_BTC'
    assert trade_history[6].trade_type == TradeType.SELL
    assert trade_history[7].location == 'poloniex'
    assert trade_history[7].pair == 'ETH_BTC'
    assert trade_history[7].trade_type == TradeType.BUY
    assert trade_history[8].location == 'poloniex'
    assert trade_history[8].pair == 'XMR_ETH'
    assert trade_history[8].trade_type == TradeType.BUY

    assert len(loan_history) == 2
    assert loan_history[0]['currency'] == A_ETH
    assert loan_history[0]['earned'] == FVal('0.00000001')
    assert loan_history[1]['currency'] == A_BTC
    assert loan_history[1]['earned'] == FVal('0.00000005')

    assert len(asset_movements) == 8
    assert asset_movements[0].exchange == 'kraken'
    assert asset_movements[0].category == 'deposit'
    assert asset_movements[0].asset == A_BTC
    assert asset_movements[1].exchange == 'kraken'
    assert asset_movements[1].category == 'deposit'
    assert asset_movements[1].asset == A_ETH
    assert asset_movements[2].exchange == 'kraken'
    assert asset_movements[2].category == 'withdrawal'
    assert asset_movements[2].asset == A_BTC
    assert asset_movements[3].exchange == 'kraken'
    assert asset_movements[3].category == 'withdrawal'
    assert asset_movements[3].asset == A_ETH
    assert asset_movements[4].exchange == 'poloniex'
    assert asset_movements[4].category == 'withdrawal'
    assert asset_movements[4].asset == A_BTC
    assert asset_movements[5].exchange == 'poloniex'
    assert asset_movements[5].category == 'withdrawal'
    assert asset_movements[5].asset == A_ETH
    assert asset_movements[6].exchange == 'poloniex'
    assert asset_movements[6].category == 'deposit'
    assert asset_movements[6].asset == A_BTC
    assert asset_movements[7].exchange == 'poloniex'
    assert asset_movements[7].category == 'deposit'
    assert asset_movements[7].asset == A_ETH

    # The history creation for these is not yet tested
    assert len(margin_history) == 0
    assert len(eth_transactions) == 0

    return {}


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_history_creation(
        rotkehlchen_server_with_exchanges,
        accountant,
        trades_historian_with_exchanges,
):
    """This is a big test that contacts all exchange mocks and returns mocked
    trades and other data from exchanges in order to create the accounting history
    for a specific period and see that rotkehlchen handles the creation of that
    history correctly"""
    server = rotkehlchen_server_with_exchanges
    rotki = server.rotkehlchen
    rotki.accountant = accountant
    rotki.trades_historian = trades_historian_with_exchanges
    rotki.kraken.random_trade_data = False
    rotki.kraken.random_ledgers_data = False

    def mock_binance_api_queries(url):
        if 'myTrades' in url:
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
        else:
            raise RuntimeError(f'Binance test mock got unexpected/unmocked url {url}')

        return MockResponse(200, payload)

    def mock_poloniex_api_queries(url, req):  # pylint: disable=unused-argument
        payload = ''
        if 'returnTradeHistory' == req['command']:
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
        if 'getorderhistory' in url:
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
        else:
            raise RuntimeError(f'Bittrex test mock got unexpected/unmocked url {url}')

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
    accountant_patch = patch.object(  # Patch away processing of history
        rotki.accountant,
        'process_history',
        side_effect=check_result_of_history_creation,
    )
    with accountant_patch, polo_patch, binance_patch, bittrex_patch:
        response = server.process_trade_history(start_ts='0', end_ts=str(TEST_END_TS))

    # The history processing is completely mocked away and omitted in this test.
    # because it is only for the history creation not its processing.
    # For history processing tests look at test_accounting.py and
    # test_accounting_events.py
    assert response['message'] == ''
    assert response['result'] == {}

    # And now make sure that warnings have also been generated for the query of
    # the unsupported/unknown assets
    warnings = rotki.msg_aggregator.consume_warnings()
    assert len(warnings) == 16
    assert 'kraken trade with unprocessable pair IDONTEXISTZEUR' in warnings[0]
    assert 'kraken trade with unknown asset IDONTEXISTTOO' in warnings[1]
    assert 'kraken trade with unprocessable pair %$#%$#%$#%$#%$#%' in warnings[2]
    assert 'unknown kraken asset IDONTEXIST. Ignoring its deposit/withdrawals query' in warnings[3]
    msg = 'unknown kraken asset IDONTEXISTEITHER. Ignoring its deposit/withdrawals query'
    assert msg in warnings[4]
    assert 'poloniex trade with unknown asset NOEXISTINGASSET' in warnings[5]
    assert 'poloniex trade with unsupported asset BALLS' in warnings[6]
    assert 'poloniex loan with unsupported asset BDC' in warnings[7]
    assert 'poloniex loan with unknown asset NOTEXISTINGASSET' in warnings[8]
    assert 'withdrawal of unknown poloniex asset IDONTEXIST' in warnings[9]
    assert 'withdrawal of unsupported poloniex asset DIS' in warnings[10]
    assert 'deposit of unknown poloniex asset IDONTEXIST' in warnings[11]
    assert 'deposit of unsupported poloniex asset EBT' in warnings[12]
    assert 'bittrex trade with unsupported asset PTON' in warnings[13]
    assert 'bittrex trade with unknown asset IDONTEXIST' in warnings[14]
    assert 'bittrex trade with unprocessable pair %$#%$#%#$%' in warnings[15]


def test_limit_trade_list_to_period():
    trade1 = Trade(
        timestamp=1459427707,
        location='kraken',
        pair='ETH_BTC',
        trade_type=TradeType.BUY,
        amount=FVal(1),
        rate=FVal(1),
        fee=FVal('0.1'),
        fee_currency=A_ETH,
    )
    trade2 = Trade(
        timestamp=1469427707,
        location='poloniex',
        pair='ETH_BTC',
        trade_type=TradeType.BUY,
        amount=FVal(1),
        rate=FVal(1),
        fee=FVal('0.1'),
        fee_currency=A_ETH,
    )
    trade3 = Trade(
        timestamp=1479427707,
        location='poloniex',
        pair='ETH_BTC',
        trade_type=TradeType.BUY,
        amount=FVal(1),
        rate=FVal(1),
        fee=FVal('0.1'),
        fee_currency=A_ETH,
    )

    full_list = [trade1, trade2, trade3]
    assert limit_trade_list_to_period(full_list, 1459427706, 1479427708) == full_list
    assert limit_trade_list_to_period(full_list, 1459427707, 1479427708) == full_list
    assert limit_trade_list_to_period(full_list, 1459427707, 1479427707) == full_list

    expected = [trade2, trade3]
    assert limit_trade_list_to_period(full_list, 1459427708, 1479427707) == expected
    expected = [trade2]
    assert limit_trade_list_to_period(full_list, 1459427708, 1479427706) == expected
    assert limit_trade_list_to_period(full_list, 0, 10) == []
    assert limit_trade_list_to_period(full_list, 1479427708, 1479427719) == []
    assert limit_trade_list_to_period([trade1], 1459427707, 1459427707) == [trade1]
    assert limit_trade_list_to_period([trade2], 1469427707, 1469427707) == [trade2]
    assert limit_trade_list_to_period([trade3], 1479427707, 1479427707) == [trade3]
    assert limit_trade_list_to_period(full_list, 1459427707, 1459427707) == [trade1]
    assert limit_trade_list_to_period(full_list, 1469427707, 1469427707) == [trade2]
    assert limit_trade_list_to_period(full_list, 1479427707, 1479427707) == [trade3]
