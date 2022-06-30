import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Tuple, cast
from unittest.mock import _patch, patch

from rotkehlchen.accounting.mixins.event import AccountingEventMixin
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.api.v1.schemas import TradeSchema
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_ETH2, A_USDC, A_USDT
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.exchanges.data_structures import AssetMovement, Loan, MarginPosition, Trade
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.serialization.serialize import process_result_list
from rotkehlchen.tests.utils.constants import (
    A_EUR,
    A_RDN,
    ETH_ADDRESS1,
    ETH_ADDRESS2,
    ETH_ADDRESS3,
    MOCK_INPUT_DATA_HEX,
    TX_HASH_STR1,
    TX_HASH_STR2,
    TX_HASH_STR3,
)
from rotkehlchen.tests.utils.exchanges import POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE
from rotkehlchen.tests.utils.kraken import MockKraken
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import AssetAmount, AssetMovementCategory, Fee, Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset

TEST_END_TS = 1559427707


# Prices queried by cryptocompare
prices = {
    'USD': {
        'EUR': {
            1459024920: FVal('0.8982'),
            1467279735: FVal('0.9004'),
            1485895742: FVal('0.9327'),
            1500705839: FVal('0.8547'),
            1519001640: FVal('0.8071'),
            1539713238: FVal('0.8612'),
            1609537953: FVal('0.82411'),
            1609877514: FVal('0.812'),
            1611426233: FVal('0.8218'),
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
            1488373504: FVal('1156.18'),
            1491177600: FVal(1039.935),
            1491231601: FVal(1062.67),
            1491593374: FVal('1123.86'),
            1493650800: FVal(1259.295),
            1493737201: FVal(1310.735),
            1495551601: FVal(2030.01),
            1495969504: FVal(1964.685),
            1498694400: FVal(2244.465),
            1500595200: FVal('2295.68'),
            1500705839: FVal('2424.4'),
            1512561941: FVal(10929.925),
            1512693374: FVal(14415.365),
            1514937600: FVal('12786.04'),
            1539713117: FVal(5626.17),
            1539713237: FVal(5626.17),
            1566572401: FVal(9367.55),
        },
    },
    'BCH': {
        'EUR': {
            1512693374: FVal('1175.06'),
            1524937600: FVal('1146.98'),
            1525937600: FVal('1272.05'),
            1552304352: FVal('114.27'),
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
            1457279735: ONE,
            1459024920: FVal('9.875'),
            1461021812: FVal('7.875'),
            1463184190: FVal(9.187),
            1463508234: FVal(10.785),
            1468994442: FVal(10.80),
            1473505138: FVal(10.36),
            1475042230: FVal(11.925),
            1476536704: FVal(10.775),
            1479510304: FVal(8.9145),
            1482138141: FVal('7.345'),
            1483313925: FVal(7.764),
            1491062063: FVal(47.865),
            1493291104: FVal(53.175),
            1493737200: FVal(69.505),
            1496979735: FVal(251.36),
            1501062063: FVal(175.44),
            1506979735: FVal('253.39'),
            1508924574: FVal('252.74'),
            1511626623: FVal(396.56),
            1512561941: FVal(380.34),
            1512561942: FVal(380.34),
            1539388574: FVal('168.7'),
            1539713117: FVal(178.615),
            1539713237: FVal(178.615),
            1539713238: FVal(178.615),
            1566726126: FVal('167.58'),
            1569924574: FVal('161.59'),
            1607727600: FVal('449.68'),
            1607814000: FVal('469.82'),
            1607900400: FVal('486.57'),
            1609537953: FVal(598.26),
            1609950165: FVal('978.54'),
            1624395186: FVal(1862.06),
            1624791600: FVal(1659.59),
            1628994441: FVal(3258.55),
            1625001464: FVal(1837.31),
            1636638550: FVal(4641.49),
            1636740198: FVal(4042.84),
            1640493374: FVal(4072.51),
        },
        'USD': {
            1624798800: FVal(1983.33),
            1628994441: FVal(3258.55),
            1636638550: FVal(4641.49),
            1636738550: FVal(4042.84),
            1636740198: FVal(4042.84),
            1640493374: FVal(4072.51),
            1651258550: FVal(3903.45),
            1651259834: FVal(2904.42),
        },
    },
    'ETC': {
        'EUR': {
            1481979135: FVal('0.9514'),
        },
    },
    A_USDC.identifier: {
        'EUR': {
            1612051199: FVal(0.8241),
        },
    },
    strethaddress_to_identifier('0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6'): {  # RDN
        'EUR': {
            1512561942: ZERO,
        },
    },
    strethaddress_to_identifier('0xc00e94Cb662C3520282E6f5717214004A7f26888'): {  # COMP
        'EUR': {
            1635314397: ZERO,
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
            1612051199: FVal(109.99),
        },
    },
    'XMR': {
        'EUR': {
            1447279735: FVal('0.4'),
            1449809536: FVal(0.39665),
            1458070370: FVal('1.0443027675'),
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
    'KFEE': {
        'EUR': {
            1609950165: FVal(0.1),
        },
    },
    A_USDT.identifier: {
        'EUR': {
            1609537953: FVal(0.89),
        },
    },
    'XTZ': {
        'USD': {
            1640493376: FVal(4.63),
        },
        'EUR': {
            1640493376: FVal(6.99),
        },
    },
}


def check_result_of_history_creation_for_remote_errors(  # pylint: disable=useless-return
        start_ts: Timestamp,  # pylint: disable=unused-argument
        end_ts: Timestamp,  # pylint: disable=unused-argument
        events: List[AccountingEventMixin],
) -> Optional[int]:
    assert len(events) == 0
    return None  # fake report id


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
        elif 'fiat/orders' in url:
            payload = '[]'
        elif 'fiat/payments' in url:
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
    expected = [
        AssetMovement(
            location=Location.KRAKEN,
            category=AssetMovementCategory.DEPOSIT,
            address=None,
            transaction_id=None,
            timestamp=Timestamp(1458994442),
            asset=A_BTC,
            amount=FVal('5.0'),
            fee_asset=A_BTC,
            fee=Fee(FVal('0')),
            link='D1',
        ),
        AssetMovement(
            location=Location.KRAKEN,
            category=AssetMovementCategory.DEPOSIT,
            address=None,
            transaction_id=None,
            timestamp=Timestamp(1458994441),
            asset=A_EUR,
            amount=FVal('4000000.0000'),
            fee_asset=A_EUR,
            fee=Fee(FVal('1.7500')),
            link='0',
        ), AssetMovement(
            location=Location.KRAKEN,
            address=None,
            transaction_id=None,
            category=AssetMovementCategory.DEPOSIT,
            timestamp=Timestamp(1448994442),
            asset=A_ETH,
            amount=FVal('10.0000'),
            fee_asset=A_ETH,
            fee=Fee(FVal('0')),
            link='D2',
        ), AssetMovement(
            location=Location.KRAKEN,
            category=AssetMovementCategory.WITHDRAWAL,
            address=None,
            transaction_id=None,
            timestamp=Timestamp(1439994442),
            asset=A_ETH,
            amount=FVal('1.0000000000'),
            fee_asset=A_ETH,
            fee=Fee(FVal('0.0035000000')),
            link='2',
        ), AssetMovement(
            location=Location.KRAKEN,
            category=AssetMovementCategory.WITHDRAWAL,
            address=None,
            transaction_id=None,
            timestamp=Timestamp(1439994442),
            asset=A_ETH,
            amount=FVal('10.0000'),
            fee_asset=A_ETH,
            fee=Fee(FVal('1.7500')),
            link='W2',
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
            link='W1',
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
            events: List[AccountingEventMixin],
    ) -> Optional[int]:
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
        limited_range_test = False
        expected_trades_num = 9
        expected_margin_num = 1
        expected_asset_movements_num = 13
        if not limited_range_test:
            expected_margin_num = 2
            expected_asset_movements_num = 13
        if end_ts == 1539713238:
            limited_range_test = True
            expected_trades_num = 8
            expected_margin_num = 1
            expected_asset_movements_num = 12
        if end_ts == 1601040361:
            expected_trades_num = 8

        trades = [x for x in events if isinstance(x, Trade)]
        assert len(trades) == expected_trades_num, f'Expected {len(trades)} during history creation check from {start_ts} to {end_ts}'  # noqa: E501

        margin_positions = [x for x in events if isinstance(x, MarginPosition)]
        assert len(margin_positions) == expected_margin_num

        loans = [x for x in events if isinstance(x, Loan)]
        assert len(loans) == 2
        assert loans[0].currency == A_ETH
        assert loans[0].earned == AssetAmount(FVal('0.00000001'))
        assert loans[1].currency == A_BTC
        assert loans[1].earned == AssetAmount(FVal('0.00000005'))

        asset_movements = [x for x in events if isinstance(x, AssetMovement)]
        assert len(asset_movements) == expected_asset_movements_num
        if not limited_range_test:
            assert asset_movements[0].location == Location.KRAKEN
            assert asset_movements[0].category == AssetMovementCategory.WITHDRAWAL
            assert asset_movements[0].asset == A_BTC
            assert asset_movements[1].location == Location.POLONIEX
            assert asset_movements[1].category == AssetMovementCategory.DEPOSIT
            assert asset_movements[1].asset == A_ETH
            assert asset_movements[2].location == Location.KRAKEN
            assert asset_movements[2].category == AssetMovementCategory.WITHDRAWAL
            assert asset_movements[2].asset == A_ETH
            assert asset_movements[3].location == Location.KRAKEN
            assert asset_movements[3].category == AssetMovementCategory.WITHDRAWAL
            assert asset_movements[3].asset == A_ETH
            assert asset_movements[4].location == Location.POLONIEX
            assert asset_movements[4].category == AssetMovementCategory.DEPOSIT
            assert asset_movements[4].asset == A_BTC
            assert asset_movements[5].location == Location.KRAKEN
            assert asset_movements[5].category == AssetMovementCategory.DEPOSIT
            assert asset_movements[5].asset == A_ETH
            assert asset_movements[6].location == Location.KRAKEN
            assert asset_movements[6].category == AssetMovementCategory.DEPOSIT
            assert asset_movements[6].asset == A_EUR
            assert asset_movements[7].location == Location.POLONIEX
            assert asset_movements[7].category == AssetMovementCategory.WITHDRAWAL
            assert asset_movements[7].asset == A_BTC
            assert asset_movements[8].location == Location.KRAKEN
            assert asset_movements[8].category == AssetMovementCategory.DEPOSIT
            assert asset_movements[8].asset == A_BTC
            assert asset_movements[9].location == Location.POLONIEX
            assert asset_movements[9].category == AssetMovementCategory.WITHDRAWAL
            assert asset_movements[9].asset == A_ETH
            assert asset_movements[10].location == Location.BITMEX
            assert asset_movements[10].category == AssetMovementCategory.DEPOSIT
            assert asset_movements[10].asset == A_BTC
            assert asset_movements[11].location == Location.BITMEX
            assert asset_movements[11].category == AssetMovementCategory.WITHDRAWAL
            assert asset_movements[11].asset == A_BTC
            assert asset_movements[12].location == Location.BITMEX
            assert asset_movements[12].category == AssetMovementCategory.WITHDRAWAL
            assert asset_movements[12].asset == A_BTC

        tx_events = [x for x in events if isinstance(x, HistoryBaseEntry) and x.event_identifier.startswith('0x')]  # noqa: E501
        gas_in_eth = FVal('14.36963')
        assert len(tx_events) == 6
        assert tx_events[0].location_label == ETH_ADDRESS1
        assert tx_events[0].event_type == HistoryEventType.SPEND
        assert tx_events[0].event_subtype == HistoryEventSubType.FEE
        assert tx_events[0].counterparty == CPT_GAS
        assert tx_events[0].balance.amount == gas_in_eth
        assert tx_events[1].location_label == ETH_ADDRESS1
        assert tx_events[1].event_type == HistoryEventType.INFORMATIONAL
        assert tx_events[1].event_subtype == HistoryEventSubType.DEPLOY

        assert tx_events[2].location_label == ETH_ADDRESS2
        assert tx_events[2].event_type == HistoryEventType.SPEND
        assert tx_events[2].event_subtype == HistoryEventSubType.FEE
        assert tx_events[2].counterparty == CPT_GAS
        assert tx_events[2].balance.amount == gas_in_eth
        assert tx_events[3].location_label == ETH_ADDRESS2
        assert tx_events[3].event_type == HistoryEventType.TRANSFER
        assert tx_events[3].event_subtype == HistoryEventSubType.NONE
        assert tx_events[3].counterparty == ETH_ADDRESS1
        assert tx_events[3].balance.amount == FVal('4.00003E-11')

        assert tx_events[4].location_label == ETH_ADDRESS3
        assert tx_events[4].event_type == HistoryEventType.SPEND
        assert tx_events[4].event_subtype == HistoryEventSubType.FEE
        assert tx_events[4].counterparty == CPT_GAS
        assert tx_events[4].balance.amount == gas_in_eth
        assert tx_events[5].location_label == ETH_ADDRESS3
        assert tx_events[5].event_type == HistoryEventType.TRANSFER
        assert tx_events[5].event_subtype == HistoryEventSubType.NONE
        assert tx_events[5].counterparty == ETH_ADDRESS1
        assert tx_events[5].balance.amount == FVal('5.005203E-10')

        return 1  # need to return a report id

    def check_result_of_history_creation_and_process_it(
            start_ts: Timestamp,
            end_ts: Timestamp,
            events: List[AccountingEventMixin],
    ) -> Optional[int]:
        """Checks results of history creation but also proceeds to normal history processing"""
        check_result_of_history_creation(
            start_ts=start_ts,
            end_ts=end_ts,
            events=events,
        )
        return original_history_processing_function(
            start_ts=start_ts,
            end_ts=end_ts,
            events=events,
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
        addr1_receipt = f"""{{"blockHash":"0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159","blockNumber":"0xdd1987","contractAddress":null,"cumulativeGasUsed":"0x1ba9a3f","effectiveGasPrice":"0xd4026e5de","from":"0x1627158aca8a8e2039f5ba3023c04a2129c634f1","gasUsed":"0x3251a","logs":[],"status":"0x1","to":"0xf8fdc3aa1f5a1ac20dd8596cd3d5b471ad305de1","transactionHash":"{TX_HASH_STR1}","transactionIndex":"0x12c","type":"0x2"}}
        """
        addr2_tx = f"""{{"blockNumber":"54093","timeStamp":"1439048643","hash":"{TX_HASH_STR2}","nonce":"0","blockHash":"0xf3cabad6adab0b52eb632c386ea194036805713682c62cb589b5abcd76df2159","transactionIndex":"0","from":"{ETH_ADDRESS2}","to":"{ETH_ADDRESS1}","value":"40000300","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"{MOCK_INPUT_DATA_HEX}","contractAddress":"0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"8569454"}}
        """
        addr2_receipt = f"""{{"blockHash":"0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159","blockNumber":"0xdd1987","contractAddress":null,"cumulativeGasUsed":"0x1ba9a3f","effectiveGasPrice":"0xd4026e5de","from":"0x1627158aca8a8e2039f5ba3023c04a2129c634f1","gasUsed":"0x3251a","logs":[],"status":"0x1","to":"0xf8fdc3aa1f5a1ac20dd8596cd3d5b471ad305de1","transactionHash":"{TX_HASH_STR2}","transactionIndex":"0x12c","type":"0x2"}}
        """
        addr3_tx = f"""{{"blockNumber":"54094","timeStamp":"1439048645","hash":"{TX_HASH_STR3}","nonce":"0","blockHash":"0xe3cabad6adab0b52eb632c3165a194036805713682c62cb589b5abcd76de2159","transactionIndex":"0","from":"{ETH_ADDRESS3}","to":"{ETH_ADDRESS1}","value":"500520300","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"{MOCK_INPUT_DATA_HEX}","contractAddress":"0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"8569454"}}
        """
        addr3_receipt = f"""{{"blockHash":"0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159","blockNumber":"0xdd1987","contractAddress":null,"cumulativeGasUsed":"0x1ba9a3f","effectiveGasPrice":"0xd4026e5de","from":"0x1627158aca8a8e2039f5ba3023c04a2129c634f1","gasUsed":"0x3251a","logs":[],"status":"0x1","to":"0xf8fdc3aa1f5a1ac20dd8596cd3d5b471ad305de1","transactionHash":"{TX_HASH_STR3}","transactionIndex":"0x12c","type":"0x2"}}
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
        elif '=tokentx&' in url:
            # don't return any token transactions
            payload = '{"status":"1","message":"OK","result":[]}'
        elif '=getblocknobytime&' in url:
            # we don't really care about this in the history tests so just return whatever
            payload = '{"status":"1","message":"OK","result": "1"}'
        elif 'eth_getTransactionReceipt&txhash=' in url:
            if TX_HASH_STR1 in url:
                receipt_str = addr1_receipt
            elif TX_HASH_STR2 in url:
                receipt_str = addr2_receipt
            elif TX_HASH_STR3 in url:
                receipt_str = addr3_receipt
            else:
                raise AssertionError(
                    'Requested etherscan receipts for unknown hashes in tests',
                )

            payload = f'{{"jsonrpc":"2.0","id":1,"result":{receipt_str}}}'
        else:
            raise AssertionError(f'Unexpected etherscan query {url} at test mock')

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
        dont_mock_price_for: Optional[List['Asset']] = None,
        force_no_price_found_for: Optional[List[Tuple['Asset', Timestamp]]] = None,
) -> None:
    """If needed will make sure the historian's price queries are mocked"""
    if not should_mock_price_queries:
        return

    if dont_mock_price_for is None:
        dont_mock_price_for = []

    if force_no_price_found_for is None:
        force_no_price_found_for = []

    # save the original function in this variable to be used when
    # the list of assets to not mock is non empty.
    original_function = historian.query_historical_price

    def mock_historical_price_query(from_asset, to_asset, timestamp):
        if from_asset == to_asset:
            return ONE

        if from_asset == A_ETH2:
            from_asset = A_ETH

        if from_asset in dont_mock_price_for:
            return original_function(from_asset, to_asset, timestamp)

        if (from_asset, timestamp) in force_no_price_found_for:
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            )

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


def assert_pnl_debug_import(filepath: Path, database: DBHandler) -> None:
    """This function asserts that the debug PnL data in the DB matches
    the one in the file uploaded.
    """
    with open(filepath) as f:
        pnl_debug_json = json.load(f)

    settings_from_file = pnl_debug_json['settings']
    settings_from_file.pop('last_write_ts')
    ignored_actions_ids_from_file = pnl_debug_json['ignored_events_ids']

    with database.conn.read_ctx() as cursor:
        settings_from_db = database.get_settings(cursor=cursor).serialize()
        settings_from_db.pop('last_write_ts')
        ignored_actions_ids_from_db = database.get_ignored_action_ids(
            cursor=cursor,
            action_type=None,
        )
        serialized_ignored_actions_from_db = {
            k.serialize(): v for k, v in ignored_actions_ids_from_db.items()
        }
    assert settings_from_file == settings_from_db
    assert serialized_ignored_actions_from_db == ignored_actions_ids_from_file
