import json
import os
import warnings as test_warnings
from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH, A_SOL, A_USDC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.asset import UnknownAsset, UnprocessableTradePair
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.bybit import Bybit, bybit_symbol_to_base_quote
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.types import (
    AssetAmount,
    Fee,
    Location,
    Price,
    Timestamp,
    TimestampMS,
    TradeType,
)
from rotkehlchen.utils.misc import ts_now


def bybit_account_mock(
        is_unified: bool,
        calls: dict[str, list[dict[str, Any]]],
) -> Callable[[str, dict[str, Any]], dict[str, Any]]:
    """
    Mock call to the bybit API.
    - if `is_unified` is set to true then the endpoint for the information of the account will
    return as if it was a unified account.
    - calls is a map of a URL to a list of call outputs consumed in the order provided.
    """
    iterators = {key: iter(val) for key, val in calls.items()}

    def _mock_authenticated_query(path: str, options: dict[str, Any] | None = None) -> dict[str, Any]:  # pylint: disable=unused-argument  # noqa: E501
        if path == 'user/query-api':
            return {
                'retCode': 0,
                'retMsg': '',
                'result': {
                    'note': 'rotki',
                    'uta': int(is_unified),
                    'time': 1702310552326,
                },
            }

        if (
            options is not None and 'startTime' in options and
            int(options['startTime']) < (ts_now() - DAY_IN_SECONDS * 365 * 2) * 1000
        ):
            # simulate an error on Bybit if we query a period of time that is older than the
            # maximum allowed in the API
            raise RemoteError(f'Invalid startTime provided: {options["startTime"]}')

        return next(iterators.get(path, iter([{}])))

    return _mock_authenticated_query


def test_query_balances(bybit_exchange: Bybit):
    balance_response = {'list': [
        {
            'accountIMRate': '',
            'accountLTV': '',
            'accountMMRate': '',
            'accountType': 'UNIFIED',
            'coin': [{
                'accruedInterest': '0',
                'availableToBorrow': '',
                'availableToWithdraw': '0.07681',
                'bonus': '0',
                'borrowAmount': '0',
                'coin': 'USDC',
                'collateralSwitch': True,
                'cumRealisedPnl': '0',
                'equity': '19.07681',
                'locked': '19',
                'marginCollateral': True,
                'spotHedgingQty': '0',
                'totalOrderIM': '0',
                'totalPositionIM': '0',
                'totalPositionMM': '0',
                'unrealisedPnl': '0',
                'usdValue': '19.07584719',
                'walletBalance': '19.07681',
            }, {
                'accruedInterest': '0',
                'availableToBorrow': '',
                'availableToWithdraw': '0.0025',
                'bonus': '0',
                'borrowAmount': '0',
                'coin': 'ETH',
                'collateralSwitch': True,
                'cumRealisedPnl': '0',
                'equity': '0.0025',
                'locked': '0',
                'marginCollateral': True,
                'spotHedgingQty': '0',
                'totalOrderIM': '0',
                'totalPositionIM': '0',
                'totalPositionMM': '0',
                'unrealisedPnl': '0',
                'usdValue': '5.55038468',
                'walletBalance': '0.0025',
            }, {
                'accruedInterest': '0',
                'availableToBorrow': '',
                'availableToWithdraw': '0.119',
                'bonus': '0',
                'borrowAmount': '0',
                'coin': 'SOL',
                'collateralSwitch': True,
                'cumRealisedPnl': '0',
                'equity': '0.119',
                'locked': '0',
                'marginCollateral': True,
                'spotHedgingQty': '0',
                'totalOrderIM': '0',
                'totalPositionIM': '0',
                'totalPositionMM': '0',
                'unrealisedPnl': '0',
                'usdValue': '8.22967611',
                'walletBalance': '0.119',
            }, {'accruedInterest': '0',
                'availableToBorrow': '',
                'availableToWithdraw': '20',
                'bonus': '0',
                'borrowAmount': '0',
                'coin': 'MATIC',
                'collateralSwitch': True,
                'cumRealisedPnl': '0',
                'equity': '20',
                'locked': '0',
                'marginCollateral': True,
                'spotHedgingQty': '0',
                'totalOrderIM': '0',
                'totalPositionIM': '0',
                'totalPositionMM': '0',
                'unrealisedPnl': '0',
                'usdValue': '16.77825124',
                'walletBalance': '20',
                },
            ],
            'totalAvailableBalance': '',
            'totalEquity': '49.63415922',
            'totalInitialMargin': '',
            'totalMaintenanceMargin': '',
            'totalMarginBalance': '',
            'totalPerpUPL': '0',
            'totalWalletBalance': '49.63415922',
        },
    ]}

    funding_balance_response = {
        'balance': [
            {'coin': 'BTC', 'transferBalance': '0', 'walletBalance': '0', 'bonus': ''},
            {'coin': 'MNT', 'transferBalance': '0', 'walletBalance': '0', 'bonus': ''},
            {'coin': 'EUR', 'transferBalance': '0', 'walletBalance': '0', 'bonus': ''},
            {'coin': 'XRP', 'transferBalance': '2', 'walletBalance': '2', 'bonus': ''},
            {'coin': 'ETH', 'transferBalance': '1', 'walletBalance': '1', 'bonus': ''},
            {'coin': 'USDT', 'transferBalance': '0', 'walletBalance': '0', 'bonus': ''},
            {'coin': 'USDC', 'transferBalance': '0.05', 'walletBalance': '0.05', 'bonus': ''},
        ],
    }

    mock_fn = bybit_account_mock(
        is_unified=True,
        calls={
            'account/wallet-balance': [balance_response],
            'asset/transfer/query-account-coins-balance': [funding_balance_response],
        },
    )
    with patch.object(bybit_exchange, '_api_query', side_effect=mock_fn):
        assert bybit_exchange.query_balances()[0] == {
            A_SOL: Balance(amount=FVal('0.119'), usd_value=FVal('8.22967611')),
            Asset('eip155:1/erc20:0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'): Balance(amount=FVal('20'), usd_value=FVal('16.77825124')),  # noqa: E501
            A_ETH: Balance(amount=FVal('1.0025'), usd_value=FVal('7.05038468')),  # 1 from funding + 0.0025 from unified account  # noqa: E501
            A_USDC: Balance(amount=FVal('19.12681'), usd_value=FVal('19.15084719')),
            Asset('XRP'): Balance(amount=FVal(2), usd_value=FVal(3)),  # only in funding
        }


