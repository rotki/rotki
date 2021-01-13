from typing import Any, Dict, NamedTuple
from unittest.mock import MagicMock

import pytest

from rotkehlchen.chain.substrate.typing import BlockNumber, SubstrateChain
from rotkehlchen.constants.assets import A_KSM
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.substrate import attempt_connect_test_nodes

KSM_ADDRESS_1 = 'GLVeryFRbg5hEKvQZcAnLvXZEXhiYaBjzSDwrXBXrfPF7wj'
KSM_ADDRESS_2 = 'FRb4hMAhvVjuztKtvNgjEbK863MR3tGSWB9a2EhKem6AygK'
DOT_ADDRESS_1 = '1gXKQA8JDTjetR759QGGXX98siY4AvaCdp35bswUiuGormc'


class AccountInfo(NamedTuple):
    value: Dict[str, Any]


@pytest.fixture(scope='session', name='kusama_available_node_attributes_map')
def fixture_kusama_available_node_attributes_map():
    """Attempt to connect to Kusama nodes and return the available nodes map.
    The connection will persist along the session.
    """
    available_node_attributes_map = attempt_connect_test_nodes(SubstrateChain.KUSAMA)
    return available_node_attributes_map


def test_get_account_balance_invalid_account(kusama_manager):
    """Test querying KSM balance with invalid address adds the specific error
    in `msg_aggregator` but also that the request is done for each available
    node. RemoteError is raised by `request_available_nodes()`.
    """
    with pytest.raises(RemoteError) as e:
        kusama_manager.get_account_balance(DOT_ADDRESS_1)

    errors = kusama_manager.msg_aggregator.consume_errors()
    user_error_msg = (
        f'Got remote error while querying Kusama KSM balance for account {DOT_ADDRESS_1}'
    )
    account_balance_errors = [error for error in errors if error.startswith(user_error_msg)]
    for error in account_balance_errors:
        assert 'Invalid Address type' in error

    assert 'Kusama request failed after trying the following nodes' in str(e.value)


def test_get_account_balance(kusama_manager):
    balance = kusama_manager.get_account_balance(KSM_ADDRESS_1)
    assert balance >= ZERO


def test_get_accounts_balance_invalid_account(kusama_manager):
    """Test querying KSM balances with an invalid address adds the specific error
    in `msg_aggregator` but also that the request is done for each available
    node. RemoteError is raised by `request_available_nodes()`.
    """
    with pytest.raises(RemoteError) as e:
        kusama_manager.get_accounts_balance([KSM_ADDRESS_1, DOT_ADDRESS_1])

    errors = kusama_manager.msg_aggregator.consume_errors()
    user_error_msg = (
        f'Got remote error while querying Kusama KSM balance for account {DOT_ADDRESS_1}'
    )
    account_balance_errors = [error for error in errors if error.startswith(user_error_msg)]
    for error in account_balance_errors:
        assert 'Invalid Address type' in error

    assert 'Kusama request failed after trying the following nodes' in str(e.value)


def test_get_accounts_balance(kusama_manager):
    account_balance = kusama_manager.get_accounts_balance([KSM_ADDRESS_1, KSM_ADDRESS_2])
    assert account_balance[KSM_ADDRESS_1] >= ZERO
    assert account_balance[KSM_ADDRESS_2] >= ZERO


def test_get_chain_id(kusama_manager):
    chain_id = kusama_manager.get_chain_id()
    assert chain_id == str(SubstrateChain.KUSAMA)


def test_get_chain_properties(kusama_manager):
    chain_properties = kusama_manager.get_chain_properties()
    assert chain_properties.ss58_format == 2
    assert chain_properties.token == A_KSM
    assert chain_properties.token_decimals == FVal(12)


def test_get_last_block(kusama_manager):
    last_block = kusama_manager.get_last_block()
    assert last_block > BlockNumber(5740274)


def test_get_account_balance_calculation(kusama_manager):
    """Test `_get_account_balance()` balance calculation sums 'free' and 'reserved'
    amounts and amends the decimals using the native token decimals.
    """
    mock_node_interface = MagicMock()
    mock_node_interface.url.return_value = 'https://whatever.com'
    mock_node_interface.query.return_value = AccountInfo(
        value={
            'nonce': 617,
            'refcount': 1,
            'data': {
                'free': 92949368426409,
                'reserved': 18055333327842,
                'miscFrozen': 50000000000000,
                'feeFrozen': 1000000000000,
            },
        },
    )
    balance = kusama_manager._get_account_balance(
        account=KSM_ADDRESS_1,
        node_interface=mock_node_interface,
    )
    assert balance == FVal(111.004701754251)  # (free + reserved)/10**12
