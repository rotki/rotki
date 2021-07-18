import json
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union, cast
from unittest.mock import _patch, patch

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures import DefiEvent
from rotkehlchen.api.v1.encoding import TradeSchema
from rotkehlchen.chain.ethereum.trades import AMMTrade
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_LTC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.exchanges.data_structures import AssetMovement, Loan, MarginPosition, Trade
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.serialization.serialize import process_result_list
from rotkehlchen.tests.utils.constants import (
    A_EUR,
    A_RDN,
    A_XMR,
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
from rotkehlchen.tests.utils.kraken import MockKraken
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import (
    AssetAmount,
    AssetMovementCategory,
    EthereumTransaction,
    Fee,
    Location,
    Timestamp,
    TradeType,
)
from rotkehlchen.utils.misc import hexstring_to_bytes

TEST_END_TS = 1559427707


# Prices queried by cryptocompare
prices = {
    'USD': {
        'EUR': {
            1467279735: FVal('0.9004'),
        },
    },
    'EUR': {
        'USD': {
            1467279735: FVal('1.1001'),
            1599221029: FVal('1.1001'),
            1599492244: FVal('1.1001'),
            1600380544: FVal('1.1001'),
            1600395691: FVal('1.1001'),
            1600473301: FVal('1.1001'),
        },
    },
    'BTC': {
        'EUR': {
            1428994442: FVal(210.865),
            1437279735: FVal('250'),
            1446979735: FVal(355.9),
            1448994442: FVal(338.805),
            1449809536: FVal(386.175),
            1458994442: FVal(373.295),
            1464393600: FVal(422.9),
            1467279735: FVal(420),
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
            1435979735: FVal('0.1'),
            1438994442: FVal(2.549),
            1439048640: FVal(1.13),
            1439048643: FVal(1.13),
            1439048645: FVal(1.13),
            1439994442: FVal(1.134),
            1446979735: FVal(0.8583),
            1448994442: FVal(0.83195),
            1457279735: FVal(1),
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
            1496979735: FVal(251.36),
            1501062063: FVal(175.44),
            1511626623: FVal(396.56),
            1512561941: FVal(380.34),
            1512561942: FVal(380.34),
            1539713117: FVal(178.615),
            1539713237: FVal(178.615),
            1539713238: FVal(178.615),
            1609537953: FVal(598.26),
            1624395186: FVal(1862.06),
            1624791600: FVal(1659.59),
            1625001464: FVal(1837.31),
        },
        'USD': {
            1624798800: FVal(1983.33),
        },
    },
    strethaddress_to_identifier('0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6'): {
        'EUR': {
            1512561942: ZERO,
        },
    },
    'CHF': {
        'EUR': {
            1496979735: FVal(1.001),
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
            1447279735: FVal('0.4'),
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
        start_ts: Timestamp,  # pylint: disable=unused-argument
        end_ts: Timestamp,  # pylint: disable=unused-argument
        trade_history: List[Union[Trade, MarginPosition, AMMTrade]],
        loan_history: List[Loan],
        asset_movements: List[AssetMovement],
        eth_transactions: List[EthereumTransaction],
        defi_events: List[DefiEvent],
        ledger_actions: List[LedgerAction],
) -> Dict[str, Any]:
    assert len(trade_history) == 0
    assert len(loan_history) == 0
    assert len(asset_movements) == 0
    assert len(eth_transactions) == 0
    assert len(defi_events) == 0
    assert len(ledger_actions) == 0
    return {}


def mock_exchange_responses(rotki: Rotkehlchen, remote_errors: bool):
    invalid_payload = "[{"

    def mock_binance_api_queries(url, timeout):  # pylint: disable=unused-argument
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
        elif 'capital/deposit' in url:
            payload = '[]'
        elif 'capital/withdraw' in url:
            payload = '[]'
        else:
            raise RuntimeError(f'Binance test mock got unexpected/unmocked url {url}')

        return MockResponse(200, payload)

    def mock_poloniex_api_queries(url, req, timeout):  # pylint: disable=unused-argument
        payload = ''
        if remote_errors:
            payload = invalid_payload
        elif req['command'] == 'returnTradeHistory':
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

        elif req['command'] == 'returnLendingHistory':
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
        elif req['command'] == 'returnDepositsWithdrawals':
            data = json.loads(POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE)
            new_data = {}
            for x in ('deposits', 'withdrawals'):
                new_data[x] = []
                for entry in data[x]:
                    if entry['timestamp'] < req['start'] or entry['timestamp'] > req['end']:
                        continue
                    new_data[x].append(entry)

            payload = json.dumps(new_data)
        else:
            raise RuntimeError(
                f'Poloniex test mock got unexpected/unmocked command {req["command"]}',
            )
        return MockResponse(200, payload)

    def mock_bittrex_api_queries(url, method, json):  # pylint: disable=unused-argument,redefined-outer-name  # noqa: E501
        if remote_errors:
            payload = invalid_payload
        elif 'orders/closed' in url:
            payload = """
[{
      "id": "fd97d393-e9b9-4dd1-9dbf-f288fc72a185",
      "marketSymbol": "LTC-BTC",
      "closedAt": "2017-05-01T15:00:00.00Z",
      "direction": "BUY",
      "type": "LIMIT",
      "fillQuantity": 667.03644955,
      "limit": 0.0000295,
      "commission": 0.00004921
    }, {
      "id": "ad97d393-e9b9-4dd1-9dbf-f288fc72a185",
      "marketSymbol": "LTC-ETH",
      "closedAt": "2017-05-02T15:00:00.00Z",
      "direction": "SELL",
      "type": "LIMIT",
      "fillQuantity": 667.03644955,
      "commission": 0.00004921,
      "limit": 0.0000295
    }, {
      "id": "ed97d393-e9b9-4dd1-9dbf-f288fc72a185",
      "marketSymbol": "PTON-ETH",
      "closedAt": "2017-05-02T15:00:00.00Z",
      "direction": "SELL",
      "type": "LIMIT",
      "fillQuantity": 667.03644955,
      "commission": 0.00004921,
      "limit": 0.0000295
    }, {
      "id": "1d97d393-e9b9-4dd1-9dbf-f288fc72a185",
      "marketSymbol": "IDONTEXIST-ETH",
      "closedAt": "2017-05-02T15:00:00.00Z",
      "direction": "SELL",
      "type": "LIMIT",
      "fillQuantity": 667.03644955,
      "commission": 0.00004921,
      "limit": 0.0000295
    }, {
      "id": "2d97d393-e9b9-4dd1-9dbf-f288fc72a185",
      "marketSymbol": "%$#%$#%#$%",
      "closedAt": "2017-05-02T15:00:00.00Z",
      "direction": "BUY",
      "type": "LIMIT",
      "fillQuantity": 667.03644955,
      "commission": 0.00004921,
      "limit": 0.0000295
}]
"""
        elif 'deposits/closed' in url or 'withdrawals/closed' in url:
            # For now no deposits or withdrawals for bittrex in the big history test
            payload = '[]'
        else:
            raise RuntimeError(f'Bittrex test mock got unexpected/unmocked url {url}')

        return MockResponse(200, payload)

    def mock_bitmex_api_queries(url, data):  # pylint: disable=unused-argument
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
    poloniex_objects = rotki.exchange_manager.connected_exchanges.get(Location.POLONIEX, None)
    poloniex = None if poloniex_objects is None else poloniex_objects[0]
    polo_patch = None
    if poloniex:
        polo_patch = patch.object(
            poloniex.session,
            'post',
            side_effect=mock_poloniex_api_queries,
        )

    binance_objects = rotki.exchange_manager.connected_exchanges.get(Location.BINANCE, None)
    binance = None if binance_objects is None else binance_objects[0]
    binance_patch = None
    if binance:
        binance_patch = patch.object(
            binance.session,
            'get',
            side_effect=mock_binance_api_queries,
        )

    bittrex_objects = rotki.exchange_manager.connected_exchanges.get(Location.BITTREX, None)
    bittrex = None if bittrex_objects is None else bittrex_objects[0]
    bittrex_patch = None
    if bittrex:
        bittrex_patch = patch.object(
            bittrex.session,
            'request',
            side_effect=mock_bittrex_api_queries,
        )

    bitmex_objects = rotki.exchange_manager.connected_exchanges.get(Location.BITMEX, None)
    bitmex = None if bitmex_objects is None else bitmex_objects[0]
    bitmex_patch = None
    if bitmex:
        bitmex_patch = patch.object(
            bitmex.session,
            'get',
            side_effect=mock_bitmex_api_queries,
        )

    return polo_patch, binance_patch, bittrex_patch, bitmex_patch


def assert_asset_movements(
        expected: List[AssetMovement],
        to_check_list: List[Any],
        deserialized: bool,
        movements_to_check: Optional[Tuple[int, ...]] = None,
) -> None:
    if deserialized:
        expected = process_result_list([x.serialize() for x in expected])

    if movements_to_check is None:
        assert len(to_check_list) == len(expected)
        assert all(x in to_check_list for x in expected)
    else:
        assert all(expected[x] in to_check_list for x in movements_to_check)
        assert len(to_check_list) == len(movements_to_check)


def assert_poloniex_asset_movements(
        to_check_list: List[Any],
        deserialized: bool,
        movements_to_check: Optional[Tuple[int, ...]] = None,
) -> None:
    expected = [AssetMovement(
        location=Location.POLONIEX,
        category=AssetMovementCategory.WITHDRAWAL,
        address='0xB7E033598Cb94EF5A35349316D3A2e4f95f308Da',
        transaction_id='0xbd4da74e1a0b81c21d056c6f58a5b306de85d21ddf89992693b812bb117eace4',
        timestamp=Timestamp(1468994442),
        asset=A_ETH,
        amount=FVal('10.0'),
        fee_asset=A_ETH,
        fee=Fee(FVal('0.1')),
        link='2',
    ), AssetMovement(
        location=Location.POLONIEX,
        category=AssetMovementCategory.WITHDRAWAL,
        address='131rdg5Rzn6BFufnnQaHhVa5ZtRU1J2EZR',
        transaction_id='2d27ae26fa9c70d6709e27ac94d4ce2fde19b3986926e9f3bfcf3e2d68354ec5',
        timestamp=Timestamp(1458994442),
        asset=A_BTC,
        amount=FVal('5.0'),
        fee_asset=A_BTC,
        fee=Fee(FVal('0.5')),
        link='1',
    ), AssetMovement(
        location=Location.POLONIEX,
        category=AssetMovementCategory.DEPOSIT,
        address='131rdg5Rzn6BFufnnQaHhVa5ZtRU1J2EZR',
        transaction_id='b05bdec7430a56b5a5ed34af4a31a54859dda9b7c88a5586bc5d6540cdfbfc7a',
        timestamp=Timestamp(1448994442),
        asset=A_BTC,
        amount=FVal('50.0'),
        fee_asset=A_BTC,
        fee=Fee(FVal('0')),
        link='1',
    ), AssetMovement(
        location=Location.POLONIEX,
        category=AssetMovementCategory.DEPOSIT,
        address='0xB7E033598Cb94EF5A35349316D3A2e4f95f308Da',
        transaction_id='0xf7e7eeb44edcad14c0f90a5fffb1cbb4b80e8f9652124a0838f6906ca939ccd2',
        timestamp=Timestamp(1438994442),
        asset=A_ETH,
        amount=FVal('100.0'),
        fee_asset=A_ETH,
        fee=Fee(FVal('0')),
        link='2',
    )]
    assert_asset_movements(expected, to_check_list, deserialized, movements_to_check)


def assert_kraken_asset_movements(
        to_check_list: List[Any],
        deserialized: bool,
        movements_to_check: Optional[Tuple[int, ...]] = None,
):
    expected = [AssetMovement(
        location=Location.KRAKEN,
        category=AssetMovementCategory.DEPOSIT,
        address=None,
        transaction_id=None,
        timestamp=Timestamp(1458994442),
        asset=A_BTC,
        amount=FVal('5.0'),
        fee_asset=A_BTC,
        fee=Fee(FVal('0.1')),
        link='1',
    ), AssetMovement(
        location=Location.KRAKEN,
        address=None,
        transaction_id=None,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=Timestamp(1448994442),
        asset=A_ETH,
        amount=FVal('10.0'),
        fee_asset=A_ETH,
        fee=Fee(FVal('0.11')),
        link='2',
    ), AssetMovement(
        location=Location.KRAKEN,
        category=AssetMovementCategory.WITHDRAWAL,
        address=None,
        transaction_id=None,
        timestamp=Timestamp(1439994442),
        asset=A_ETH,
        amount=FVal('10.0'),
        fee_asset=A_ETH,
        fee=Fee(FVal('0.11')),
        link='5',
    ), AssetMovement(
        location=Location.KRAKEN,
        category=AssetMovementCategory.WITHDRAWAL,
        address=None,
        transaction_id=None,
        timestamp=Timestamp(1428994442),
        asset=A_BTC,
        amount=FVal('5.0'),
        fee_asset=A_BTC,
        fee=Fee(FVal('0.1')),
        link='4',
    )]
    assert_asset_movements(expected, to_check_list, deserialized, movements_to_check)


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
            trade_history: List[Union[Trade, MarginPosition, AMMTrade]],
            loan_history: List[Loan],
            asset_movements: List[AssetMovement],
            eth_transactions: List[EthereumTransaction],
            defi_events: List[DefiEvent],
            ledger_actions: List[LedgerAction],
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

        # TODO: terrible way to check. Figure out something better
        # This whole function needs better thinking also on the order it expects
        # the events to be. It's super brittle right now
        limited_range_test = False
        expected_trades_num = 11
        expected_asset_movements_num = 11
        if end_ts == 1539713238:
            limited_range_test = True
            expected_trades_num = 10
            expected_asset_movements_num = 10

        # TODO: Add more assertions/check for each action
        # OR instead do it in tests for conversion of actions(trades, loans, deposits e.t.c.)
        # from exchange to our format for each exchange
        assert len(trade_history) == expected_trades_num
        assert isinstance(trade_history[0], Trade)
        assert trade_history[0].location == Location.KRAKEN
        assert trade_history[0].base_asset == A_ETH
        assert trade_history[0].quote_asset == A_EUR
        assert trade_history[0].trade_type == TradeType.BUY
        assert isinstance(trade_history[1], Trade)
        assert trade_history[1].location == Location.KRAKEN
        assert trade_history[1].base_asset == A_BTC
        assert trade_history[1].quote_asset == A_EUR
        assert trade_history[1].trade_type == TradeType.BUY
        assert isinstance(trade_history[2], Trade)
        assert trade_history[2].location == Location.BITTREX
        assert trade_history[2].base_asset == A_LTC
        assert trade_history[2].quote_asset == A_BTC
        assert trade_history[2].trade_type == TradeType.BUY
        assert isinstance(trade_history[3], Trade)
        assert trade_history[3].location == Location.BITTREX
        assert trade_history[3].base_asset == A_LTC
        assert trade_history[3].quote_asset == A_ETH
        assert trade_history[3].trade_type == TradeType.SELL
        assert isinstance(trade_history[4], MarginPosition)
        assert trade_history[4].profit_loss == FVal('0.05')
        assert isinstance(trade_history[5], Trade)
        assert trade_history[5].location == Location.BINANCE
        assert trade_history[5].base_asset == A_ETH
        assert trade_history[5].quote_asset == A_BTC
        assert trade_history[5].trade_type == TradeType.BUY
        assert isinstance(trade_history[6], Trade)
        assert trade_history[6].location == Location.BINANCE
        assert trade_history[6].base_asset == A_RDN
        assert trade_history[6].quote_asset == A_ETH
        assert trade_history[6].trade_type == TradeType.SELL
        assert isinstance(trade_history[7], Trade)
        assert trade_history[7].location == Location.POLONIEX
        assert trade_history[7].base_asset == A_ETH
        assert trade_history[7].quote_asset == A_BTC
        assert trade_history[7].trade_type == TradeType.SELL
        assert isinstance(trade_history[8], Trade)
        assert trade_history[8].location == Location.POLONIEX
        assert trade_history[8].base_asset == A_ETH
        assert trade_history[8].quote_asset == A_BTC
        assert trade_history[8].trade_type == TradeType.BUY
        assert isinstance(trade_history[9], Trade)
        assert trade_history[9].location == Location.POLONIEX
        assert trade_history[9].base_asset == A_XMR
        assert trade_history[9].quote_asset == A_ETH
        assert trade_history[9].trade_type == TradeType.BUY
        if not limited_range_test:
            assert isinstance(trade_history[10], MarginPosition)
            assert trade_history[10].profit_loss == FVal('5E-9')

        assert len(loan_history) == 2
        assert loan_history[0].currency == A_ETH
        assert loan_history[0].earned == AssetAmount(FVal('0.00000001'))
        assert loan_history[1].currency == A_BTC
        assert loan_history[1].earned == AssetAmount(FVal('0.00000005'))

        assert len(asset_movements) == expected_asset_movements_num
        if not limited_range_test:
            assert asset_movements[0].location == Location.POLONIEX
            assert asset_movements[0].category == AssetMovementCategory.WITHDRAWAL
            assert asset_movements[0].asset == A_BTC
            assert asset_movements[1].location == Location.POLONIEX
            assert asset_movements[1].category == AssetMovementCategory.WITHDRAWAL
            assert asset_movements[1].asset == A_ETH
            assert asset_movements[2].location == Location.POLONIEX
            assert asset_movements[2].category == AssetMovementCategory.DEPOSIT
            assert asset_movements[2].asset == A_BTC
            assert asset_movements[3].location == Location.POLONIEX
            assert asset_movements[3].category == AssetMovementCategory.DEPOSIT
            assert asset_movements[3].asset == A_ETH
            assert asset_movements[4].location == Location.BITMEX
            assert asset_movements[4].category == AssetMovementCategory.DEPOSIT
            assert asset_movements[4].asset == A_BTC
            assert asset_movements[5].location == Location.BITMEX
            assert asset_movements[5].category == AssetMovementCategory.WITHDRAWAL
            assert asset_movements[5].asset == A_BTC
            assert asset_movements[6].location == Location.BITMEX
            assert asset_movements[6].category == AssetMovementCategory.WITHDRAWAL
            assert asset_movements[6].asset == A_BTC
            assert asset_movements[7].location == Location.KRAKEN
            assert asset_movements[7].category == AssetMovementCategory.DEPOSIT
            assert asset_movements[7].asset == A_BTC
            assert asset_movements[8].location == Location.KRAKEN
            assert asset_movements[8].category == AssetMovementCategory.DEPOSIT
            assert asset_movements[8].asset == A_ETH
            assert asset_movements[9].location == Location.KRAKEN
            assert asset_movements[9].category == AssetMovementCategory.WITHDRAWAL
            assert asset_movements[9].asset == A_BTC
            assert asset_movements[10].location == Location.KRAKEN
            assert asset_movements[10].category == AssetMovementCategory.WITHDRAWAL
            assert asset_movements[10].asset == A_ETH

        # The history creation for these is not yet tested
        assert len(eth_transactions) == 3
        assert eth_transactions[0].block_number == 54092
        assert eth_transactions[0].tx_hash == hexstring_to_bytes(TX_HASH_STR1)
        assert eth_transactions[0].from_address == ETH_ADDRESS1
        assert eth_transactions[0].to_address is None
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

        assert len(defi_events) == 0
        assert len(ledger_actions) == 0

        return {}

    def check_result_of_history_creation_and_process_it(
            start_ts: Timestamp,
            end_ts: Timestamp,
            trade_history: List[Union[Trade, MarginPosition, AMMTrade]],
            loan_history: List[Loan],
            asset_movements: List[AssetMovement],
            eth_transactions: List[EthereumTransaction],
            defi_events: List[DefiEvent],
            ledger_actions: List[LedgerAction],
    ) -> Dict[str, Any]:
        """Checks results of history creation but also proceeds to normal history processing"""
        check_result_of_history_creation(
            start_ts=start_ts,
            end_ts=end_ts,
            trade_history=trade_history,
            loan_history=loan_history,
            asset_movements=asset_movements,
            eth_transactions=eth_transactions,
            defi_events=defi_events,
            ledger_actions=ledger_actions,
        )
        return original_history_processing_function(
            start_ts=start_ts,
            end_ts=end_ts,
            trade_history=trade_history,
            loan_history=loan_history,
            asset_movements=asset_movements,
            eth_transactions=eth_transactions,
            defi_events=defi_events,
            ledger_actions=ledger_actions,
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
    def mocked_request_dict(url, *_args, **_kwargs):
        if remote_errors:
            return MockResponse(200, "[{")

        addr1_tx = f"""{{"blockNumber":"54092","timeStamp":"1439048640","hash":"{TX_HASH_STR1}","nonce":"0","blockHash":"0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159","transactionIndex":"0","from":"{ETH_ADDRESS1}","to":"","value":"11901464239480000000000000","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"{MOCK_INPUT_DATA_HEX}","contractAddress":"0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"8569454"}}
        """
        addr2_tx = f"""{{"blockNumber":"54093","timeStamp":"1439048643","hash":"{TX_HASH_STR2}","nonce":"0","blockHash":"0xf3cabad6adab0b52eb632c386ea194036805713682c62cb589b5abcd76df2159","transactionIndex":"0","from":"{ETH_ADDRESS2}","to":"{ETH_ADDRESS1}","value":"40000300","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"{MOCK_INPUT_DATA_HEX}","contractAddress":"0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"8569454"}}
        """
        addr3_tx = f"""{{"blockNumber":"54094","timeStamp":"1439048645","hash":"{TX_HASH_STR3}","nonce":"0","blockHash":"0xe3cabad6adab0b52eb632c3165a194036805713682c62cb589b5abcd76de2159","transactionIndex":"0","from":"{ETH_ADDRESS3}","to":"{ETH_ADDRESS1}","value":"500520300","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"{MOCK_INPUT_DATA_HEX}","contractAddress":"0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"8569454"}}
        """
        if '=txlistinternal&' in url:
            # don't return any internal transactions
            payload = '{"status":"1","message":"OK","result":[]}'
        elif '=txlist&' in url:
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
        elif '=getblocknobytime&' in url:
            # we don't really care about this in the history tests so just return whatever
            payload = '{"status":"1","message":"OK","result": "1"}'
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
    kraken = cast(MockKraken, rotki.exchange_manager.connected_exchanges.get(Location.KRAKEN)[0])  # type: ignore  # noqa: E501
    kraken.random_trade_data = False
    kraken.random_ledgers_data = False
    kraken.remote_errors = remote_errors
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
        trades_to_check: Optional[Tuple[int, ...]] = None,
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
        raw_trade = trades[given_idx]
        input_data = {k: v for k, v in raw_trade.items() if k != 'trade_id'}
        expected_id = Trade(**TradeSchema().load(input_data)).identifier
        assert raw_trade['trade_id'] == expected_id
        if idx == 0:
            assert raw_trade['timestamp'] == 1512561942
            assert raw_trade['location'] == 'binance'
            assert raw_trade['base_asset'] == A_RDN.identifier
            assert raw_trade['quote_asset'] == 'ETH'
            assert raw_trade['trade_type'] == 'sell'
            assert raw_trade['amount'] == '5.0'
            assert raw_trade['rate'] == '0.0063213'
            assert raw_trade['fee'] == '0.005'
            assert raw_trade['fee_currency'] == A_RDN.identifier
            assert raw_trade['link'] == '2'
            assert raw_trade['notes'] is None
        elif idx == 1:
            assert raw_trade['timestamp'] == 1512561941
            assert raw_trade['location'] == 'binance'
            assert raw_trade['base_asset'] == 'ETH'
            assert raw_trade['quote_asset'] == 'BTC'
            assert raw_trade['trade_type'] == 'buy'
            assert raw_trade['amount'] == '5.0'
            assert raw_trade['rate'] == '0.0063213'
            assert raw_trade['fee'] == '0.005'
            assert raw_trade['fee_currency'] == 'ETH'
            assert raw_trade['link'] == '1'
            assert raw_trade['notes'] is None
        else:
            raise AssertionError('index out of range')


def assert_poloniex_trades_result(
        trades: List[Dict[str, Any]],
        trades_to_check: Optional[Tuple[int, ...]] = None,
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
        raw_trade = trades[given_idx]
        input_data = {k: v for k, v in raw_trade.items() if k != 'trade_id'}
        expected_id = Trade(**TradeSchema().load(input_data)).identifier
        assert raw_trade['trade_id'] == expected_id
        if idx == 0:
            assert raw_trade['timestamp'] == 1539713238
            assert raw_trade['location'] == 'poloniex'
            assert raw_trade['base_asset'] == 'XMR'
            assert raw_trade['quote_asset'] == 'ETH'
            assert raw_trade['trade_type'] == 'buy'
            assert FVal(raw_trade['amount']) == FVal('1.40308443')
            assert FVal(raw_trade['rate']) == FVal('0.06935244')
            assert FVal(raw_trade['fee']) == FVal('0.00140308443')
            assert raw_trade['fee_currency'] == 'XMR'
            assert raw_trade['link'] == '394131415'
            assert raw_trade['notes'] is None
        elif idx == 1:
            assert raw_trade['timestamp'] == 1539713237
            assert raw_trade['location'] == 'poloniex'
            assert raw_trade['base_asset'] == 'ETH'
            assert raw_trade['quote_asset'] == 'BTC'
            assert raw_trade['trade_type'] == 'buy'
            assert FVal(raw_trade['amount']) == FVal('1.40308443')
            assert FVal(raw_trade['rate']) == FVal('0.06935244')
            assert FVal(raw_trade['fee']) == FVal('0.00140308443')
            assert raw_trade['fee_currency'] == 'ETH'
            assert raw_trade['link'] == '394131413'
            assert raw_trade['notes'] is None
        elif idx == 2:
            assert raw_trade['timestamp'] == 1539713117
            assert raw_trade['location'] == 'poloniex'
            assert raw_trade['base_asset'] == 'ETH'
            assert raw_trade['quote_asset'] == 'BTC'
            assert raw_trade['trade_type'] == 'sell'
            assert raw_trade['amount'] == '1.40308443'
            assert FVal(raw_trade['rate']) == FVal('0.06935244')
            assert FVal(raw_trade['fee']) == FVal('0.0000973073287465092')
            assert raw_trade['fee_currency'] == 'BTC'
            assert raw_trade['link'] == '394131412'
            assert raw_trade['notes'] is None
        else:
            raise AssertionError('index out of range')


def maybe_mock_historical_price_queries(
        historian,
        should_mock_price_queries: bool,
        mocked_price_queries,
        default_mock_value: Optional[FVal] = None,
) -> None:
    """If needed will make sure the historian's price queries are mocked"""
    if not should_mock_price_queries:
        return

    def mock_historical_price_query(from_asset, to_asset, timestamp):
        if from_asset == to_asset:
            return FVal(1)

        try:
            price = mocked_price_queries[from_asset.identifier][to_asset.identifier][timestamp]
        except KeyError:
            if default_mock_value is None:
                raise AssertionError(
                    f'No mocked price found from {from_asset.identifier} to '
                    f'{to_asset.identifier} at {timestamp}',
                ) from None
            # else just use the default
            return default_mock_value

        return price

    historian.query_historical_price = mock_historical_price_query