@pytest.mark.freeze_time('2023-12-15 10:45:45 GMT')
def test_trades(bybit_exchange: Bybit) -> None:
    mock_fn = bybit_account_mock(is_unified=True, calls={
        'order/history': [
            json.loads('{"nextPageCursor":"1573377285745286144%3A1702297188428%2C1573376610655280128%3A1702297107951","category":"spot","list":[{"symbol":"SOLUSDC","orderType":"Limit","orderLinkId":"1702297","orderId":"1573377285745286144","cancelType":"UNKNOWN","avgPrice":"69.71","stopOrderType":"","lastPriceOnCreated":"","orderStatus":"Filled","takeProfit":"0","cumExecValue":"8.29549","smpType":"None","triggerDirection":0,"blockTradeId":"","rejectReason":"EC_NoError","isLeverage":"0","price":"69.71","orderIv":"","createdTime":"1702297188428","tpTriggerBy":"","positionIdx":0,"timeInForce":"GTC","leavesValue":"0.00000","updatedTime":"1702297236826","side":"Buy","smpGroup":0,"triggerPrice":"0.00","cumExecFee":"0","slTriggerBy":"","leavesQty":"0.000","closeOnTrigger":false,"placeType":"","cumExecQty":"0.119","reduceOnly":false,"qty":"0.119","stopLoss":"0","smpOrderId":"","triggerBy":""},{"symbol":"SOLUSDC","orderType":"Limit","orderLinkId":"1702297166844","orderId":"1573377106254240768","cancelType":"CancelByUser","avgPrice":"","stopOrderType":"","lastPriceOnCreated":"","orderStatus":"Cancelled","takeProfit":"0","cumExecValue":"0.00000","smpType":"None","triggerDirection":0,"blockTradeId":"","rejectReason":"EC_PerCancelRequest","isLeverage":"0","price":"69.76","orderIv":"","createdTime":"1702297167031","tpTriggerBy":"","positionIdx":0,"timeInForce":"GTC","leavesValue":"0","updatedTime":"1702297176364","side":"Buy","smpGroup":0,"triggerPrice":"0.00","cumExecFee":"0","slTriggerBy":"","leavesQty":"0","closeOnTrigger":false,"placeType":"","cumExecQty":"0.000","reduceOnly":false,"qty":"0.120","stopLoss":"0","smpOrderId":"","triggerBy":""},{"symbol":"MATICUSDC","orderType":"Limit","orderLinkId":"1702297","orderId":"1573376610655280128","cancelType":"UNKNOWN","avgPrice":"0.8736","stopOrderType":"","lastPriceOnCreated":"","orderStatus":"Filled","takeProfit":"0","cumExecValue":"17.472000","smpType":"None","triggerDirection":0,"blockTradeId":"","rejectReason":"EC_NoError","isLeverage":"0","price":"0.8741","orderIv":"","createdTime":"1702297107951","tpTriggerBy":"","positionIdx":0,"timeInForce":"GTC","leavesValue":"0.010000","updatedTime":"1702297107954","side":"Buy","smpGroup":0,"triggerPrice":"0.0000","cumExecFee":"0","slTriggerBy":"","leavesQty":"0.00","closeOnTrigger":false,"placeType":"","cumExecQty":"20.00","reduceOnly":false,"qty":"20.00","stopLoss":"0","smpOrderId":"","triggerBy":""}]}'),
            json.loads('{"nextPageCursor":"","category":"spot","list":[]}'),
            json.loads('{"nextPageCursor":"1564184955935005696%3A1701201377324%2C1564184955935005696%3A1701201377324","category":"spot","list":[{"symbol":"ETHUSDC","orderType":"Limit","orderLinkId":"17012013","orderId":"1564184955935005696","cancelType":"UNKNOWN","avgPrice":"2062.28","stopOrderType":"","lastPriceOnCreated":"","orderStatus":"Filled","takeProfit":"0","cumExecValue":"5.1557000","smpType":"None","triggerDirection":0,"blockTradeId":"","rejectReason":"EC_NoError","isLeverage":"0","price":"2062.93","orderIv":"","createdTime":"1701201377324","tpTriggerBy":"","positionIdx":0,"timeInForce":"GTC","leavesValue":"0.0016250","updatedTime":"1701201377325","side":"Buy","smpGroup":0,"triggerPrice":"0.00","cumExecFee":"0","slTriggerBy":"","leavesQty":"0.00000","closeOnTrigger":false,"placeType":"","cumExecQty":"0.00250","reduceOnly":false,"qty":"0.00250","stopLoss":"0","smpOrderId":"","triggerBy":""}]}'),
        ] + [json.loads('{"nextPageCursor":"","category":"spot","list":[]}')] * 52,
    })

    with patch.object(bybit_exchange, '_api_query', side_effect=mock_fn):
        trades, _ = bybit_exchange.query_online_trade_history(
            start_ts=Timestamp(ts_now() - DAY_IN_SECONDS * 365),
            end_ts=ts_now(),
        )

    assert trades == [
        Trade(
            timestamp=Timestamp(1702297236),
            location=Location.BYBIT,
            base_asset=A_SOL,
            quote_asset=A_USDC,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.119')),
            rate=Price(FVal('69.71')),
            fee=Fee(ZERO),
            fee_currency=None,
            link='1702297',
        ), Trade(
            timestamp=Timestamp(1702297107),
            location=Location.BYBIT,
            base_asset=Asset('eip155:1/erc20:0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'),
            quote_asset=A_USDC,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('20')),
            rate=Price(FVal('0.8741')),
            fee=Fee(ZERO),
            fee_currency=None,
            link='1702297',
        ), Trade(
            timestamp=Timestamp(1701201377),
            location=Location.BYBIT,
            base_asset=A_ETH,
            quote_asset=A_USDC,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.00250')),
            rate=Price(FVal('2062.93')),
            fee=Fee(ZERO),
            fee_currency=None,
            link='17012013',
        ),
    ]


