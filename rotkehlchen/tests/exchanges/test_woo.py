import os
import warnings as test_warnings
from json.decoder import JSONDecodeError
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_woo
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USDT, A_WOO
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.woo import API_MAX_LIMIT, Woo
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.constants import A_SOL
from rotkehlchen.types import Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_sec_to_ms


def test_name():
    exchange = Woo('woo', 'a', b'a', object(), object())
    assert exchange.location == Location.WOO
    assert exchange.name == 'woo'


@pytest.mark.xfail('CI' in os.environ, reason='WOO API sometimes fails with 403 HTML error pages')
@pytest.mark.asset_test
def test_woo_assets_are_known(mock_woo):
    request_url = f'{mock_woo.base_uri}/v1/public/token'
    try:
        response = requests.get(request_url)
    except requests.exceptions.RequestException as e:
        raise RemoteError(
            f'Woo get request at {request_url} connection error: {e!s}.',
        ) from e
    if response.status_code != 200:
        raise RemoteError(
            f'Woo query responded with error status code: {response.status_code} '
            f'and text: {response.text}',
        )
    try:
        response_list = response.json()
    except JSONDecodeError as e:
        raise RemoteError(f'Woo returned invalid JSON response: {response.text}') from e
    for row in response_list['rows']:
        try:
            asset_from_woo(row['token'])
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.identifier} in {mock_woo.name}. '
                f'Support for it has to be added',
            ))


def test_query_online_history_events_basic(mock_woo):
    """Assert that the expected arguments are passed to the `_api_query` method"""
    with patch.object(mock_woo, '_api_query') as mock_query:
        mock_woo.query_online_history_events(
            start_ts=(start_ts := Timestamp(1634600000)),
            end_ts=(end_ts := Timestamp(1634620000)),
        )
    assert mock_query.call_args_list == [call(
        endpoint='v1/asset/history',
        options={
            'end_t': (end_ts_ms := ts_sec_to_ms(end_ts)),
            'page': 1,
            'size': API_MAX_LIMIT,
            'start_t': (start_ts_ms := ts_sec_to_ms(start_ts)),
            'status': 'COMPLETED',
            'type': 'BALANCE',
        },
    ), call(
        endpoint='v1/client/hist_trades',
        options={
            'end_t': end_ts_ms,
            'fromId': 1,
            'limit': API_MAX_LIMIT,
            'start_t': start_ts_ms,
        },
    )]


