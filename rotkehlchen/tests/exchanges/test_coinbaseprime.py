import uuid
from unittest.mock import patch

from rotkehlchen.assets.converters import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ENS, A_SOL
from rotkehlchen.exchanges.coinbaseprime import (
    Coinbaseprime,
    _process_deposit_withdrawal,
    _process_trade,
)
from rotkehlchen.inquirer import A_ETH, A_USD
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import FVal


def test_coinbase_query_balances(function_scope_coinbaseprime: Coinbaseprime):
    """Test that coinbase balance query works fine for the happy path"""

    def mock_coinbase_accounts(url, *args, **kwargs):  # pylint: disable=unused-argument
        response = MockResponse(
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
                    }
                ]
            }
            """,
        )
        return response

    coinbase = function_scope_coinbaseprime
    with (
        patch.object(coinbase.session, 'get', side_effect=mock_coinbase_accounts),
        patch.object(coinbase, '_get_portfolio_ids', new=lambda *args, **kwargs: ['fake_id']),
    ):
        balances, msg = coinbase.query_balances()

    assert msg == ''
    assert len(balances) == 3
    assert balances[A_ENS].amount == FVal('5000')
    assert balances[A_SOL].amount == FVal('150000')
    assert balances[A_USD].amount == FVal('0.0082435113740889')


def test_process_trade():
    user_id, portfolio_id = uuid.uuid4(), uuid.uuid4()
    buy_trade = _process_trade(trade_data={
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
        'id': uuid.uuid4(),
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
    })
    sell_trade = _process_trade(trade_data={
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
        'id': uuid.uuid4(),
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
    })

    assert sell_trade.quote_asset == A_ETH
    assert sell_trade.base_asset == 'eip155:1/erc20:0xBe9895146f7AF43049ca1c1AE358B0541Ea49704'  # cbETH  # noqa: E501
    assert sell_trade.rate == FVal('1.0123003094731783')
    assert sell_trade.amount == FVal('251.0195712209')

    assert buy_trade.quote_asset == A_USD
    assert buy_trade.base_asset == 'SUI'
    assert buy_trade.rate == FVal('2.1455267911930416')
    assert buy_trade.fee_currency == A_USD
    assert buy_trade.fee == FVal('49.94')


def test_process_movements(function_scope_coinbaseprime: Coinbaseprime):
    """Test that the logic to process asset movements works as expected"""
    address = make_evm_address()
    tx_hash = make_evm_tx_hash()
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
    processed_deposited = _process_deposit_withdrawal(deposit)
    assert processed_deposited is not None
    assert processed_deposited.transaction_id == tx_hash
    assert processed_deposited.address == address
    assert processed_deposited.asset == A_ETH
    assert processed_deposited.amount == FVal(100)
    assert processed_deposited.timestamp == 1697050985
    assert processed_deposited.fee == ZERO

    icp_address = '0d7ab24f2293648e10d35fb78863e86d20dd7e4d85f4dfb589c709fe47000fd5'
    icp_tx_hash = '3108a11dc6a7599d6171d35c483f01d726b3e38b162894e84b0d5c2f9827b9fa'
    withdrawal = {
        'amount': '-250',
        'blockchain_ids': [icp_tx_hash],
        'completed_at': '2024-10-12T08:16:26.717Z',
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

    processed_withdrawal = _process_deposit_withdrawal(withdrawal)
    assert processed_withdrawal is not None
    assert processed_withdrawal.transaction_id == icp_tx_hash
    assert processed_withdrawal.address == icp_address
    assert processed_withdrawal.asset == Asset('ICP')
    assert processed_withdrawal.amount == FVal(250)
    assert processed_withdrawal.timestamp == 1728720987
    assert processed_withdrawal.fee == ZERO
