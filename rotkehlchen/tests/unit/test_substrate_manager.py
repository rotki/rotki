from typing import Any, NamedTuple
from unittest.mock import MagicMock

import pytest

from rotkehlchen.chain.substrate.manager import SubstrateManager
from rotkehlchen.chain.substrate.types import (
    BlockNumber,
    KusamaNodeName,
    NodeNameAttributes,
    PolkadotNodeName,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_KSM
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.substrate import (
    SUBSTRATE_ACC1_KSM_ADDR,
    SUBSTRATE_ACC2_KSM_ADDR,
    attempt_connect_test_nodes,
)
from rotkehlchen.types import SupportedBlockchain


class AccountInfo(NamedTuple):
    value: dict[str, Any]


@pytest.fixture(scope='module', name='kusama_available_node_attributes_map')
def fixture_kusama_available_node_attributes_map():
    """Attempt to connect to Kusama nodes and return the available nodes map.
    The connection will persist along the session.
    """
    return attempt_connect_test_nodes(SupportedBlockchain.KUSAMA)


def test_get_account_balance(kusama_manager):
    balance = kusama_manager.get_account_balance(SUBSTRATE_ACC1_KSM_ADDR)
    assert balance >= ZERO


def test_get_accounts_balance_invalid_account(kusama_manager):
    """Test querying KSM balances with an invalid address adds the specific error
    in `msg_aggregator` but also that the request is done for each available
    node. RemoteError is raised by `request_available_nodes()`.
    """
    with pytest.raises(RemoteError) as e:
        kusama_manager.get_accounts_balance([SUBSTRATE_ACC1_KSM_ADDR, '13mB8stSf1vdP7WzbVr82YPgGGF7cBK9N7KxiVEac9UQgYj8'])  # noqa: E501

    assert 'kusama request failed after trying the following nodes' in str(e.value)


def test_get_accounts_balance(kusama_manager):
    account_balance = kusama_manager.get_accounts_balance([
        SUBSTRATE_ACC1_KSM_ADDR,
        SUBSTRATE_ACC2_KSM_ADDR,
    ])
    assert account_balance[SUBSTRATE_ACC1_KSM_ADDR] >= ZERO
    assert account_balance[SUBSTRATE_ACC2_KSM_ADDR] >= ZERO


def test_get_chain_id(kusama_manager):
    chain_id = kusama_manager.get_chain_id()
    assert chain_id == 'Kusama'


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
        account=SUBSTRATE_ACC1_KSM_ADDR,
        node_interface=mock_node_interface,
    )
    assert balance == FVal(111.004701754251)  # (free + reserved)/10**12


def test_set_available_nodes_call_order(kusama_manager):
    """Test `_set_available_nodes_call_order()` sets the available nodes sorted
    by preference; currently own node first and then by the highest 'weight_block'.
    """
    # Due to `available_node_attributes_map` is a dict we must fake a key for
    # testing purposes as currently KusamaNodeName only has PARITY
    fake_kusama_node_name = object()
    node_attrs_item_1 = (
        KusamaNodeName.OWN,
        NodeNameAttributes(
            node_interface=object(),
            weight_block=1000,
        ),
    )
    node_attrs_item_2 = (
        fake_kusama_node_name,
        NodeNameAttributes(
            node_interface=object(),
            weight_block=750,
        ),
    )
    node_attrs_item_3 = (
        KusamaNodeName.PARITY,
        NodeNameAttributes(
            node_interface=object(),
            weight_block=1000,
        ),
    )
    node_attrs_items = [node_attrs_item_3, node_attrs_item_2, node_attrs_item_1]
    available_node_attributes_map = dict(node_attrs_items)
    kusama_manager.available_node_attributes_map = available_node_attributes_map
    kusama_manager._set_available_nodes_call_order()

    assert kusama_manager.available_nodes_call_order == [
        node_attrs_item_1,
        node_attrs_item_3,
        node_attrs_item_2,
    ]


@pytest.mark.parametrize(('endpoint', 'formatted_endpoint'), [
    ('', 'http://'),
    ('localhost:9933', 'http://localhost:9933'),
    ('http://localhost:9933', 'http://localhost:9933'),
])
def test_format_own_rpc_endpoint(endpoint, formatted_endpoint):
    assert formatted_endpoint == SubstrateManager._format_own_rpc_endpoint(endpoint)


def test_connect_to_own_node(polkadot_manager: 'SubstrateManager'):
    polkadot_manager.connect_at_start = [PolkadotNodeName.OWN, PolkadotNodeName.PARITY]
    polkadot_manager.own_rpc_endpoint = ''
    polkadot_manager.attempt_connections()
    assert [task.task_name for task in polkadot_manager.greenlet_manager.greenlets] == ['polkadot manager connection to parity node']  # noqa: E501
    polkadot_manager.greenlet_manager.clear()
    polkadot_manager.greenlet_manager.greenlets = []
    polkadot_manager.own_rpc_endpoint = 'http://localhost:1234'
    polkadot_manager.attempt_connections()
    assert [task.task_name for task in polkadot_manager.greenlet_manager.greenlets] == [
        'polkadot manager connection to own node',
        'polkadot manager connection to parity node',
    ]
