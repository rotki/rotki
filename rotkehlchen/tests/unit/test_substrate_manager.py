from threading import Event
from typing import Any, NamedTuple
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.chain.substrate.manager import (
    SUBSTRATE_CODEC_LOCK,
    SubstrateChainProperties,
    SubstrateManager,
)
from rotkehlchen.chain.substrate.types import (
    BlockNumber,
    KusamaNodeName,
    NodeNameAttributes,
    PolkadotNodeName,
    SubstrateAddress,
)
from rotkehlchen.concurrency import result_of, spawn
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DOT, A_KSM
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
    assert account_balance[SUBSTRATE_ACC1_KSM_ADDR] > ZERO
    assert account_balance[SUBSTRATE_ACC2_KSM_ADDR] > ZERO


def test_get_chain_id(kusama_manager):
    chain_id = kusama_manager.get_chain_id()
    assert chain_id == 'Kusama Asset Hub'


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


def test_concurrent_account_queries_are_serialized(polkadot_manager: SubstrateManager) -> None:
    """Polkadot and Kusama managers must not decode metadata concurrently."""
    first_started, release_first = Event(), Event()
    second_attempting, second_started = Event(), Event()
    first_node_interface, second_node_interface = MagicMock(), MagicMock()
    account_info = AccountInfo(value={'data': {'free': 1, 'reserved': 0}})
    kusama_manager = SubstrateManager(
        chain=SupportedBlockchain.KUSAMA,
        task_supervisor=polkadot_manager.task_supervisor,
        msg_aggregator=polkadot_manager.msg_aggregator,
        connect_at_start=(),
        connect_on_startup=False,
        own_rpc_endpoint='',
    )
    polkadot_manager.chain_properties = SubstrateChainProperties(
        ss58_format=0,
        token=A_DOT.resolve_to_crypto_asset(),
        token_decimals=10,
    )
    kusama_manager.chain_properties = SubstrateChainProperties(
        ss58_format=2,
        token=A_KSM.resolve_to_crypto_asset(),
        token_decimals=12,
    )

    def query_first(**kwargs: Any) -> AccountInfo:  # pylint: disable=unused-argument
        first_started.set()
        assert release_first.wait(timeout=5)
        return account_info

    def query_second(**kwargs: Any) -> AccountInfo:  # pylint: disable=unused-argument
        second_started.set()
        return account_info

    def get_second_balance() -> FVal:
        second_attempting.set()
        return kusama_manager._get_account_balance(
            account=SubstrateAddress(SUBSTRATE_ACC1_KSM_ADDR),
            node_interface=second_node_interface,
        )

    first_node_interface.query.side_effect = query_first
    second_node_interface.query.side_effect = query_second
    first_task = spawn(
        polkadot_manager._get_account_balance,
        account=SubstrateAddress(SUBSTRATE_ACC1_KSM_ADDR),
        node_interface=first_node_interface,
    )
    assert first_started.wait(timeout=5)
    second_task = spawn(get_second_balance)
    try:
        assert second_attempting.wait(timeout=5)
        assert second_started.wait(timeout=0.5) is False
    finally:
        release_first.set()

    assert result_of(first_task) == FVal(10 ** -10)
    assert result_of(second_task) == FVal(10 ** -12)
    assert second_started.is_set()


def test_codec_lock_wait_times_out(polkadot_manager: SubstrateManager) -> None:
    """A request waiting on a stuck codec lock holder fails with RemoteError instead of hanging,
    so the request can fall back to the next node."""
    polkadot_manager.chain_properties = SubstrateChainProperties(
        ss58_format=0,
        token=A_DOT.resolve_to_crypto_asset(),
        token_decimals=10,
    )
    assert SUBSTRATE_CODEC_LOCK.acquire(timeout=5)
    try:
        with (
            patch('rotkehlchen.chain.substrate.manager.SUBSTRATE_CODEC_LOCK_TIMEOUT', 0.1),
            patch('rotkehlchen.chain.substrate.manager.SubstrateInterface') as interface_mock,
        ):
            with pytest.raises(RemoteError, match=r'timed out .* waiting for another substrate'):
                polkadot_manager._get_account_balance(
                    account=SubstrateAddress(SUBSTRATE_ACC1_KSM_ADDR),
                    node_interface=(node_interface := MagicMock()),
                )
            with pytest.raises(RemoteError, match=r'timed out .* waiting for another substrate'):
                polkadot_manager._get_node_interface(endpoint='https://example.com')
    finally:
        SUBSTRATE_CODEC_LOCK.release()

    assert node_interface.query.call_count == 0
    assert interface_mock.call_count == 0


