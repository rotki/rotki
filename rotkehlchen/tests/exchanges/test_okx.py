import warnings as test_warnings
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_okx
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_USDT
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.okx import Okx, OkxEndpoint
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.tests.utils.constants import A_SOL, A_XMR
from rotkehlchen.tests.utils.globaldb import is_asset_symbol_unsupported
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location, Timestamp, TimestampMS


def test_name():
    exchange = Okx('okx1', 'a', b'a', 'a', object(), object())
    assert exchange.location == Location.OKX
    assert exchange.name == 'okx1'


@pytest.mark.asset_test
def test_assets_are_known(mock_okx: Okx, globaldb):
    currencies = mock_okx._api_query(OkxEndpoint.CURRENCIES)
    okx_assets = {currency['ccy'] for currency in currencies['data']}

    for okx_asset in okx_assets:
        try:
            asset_from_okx(okx_asset)
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.identifier} in OKX. '
                f'Support for it has to be added',
            ))
        except UnsupportedAsset as e:
            if is_asset_symbol_unsupported(globaldb, Location.OKX, okx_asset) is False:
                test_warnings.warn(UserWarning(
                    f'Found unsupported asset {e.identifier} in OKX. '
                    f'Support for it has to be added',
                ))


def test_okx_api_signature(mock_okx: Okx):
    sig = mock_okx._generate_signature(
        '2022-12-27T10:55:09.836Z',
        'GET',
        '/api/v5/asset/currencies',
        '',
    )
    assert sig == 'miq5qKL+pRzZJjf0fq0qnUshMuNjvmwHWWyWv0QxsLs='


def test_okx_query_balances(mock_okx: Okx):
    def mock_okx_balances(method, url):     # pylint: disable=unused-argument
        if '/api/v5/asset/balances' in url:
            return MockResponse(200, '{"code":"0","data":[{"availBal":"25","bal":"25","ccy":"USDT","frozenBal":"0"},{"availBal":"30","bal":"30","ccy":"USDC","frozenBal":"0"}],"msg":""}')  # noqa: E501

        return MockResponse(
            200,
            """
{
   "code":"0",
   "data":[
      {
         "adjEq":"",
         "details":[
            {
               "availBal":"299.9920000068",
               "availEq":"299.9920000068",
               "cashBal":"299.9920000068",
               "ccy":"SOL",
               "crossLiab":"",
               "disEq":"2865.1035952649445",
               "eq":"299.9920000068",
               "eqUsd":"3370.7101120764055",
               "fixedBal":"0",
               "frozenBal":"0",
               "interest":"",
               "isoEq":"0",
               "isoLiab":"",
               "isoUpl":"0",
               "liab":"",
               "maxLoan":"",
               "mgnRatio":"",
               "notionalLever":"0",
               "ordFrozen":"0",
               "spotInUseAmt":"",
               "stgyEq":"0",
               "twap":"0",
               "uTime":"1671542570024",
               "upl":"0",
               "uplLiab":""
            },
            {
               "availBal":"0.027846",
               "availEq":"0.027846",
               "cashBal":"0.027846",
               "ccy":"XMR",
               "crossLiab":"",
               "disEq":"3.260655216",
               "eq":"0.027846",
               "eqUsd":"4.07581902",
               "fixedBal":"0",
               "frozenBal":"0",
               "interest":"",
               "isoEq":"0",
               "isoLiab":"",
               "isoUpl":"0",
               "liab":"",
               "maxLoan":"",
               "mgnRatio":"",
               "notionalLever":"0",
               "ordFrozen":"0",
               "spotInUseAmt":"",
               "stgyEq":"0",
               "twap":"0",
               "uTime":"1666762735059",
               "upl":"0",
               "uplLiab":""
            },
            {
               "availBal":"0.00000065312",
               "availEq":"0.00000065312",
               "cashBal":"0.00000065312",
               "ccy":"USDT",
               "crossLiab":"",
               "disEq":"0.00000065312",
               "eq":"0.00000065312",
               "eqUsd":"0.00000065312",
               "fixedBal":"0",
               "frozenBal":"50",
               "interest":"",
               "isoEq":"0",
               "isoLiab":"",
               "isoUpl":"0",
               "liab":"",
               "maxLoan":"",
               "mgnRatio":"",
               "notionalLever":"0",
               "ordFrozen":"0",
               "spotInUseAmt":"",
               "stgyEq":"0",
               "twap":"0",
               "uTime":"1670953160041",
               "upl":"0",
               "uplLiab":""
            }
         ],
         "imr":"",
         "isoEq":"0",
         "mgnRatio":"",
         "mmr":"",
         "notionalUsd":"",
         "ordFroz":"",
         "totalEq":"3374.785943540432",
         "uTime":"1672123182199"
      }
   ],
   "msg":""
}
            """,
        )

    with patch.object(mock_okx.session, 'request', side_effect=mock_okx_balances):
        balances, msg = mock_okx.query_balances()

    assert msg == ''
    assert balances is not None
    assert len(balances) == 4
    assert (balances[A_XMR.resolve_to_asset_with_oracles()]).amount == FVal('0.027846')
    assert (balances[A_SOL.resolve_to_asset_with_oracles()]).amount == FVal('299.9920000068')
    assert (balances[A_USDT.resolve_to_asset_with_oracles()]).amount == FVal('75.00000065312')
    assert (balances[A_USDC.resolve_to_asset_with_oracles()]).amount == FVal('30')

    warnings = mock_okx.msg_aggregator.consume_warnings()
    errors = mock_okx.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0


