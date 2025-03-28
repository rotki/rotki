import warnings as test_warnings
from collections.abc import Generator
from contextlib import ExitStack
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_kucoin
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_LINK, A_USDT
from rotkehlchen.constants.timing import WEEK_IN_SECONDS
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.data_structures import Trade, TradeType
from rotkehlchen.exchanges.kucoin import KUCOIN_LAUNCH_TS, Kucoin, KucoinCase
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.tests.utils.constants import A_BSV, A_KCS, A_NANO
from rotkehlchen.tests.utils.exchanges import get_exchange_asset_symbols
from rotkehlchen.tests.utils.globaldb import is_asset_symbol_unsupported
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import AssetAmount, Fee, Location, Price, Timestamp, TimestampMS
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.inquirer import Inquirer


def test_name():
    exchange = Kucoin(
        name='kucoin1',
        api_key='a',
        secret=b'a',
        database=object(),
        msg_aggregator=object(),
        passphrase='a',
    )
    assert exchange.location == Location.KUCOIN
    assert exchange.name == 'kucoin1'


def test_kucoin_exchange_assets_are_known(mock_kucoin, globaldb):
    request_url = f'{mock_kucoin.base_uri}/api/v1/currencies'
    try:
        response = requests.get(request_url)
    except requests.exceptions.RequestException as e:
        raise RemoteError(
            f'Kucoin get request at {request_url} connection error: {e!s}.',
        ) from e

    if response.status_code != HTTPStatus.OK:
        raise RemoteError(
            f'Kucoin query responded with error status code: {response.status_code} '
            f'and text: {response.text}',
        )
    try:
        response_dict = jsonloads_dict(response.text)
    except JSONDecodeError as e:
        raise RemoteError(f'Kucoin returned invalid JSON response: {response.text}') from e

    for asset in get_exchange_asset_symbols(Location.KUCOIN):
        assert is_asset_symbol_unsupported(globaldb, Location.KUCOIN, asset) is False, f'Kucoin assets {asset} should not be unsupported'  # noqa: E501

    for entry in response_dict['data']:
        symbol = entry['currency']
        try:
            asset_from_kucoin(symbol)
        except UnsupportedAsset:
            assert is_asset_symbol_unsupported(globaldb, Location.KUCOIN, symbol)
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.identifier} with symbol {symbol} in kucoin. '
                f'Support for it has to be added',
            ))


