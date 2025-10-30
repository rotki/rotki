import uuid
from unittest.mock import patch

import pytest

from rotkehlchen.assets.converters import Asset
from rotkehlchen.constants.assets import A_ENS, A_USDC
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.exchanges.coinbaseprime import (
    Coinbaseprime,
    _process_deposit_withdrawal,
    _process_trade,
)
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import (
    HistoryEvent,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.inquirer import A_ETH, A_USD
from rotkehlchen.tests.utils.constants import A_SOL
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import FVal, Location
from rotkehlchen.utils.misc import TimestampMS, ts_now


def test_coinbase_query_balances(function_scope_coinbaseprime: Coinbaseprime):
    """Test that coinbase balance query works fine for the happy path"""

    def mock_coinbase_accounts(url, *args, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(
            200,
            """
            {
                "balances":[
                    {
                        "symbol":"ens",
                        "amount":"5000",
                        "holds":"0.00",
                        "bonded_amount":"0.00",
                        "reserved_amount":"0.00",
                        "unbonding_amount":"0.00",
                        "unvested_amount":"0.00",
                        "pending_rewards_amount":"0.00",
                        "past_rewards_amount":"0.00",
                        "bondable_amount":"0.00",
                        "withdrawable_amount":"0",
                        "fiat_amount":"0.00"
                    },
                    {
                        "symbol":"sol",
                        "amount":"0.00",
                        "holds":"0.00",
                        "bonded_amount":"150000",
                        "reserved_amount":"0.00",
                        "unbonding_amount":"0.00",
                        "unvested_amount":"0.00",
                        "pending_rewards_amount":"0.00",
                        "past_rewards_amount":"0.00",
                        "bondable_amount":"0.00",
                        "withdrawable_amount":"0",
                        "fiat_amount":"0.00"
                    },
                    {
                        "symbol":"usd",
                        "amount":"0.0082435113740889",
                        "holds":"0",
                        "bonded_amount":"0.00",
                        "reserved_amount":"0.00",
                        "unbonding_amount":"0.00",
                        "unvested_amount":"0.00",
                        "pending_rewards_amount":"0.00",
                        "past_rewards_amount":"0.00",
                        "bondable_amount":"0.00",
                        "withdrawable_amount":"0",
                        "fiat_amount":"0.00"
                    },
                    {
                        "symbol":"idonotexist",
                        "amount":"0.123",
                        "holds":"0",
                        "bonded_amount":"0.00",
                        "reserved_amount":"0.00",
                        "unbonding_amount":"0.00",
                        "unvested_amount":"0.00",
                        "pending_rewards_amount":"0.00",
                        "past_rewards_amount":"0.00",
                        "bondable_amount":"0.00",
                        "withdrawable_amount":"0",
                        "fiat_amount":"0.00"
                    }
                ]
            }
            """,
        )

    coinbase = function_scope_coinbaseprime
    with (
        patch.object(coinbase.session, 'get', side_effect=mock_coinbase_accounts),
        patch.object(coinbase, '_get_portfolio_ids', new=lambda *args, **kwargs: ['fake_id']),
        patch.object(coinbase.db.msg_aggregator, 'add_message') as mock_msg_aggregator,
    ):
        balances, msg = coinbase.query_balances()

    assert msg == ''
    assert len(balances) == 3
    assert balances[A_ENS].amount == FVal('5000')
    assert balances[A_SOL].amount == FVal('150000')
    assert balances[A_USD].amount == FVal('0.0082435113740889')
    # Confirm the missing asset ws message has a location of coinbase rather than coinbaseprime.
    assert mock_msg_aggregator.call_count == 1
    assert mock_msg_aggregator.call_args_list[0].kwargs['data'] == {'location': 'coinbase', 'name': 'coinbaseprime', 'identifier': 'IDONOTEXIST', 'details': 'balance query'}  # noqa: E501


def test_process_trade():
    user_id, portfolio_id = uuid.uuid4(), uuid.uuid4()
    assert _process_trade(trade_data={
        'average_filled_price': '2.143375433810637',
        'base_quantity': '',
        'client_order_id': uuid.uuid4(),
        'commission': '49.94',
        'created_at': '2024-10-15T13:01:39.939144Z',
        'exchange_fee': '',
        'expiry_time': None,
        'filled_quantity': '23304.3',
        'filled_value': '49950.06',
        'historical_pov': '',
        'id': (unique_id_1 := uuid.uuid4()),
        'limit_price': '',
        'net_average_filled_price': '2.1455267911930416',
        'portfolio_id': portfolio_id,
        'product_id': 'SUI-USD',
        'quote_value': '50000',
        'side': 'BUY',
        'start_time': None,
        'status': 'FILLED',
        'stop_price': '',
        'time_in_force': 'IMMEDIATE_OR_CANCEL',
        'type': 'MARKET',
        'user_id': user_id,
    }, exchange_name=(exchange_name := 'coinbaseprime1')) == [SwapEvent(
        timestamp=TimestampMS(1728997300000),
        location=Location.COINBASEPRIME,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USD,
        amount=FVal('49950.06'),
        location_label=exchange_name,
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.COINBASEPRIME,
            unique_id=str(unique_id_1),
        ),
    ), SwapEvent(
        timestamp=TimestampMS(1728997300000),
        location=Location.COINBASEPRIME,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('SUI'),
        amount=FVal('23304.3'),
        location_label=exchange_name,
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.COINBASEPRIME,
            unique_id=str(unique_id_1),
        ),
    ), SwapEvent(
        timestamp=TimestampMS(1728997300000),
        location=Location.COINBASEPRIME,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USD,
        amount=FVal('49.94'),
        location_label=exchange_name,
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.COINBASEPRIME,
            unique_id=str(unique_id_1),
        ),
    )]

    assert _process_trade(trade_data={
        'average_filled_price': '1.0123003094731783',
        'base_quantity': '247.96947',
        'client_order_id': uuid.uuid4(),
        'commission': '0.2510195712209',
        'created_at': '2023-03-25T20:49:04.516836Z',
        'exchange_fee': '',
        'expiry_time': None,
        'filled_quantity': '247.96947',
        'filled_value': '251.0195712209',
        'historical_pov': '',
        'id': (unique_id_2 := uuid.uuid4()),
        'limit_price': '1.0123',
        'net_average_filled_price': '1.0112880091637051',
        'portfolio_id': portfolio_id,
        'product_id': 'CBETH-ETH',
        'quote_value': '',
        'side': 'SELL',
        'start_time': None,
        'status': 'FILLED',
        'stop_price': '',
        'time_in_force': 'GOOD_UNTIL_CANCELLED',
        'type': 'LIMIT',
        'user_id': user_id,
    }, exchange_name=exchange_name) == [SwapEvent(
        timestamp=TimestampMS(1679777345000),
        location=Location.COINBASEPRIME,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0xBe9895146f7AF43049ca1c1AE358B0541Ea49704'),  # cbETH
        amount=FVal('251.0195712209'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.COINBASEPRIME,
            unique_id=str(unique_id_2),
        ),
        location_label=exchange_name,
    ), SwapEvent(
        timestamp=TimestampMS(1679777345000),
        location=Location.COINBASEPRIME,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal('247.96947'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.COINBASEPRIME,
            unique_id=str(unique_id_2),
        ),
        location_label=exchange_name,
    ), SwapEvent(
        timestamp=TimestampMS(1679777345000),
        location=Location.COINBASEPRIME,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.2510195712209'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.COINBASEPRIME,
            unique_id=str(unique_id_2),
        ),
        location_label=exchange_name,
    )]