def test_query_online_history_events(mock_woo):
    """Assert that the expected calls are made to the `_api_query` method
    for deposit/withdrawals and trades with multiple pages
    """
    def deposits_withdrawals_generator():
        for i, response in enumerate((
            [
                {
                    'created_time': '1579399877.041',
                    'updated_time': '1579399877.041',
                    'id': '202029292829292',
                    'external_id': '202029292829292',
                    'application_id': None,
                    'token': 'ETH',
                    'target_address': '0x31d64B3230f8baDD91dE1710A65DF536aF8f7cDa',
                    'source_address': '0x70fd25717f769c7f9a46b319f0f9103c0d887af0',
                    'confirming_threshold': 12,
                    'confirmed_number': 12,
                    'extra': '',
                    'type': 'BALANCE',
                    'token_side': 'DEPOSIT',
                    'amount': 1000,
                    'tx_id': '0x8a74c517bc104c8ebad0c3c3f64b1f302ed5f8bca598ae4459c63419038106b6',
                    'fee_token': 'ETH',
                    'fee_amount': 0,
                    'status': 'COMPLETED',
                }, {
                    'id': '23061317355600291',
                    'token': 'SOL',
                    'extra': '',
                    'amount': 12.71,
                    'status': 'COMPLETED',
                    'created_time': '1686677756.753',
                    'updated_time': '1686677950.305',
                    'external_id': '230613173800289',
                    'application_id': 'e312028a-6afd-4eac-b2b8-206f66e7e086',
                    'target_address': 'D2egh1gRCHNuDLWhdcxPVEVvmiMB6KGMKAgQm6vR1diL',
                    'source_address': '',
                    'type': 'BALANCE',
                    'token_side': 'WITHDRAW',
                    'tx_id': '4DPkJEmE3RnmDLZnM65NtFZ6L5J2R8Lwy2C1sVq7iwcPfTkjJhN5Uuh2GFsT6m13UHkeQiKjznLKK5SqK1kfTfZa',  # noqa: E501
                    'fee_token': 'SOL',
                    'fee_amount': 0.0,
                    'confirming_threshold': 1,
                    'confirmed_number': 1,
                },
            ],
            [
                {
                    'id': '23061317355600291',
                    'token': 'USDT',
                    'extra': '',
                    'amount': 12.71,
                    'status': 'COMPLETED',
                    'created_time': '1686677756.753',
                    'updated_time': '1686677950.305',
                    'external_id': '230613173800289',
                    'application_id': 'e312028a-6afd-4eac-b2b8-206f66e7e086',
                    'target_address': 'D2egh1gRCHNuDLWhdcxPVEVvmiMB6KGMKAgQm6vR1diL',
                    'source_address': '',
                    'type': 'BALANCE',
                    'token_side': 'WITHDRAW',
                    'tx_id': '4DPkJEmE3RnmDLZnM65NtFZ6L5J2R8Lwy2C1sVq7iwcPfTkjJhN5Uuh2GFsT6m13UHkeQiKjznLKK5SqK1kfTfZa',  # noqa: E501
                    'fee_token': 'USDT',
                    'fee_amount': 0.0,
                    'confirming_threshold': 1,
                    'confirmed_number': 1,
                },
            ],
        )):
            yield {
                'rows': response,
                'meta': {
                    'current_page': i + 1,
                    'records_per_page': 2,
                    'total': 3,
                },
            }

    def trades_generator():
        for response in (
            [{
                'id': 121,
                'symbol': 'SPOT_BTC_ETH',
                'order_id': 100,
                'executed_price': 48000.0,
                'executed_quantity': 1.0,
                'side': 'BUY',
                'fee': 0.1,
                'fee_asset': 'ETH',
                'executed_timestamp': '1634600000.0',
            }, {
                'id': 122,
                'symbol': 'SPOT_BTC_ETH',
                'order_id': 101,
                'executed_price': 50000.0,
                'executed_quantity': 1.0,
                'side': 'BUY',
                'fee': 0.1,
                'fee_asset': 'ETH',
                'executed_timestamp': '1634610000.0',
            }],
            [],
        ):
            yield {'data': response}

    limit_patch = patch(
        'rotkehlchen.exchanges.woo.API_MAX_LIMIT',
        new_callable=MagicMock(return_value=2),
    )
    deposits_withdrawals_response = deposits_withdrawals_generator()
    trades_response = trades_generator()
    api_query_patch = patch.object(
        mock_woo,
        '_api_query',
        side_effect=lambda endpoint, options: (
            next(trades_response)
            if 'hist_trades' in endpoint else
            next(deposits_withdrawals_response)
        ),
    )
    with limit_patch, api_query_patch as mock_query:
        mock_woo.query_online_history_events(
            start_ts=(start_ts := Timestamp(1634600000)),
            end_ts=(end_ts := Timestamp(1634620000)),
        )

    assert mock_query.call_args_list == [
        call(
            endpoint='v1/asset/history',
            options={
                'end_t': (end_ts_ms := ts_sec_to_ms(end_ts)),
                'page': 1,
                'size': 2,
                'start_t': (start_ts_ms := ts_sec_to_ms(start_ts)),
                'status': 'COMPLETED',
                'type': 'BALANCE',
            },
        ), call(
            endpoint='v1/asset/history',
            options={
                'end_t': end_ts_ms,
                'page': 2,
                'size': 2,
                'start_t': start_ts_ms,
                'status': 'COMPLETED',
                'type': 'BALANCE',
            },
        ), call(
            endpoint='v1/client/hist_trades',
            options={
                'end_t': end_ts_ms,
                'fromId': 1,
                'limit': 2,
                'start_t': start_ts_ms,
            },
        ), call(
            endpoint='v1/client/hist_trades',
            options={
                'end_t': end_ts_ms,
                'fromId': 122,
                'limit': 2,
                'start_t': start_ts_ms,
            },
        )]