def test_api_query_retries_request(mock_kucoin):

    def get_response():
        results = [
            """{"code":400007,"msg":"unknown error"}""",
            """{"code":400007,"msg":"unknown error"}""",
        ]
        yield from results

    def mock_api_query_response(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.TOO_MANY_REQUESTS, next(get_response))

    get_response = get_response()
    api_request_retry_times_patch = patch(
        target='rotkehlchen.exchanges.kucoin.API_REQUEST_RETRY_TIMES',
        new=1,
    )
    api_request_retry_after_seconds_patch = patch(
        target='rotkehlchen.exchanges.kucoin.API_REQUEST_RETRIES_AFTER_SECONDS',
        new=0,
    )
    api_query_patch = patch.object(
        target=mock_kucoin.session,
        attribute='get',
        side_effect=mock_api_query_response,
    )
    with ExitStack() as stack:
        stack.enter_context(api_request_retry_times_patch)
        stack.enter_context(api_request_retry_after_seconds_patch)
        stack.enter_context(api_query_patch)
        result = mock_kucoin._api_query(
            options={
                'currentPage': 1,
                'pageSize': 500,
                'tradeType': 'TRADE',
                'startAt': 1504224000000,
            },
            case=KucoinCase.TRADES,
        )

    assert result.status_code == HTTPStatus.TOO_MANY_REQUESTS
    errors = mock_kucoin.msg_aggregator.consume_errors()
    assert len(errors) == 1
    expected_error = (
        'Got remote error while querying kucoin trades: Kucoin trades request '
        'failed after retrying 1 times.'
    )
    assert errors[0] == expected_error


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_deserialize_accounts_balances(mock_kucoin, inquirer):  # pylint: disable=unused-argument
    accounts_data = [
        {
            'id': '601ac6f7d48f8000063ab2da',
            'currency': 'UNEXISTINGSYMBOL',
            'type': 'main',
            'balance': '999',
            'available': '999',
            'holds': '0',
        },
        {
            'id': '601ac6f7d48f8000063ab2db',
            'currency': 'BCHSV',
            'type': 'main',
            'balance': '1',
            'available': '1',
            'holds': '0',
        },
        {
            'id': '601ac6f7d48f8000063ab2de',
            'currency': 'BTC',
            'type': 'main',
            'balance': '2.52',
            'available': '2.52',
            'holds': '0',
        },
        {
            'id': '601ac6f7d48f8000063ab2e7',
            'currency': 'ETH',
            'type': 'main',
            'balance': '47.33',
            'available': '47.33',
            'holds': '0',
        },
        {
            'id': '601ac6f7d48f8000063ab2e1',
            'currency': 'USDT',
            'type': 'main',
            'balance': '34500',
            'available': '34500',
            'holds': '0',
        },
        {
            'id': '60228f81d48f8000060cec67',
            'currency': 'USDT',
            'type': 'margin',
            'balance': '10000',
            'available': '10000',
            'holds': '0',
        },
        {
            'id': '601acdb7d48f8000063c6d4a',
            'currency': 'BTC',
            'type': 'trade',
            'balance': '0.09018067',
            'available': '0.09018067',
            'holds': '0',
        },
        {
            'id': '601acdc5d48f8000063c70b3',
            'currency': 'USDT',
            'type': 'trade',
            'balance': '597.26244755',
            'available': '597.26244755',
            'holds': '0',
        },
        {
            'id': '601da9fad48f8000063960cc',
            'currency': 'KCS',
            'type': 'trade',
            'balance': '0.2',
            'available': '0.2',
            'holds': '0',
        },
        {
            'id': '601da9ddd48f80000639553f',
            'currency': 'ETH',
            'type': 'trade',
            'balance': '0.10934995',
            'available': '0.10934995',
            'holds': '0',
        },
    ]
    assets_balance = mock_kucoin._deserialize_accounts_balances({'data': accounts_data})
    assert assets_balance == {
        A_BTC: Balance(
            amount=FVal('2.61018067'),
            usd_value=FVal('3.915271005'),
        ),
        A_ETH: Balance(
            amount=FVal('47.43934995'),
            usd_value=FVal('71.159024925'),
        ),
        A_KCS: Balance(
            amount=FVal('0.2'),
            usd_value=FVal('0.30'),
        ),
        A_USDT: Balance(
            amount=FVal('45097.26244755'),
            usd_value=FVal('67645.893671325'),
        ),
        A_BSV: Balance(
            amount=FVal('1'),
            usd_value=FVal('1.5'),
        ),
    }


def test_deserialize_v2_trade_buy(mock_kucoin):
    raw_result = {
        'symbol': 'KCS-USDT',
        'tradeId': '601da9faf1297d0007efd712',
        'orderId': '601da9fa0c92050006bd83be',
        'counterOrderId': '601bad620c9205000642300f',
        'side': 'buy',
        'liquidity': 'taker',
        'forceTaker': True,
        'price': 1000,
        'size': '0.2',
        'funds': 200,
        'fee': '0.14',
        'feeRate': '0.0007',
        'feeCurrency': 'USDT',
        'stop': '',
        'tradeType': 'TRADE',
        'type': 'market',
        'createdAt': 1612556794259,
    }
    expected_trade = Trade(
        timestamp=Timestamp(1612556794),
        location=Location.KUCOIN,
        base_asset=A_KCS,
        quote_asset=A_USDT,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.2')),
        rate=Price(FVal('1000')),
        fee=Fee(FVal('0.14')),
        fee_currency=A_USDT,
        link='601da9faf1297d0007efd712',
        notes='',
    )
    trade = mock_kucoin._deserialize_trade(
        raw_result=raw_result,
        case=KucoinCase.TRADES,
    )
    assert trade == expected_trade


def test_deserialize_v2_trade_sell(mock_kucoin):
    raw_result = {
        'symbol': 'BCHSV-USDT',
        'tradeId': '601da995e0ee8b00063a075c',
        'orderId': '601da9950c92050006bd45c5',
        'counterOrderId': '601da9950c92050006bd457d',
        'side': 'sell',
        'liquidity': 'taker',
        'forceTaker': True,
        'price': '37624.4',
        'size': '0.0013',
        'funds': '48.91172',
        'fee': '0.034238204',
        'feeRate': '0.0007',
        'feeCurrency': 'USDT',
        'stop': '',
        'tradeType': 'TRADE',
        'type': 'market',
        'createdAt': 1612556794259,
    }
    expected_trade = Trade(
        timestamp=Timestamp(1612556794),
        location=Location.KUCOIN,
        base_asset=A_BSV,
        quote_asset=A_USDT,
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal('0.0013')),
        rate=Price(FVal('37624.4')),
        fee=Fee(FVal('0.034238204')),
        fee_currency=A_USDT,
        link='601da995e0ee8b00063a075c',
        notes='',
    )
    trade = mock_kucoin._deserialize_trade(
        raw_result=raw_result,
        case=KucoinCase.TRADES,
    )
    assert trade == expected_trade


