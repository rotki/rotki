from unittest.mock import patch

import pytest

from rotkehlchen.tests.utils.exchanges import POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.utils.misc import ts_now


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_history_creation(
        rotkehlchen_server_with_exchanges,
        accountant,
        trades_historian_with_exchanges,
):
    server = rotkehlchen_server_with_exchanges
    rotki = server.rotkehlchen
    rotki.accountant = accountant
    rotki.trades_historian = trades_historian_with_exchanges
    # Temporarily remove other
    # rotki.trades_historian.binance = None
    # rotki.trades_historian.kraken = None
    rotki.trades_historian.bittrex = None
    rotki.kraken.random_trade_data = False
    rotki.kraken.random_ledgers_data = False
    end_ts = ts_now()

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
                "time": 1512561941,
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
                "time": 1512561942,
                "isBuyer": true,
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
                    "date": "2018-10-16 18:07:17",
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
                "currency": "NOEXISTINGASSET",
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
                f'Poloniex test mock got unexpected/unmocked command {req["command"]}'
            )
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
    accountant_patch = patch.object(  # Patch away processing of history
        rotki.accountant,
        'process_history',
        return_value={},
    )
    with accountant_patch, polo_patch, binance_patch:
        response = server.process_trade_history(start_ts='0', end_ts=str(end_ts))

    # The history processing is completely mocked away and omitted in this test.
    # because it is only for the history creation not its processing.
    # For history processing tests look at test_accounting.py and
    # test_accounting_events.py
    assert response['message'] == ''
    assert response['result'] == {}

    # And now make sure that warnings have also been generated for the query of
    # the unsupported/unknown assets
    warnings = rotki.msg_aggregator.consume_warnings()
    assert len(warnings) == 11
    assert 'kraken trade with unprocessable pair IDONTEXISTZEUR' in warnings[0]
    assert 'kraken trade with unknown asset IDONTEXISTTOO' in warnings[1]
    assert 'kraken trade with unprocessable pair %$#%$#%$#%$#%$#%' in warnings[2]
    assert 'unknown kraken asset IDONTEXIST. Ignoring its deposit/withdrawals query' in warnings[3]
    msg = 'unknown kraken asset IDONTEXISTEITHER. Ignoring its deposit/withdrawals query'
    assert msg in warnings[4]
    assert 'poloniex trade with unknown asset NOEXISTINGASSET' in warnings[5]
    assert 'poloniex trade with unsupported asset BALLS' in warnings[6]
    assert 'withdrawal of unknown poloniex asset IDONTEXIST' in warnings[7]
    assert 'withdrawal of unsupported poloniex asset DIS' in warnings[8]
    assert 'deposit of unknown poloniex asset IDONTEXIST' in warnings[9]
    assert 'deposit of unsupported poloniex asset EBT' in warnings[10]