def test_process_movements(function_scope_coinbaseprime: Coinbaseprime):
    """Test that the logic to process asset movements works as expected"""
    address = make_evm_address()
    tx_hash = str(make_evm_tx_hash())
    deposit = {
        'amount': '100',
        'blockchain_ids': [tx_hash],
        'completed_at': '2023-10-11T19:03:05.297Z',
        'created_at': '2023-10-11T19:00:06.927Z',
        'destination_symbol': '',
        'estimated_asset_changes': [],
        'estimated_network_fees': None,
        'fee_symbol': 'ETH',
        'fees': '0',
        'id': uuid.uuid4(),
        'idempotency_key': uuid.uuid4(),
        'metadata': None,
        'network': '',
        'network_fees': '0',
        'portfolio_id': uuid.uuid4(),
        'status': 'TRANSACTION_IMPORTED',
        'symbol': 'ETH',
        'transaction_id': 'XXXX',
        'transfer_from': {'type': 'ADDRESS', 'value': address},
        'transfer_to': {'type': 'WALLET', 'value': uuid.uuid4()},
        'type': 'DEPOSIT',
        'wallet_id': uuid.uuid4(),
    }
    deposit_movements = _process_deposit_withdrawal(
        exchange_name=function_scope_coinbaseprime.name,
        event_data=deposit,
    )
    assert len(deposit_movements) == 1
    processed_deposited = deposit_movements[0]
    assert processed_deposited.event_type == HistoryEventType.DEPOSIT
    assert processed_deposited.asset == A_ETH
    assert processed_deposited.location_label == function_scope_coinbaseprime.name
    assert processed_deposited.amount == FVal(100)
    assert processed_deposited.timestamp == 1697050985000
    assert processed_deposited.extra_data == {
        'transaction_id': tx_hash,
        'address': address,
    }

    icp_address = '0d7ab24f2293648e10d35fb78863e86d20dd7e4d85f4dfb589c709fe47000fd5'
    icp_tx_hash = '3108a11dc6a7599d6171d35c483f01d726b3e38b162894e84b0d5c2f9827b9fa'
    withdrawal = {
        'amount': '-250',
        'blockchain_ids': [icp_tx_hash],
        'completed_at': None,
        'created_at': '2024-10-12T06:14:12.857Z',
        'destination_symbol': '',
        'estimated_asset_changes': [],
        'estimated_network_fees': None,
        'fee_symbol': 'ICP',
        'fees': '0',
        'id': uuid.uuid4(),
        'idempotency_key': uuid.uuid4(),
        'metadata': None,
        'network': '',
        'network_fees': '0',
        'portfolio_id': uuid.uuid4(),
        'status': 'TRANSACTION_DONE',
        'symbol': 'ICP',
        'transaction_id': '065EF358',
        'transfer_from': {'type': 'WALLET', 'value': uuid.uuid4()},
        'transfer_to': {'type': 'ADDRESS', 'value': icp_address},
        'type': 'WITHDRAWAL',
        'wallet_id': uuid.uuid4(),
    }
    withdrawal_movements = _process_deposit_withdrawal(
        exchange_name=function_scope_coinbaseprime.name,
        event_data=withdrawal,
    )
    assert len(withdrawal_movements) == 1
    processed_withdrawal = withdrawal_movements[0]
    assert processed_withdrawal.event_type == HistoryEventType.WITHDRAWAL
    assert processed_withdrawal.asset == Asset('ICP')
    assert processed_deposited.location_label == function_scope_coinbaseprime.name
    assert processed_withdrawal.amount == FVal(250)
    assert processed_withdrawal.timestamp == 1728713653000
    assert processed_withdrawal.extra_data == {
        'transaction_id': icp_tx_hash,
        'address': icp_address,
    }