def test_deserialize_v1_trade(mock_kucoin):
    raw_result = {
        'id': 'xxxx',
        'symbol': 'NANO-ETH',
        'dealPrice': '0.015743',
        'dealValue': '0.00003441',
        'amount': '0.002186',
        'fee': '0.00000003',
        'side': 'sell',
        'createdAt': 1520471876,
    }
    expected_trade = Trade(
        timestamp=Timestamp(1520471876),
        location=Location.KUCOIN,
        base_asset=A_NANO,
        quote_asset=A_ETH,
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal('0.002186')),
        rate=Price(FVal('0.015743')),
        fee=Fee(FVal('0.00000003')),
        fee_currency=A_ETH,
        link='xxxx',
        notes='',
    )
    trade = mock_kucoin._deserialize_trade(
        raw_result=raw_result,
        case=KucoinCase.OLD_TRADES,
    )
    assert trade == expected_trade


def test_deserialize_asset_movement_deposit(mock_kucoin: 'Kucoin') -> None:
    raw_result = {
        'address': '0x5bedb060b8eb8d823e2414d82acce78d38be7fe9',
        'memo': '',
        'currency': 'ETH',
        'amount': 1,
        'fee': 0.01,
        'walletTxId': '3e2414d82acce78d38be7fe9',
        'isInner': False,
        'status': 'SUCCESS',
        'remark': 'test',
        'createdAt': 1612556794259,
        'updatedAt': 1612556795000,
    }
    expected_asset_movement = [AssetMovement(
        timestamp=TimestampMS(1612556794259),
        location=Location.KUCOIN,
        location_label=mock_kucoin.name,
        event_type=HistoryEventType.DEPOSIT,
        asset=A_ETH,
        amount=ONE,
        unique_id='3e2414d82acce78d38be7fe9',
        extra_data={
            'address': '0x5bedb060b8eb8d823e2414d82acce78d38be7fe9',
            'transaction_id': '3e2414d82acce78d38be7fe9',
        },
    ), AssetMovement(
        timestamp=TimestampMS(1612556794259),
        location=Location.KUCOIN,
        location_label=mock_kucoin.name,
        event_type=HistoryEventType.DEPOSIT,
        asset=A_ETH,
        amount=FVal('0.01'),
        unique_id='3e2414d82acce78d38be7fe9',
        is_fee=True,
    )]
    asset_movement = mock_kucoin._deserialize_asset_movement(
        raw_result=raw_result,
        case=KucoinCase.DEPOSITS,
    )
    assert asset_movement == expected_asset_movement


def test_deserialize_asset_movement_withdrawal(mock_kucoin: 'Kucoin') -> None:
    raw_result = {
        'id': '5c2dc64e03aa675aa263f1ac',
        'address': '0x5bedb060b8eb8d823e2414d82acce78d38be7fe9',
        'memo': '',
        'currency': 'ETH',
        'amount': 1,
        'fee': 0.01,
        'walletTxId': '3e2414d82acce78d38be7fe9',
        'isInner': False,
        'status': 'SUCCESS',
        'remark': 'test',
        'createdAt': 1612556794259,
        'updatedAt': 1612556795000,
    }
    expected_asset_movement = [AssetMovement(
        timestamp=TimestampMS(1612556794259),
        location=Location.KUCOIN,
        location_label=mock_kucoin.name,
        event_type=HistoryEventType.WITHDRAWAL,
        asset=A_ETH,
        amount=ONE,
        unique_id='5c2dc64e03aa675aa263f1ac',
        extra_data={
            'address': '0x5bedb060b8eb8d823e2414d82acce78d38be7fe9',
            'transaction_id': '3e2414d82acce78d38be7fe9',
        },
    ), AssetMovement(
        timestamp=TimestampMS(1612556794259),
        location=Location.KUCOIN,
        location_label=mock_kucoin.name,
        event_type=HistoryEventType.WITHDRAWAL,
        asset=A_ETH,
        amount=FVal('0.01'),
        unique_id='5c2dc64e03aa675aa263f1ac',
        is_fee=True,
    )]
    asset_movement = mock_kucoin._deserialize_asset_movement(
        raw_result=raw_result,
        case=KucoinCase.WITHDRAWALS,
    )
    assert asset_movement == expected_asset_movement