def test_query_balances(mock_woo):
    balances_response = {
        'success': 'true',
        'data': {
            'holding': [
                {
                    'token': 'WOO',
                    'holding': 1,
                    'frozen': 0,
                    'staked': 0,
                    'unbonding': 0,
                    'vault': 0,
                    'interest': 0,
                    'pendingShortQty': 0,
                    'pendingLongQty': 0,
                    'availableBalance': 0,
                    'averageOpenPrice': 0.23432,
                    'markPrice': 0.25177,
                    'updatedTime': 312321.121,
                },
                {
                    'token': 'ETH',
                    'holding': 2,
                    'frozen': 0,
                    'staked': 0,
                    'unbonding': 0,
                    'vault': 0,
                    'interest': 0,
                    'pendingShortQty': 0,
                    'pendingLongQty': 0,
                    'availableBalance': 0,
                    'averageOpenPrice': 0.23432,
                    'markPrice': 0.25177,
                    'updatedTime': 31321.121,
                },
                {
                    'token': 'BTC',
                    'holding': 0,
                    'frozen': 0,
                    'staked': 0,
                    'unbonding': 0,
                    'vault': 0,
                    'interest': 0,
                    'pendingShortQty': 0,
                    'pendingLongQty': 0,
                    'availableBalance': 0,
                    'averageOpenPrice': 0.23432,
                    'markPrice': 0.25177,
                    'updatedTime': 31321.121,
                },
            ],
        },
    }

    with patch.object(mock_woo, '_api_query', side_effect=lambda _: balances_response):
        assert mock_woo.query_balances()[0] == {
            A_WOO: Balance(
                amount=FVal('1'),
                usd_value=FVal('1.5'),
            ),
            A_ETH: Balance(
                amount=FVal('2'),
                usd_value=FVal('3'),
            ),
        }


def test_deserialize_trade_buy(mock_woo: Woo):
    assert mock_woo._deserialize_trade(trade={
        'id': 1,
        'symbol': 'SPOT_BTC_ETH',
        'order_id': 101,
        'executed_price': 50000.0,
        'executed_quantity': 1.0,
        'side': 'BUY',
        'fee': 0.1,
        'fee_asset': 'ETH',
        'executed_timestamp': '1634600000.0',
    }) == [SwapEvent(
        timestamp=(timestamp := TimestampMS(1634600000000)),
        location=Location.WOO,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal('50000.00'),
        location_label=mock_woo.name,
        event_identifier=(event_identifier := '4e59a50777b6eddb1a916539d7151fd47c489b0badc8488a01a5f835e52844c8'),  # noqa: E501
    ), SwapEvent(
        timestamp=timestamp,
        location=Location.WOO,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('1.0'),
        location_label=mock_woo.name,
        event_identifier=event_identifier,
    ), SwapEvent(
        timestamp=timestamp,
        location=Location.WOO,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.1'),
        location_label=mock_woo.name,
        event_identifier=event_identifier,
    )]