def test_node_initialization_waits_for_account_query(polkadot_manager: SubstrateManager) -> None:
    """Type registry initialization must not overlap metadata decoding."""
    query_started, release_query, initialization_started = Event(), Event(), Event()
    querying_node_interface, initialized_node_interface = MagicMock(), MagicMock()
    polkadot_manager.chain_properties = SubstrateChainProperties(
        ss58_format=0,
        token=A_DOT.resolve_to_crypto_asset(),
        token_decimals=10,
    )

    def query(**kwargs: Any) -> AccountInfo:  # pylint: disable=unused-argument
        query_started.set()
        assert release_query.wait(timeout=5)
        return AccountInfo(value={'data': {'free': 1, 'reserved': 0}})

    def initialize(**kwargs: Any) -> MagicMock:  # pylint: disable=unused-argument
        initialization_started.set()
        return initialized_node_interface

    querying_node_interface.query.side_effect = query
    with patch(
        'rotkehlchen.chain.substrate.manager.SubstrateInterface',
        side_effect=initialize,
    ):
        query_task = spawn(
            polkadot_manager._get_account_balance,
            account=SubstrateAddress(SUBSTRATE_ACC1_KSM_ADDR),
            node_interface=querying_node_interface,
        )
        assert query_started.wait(timeout=5)
        initialization_task = spawn(
            polkadot_manager._get_node_interface,
            endpoint='https://example.com',
        )
        try:
            assert initialization_started.wait(timeout=0.5) is False
        finally:
            release_query.set()

        assert result_of(query_task) == FVal(10 ** -10)
        assert result_of(initialization_task) is initialized_node_interface


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
        KusamaNodeName.DWELLIR,
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


def test_check_node_synchronization(polkadot_manager: SubstrateManager) -> None:
    """Test that a node is checked for synchronization against the already
    connected nodes, warning only if it lags behind them more than the threshold.
    """
    node_interface = MagicMock(url='https://lagging.node')
    with patch.object(polkadot_manager, '_get_last_block', return_value=BlockNumber(1000)):
        # no other connected nodes to compare against
        assert polkadot_manager._check_node_synchronization(node_interface) == 1000
        assert polkadot_manager.msg_aggregator.consume_warnings() == []

        polkadot_manager.available_node_attributes_map[PolkadotNodeName.DWELLIR] = NodeNameAttributes(  # noqa: E501
            node_interface=MagicMock(),
            weight_block=BlockNumber(1010),
        )  # within the threshold
        assert polkadot_manager._check_node_synchronization(node_interface) == 1000
        assert polkadot_manager.msg_aggregator.consume_warnings() == []

        polkadot_manager.available_node_attributes_map[PolkadotNodeName.ONFINALITY] = NodeNameAttributes(  # noqa: E501
            node_interface=MagicMock(),
            weight_block=BlockNumber(1011),
        )  # beyond the threshold
        assert polkadot_manager._check_node_synchronization(node_interface) == 1000
        assert polkadot_manager.msg_aggregator.consume_warnings() == [(
            'Found that polkadot node at endpoint https://lagging.node is not synced with '
            'the chain. Node last block is 1000, while other connected nodes are at block '
            '1011. Balances and other queries may be incorrect.'
        )]


@pytest.mark.parametrize(('endpoint', 'formatted_endpoint'), [
    ('', 'http://'),
    ('localhost:9933', 'http://localhost:9933'),
    ('http://localhost:9933', 'http://localhost:9933'),
])
def test_format_own_rpc_endpoint(endpoint, formatted_endpoint):
    assert formatted_endpoint == SubstrateManager._format_own_rpc_endpoint(endpoint)


def test_connect_to_own_node(polkadot_manager: SubstrateManager):
    polkadot_manager.connect_at_start = [PolkadotNodeName.OWN, PolkadotNodeName.DWELLIR]
    polkadot_manager.own_rpc_endpoint = ''
    polkadot_manager.attempt_connections()
    assert [task.task_name for task in polkadot_manager.task_supervisor.tasks] == ['polkadot manager connection to dwellir node']  # noqa: E501
    polkadot_manager.task_supervisor.clear()
    # clear() latches cancel-at-registration for teardown; lift it so the
    # connection tasks spawned below are not cancelled at birth
    polkadot_manager.task_supervisor.allow_new_tasks()
    polkadot_manager.task_supervisor.tasks = []
    polkadot_manager.own_rpc_endpoint = 'http://localhost:1234'
    polkadot_manager.attempt_connections()
    assert [task.task_name for task in polkadot_manager.task_supervisor.tasks] == [
        'polkadot manager connection to own node node',
        'polkadot manager connection to dwellir node',
    ]