@pytest.mark.skip('Fails with status code: 404 and text: KC-API-KEY not exists')
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_balances_sandbox(sandbox_kucoin, inquirer):  # pylint: disable=unused-argument
    assets_balance, msg = sandbox_kucoin.query_balances()
    assert assets_balance == {
        A_BTC: Balance(
            amount=FVal('2.61018067'),
            usd_value=FVal('3.915271005'),
        ),
        A_ETH: Balance(
            amount=FVal('47.43934995'),
            usd_value=FVal('71.159024925'),
        ),
        A_KCS: Balance(
            amount=FVal('0.2'),
            usd_value=FVal('0.30'),
        ),
        A_USDT: Balance(
            amount=FVal('45097.26244755'),
            usd_value=FVal('67645.893671325'),
        ),
    }
    assert msg == ''


@pytest.mark.skip('Fails with status code: 404 and text: KC-API-KEY not exists')
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_trades_sandbox(sandbox_kucoin, inquirer):  # pylint: disable=unused-argument
    """The sandbox account has 6 trades. Below a list of the trades and their
    timestamps in ascending mode.
    - trade 1: 1612556651 -> skipped
    - trade 2: 1612556693
    - trade 3: 1612556765
    - trade 4: 1612556765
    - trade 5: 1612556765
    - trade 6: 1612556794 -> skipped

    By requesting trades from 1612556693 to 1612556765, the first and last trade
    should be skipped.
    """
    expected_trades = [
        Trade(
            timestamp=Timestamp(1612556765),
            location=Location.KUCOIN,
            base_asset=A_ETH,
            quote_asset=A_BTC,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.02934995')),
            rate=Price(FVal('0.046058')),
            fee=Fee(FVal('9.4625999797E-7')),
            fee_currency=A_BTC,
            link='601da9ddf73c300006194ec6',
            notes='',
        ),
        Trade(
            timestamp=Timestamp(1612556765),
            location=Location.KUCOIN,
            base_asset=A_ETH,
            quote_asset=A_BTC,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.02')),
            rate=Price(FVal('0.04561')),
            fee=Fee(FVal('6.3854E-7')),
            fee_currency=A_BTC,
            link='601da9ddf73c300006194ec5',
            notes='',
        ),
        Trade(
            timestamp=Timestamp(1612556765),
            location=Location.KUCOIN,
            base_asset=A_ETH,
            quote_asset=A_BTC,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal('0.06')),
            rate=Price(FVal('0.0456')),
            fee=Fee(FVal('0.0000019152')),
            fee_currency=A_BTC,
            link='601da9ddf73c300006194ec4',
            notes='',
        ),
        Trade(
            timestamp=Timestamp(1612556693),
            location=Location.KUCOIN,
            base_asset=A_BTC,
            quote_asset=A_USDT,
            trade_type=TradeType.SELL,
            amount=AssetAmount(FVal('0.0013')),
            rate=Price(FVal('37624.4')),
            fee=Fee(FVal('0.034238204')),
            fee_currency=A_USDT,
            link='601da995e0ee8b00063a075c',
            notes='',
        ),
    ]
    trades, _ = sandbox_kucoin.query_online_trade_history(
        start_ts=Timestamp(1612556693),
        end_ts=Timestamp(1612556765),
    )
    assert trades == expected_trades


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_asset_movements_sandbox(
        sandbox_kucoin: 'Kucoin',
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Unfortunately the sandbox environment does not support deposits and
    withdrawals, therefore they must be mocked.

    Below a list of the movements and their timestamps in ascending mode:

    Deposits:
    - deposit 1 - deposit: 1612556651
    - deposit 2 - deposit: 1612556652
    - deposit 3 - deposit: 1612556653 -> skipped, inner deposit

    Withdrawals:
    - withdraw 1: 1612556651 -> skipped, inner withdraw
    - withdraw 2: 1612556652
    - withdraw 3: 1612556656 -> never requested

    By requesting trades from 1612556651 to 1612556654 and patching the time
    step as 2s (via MONTHS_IN_SECONDS) we should get back 3 movements.
    """
    deposits_response_1 = (
        """
        {
            "code":"200000",
            "data":{
                "currentPage":1,
                "pageSize":2,
                "totalNum":2,
                "totalPage":1,
                "items":[
                    {
                        "address":"0x5f047b29041bcfdbf0e4478cdfa753a336ba6989",
                        "memo":"5c247c8a03aa677cea2a251d",
                        "amount":1,
                        "fee":0.0001,
                        "currency":"KCS",
                        "isInner":false,
                        "walletTxId":"5bbb57386d99522d9f954c5a",
                        "status":"SUCCESS",
                        "remark":"movement 2 - deposit",
                        "createdAt":1612556652000,
                        "updatedAt":1612556652000
                    },
                    {
                        "address":"0x5f047b29041bcfdbf0e4478cdfa753a336ba6989",
                        "memo":"5c247c8a03aa677cea2a251d",
                        "amount":1000,
                        "fee":0.01,
                        "currency":"LINK",
                        "isInner":false,
                        "walletTxId":"5bbb57386d99522d9f954c5b@test",
                        "status":"SUCCESS",
                        "remark":"movement 1 - deposit",
                        "createdAt":1612556651000,
                        "updatedAt":1612556651000
                    }
                ]
            }
        }
        """
    )
    deposits_response_2 = (
        """
        {
            "code":"200000",
            "data":{
                "currentPage":1,
                "pageSize":1,
                "totalNum":1,
                "totalPage":1,
                "items":[
                    {
                        "address":"1DrT5xUaJ3CBZPDeFR2qdjppM6dzs4rsMt",
                        "memo":"",
                        "currency":"BCHSV",
                        "amount":1,
                        "fee":0.1,
                        "walletTxId":"b893c3ece1b8d7cacb49a39ddd759cf407817f6902f566c443ba16614874ada6",
                        "isInner":true,
                        "status":"SUCCESS",
                        "remark":"movement 4 - deposit",
                        "createdAt":1612556653000,
                        "updatedAt":1612556653000
                    }
                ]
            }
        }
        """
    )
    withdrawals_response_1 = (
        """
        {
            "code":"200000",
            "data":{
                "currentPage":1,
                "pageSize":2,
                "totalNum":2,
                "totalPage":1,
                "items":[
                    {
                        "id":"5c2dc64e03aa675aa263f1a4",
                        "address":"1DrT5xUaJ3CBZPDeFR2qdjppM6dzs4rsMt",
                        "memo":"",
                        "currency":"BCHSV",
                        "amount":2.5,
                        "fee":0.25,
                        "walletTxId":"b893c3ece1b8d7cacb49a39ddd759cf407817f6902f566c443ba16614874ada4",
                        "isInner":false,
                        "status":"SUCCESS",
                        "remark":"movement 4 - withdraw",
                        "createdAt":1612556652000,
                        "updatedAt":1612556652000
                    },
                    {
                        "id":"5c2dc64e03aa675aa263f1a3",
                        "address":"0x5bedb060b8eb8d823e2414d82acce78d38be7fe9",
                        "memo":"",
                        "currency":"ETH",
                        "amount":1,
                        "fee":0.01,
                        "walletTxId":"3e2414d82acce78d38be7fe9",
                        "isInner":true,
                        "status":"SUCCESS",
                        "remark":"movement 3 - withdraw",
                        "createdAt":1612556651000,
                        "updatedAt":1612556651000
                    }
                ]
            }
        }
        """
    )
    withdrawals_response_2 = (
        """
        {
            "code":"200000",
            "data":{
                "currentPage":0,
                "pageSize":0,
                "totalNum":0,
                "totalPage":0,
                "items":[]
            }
        }
        """
    )
    withdrawals_response_3 = (
        """
        {
            "code":"200000",
            "data":{
                "currentPage":1,
                "pageSize":1,
                "totalNum":1,
                "totalPage":1,
                "items":[
                    {
                        "id":"5c2dc64e03aa675aa263f1a5",
                        "address":"0x5bedb060b8eb8d823e2414d82acce78d38be7f00",
                        "memo":"",
                        "currency":"KCS",
                        "amount":2.5,
                        "fee":0.25,
                        "walletTxId":"b893c3ece1b8d7cacb49a39ddd759cf407817f6902f566c443ba16614874ada5",
                        "isInner":false,
                        "status":"SUCCESS",
                        "remark":"movement 5 - withdraw",
                        "createdAt":1612556655000,
                        "updatedAt":1612556655000
                    }
                ]
            }
        }
        """
    )
    expected_asset_movements = [AssetMovement(
        location=Location.KUCOIN,
        location_label=sandbox_kucoin.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1612556652000),
        asset=A_KCS,
        amount=ONE,
        unique_id='5bbb57386d99522d9f954c5a',
        extra_data={
            'address': '0x5f047b29041bcfdbf0e4478cdfa753a336ba6989',
            'transaction_id': '5bbb57386d99522d9f954c5a',
        },
    ), AssetMovement(
        location=Location.KUCOIN,
        location_label=sandbox_kucoin.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1612556652000),
        asset=A_KCS,
        amount=FVal('0.0001'),
        unique_id='5bbb57386d99522d9f954c5a',
        is_fee=True,
    ), AssetMovement(
        location=Location.KUCOIN,
        location_label=sandbox_kucoin.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1612556651000),
        asset=A_LINK,
        amount=FVal('1000'),
        unique_id='5bbb57386d99522d9f954c5b',
        extra_data={
            'address': '0x5f047b29041bcfdbf0e4478cdfa753a336ba6989',
            'transaction_id': '5bbb57386d99522d9f954c5b',
        },
    ), AssetMovement(
        location=Location.KUCOIN,
        location_label=sandbox_kucoin.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1612556651000),
        asset=A_LINK,
        amount=FVal('0.01'),
        unique_id='5bbb57386d99522d9f954c5b',
        is_fee=True,
    ), AssetMovement(
        location=Location.KUCOIN,
        location_label=sandbox_kucoin.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1612556652000),
        asset=A_BSV,
        amount=FVal('2.5'),
        unique_id='5c2dc64e03aa675aa263f1a4',
        extra_data={
            'address': '1DrT5xUaJ3CBZPDeFR2qdjppM6dzs4rsMt',
            'transaction_id': 'b893c3ece1b8d7cacb49a39ddd759cf407817f6902f566c443ba16614874ada4',
        },
    ), AssetMovement(
        location=Location.KUCOIN,
        location_label=sandbox_kucoin.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1612556652000),
        asset=A_BSV,
        amount=FVal('0.25'),
        unique_id='5c2dc64e03aa675aa263f1a4',
        is_fee=True,
    )]

    def get_endpoints_response() -> Generator[str, None, None]:
        results = [
            f'{deposits_response_1}',
            f'{deposits_response_2}',
            f'{withdrawals_response_1}',
            f'{withdrawals_response_2}',
            # if pagination works as expected and the requesting loop is broken,
            # the response below won't be processed
            f'{withdrawals_response_3}',
        ]
        yield from results

    def mock_api_query_response(case, options):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, next(get_response))

    get_response = get_endpoints_response()
    # Force a time_step of 2s
    months_in_seconds_patch = patch(
        target='rotkehlchen.exchanges.kucoin.MONTH_IN_SECONDS',
        new=2,
    )
    api_query_patch = patch.object(
        target=sandbox_kucoin,
        attribute='_api_query',
        side_effect=mock_api_query_response,
    )
    with ExitStack() as stack:
        stack.enter_context(months_in_seconds_patch)
        stack.enter_context(api_query_patch)
        asset_movements, _ = sandbox_kucoin.query_online_history_events(
            start_ts=Timestamp(1612556651),
            end_ts=Timestamp(1612556654),
        )

    assert asset_movements == expected_asset_movements


@pytest.mark.skip('Fails with Kucoin old trades JSON response is missing key: "data"')
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_old_trades_sandbox(sandbox_kucoin, inquirer):  # pylint: disable=unused-argument
    """Test that the endpoint for old trades returns valid results from the api
    in very old timestamps
    """
    trades, _ = sandbox_kucoin.query_online_trade_history(
        start_ts=Timestamp(KUCOIN_LAUNCH_TS),
        end_ts=Timestamp(KUCOIN_LAUNCH_TS + WEEK_IN_SECONDS * 4),
    )
    msg_aggregator = sandbox_kucoin.msg_aggregator
    assert len(msg_aggregator.consume_errors()) == 0
    assert len(msg_aggregator.consume_warnings()) == 0
    assert trades == []

    last_trades, _ = sandbox_kucoin.query_online_trade_history(
        start_ts=Timestamp(1651425348),
        end_ts=Timestamp(1654110961),
    )
    assert len(last_trades) == 24