def test_okx_query_trades(mock_okx: 'Okx') -> None:
    def mock_okx_trades(method, url):  # pylint: disable=unused-argument
        if 'trade/orders-history-archive' in url:
            data = """
{
   "code":"0",
   "data":[
      {
         "accFillSz":"30009.966",
         "avgPx":"0.06236",
         "cTime":"1665846604080",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-1.87142147976",
         "feeCcy":"USDT",
         "fillPx":"0.06236",
         "fillSz":"10285.714558",
         "fillTime":"1665846604081",
         "instId":"TRX-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"TRADE1",
         "ordType":"limit",
         "pnl":"0",
         "posSide":"",
         "px":"0.06236",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"TRX",
         "reduceOnly":"false",
         "side":"sell",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"30009.966",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1665846604147"
      },
      {
         "accFillSz":"10",
         "avgPx":"0.06174",
         "cTime":"1665641177030",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-0.01",
         "feeCcy":"TRX",
         "fillPx":"0.06174",
         "fillSz":"10",
         "fillTime":"1665641177031",
         "instId":"TRX-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"TRADE2",
         "ordType":"limit",
         "pnl":"0",
         "posSide":"",
         "px":"0.06174",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDT",
         "reduceOnly":"false",
         "side":"buy",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"10",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1665641177086"
      },
      {
         "accFillSz":"24",
         "avgPx":"0.06174",
         "cTime":"1665641133954",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-0.024",
         "feeCcy":"TRX",
         "fillPx":"0.06174",
         "fillSz":"24",
         "fillTime":"1665641133955",
         "instId":"TRX-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"TRADE3",
         "ordType":"limit",
         "pnl":"0",
         "posSide":"",
         "px":"0.06174",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDT",
         "reduceOnly":"false",
         "side":"buy",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"24",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1665641133978"
      },
      {
         "accFillSz":"30000",
         "avgPx":"0.06174",
         "cTime":"1665641100283",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-24",
         "feeCcy":"TRX",
         "fillPx":"0.06174",
         "fillSz":"0.000003",
         "fillTime":"1665641106343",
         "instId":"TRX-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"TRADE4",
         "ordType":"limit",
         "pnl":"0",
         "posSide":"",
         "px":"0.06174",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDT",
         "reduceOnly":"false",
         "side":"buy",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"30000",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1665641106388"
      },
      {
         "accFillSz":"3513.8312",
         "avgPx":"1.0001",
         "cTime":"1665594495006",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-3.51418258312",
         "feeCcy":"USDT",
         "fillPx":"1.0001",
         "fillSz":"3513.8312",
         "fillTime":"1665594495008",
         "instId":"USDC-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"TRADE5",
         "ordType":"market",
         "pnl":"0",
         "posSide":"",
         "px":"",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDC",
         "reduceOnly":"false",
         "side":"sell",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"3513.8312",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"base_ccy",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1665594495121"
      },
      {
         "accFillSz":"4.5",
         "avgPx":"1287.177158951111111",
         "cTime":"1665512880478",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-0.00315",
         "feeCcy":"ETH",
         "fillPx":"1287.21",
         "fillSz":"2.390191",
         "fillTime":"1665512880479",
         "instId":"ETH-USDC",
         "instType":"SPOT",
         "lever":"",
         "ordId":"TRADE6",
         "ordType":"market",
         "pnl":"0",
         "posSide":"",
         "px":"",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDC",
         "reduceOnly":"false",
         "side":"buy",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"4.5",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"base_ccy",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1665512880542"
      },
      {
         "accFillSz":"3600",
         "avgPx":"1",
         "cTime":"1664784938639",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-3.6",
         "feeCcy":"USDT",
         "fillPx":"1",
         "fillSz":"3600",
         "fillTime":"1664784938640",
         "instId":"USDC-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"TRADE7",
         "ordType":"limit",
         "pnl":"0",
         "posSide":"",
         "px":"1",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDC",
         "reduceOnly":"false",
         "side":"sell",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"3600",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1664784938717"
      },
      {
         "accFillSz":"850",
         "avgPx":"1",
         "cTime":"1664783042522",
         "cancelSource":"",
         "cancelSourceReason":"",
         "category":"normal",
         "ccy":"",
         "clOrdId":"",
         "fee":"-0.85",
         "feeCcy":"USDT",
         "fillPx":"1",
         "fillSz":"850",
         "fillTime":"1664783042523",
         "instId":"USDC-USDT",
         "instType":"SPOT",
         "lever":"",
         "ordId":"TRADE8",
         "ordType":"limit",
         "pnl":"0",
         "posSide":"",
         "px":"1",
         "quickMgnType":"",
         "rebate":"0",
         "rebateCcy":"USDC",
         "reduceOnly":"false",
         "side":"sell",
         "slOrdPx":"",
         "slTriggerPx":"",
         "slTriggerPxType":"",
         "source":"",
         "state":"filled",
         "sz":"850",
         "tag":"",
         "tdMode":"cash",
         "tgtCcy":"",
         "tpOrdPx":"",
         "tpTriggerPx":"",
         "tpTriggerPxType":"",
         "tradeId":"77777777",
         "uTime":"1664783042604"
      }
   ],
   "msg":""
}"""
        else:
            data = '{"code":"0","data":[]}'
        return MockResponse(200, data)

    with patch.object(mock_okx.session, 'request', side_effect=mock_okx_trades):
        events, _ = mock_okx.query_online_history_events(
            Timestamp(1609103082),
            Timestamp(1672175105),
        )
        assert events == [SwapEvent(
            timestamp=TimestampMS(1665846604080),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0x50327c6c5a14DCaDE707ABad2E27eB517df87AB5'),
            amount=FVal('30009.966'),
            location_label='okx',
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE1',
            ),
        ), SwapEvent(
            timestamp=TimestampMS(1665846604080),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('1871.42147976'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE1',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665846604080),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDT,
            amount=FVal('1.87142147976'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE1',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665641177030),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal('0.61740'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE2',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665641177030),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x50327c6c5a14DCaDE707ABad2E27eB517df87AB5'),
            amount=FVal('10'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE2',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665641177030),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('eip155:1/erc20:0x50327c6c5a14DCaDE707ABad2E27eB517df87AB5'),
            amount=FVal('0.01'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE2',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665641133954),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal('1.48176'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE3',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665641133954),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x50327c6c5a14DCaDE707ABad2E27eB517df87AB5'),
            amount=FVal('24'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE3',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665641133954),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('eip155:1/erc20:0x50327c6c5a14DCaDE707ABad2E27eB517df87AB5'),
            amount=FVal('0.024'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE3',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665641100283),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal('1852.20000'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE4',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665641100283),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x50327c6c5a14DCaDE707ABad2E27eB517df87AB5'),
            amount=FVal('30000'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE4',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665641100283),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('eip155:1/erc20:0x50327c6c5a14DCaDE707ABad2E27eB517df87AB5'),
            amount=FVal('24'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE4',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665594495006),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            amount=FVal('3513.8312'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE5',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665594495006),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('3514.18258312'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE5',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665594495006),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDT,
            amount=FVal('3.51418258312'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE5',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665512880478),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            amount=FVal('5792.2972152799999995'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE6',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665512880478),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('4.5'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE6',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1665512880478),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00315'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE6',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1664784938639),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            amount=FVal('3600'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE7',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1664784938639),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('3600'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE7',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1664784938639),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDT,
            amount=FVal('3.6'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE7',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1664783042522),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            amount=FVal('850'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE8',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1664783042522),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('850'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE8',
            ),
            location_label='okx',
        ), SwapEvent(
            timestamp=TimestampMS(1664783042522),
            location=Location.OKX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDT,
            amount=FVal('0.85'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.OKX,
                unique_id='TRADE8',
            ),
            location_label='okx',
        )]


def test_okx_query_deposits_withdrawals(mock_okx: 'Okx') -> None:
    def mock_okx_deposits_withdrawals(method, url):     # pylint: disable=unused-argument
        if 'deposit' in url:
            data = """
{
   "code":"0",
   "data":[
      {
         "actualDepBlkConfirm":"991",
         "amt":"2500.180327",
         "areaCodeFrom":"",
         "ccy":"USDT",
         "chain":"USDT-Arbitrum one",
         "depId":"88888888",
         "from":"",
         "fromWdId":"",
         "state":"2",
         "to":"0xaab27b150451726ec7738aa1d0a94505c8729bd1",
         "ts":"1669963555000",
         "txId":"0xfd12f8850218dc9d1d706c2dbd6c38f495988109c220bf8833255697b85c92db"
      },
      {
         "actualDepBlkConfirm":"200",
         "amt":"990.795352",
         "areaCodeFrom":"",
         "ccy":"USDC",
         "chain":"USDC-Polygon",
         "depId":"88888888",
         "from":"",
         "fromWdId":"",
         "state":"2",
         "to":"0xaab27b150451726ec7738aa1d0a94505c8729bd1",
         "ts":"1669405596000",
         "txId":"0xcea993d53b2c1f79430a003fb8facb5cd6b83b6cb6a502b6233d83eb338ba8ba"
      }
   ],
   "msg":""
}
            """
        elif 'withdraw' in url:
            data = """
{
   "code":"0",
   "data":[
      {
         "chain":"SOL-Solana",
         "areaCodeFrom":"",
         "clientId":"",
         "fee":"0.008",
         "amt":"49.86051649",
         "txId":"46tgp3RHNuQqQrHbms1NtPFkRRwsabCajvEUPXBryVuH6qJmQysn1V9VhTYBEJmVQq8s8fbfv4WFW3oj2LtwRzyU",
         "areaCodeTo":"",
         "ccy":"SOL",
         "from":"",
         "to":"9ZLfHwxzgbZi3eiK43duZVJ2nXft3mtkRMjs9YD5Yds2",
         "state":"2",
         "nonTradableAsset":false,
         "ts":"1671542569000",
         "wdId":"66666666",
         "feeCcy":"SOL"
      },
      {
         "chain":"USDT-Arbitrum one",
         "areaCodeFrom":"",
         "clientId":"",
         "fee":"0.1",
         "amt":"421.169831",
         "txId":"0x9444b018c33c5adb58ee171bc18e61c56078495e37ae88833007a46c02b4552f",
         "areaCodeTo":"",
         "ccy":"USDT",
         "from":"",
         "to":"0x388c818ca8b9251b393131c08a736a67ccb19297",
         "state":"2",
         "nonTradableAsset":false,
         "ts":"1670953159000",
         "wdId":"66666666",
         "feeCcy":"USDT"
      }
   ],
   "msg":""
}
            """
        else:
            data = '{"code":"0","data":[]}'
        return MockResponse(200, data)

    with patch.object(
            mock_okx.session,
            'request',
            side_effect=mock_okx_deposits_withdrawals,
    ):
        asset_movements, _ = mock_okx.query_online_history_events(
            Timestamp(1609103082),
            Timestamp(1672175105),
        )

    expected_asset_movements = [
        AssetMovement(
            location=Location.OKX,
            location_label=mock_okx.name,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1669963555000),
            asset=A_USDT,
            amount=FVal(2500.180327),
            unique_id='0xfd12f8850218dc9d1d706c2dbd6c38f495988109c220bf8833255697b85c92db',
            extra_data={
                'address': '0xAAB27b150451726EC7738aa1d0A94505c8729bd1',
                'transaction_id': '0xfd12f8850218dc9d1d706c2dbd6c38f495988109c220bf8833255697b85c92db',  # noqa: E501
            },
        ),
        AssetMovement(
            location=Location.OKX,
            location_label=mock_okx.name,
            event_type=HistoryEventType.DEPOSIT,
            timestamp=TimestampMS(1669405596000),
            asset=A_USDC,
            amount=FVal(990.795352),
            unique_id='0xcea993d53b2c1f79430a003fb8facb5cd6b83b6cb6a502b6233d83eb338ba8ba',
            extra_data={
                'address': '0xAAB27b150451726EC7738aa1d0A94505c8729bd1',
                'transaction_id': '0xcea993d53b2c1f79430a003fb8facb5cd6b83b6cb6a502b6233d83eb338ba8ba',  # noqa: E501
            },
        ),
        AssetMovement(
            location=Location.OKX,
            location_label=mock_okx.name,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1671542569000),
            asset=A_SOL,
            amount=FVal(49.86051649),
            unique_id='46tgp3RHNuQqQrHbms1NtPFkRRwsabCajvEUPXBryVuH6qJmQysn1V9VhTYBEJmVQq8s8fbfv4WFW3oj2LtwRzyU',
            extra_data={
                'address': '9ZLfHwxzgbZi3eiK43duZVJ2nXft3mtkRMjs9YD5Yds2',
                'transaction_id': '46tgp3RHNuQqQrHbms1NtPFkRRwsabCajvEUPXBryVuH6qJmQysn1V9VhTYBEJmVQq8s8fbfv4WFW3oj2LtwRzyU',  # noqa: E501
            },
        ),
        AssetMovement(
            location=Location.OKX,
            location_label=mock_okx.name,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1671542569000),
            asset=A_SOL,
            amount=FVal(0.008),
            unique_id='46tgp3RHNuQqQrHbms1NtPFkRRwsabCajvEUPXBryVuH6qJmQysn1V9VhTYBEJmVQq8s8fbfv4WFW3oj2LtwRzyU',
            is_fee=True,
        ),
        AssetMovement(
            location=Location.OKX,
            location_label=mock_okx.name,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1670953159000),
            asset=A_USDT,
            amount=FVal(421.169831),
            unique_id='0x9444b018c33c5adb58ee171bc18e61c56078495e37ae88833007a46c02b4552f',
            extra_data={
                'address': '0x388C818CA8B9251b393131C08a736A67ccB19297',
                'transaction_id': '0x9444b018c33c5adb58ee171bc18e61c56078495e37ae88833007a46c02b4552f',  # noqa: E501
            },
        ),
        AssetMovement(
            location=Location.OKX,
            location_label=mock_okx.name,
            event_type=HistoryEventType.WITHDRAWAL,
            timestamp=TimestampMS(1670953159000),
            asset=A_USDT,
            amount=FVal(0.1),
            unique_id='0x9444b018c33c5adb58ee171bc18e61c56078495e37ae88833007a46c02b4552f',
            is_fee=True,
        ),
    ]

    assert asset_movements == expected_asset_movements