def test_deposit_withdrawals(bybit_exchange: Bybit) -> None:
    """Test that withdrawals and deposits get correctly processed"""
    mock_fn = bybit_account_mock(is_unified=True, calls={
        'asset/deposit/query-record': [
            json.loads('{"rows":[{"coin":"USDC","chain":"OP.E","amount":"79.993947","txID":"0xe9bce05f14cb35eeb762ed5ce109ab4676ed1459480f6196c82060c4e0c63b27","status":3,"toAddress":"0x6f8a9d0210ea4ac4808d8fa15368fc330f12dd0c","tag":"","depositFee":"","successAt":"1701200911000","confirmations":"34","txIndex":"4","blockHash":"0xa44d2adc02e19cb38486f3ea86857fb54011d70f404ea4671ee3c0a64ca256d8","batchReleaseLimit":"100000","depositType":"0"},{"coin":"USDC","chain":"OP.E","amount":"20","txID":"0xc2433faf5938e4be896127a15815952e99b41412b8aa0fbe239ce24c8bc435ab","status":3,"toAddress":"0x6f8a9d0210ea4ac4808d8fa15368fc330f12dd0c","tag":"","depositFee":"","successAt":"1701200780000","confirmations":"34","txIndex":"6","blockHash":"0x0d3fee0a9110924848d4be9e25a96582c8276c02ba30c38f90f0c70012d60fbd","batchReleaseLimit":"100000","depositType":"0"}],"nextPageCursor":"eyJtaW5JRCI6MzQ4Nzg4MzUsIm1heElEIjozNDg3OTAzM30="}'),
        ],
        'asset/withdraw/query-record': [
            json.loads('{"rows":[{"coin":"ETH","chain":"ARBI","amount":"0.0024","txID":"0xce631ee0a52326d16cea9a2f666f02be55ebbf9f93641d42a488c3c1fc2ebc8c","status":"success","toAddress":"0xDeEB02ADA5B089F851f2A1C0301d46631514D312","tag":"","withdrawFee":"0.0001","createTime":"1702628620000","updateTime":"1702628676000","withdrawId":"29848227","withdrawType":0}],"nextPageCursor":"eyJtaW5JRCI6Mjk4NDgyMjcsIm1heElEIjoyOTg0ODIyN30="}'),
        ],
    })
    with patch.object(bybit_exchange, '_api_query', side_effect=mock_fn):
        movements = bybit_exchange.query_online_history_events(
            start_ts=Timestamp(1701200010),
            end_ts=Timestamp(1701300880),
        )

    assert movements == [
        AssetMovement(
            timestamp=TimestampMS(1701200911000),
            location=Location.BYBIT,
            location_label=bybit_exchange.name,
            event_type=HistoryEventType.DEPOSIT,
            asset=A_USDC,
            balance=Balance(FVal('79.993947')),
            unique_id='0xe9bce05f14cb35eeb762ed5ce109ab4676ed1459480f6196c82060c4e0c63b27',
            extra_data={'transaction_id': '0xe9bce05f14cb35eeb762ed5ce109ab4676ed1459480f6196c82060c4e0c63b27'},  # noqa: E501
        ), AssetMovement(
            timestamp=TimestampMS(1701200780000),
            location=Location.BYBIT,
            location_label=bybit_exchange.name,
            event_type=HistoryEventType.DEPOSIT,
            asset=A_USDC,
            balance=Balance(FVal('20')),
            unique_id='0xc2433faf5938e4be896127a15815952e99b41412b8aa0fbe239ce24c8bc435ab',
            extra_data={'transaction_id': '0xc2433faf5938e4be896127a15815952e99b41412b8aa0fbe239ce24c8bc435ab'},  # noqa: E501
        ),
    ]


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='Cannot connect to server due to cloudflare blocking the github server',
)
def test_assets_are_known(bybit_exchange: Bybit):
    tickers = bybit_exchange._api_query(
        path='market/tickers',
        options={'category': 'spot'},
    )

    for ticker in tickers['list']:
        try:
            bybit_symbol_to_base_quote(
                symbol=ticker['symbol'],
                five_letter_assets=bybit_exchange.five_letter_assets,
                six_letter_assets=bybit_exchange.six_letter_assets,
            )
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.identifier} in Bybit. '
                f'Support for it has to be added',
            ))
        except UnprocessableTradePair:
            test_warnings.warn(UserWarning(f'Found bybit pair that cannot be processed {ticker["symbol"]}'))  # noqa: E501


def test_query_old_trades(bybit_exchange: Bybit) -> None:
    """Check that we don't exceed the range that can be queried in bybit for trades"""
    mock_fn = bybit_account_mock(is_unified=True, calls={
        'order/history': [json.loads('{"nextPageCursor":"","category":"spot","list":[]}')] * 2,
    })

    with patch.object(bybit_exchange, '_api_query', side_effect=mock_fn):
        bybit_exchange.query_online_trade_history(
            start_ts=Timestamp(ts_now() - DAY_IN_SECONDS * 365 * 3),
            end_ts=Timestamp(ts_now() - DAY_IN_SECONDS * 365 - DAY_IN_SECONDS * 360),
        )  # remoteError is raised if we don't properly query the logic