def test_deserialize_trade_sell(mock_woo):
    assert mock_woo._deserialize_trade(
        trade={
        'id': 2,
        'symbol': 'SPOT_ETH_USDT',
        'order_id': 102,
        'executed_price': 3000.0,
        'executed_quantity': 2.0,
        'side': 'SELL',
        'fee': 0.2,
        'fee_asset': 'USDT',
        'executed_timestamp': '1634610000.0',
    }) == [SwapEvent(
        timestamp=(timestamp := TimestampMS(1634610000000)),
        location=Location.WOO,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal('2.0'),
        location_label=mock_woo.name,
        event_identifier=(event_identifier := '98e48230961b7e3427b04a4264bcbee3eede633906d549202b946d26e6538f7f'),  # noqa: E501
    ), SwapEvent(
        timestamp=timestamp,
        location=Location.WOO,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        amount=FVal('6000.00'),
        location_label=mock_woo.name,
        event_identifier=event_identifier,
    ), SwapEvent(
        timestamp=timestamp,
        location=Location.WOO,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDT,
        amount=FVal('0.2'),
        location_label=mock_woo.name,
        event_identifier=event_identifier,
    )]


def test_deserialize_asset_movement_deposit(mock_woo: 'Woo') -> None:
    mock_deposit = {
        'created_time': '1579399877.041',
        'updated_time': '1579399877.041',
        'id': '202029292829292',
        'external_id': '202029292829292',
        'application_id': None,
        'token': 'ETH',
        'target_address': '0x31d64B3230f8baDD91dE1710A65DF536aF8f7cDa',
        'source_address': '0x70fd25717f769c7f9a46b319f0f9103c0d887af0',
        'confirming_threshold': 12,
        'confirmed_number': 12,
        'extra': '',
        'type': 'BALANCE',
        'token_side': 'DEPOSIT',
        'amount': 1000,
        'tx_id': '0x8a74c517bc104c8ebad0c3c3f64b1f302ed5f8bca598ae4459c63419038106b6',
        'fee_token': 'ETH',
        'fee_amount': 0,
        'status': 'COMPLETED',
    }
    result = mock_woo._deserialize_asset_movement(mock_deposit)
    assert result == [AssetMovement(
        location=Location.WOO,
        location_label=mock_woo.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1579399877000),
        asset=A_ETH,
        amount=FVal(1000),
        unique_id='202029292829292',
        extra_data={
            'address': '0x70fd25717f769c7f9a46b319f0f9103c0d887af0',
            'transaction_id': '0x8a74c517bc104c8ebad0c3c3f64b1f302ed5f8bca598ae4459c63419038106b6',
        },
    )]


def test_deserialize_asset_movement_withdrawal(mock_woo: 'Woo') -> None:
    mock_withdrawal = {
        'id': '23061317355600291',
        'token': 'SOL',
        'extra': '',
        'amount': 12.71,
        'status': 'COMPLETED',
        'created_time': '1686677756.753',
        'updated_time': '1686677950.305',
        'external_id': '230613173800289',
        'application_id': 'e312028a-6afd-4eac-b2b8-206f66e7e086',
        'target_address': 'D2egh1gRCHNuDLWhdcxPVEVvmiMB6KGMKAgQm6vR1diL',
        'source_address': '',
        'type': 'BALANCE',
        'token_side': 'WITHDRAW',
        'tx_id': '4DPkJEmE3RnmDLZnM65NtFZ6L5J2R8Lwy2C1sVq7iwcPfTkjJhN5Uuh2GFsT6m13UHkeQiKjznLKK5SqK1kfTfZa',  # noqa: E501
        'fee_token': 'SOL',
        'fee_amount': 0.0,
        'confirming_threshold': 1,
        'confirmed_number': 1,
    }
    result = mock_woo._deserialize_asset_movement(mock_withdrawal)
    assert result == [AssetMovement(
        location=Location.WOO,
        location_label=mock_woo.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1686677756000),
        asset=A_SOL,
        amount=FVal(12.71),
        unique_id='23061317355600291',
        extra_data={
            'address': 'D2egh1gRCHNuDLWhdcxPVEVvmiMB6KGMKAgQm6vR1diL',
            'transaction_id': '4DPkJEmE3RnmDLZnM65NtFZ6L5J2R8Lwy2C1sVq7iwcPfTkjJhN5Uuh2GFsT6m13UHkeQiKjznLKK5SqK1kfTfZa',  # noqa: E501
        },
    )]
