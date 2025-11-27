import json
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, cast
from unittest.mock import _patch, patch

from rotkehlchen.accounting.mixins.event import AccountingEventMixin
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH, A_ETH2, A_USDC, A_USDT
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.externalapis.blockscout import Blockscout
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.constants import (
    A_EUR,
    ETH_ADDRESS1,
    ETH_ADDRESS2,
    ETH_ADDRESS3,
    MOCK_INPUT_DATA_HEX,
    TX_HASH_STR1,
    TX_HASH_STR2,
    TX_HASH_STR3,
)
from rotkehlchen.tests.utils.exchanges import POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.tests.utils.kraken import MockKraken

TEST_END_TS = 1559427707


# Prices queried by cryptocompare
prices = {
    'USD': {
        'EUR': {
            1446979735: FVal('0.9318'),
            1459024920: FVal('0.8982'),
            1463508234: FVal('0.8878'),
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
            1566687695: FVal(178.615),
            1566726126: FVal('167.58'),
            1569366095: FVal('161.59'),
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
            1681343455: FVal('1746.99'),
            1685198279: FVal('1701.45'),
            1691693607: FVal('1698.56'),
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
    strethaddress_to_identifier('0x1776e1F26f98b1A5dF9cD347953a26dd3Cb46671'): {  # NMR
        'EUR': {
            1609877514: FVal('23.15'),
        },
    },
    'ALGO': {
        'EUR': {
            1611426233: FVal('0.4573'),
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
    A_DAI.identifier: {
        'EUR': {
            1628994441: FVal(0.9),
        },
    },
    'XYZ': {  # custom asset used in test 'test_history_export_download_csv'
        'EUR': {
            1601040360: ONE,
        },
    },
}


def check_result_of_history_creation_for_remote_errors(  # type: ignore[return] # pylint: disable=useless-return
        start_ts: Timestamp,  # pylint: disable=unused-argument
        end_ts: Timestamp,  # pylint: disable=unused-argument
        events: list[AccountingEventMixin],
) -> int | None:
    assert len(events) == 0


def mock_exchange_responses(rotki: Rotkehlchen, remote_errors: bool):
    invalid_payload = '[{'

    def mock_binance_api_queries(url, params, *args, **kwargs):  # pylint: disable=unused-argument
        if remote_errors:
            payload = invalid_payload
        elif 'myTrades' in url:
            # Can't mock unknown assets in binance trade query since
            # only all known pairs are queried
            payload = '[]'
            # ensure that if the endpoint gets queried twice we don't return new trades.
            # The first time it's always queried with fromId = 0
            if params['fromId'] == 0:
                if params.get('symbol') == 'ETHBTC':
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
                elif params.get('symbol') == 'RDNETH':
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
        elif (
                'capital/deposit' in url or
                'capital/withdraw' in url or
                'fiat/orders' in url or
                'fiat/payments' in url or
                'asset/get-funding-asset' in url
        ):
            payload = '[]'
        else:
            raise RuntimeError(f'Binance test mock got unexpected/unmocked url {url}')

        return MockResponse(200, payload)

    def mock_poloniex_api_queries(url, **kwargs):  # pylint: disable=unused-argument
        payload = ''
        if remote_errors:
            payload = invalid_payload
        elif '/trades?' in url:
            payload = """[{
                    "symbol": "ETH_BTC",
                    "id": 394131412,
                    "createTime": 1539713117000,
                    "price": "0.06935244",
                    "quantity": "1.40308443",
                    "feeAmount": "0.0000973073287465092",
                    "feeCurrency": "BTC",
                    "side": "SELL",
                    "type": "LIMIT",
                    "accountType": "SPOT"
                }, {
                    "symbol": "ETH_BTC",
                    "id": 394131413,
                    "createTime": 1539713237000,
                    "price": "0.06935244",
                    "quantity": "1.40308443",
                    "feeAmount": "0.00140308443",
                    "feeCurrency": "ETH",
                    "side": "BUY",
                    "type": "LIMIT",
                    "accountType": "SPOT"
                }, {
                    "symbol": "XMR_ETH",
                    "id": 394131415,
                    "createTime": 1539713238000,
                    "price": "0.06935244",
                    "quantity": "1.40308443",
                    "feeAmount": "0.00140308443",
                    "feeCurrency": "XMR",
                    "side": "BUY",
                    "type": "LIMIT",
                    "accountType": "SPOT"
                }, {
                    "symbol": "ETH_NOEXISTINGASSET",
                    "id": 394131418,
                    "createTime": 1539713237000,
                    "price": "0.06935244",
                    "quantity": "1.40308443",
                    "feeAmount": "9.730732e-5",
                    "feeCurrency": "ETH",
                    "side": "BUY",
                    "type": "LIMIT",
                    "accountType": "SPOT"
                }, {
                    "symbol": "ETH_BALLS",
                    "id": 394131419,
                    "createTime": 1539713237000,
                    "price": "0.06935244",
                    "quantity": "1.40308443",
                    "feeAmount": "9.730732e-5",
                    "feeCurrency": "ETH",
                    "side": "BUY",
                    "type": "LIMIT",
                    "accountType": "SPOT"
                }]"""
        elif '/wallets/activity' in url:
            split1 = url.split('start=')[1]
            start_ts = int(split1.split('&')[0])
            end_ts = int(split1.split('end=')[1])
            data = json.loads(POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE)
            new_data = {}
            for x in ('deposits', 'withdrawals'):
                new_data[x] = []
                for entry in data[x]:
                    if entry['timestamp'] < start_ts or entry['timestamp'] > end_ts:
                        continue
                    new_data[x].append(entry)

            payload = json.dumps(new_data)
        else:
            raise RuntimeError(
                f'Poloniex test mock got unexpected/unmocked url {url}',
            )
        return MockResponse(200, payload)

    def mock_bitmex_api_queries(url):
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
            'get',
            side_effect=mock_poloniex_api_queries,
        )

    binance_objects = rotki.exchange_manager.connected_exchanges.get(Location.BINANCE, None)
    binance = None if binance_objects is None else binance_objects[0]
    binance_patch = None
    if binance:
        binance_patch = patch.object(
            target=binance.session,
            attribute='request',
            side_effect=mock_binance_api_queries,
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

    return polo_patch, binance_patch, bitmex_patch


def mock_history_processing(
        rotki: Rotkehlchen,
        should_mock_history_processing: bool = True,
        remote_errors: bool = False,
        history_start_ts: Timestamp | None = None,
        history_end_ts: Timestamp | None = None,
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
            events: list[AccountingEventMixin],
    ) -> int | None:
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
        expected_swap_events_num = 22
        expected_margin_num = 1
        expected_asset_movements_num = 21
        if not limited_range_test:
            expected_margin_num = 2
            expected_asset_movements_num = 21
        if end_ts == 1539713238:
            limited_range_test = True
            expected_swap_events_num = 18
            expected_margin_num = 1
            expected_asset_movements_num = 19
        if end_ts == 1601040361:
            expected_swap_events_num = 18

        swap_events = [x for x in events if isinstance(x, SwapEvent)]
        assert len(swap_events) == expected_swap_events_num, f'Expected {expected_swap_events_num} but found {len(swap_events)} during history creation check from {start_ts} to {end_ts}'  # noqa: E501

        margin_positions = [x for x in events if isinstance(x, MarginPosition)]
        assert len(margin_positions) == expected_margin_num

        asset_movements = [x for x in events if isinstance(x, AssetMovement)]
        assert len(asset_movements) == expected_asset_movements_num
        if not limited_range_test:
            assert asset_movements[0].location == Location.KRAKEN
            assert asset_movements[0].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[0].asset == A_BTC
            assert asset_movements[1].location == Location.KRAKEN
            assert asset_movements[1].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[1].event_subtype == HistoryEventSubType.FEE
            assert asset_movements[1].asset == A_BTC
            assert asset_movements[2].location == Location.POLONIEX
            assert asset_movements[2].event_type == HistoryEventType.DEPOSIT
            assert asset_movements[2].asset == A_ETH
            assert asset_movements[3].location == Location.KRAKEN
            assert asset_movements[3].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[3].asset == A_ETH
            assert asset_movements[4].location == Location.KRAKEN
            assert asset_movements[4].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[4].event_subtype == HistoryEventSubType.FEE
            assert asset_movements[4].asset == A_ETH
            assert asset_movements[5].location == Location.KRAKEN
            assert asset_movements[5].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[5].asset == A_ETH
            assert asset_movements[6].location == Location.KRAKEN
            assert asset_movements[6].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[6].event_subtype == HistoryEventSubType.FEE
            assert asset_movements[6].asset == A_ETH
            assert asset_movements[7].location == Location.KRAKEN
            assert asset_movements[7].event_type == HistoryEventType.DEPOSIT
            assert asset_movements[7].asset == A_ETH
            assert asset_movements[8].location == Location.POLONIEX
            assert asset_movements[8].event_type == HistoryEventType.DEPOSIT
            assert asset_movements[8].asset == A_BTC
            assert asset_movements[9].location == Location.KRAKEN
            assert asset_movements[9].event_type == HistoryEventType.DEPOSIT
            assert asset_movements[9].asset == A_EUR
            assert asset_movements[10].location == Location.KRAKEN
            assert asset_movements[10].event_type == HistoryEventType.DEPOSIT
            assert asset_movements[10].event_subtype == HistoryEventSubType.FEE
            assert asset_movements[10].asset == A_EUR
            assert asset_movements[11].location == Location.KRAKEN
            assert asset_movements[11].event_type == HistoryEventType.DEPOSIT
            assert asset_movements[11].asset == A_BTC
            assert asset_movements[12].location == Location.POLONIEX
            assert asset_movements[12].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[12].asset == A_BTC
            assert asset_movements[13].location == Location.POLONIEX
            assert asset_movements[13].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[13].event_subtype == HistoryEventSubType.FEE
            assert asset_movements[13].asset == A_BTC
            assert asset_movements[14].location == Location.POLONIEX
            assert asset_movements[14].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[14].asset == A_ETH
            assert asset_movements[15].location == Location.POLONIEX
            assert asset_movements[15].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[15].event_subtype == HistoryEventSubType.FEE
            assert asset_movements[15].asset == A_ETH
            assert asset_movements[16].location == Location.BITMEX
            assert asset_movements[16].event_type == HistoryEventType.DEPOSIT
            assert asset_movements[16].asset == A_BTC
            assert asset_movements[17].location == Location.BITMEX
            assert asset_movements[17].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[17].asset == A_BTC
            assert asset_movements[18].location == Location.BITMEX
            assert asset_movements[18].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[18].event_subtype == HistoryEventSubType.FEE
            assert asset_movements[18].asset == A_BTC
            assert asset_movements[19].location == Location.BITMEX
            assert asset_movements[19].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[19].asset == A_BTC
            assert asset_movements[20].location == Location.BITMEX
            assert asset_movements[20].event_type == HistoryEventType.WITHDRAWAL
            assert asset_movements[20].event_subtype == HistoryEventSubType.FEE
            assert asset_movements[20].asset == A_BTC

        tx_events = [x for x in events if isinstance(x, EvmEvent)]
        gas_in_eth = FVal('14.36963')
        assert len(tx_events) == 6
        assert tx_events[0].location_label == ETH_ADDRESS1
        assert tx_events[0].event_type == HistoryEventType.SPEND
        assert tx_events[0].event_subtype == HistoryEventSubType.FEE
        assert tx_events[0].counterparty == CPT_GAS
        assert tx_events[0].amount == gas_in_eth
        assert tx_events[1].location_label == ETH_ADDRESS1
        assert tx_events[1].event_type == HistoryEventType.DEPLOY
        assert tx_events[1].event_subtype == HistoryEventSubType.SPEND

        assert tx_events[2].location_label == ETH_ADDRESS2
        assert tx_events[2].event_type == HistoryEventType.SPEND
        assert tx_events[2].event_subtype == HistoryEventSubType.FEE
        assert tx_events[2].counterparty == CPT_GAS
        assert tx_events[2].amount == gas_in_eth
        assert tx_events[3].location_label == ETH_ADDRESS2
        assert tx_events[3].event_type == HistoryEventType.TRANSFER
        assert tx_events[3].event_subtype == HistoryEventSubType.NONE
        assert tx_events[3].address == ETH_ADDRESS1
        assert tx_events[3].amount == FVal('4.00003E-11')

        assert tx_events[4].location_label == ETH_ADDRESS3
        assert tx_events[4].event_type == HistoryEventType.SPEND
        assert tx_events[4].event_subtype == HistoryEventSubType.FEE
        assert tx_events[4].counterparty == CPT_GAS
        assert tx_events[4].amount == gas_in_eth
        assert tx_events[5].location_label == ETH_ADDRESS3
        assert tx_events[5].event_type == HistoryEventType.TRANSFER
        assert tx_events[5].event_subtype == HistoryEventSubType.NONE
        assert tx_events[5].address == ETH_ADDRESS1
        assert tx_events[5].amount == FVal('5.005203E-10')

        return 1  # need to return a report id

    def check_result_of_history_creation_and_process_it(
            start_ts: Timestamp,
            end_ts: Timestamp,
            events: list[AccountingEventMixin],
    ) -> int | None:
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
    return patch.object(
        rotki.accountant,
        'process_history',
        side_effect=mock_function,
    )


def mock_etherscan_like_transaction_response(
        etherscan_like_api: Etherscan | Blockscout,
        remote_errors: bool,
) -> _patch:
    def mocked_request_dict(url, params, *_args, **_kwargs):
        if remote_errors:
            return MockResponse(200, '[{')

        addr1_tx = f"""{{"blockNumber":"54092","timeStamp":"1439048640","hash":"{TX_HASH_STR1}","nonce":"0","blockHash":"0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159","transactionIndex":"0","from":"{ETH_ADDRESS1}","to":"","value":"11901464239480000000000000","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"{MOCK_INPUT_DATA_HEX}","contractAddress":"0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"8569454"}}"""  # noqa: E501
        addr1_receipt = f"""{{"blockHash":"0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159","blockNumber":"0xdd1987","contractAddress":null,"cumulativeGasUsed":"0x1ba9a3f","effectiveGasPrice":"0xd4026e5de","from":"0x1627158aca8a8e2039f5ba3023c04a2129c634f1","gasUsed":"0x3251a","logs":[],"status":"0x1","to":"0xf8fdc3aa1f5a1ac20dd8596cd3d5b471ad305de1","transactionHash":"{TX_HASH_STR1}","transactionIndex":"0x12c","type":"0x2"}}"""  # noqa: E501
        addr2_tx = f"""{{"blockNumber":"54093","timeStamp":"1439048643","hash":"{TX_HASH_STR2}","nonce":"0","blockHash":"0xf3cabad6adab0b52eb632c386ea194036805713682c62cb589b5abcd76df2159","transactionIndex":"0","from":"{ETH_ADDRESS2}","to":"{ETH_ADDRESS1}","value":"40000300","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"{MOCK_INPUT_DATA_HEX}","contractAddress":"0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"8569454"}}"""  # noqa: E501
        addr2_receipt = f"""{{"blockHash":"0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159","blockNumber":"0xdd1987","contractAddress":null,"cumulativeGasUsed":"0x1ba9a3f","effectiveGasPrice":"0xd4026e5de","from":"0x1627158aca8a8e2039f5ba3023c04a2129c634f1","gasUsed":"0x3251a","logs":[],"status":"0x1","to":"0xf8fdc3aa1f5a1ac20dd8596cd3d5b471ad305de1","transactionHash":"{TX_HASH_STR2}","transactionIndex":"0x12c","type":"0x2"}}"""  # noqa: E501
        addr3_tx = f"""{{"blockNumber":"54094","timeStamp":"1439048645","hash":"{TX_HASH_STR3}","nonce":"0","blockHash":"0xe3cabad6adab0b52eb632c3165a194036805713682c62cb589b5abcd76de2159","transactionIndex":"0","from":"{ETH_ADDRESS3}","to":"{ETH_ADDRESS1}","value":"500520300","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"{MOCK_INPUT_DATA_HEX}","contractAddress":"0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"8569454"}}"""  # noqa: E501
        addr3_receipt = f"""{{"blockHash":"0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159","blockNumber":"0xdd1987","contractAddress":null,"cumulativeGasUsed":"0x1ba9a3f","effectiveGasPrice":"0xd4026e5de","from":"0x1627158aca8a8e2039f5ba3023c04a2129c634f1","gasUsed":"0x3251a","logs":[],"status":"0x1","to":"0xf8fdc3aa1f5a1ac20dd8596cd3d5b471ad305de1","transactionHash":"{TX_HASH_STR3}","transactionIndex":"0x12c","type":"0x2"}}"""  # noqa: E501
        action = params.get('action')
        if action == 'txlistinternal':
            # don't return any internal transactions
            payload = '{"status":"1","message":"OK","result":[]}'
        elif action == 'txlist':
            # And depending on the given query return corresponding mock transactions for address
            if (address := params.get('address')) == ETH_ADDRESS1:
                tx_str = addr1_tx
            elif address == ETH_ADDRESS2:
                tx_str = addr2_tx
            elif address == ETH_ADDRESS3:
                tx_str = addr3_tx
            else:
                raise AssertionError(
                    'Requested etherscan transactions for unknown address in tests',
                )

            payload = f'{{"status":"1","message":"OK","result":[{tx_str}]}}'
        elif action == 'tokentx':
            # don't return any token transactions
            payload = '{"status":"1","message":"OK","result":[]}'
        elif action == 'getblocknobytime':
            # we don't really care about this in the history tests so just return whatever
            payload = '{"status":"1","message":"OK","result": "1"}'
        elif action == 'eth_getTransactionReceipt' and 'txhash' in params:
            if (tx_hash := params.get('txhash')) == TX_HASH_STR1:
                receipt_str = addr1_receipt
            elif tx_hash == TX_HASH_STR2:
                receipt_str = addr2_receipt
            elif tx_hash == TX_HASH_STR3:
                receipt_str = addr3_receipt
            else:
                raise AssertionError(
                    'Requested etherscan receipts for unknown hashes in tests',
                )

            payload = f'{{"jsonrpc":"2.0","id":1,"result":{receipt_str}}}'
        else:
            raise AssertionError(f'Unexpected etherscan query {url} at test mock')

        return MockResponse(200, payload)

    return patch.object(etherscan_like_api.session, 'get', wraps=mocked_request_dict)


class TradesTestSetup(NamedTuple):
    polo_patch: _patch
    binance_patch: _patch
    bitmex_patch: _patch
    accountant_patch: _patch
    etherscan_patch: _patch
    blockscout_patch: _patch


def mock_history_processing_and_exchanges(
        rotki: Rotkehlchen,
        should_mock_history_processing: bool = True,
        history_start_ts: Timestamp | None = None,
        history_end_ts: Timestamp | None = None,
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

    polo_patch, binance_patch, bitmex_patch = mock_exchange_responses(
        rotki,
        remote_errors,
    )
    assert rotki.chains_aggregator.ethereum.node_inquirer.blockscout is not None
    return TradesTestSetup(
        polo_patch=polo_patch,
        binance_patch=binance_patch,
        bitmex_patch=bitmex_patch,
        accountant_patch=accountant_patch,
        etherscan_patch=mock_etherscan_like_transaction_response(
            etherscan_like_api=rotki.chains_aggregator.ethereum.node_inquirer.etherscan,
            remote_errors=remote_errors,
        ),
        blockscout_patch=mock_etherscan_like_transaction_response(
            etherscan_like_api=rotki.chains_aggregator.ethereum.node_inquirer.blockscout,
            remote_errors=remote_errors,
        ),
    )


def prepare_rotki_for_history_processing_test(
        rotki: Rotkehlchen,
        should_mock_history_processing: bool = True,
        history_start_ts: Timestamp | None = None,
        history_end_ts: Timestamp | None = None,
        remote_errors: bool = False,
) -> TradesTestSetup:
    """Prepares rotki for the history processing tests

    Makes sure blockchain accounts are loaded, kraken does not generate random trades
    and that all mocks are ready.
    """
    kraken = cast('MockKraken', rotki.exchange_manager.connected_exchanges.get(Location.KRAKEN)[0])  # type: ignore
    kraken.random_trade_data = False
    kraken.random_ledgers_data = False
    kraken.remote_errors = remote_errors
    return mock_history_processing_and_exchanges(
        rotki=rotki,
        should_mock_history_processing=should_mock_history_processing,
        history_start_ts=history_start_ts,
        history_end_ts=history_end_ts,
        remote_errors=remote_errors,
    )


def maybe_mock_historical_price_queries(
        historian,
        should_mock_price_queries: bool,
        mocked_price_queries,
        default_mock_value: FVal | None = None,
        dont_mock_price_for: list['Asset'] | None = None,
        force_no_price_found_for: list[tuple['Asset', Timestamp]] | None = None,
) -> None:
    """If needed will make sure the historian's price queries are mocked"""
    if not should_mock_price_queries:
        # ensure that no previous overwrite of the price historian affects the instance
        historian.__dict__.pop('query_historical_price', None)
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
                rate_limited=False,
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
    with open(filepath, encoding='utf8') as f:
        pnl_debug_json = json.load(f)

    settings_from_file = pnl_debug_json['settings']
    ignored_actions_ids_from_file = pnl_debug_json['ignored_events_ids']
    with database.conn.read_ctx() as cursor:
        settings_from_db = database.get_settings(cursor=cursor).serialize()
        ignored_actions_ids_from_db = database.get_ignored_action_ids(cursor=cursor)

    # Since following settings change often do not compare here
    assert settings_from_file['last_data_migration'] == 5
    assert settings_from_file['version'] == 35
    assert settings_from_file['last_write_ts'] == 1656344880
    for x in ('version', 'last_data_migration', 'last_write_ts'):
        settings_from_db.pop(x)
        settings_from_file.pop(x)

    assert settings_from_file == settings_from_db
    assert list(ignored_actions_ids_from_db) == ignored_actions_ids_from_file