@pytest.mark.freeze_time('2024-10-31 13:50:00 GMT')
def test_history_events(function_scope_coinbaseprime: Coinbaseprime):
    """Test history events in coinbase prime. It tests conversions and staking rewards
    This test checks the logic for _query_paginated_endpoint by returning
    a mocked pagination from _api_query and the logic of query_history_events
    """
    first_id, second_id, third_id, fourth_id, fifth_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())  # noqa: E501
    movement_address = make_evm_address()
    movement_tx_hash = str(make_evm_tx_hash())
    raw_data = [{
        'amount': '50',
        'blockchain_ids': [],
        'completed_at': None,
        'created_at': '2024-07-24T20:50:19.484Z',
        'destination_symbol': 'USDC',
        'estimated_asset_changes': [],
        'estimated_network_fees': None,
        'fee_symbol': 'USD',
        'fees': '0',
        'id': first_id,
        'idempotency_key': uuid.uuid4(),
        'metadata': None,
        'network': '',
        'network_fees': '0',
        'portfolio_id': uuid.uuid4(),
        'status': 'TRANSACTION_DONE',
        'symbol': 'USD',
        'transaction_id': 'XXXXX123',
        'transfer_from': {'type': 'WALLET', 'value': uuid.uuid4()},
        'transfer_to': {'type': 'WALLET', 'value': uuid.uuid4()},
        'type': 'CONVERSION',
        'wallet_id': uuid.uuid4(),
    }, {
        'amount': '150',
        'blockchain_ids': [],
        'completed_at': '2024-08-24T20:50:21.849Z',
        'created_at': '2024-08-24T20:50:19.484Z',
        'destination_symbol': 'USD',
        'estimated_asset_changes': [],
        'estimated_network_fees': None,
        'fee_symbol': 'USDC',
        'fees': '1',
        'id': second_id,
        'idempotency_key': uuid.uuid4(),
        'metadata': None,
        'network': '',
        'network_fees': '0',
        'portfolio_id': uuid.uuid4(),
        'status': 'TRANSACTION_DONE',
        'symbol': 'USDC',
        'transaction_id': 'XXXXX124',
        'transfer_from': {'type': 'WALLET', 'value': uuid.uuid4()},
        'transfer_to': {'type': 'WALLET', 'value': uuid.uuid4()},
        'type': 'CONVERSION',
        'wallet_id': uuid.uuid4(),
    }, {
        'amount': '20',
        'blockchain_ids': [],
        'completed_at': '2024-09-24T20:50:21.849Z',
        'created_at': '2024-09-24T20:50:19.484Z',
        'destination_symbol': '',
        'estimated_asset_changes': [],
        'estimated_network_fees': None,
        'fee_symbol': 'ETH',
        'fees': '0',
        'id': third_id,
        'idempotency_key': uuid.uuid4(),
        'metadata': None,
        'network': '',
        'network_fees': '0',
        'portfolio_id': uuid.uuid4(),
        'status': 'TRANSACTION_DONE',
        'symbol': 'ETH',
        'transaction_id': 'XXXXX124',
        'transfer_from': {'type': 'WALLET', 'value': uuid.uuid4()},
        'transfer_to': {'type': 'WALLET', 'value': uuid.uuid4()},
        'type': 'REWARD',
        'wallet_id': uuid.uuid4(),
    }, {
        'amount': '100',
        'blockchain_ids': [movement_tx_hash],
        'completed_at': '2023-10-11T19:03:05.297Z',
        'created_at': '2023-10-11T19:00:06.927Z',
        'destination_symbol': '',
        'estimated_asset_changes': [],
        'estimated_network_fees': None,
        'fee_symbol': 'ETH',
        'fees': '0',
        'id': fourth_id,
        'idempotency_key': uuid.uuid4(),
        'metadata': None,
        'network': '',
        'network_fees': '0',
        'portfolio_id': uuid.uuid4(),
        'status': 'TRANSACTION_IMPORTED',
        'symbol': 'ETH',
        'transaction_id': 'XXXX',
        'transfer_from': {'type': 'ADDRESS', 'value': movement_address},
        'transfer_to': {'type': 'WALLET', 'value': uuid.uuid4()},
        'type': 'DEPOSIT',
        'wallet_id': uuid.uuid4(),
    }]
    order_entry = {
        'average_filled_price': '2.143375433810637',
        'base_quantity': '',
        'client_order_id': uuid.uuid4(),
        'commission': '49.94',
        'created_at': '2024-10-15T13:01:39.939144Z',
        'exchange_fee': '',
        'expiry_time': None,
        'filled_quantity': '23304.3',
        'filled_value': '49950.06',
        'historical_pov': '',
        'id': fifth_id,
        'limit_price': '',
        'net_average_filled_price': '2.1455267911930416',
        'portfolio_id': uuid.uuid4(),
        'product_id': 'SUI-USD',
        'quote_value': '50000',
        'side': 'BUY',
        'start_time': None,
        'status': 'FILLED',
        'stop_price': '',
        'time_in_force': 'IMMEDIATE_OR_CANCEL',
        'type': 'MARKET',
        'user_id': uuid.uuid4(),
    }

    raw_data_iter = iter(enumerate(raw_data))

    def mock_query(module, path='', params=None):
        if 'transaction' in path:
            idx, raw_entry = next(raw_data_iter)
            return {
                'transactions': [raw_entry],
                'pagination': {'has_next': idx < len(raw_data) - 1, 'next_cursor': 'any_string'},
            }
        elif 'orders' in path:
            return {
                'orders': [order_entry],
                'pagination': {'has_next': False, 'next_cursor': 'any_string'},
            }
        elif path == '':
            return {'portfolios': [{'id': uuid.uuid4()}]}

        raise AttributeError('Bad path provided')

    with patch.object(
        function_scope_coinbaseprime,
        attribute='_api_query',
        new=mock_query,
    ):
        function_scope_coinbaseprime.query_history_events()

    history_events_db = DBHistoryEvents(function_scope_coinbaseprime.db)
    with history_events_db.db.conn.read_ctx() as cursor:
        new_events = history_events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=function_scope_coinbaseprime.location),
        )

    assert new_events == [
        AssetMovement(
            identifier=7,
            timestamp=TimestampMS(1697050985000),
            location=Location.COINBASEPRIME,
            location_label=function_scope_coinbaseprime.name,
            event_type=HistoryEventType.DEPOSIT,
            asset=A_ETH,
            amount=FVal(100),
            unique_id=fourth_id,
            extra_data={
                'address': movement_address,
                'transaction_id': movement_tx_hash,
            },
        ), HistoryEvent(
            identifier=1,
            event_identifier=first_id,
            sequence_index=0,
            timestamp=TimestampMS(1721854219000),
            location=Location.COINBASEPRIME,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            amount=FVal(50),
            asset=A_USD,
            location_label=function_scope_coinbaseprime.name,
            notes='Swap 50 USD in Coinbase Prime',
        ), HistoryEvent(
            identifier=2,
            event_identifier=first_id,
            sequence_index=1,
            timestamp=TimestampMS(1721854219000),
            location=Location.COINBASEPRIME,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            amount=FVal(50),
            asset=A_USDC,
            location_label=function_scope_coinbaseprime.name,
            notes='Receive 50 USDC from a Coinbase Prime conversion',
        ), HistoryEvent(
            identifier=3,
            event_identifier=second_id,
            sequence_index=0,
            timestamp=TimestampMS(1724532622000),
            location=Location.COINBASEPRIME,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            amount=FVal(150),
            asset=A_USDC,
            location_label=function_scope_coinbaseprime.name,
            notes='Swap 150 USDC in Coinbase Prime',
        ), HistoryEvent(
            identifier=4,
            event_identifier=second_id,
            sequence_index=1,
            timestamp=TimestampMS(1724532622000),
            location=Location.COINBASEPRIME,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            amount=FVal(150),
            asset=A_USD,
            location_label=function_scope_coinbaseprime.name,
            notes='Receive 150 USD from a Coinbase Prime conversion',
        ), HistoryEvent(
            identifier=5,
            event_identifier=second_id,
            sequence_index=2,
            timestamp=TimestampMS(1724532622000),
            location=Location.COINBASEPRIME,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.FEE,
            amount=ONE,
            asset=A_USDC,
            location_label=function_scope_coinbaseprime.name,
            notes='Spend 1 USDC as Coinbase Prime conversion fee',
        ), HistoryEvent(
            identifier=6,
            event_identifier=third_id,
            sequence_index=0,
            timestamp=TimestampMS(1727211022000),
            location=Location.COINBASEPRIME,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            amount=FVal(20),
            asset=A_ETH,
            location_label=function_scope_coinbaseprime.name,
            notes='Receive 20 ETH as Coinbase Prime staking reward',
        ), SwapEvent(
            identifier=8,
            timestamp=TimestampMS(1728997300000),
            location=Location.COINBASEPRIME,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USD,
            amount=FVal('49950.06'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.COINBASEPRIME,
                unique_id=fifth_id,
            ),
            location_label=function_scope_coinbaseprime.name,
        ), SwapEvent(
            identifier=9,
            timestamp=TimestampMS(1728997300000),
            location=Location.COINBASEPRIME,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('SUI'),
            amount=FVal('23304.3'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.COINBASEPRIME,
                unique_id=fifth_id,
            ),
            location_label=function_scope_coinbaseprime.name,
        ), SwapEvent(
            identifier=10,
            timestamp=TimestampMS(1728997300000),
            location=Location.COINBASEPRIME,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USD,
            amount=FVal('49.94'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.COINBASEPRIME,
                unique_id=fifth_id,
            ),
            location_label=function_scope_coinbaseprime.name,
        ),
    ]

    with function_scope_coinbaseprime.db.conn.read_ctx() as cursor:
        cursor.execute('SELECT start_ts, end_ts FROM used_query_ranges')
        assert cursor.fetchall() == [(0, ts_now())]
