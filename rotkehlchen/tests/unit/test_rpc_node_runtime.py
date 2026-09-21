"""Tests for RPC node runtime state, cooldown, and configured-node cache."""
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from threading import Event
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.chain.mixins.rpc_nodes import (
    RPCManagerMixin,
    RPCNode,
    _is_rate_limit_error,
    _normalize_endpoint,
)
from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain, Timestamp


class _ConcreteManager(RPCManagerMixin):
    """Concrete subclass that provides the required abstract methods."""
    blockchain = SupportedBlockchain.ETHEREUM
    chain_name = 'ethereum'
    rpc_timeout = 10

    def __init__(self, nodes: list[WeightedNode]) -> None:
        super().__init__()
        self.database = MagicMock()
        self.database.get_rpc_nodes.return_value = nodes
        self._configured_nodes_cache = nodes  # pre-warm to avoid DB calls

    def attempt_connect(self, node: NodeName, connectivity_check: bool = True) -> tuple[bool, str]:
        return True, ''


def _make_node(name: str, endpoint: str, owned: bool = False) -> NodeName:
    return NodeName(
        name=name,
        endpoint=endpoint,
        owned=owned,
        blockchain=SupportedBlockchain.ETHEREUM,
    )


def _make_weighted_node(
        name: str,
        endpoint: str,
        weight: float = 0.5,
        owned: bool = False,
) -> WeightedNode:
    return WeightedNode(
        node_info=_make_node(name, endpoint, owned=owned),
        active=True,
        weight=FVal(weight),
        identifier=1,
    )


def _make_manager(nodes: list[WeightedNode]) -> _ConcreteManager:
    return _ConcreteManager(nodes)


@pytest.mark.parametrize(
    ('endpoint', 'normalized'),
    [
        ('https://RPC.Example.COM/', 'https://rpc.example.com'),
        ('https://rpc.example.com:443', 'https://rpc.example.com'),
        ('http://rpc.example.com:80', 'http://rpc.example.com'),
        ('https://rpc.example.com:8545', 'https://rpc.example.com:8545'),
        ('localhost:8545', 'http://localhost:8545'),
    ],
)
def test_normalize_endpoint(endpoint: str, normalized: str) -> None:
    assert _normalize_endpoint(endpoint) == normalized


@pytest.mark.parametrize(
    ('error', 'expected'),
    [
        pytest.param(Exception('rate limit exceeded'), True, id='message-rate-limit'),
        pytest.param(Exception('too many requests'), True, id='message-too-many-requests'),
        pytest.param(Exception('HTTP Error 429'), True, id='message-429'),
        pytest.param(Exception('connection refused'), False, id='message-not-rate-limit'),
    ],
)
def test_is_rate_limit_error_messages(error: Exception, expected: bool) -> None:
    assert _is_rate_limit_error(error) is expected


@pytest.mark.parametrize(
    ('status_code', 'expected'),
    [
        (429, True),
        (403, True),
        (500, False),
    ],
)
def test_is_rate_limit_error_http_status(status_code: int, expected: bool) -> None:
    import requests as req

    resp = MagicMock()
    resp.status_code = status_code
    assert _is_rate_limit_error(req.exceptions.HTTPError(response=resp)) is expected


def test_mark_node_success_clears_cooldown() -> None:
    node = _make_node('test', 'https://rpc.example.com')
    manager = _make_manager([])
    manager.mark_node_rate_limited(node, 'rate limit')
    assert manager.is_node_in_cooldown(node) is True

    manager.mark_node_success(node)
    assert manager.is_node_in_cooldown(node) is False
    state = manager.get_runtime_state(node)
    assert state is not None
    assert state.status == 'ready'
    assert state.consecutive_failures == 0
    assert state.cooldown_until is None


def test_mark_node_rate_limited_sets_cooldown() -> None:
    node = _make_node('test', 'https://rpc.example.com')
    manager = _make_manager([])
    manager.mark_node_rate_limited(node, '429')
    assert manager.is_node_in_cooldown(node) is True
    state = manager.get_runtime_state(node)
    assert state is not None
    assert state.status == 'cooling_down'
    assert state.last_error_kind == 'rate_limited'
    assert state.cooldown_until is not None


def test_cooldown_expires_transitions_to_ready() -> None:
    node = _make_node('test', 'https://rpc.example.com')
    manager = _make_manager([])
    manager.mark_node_rate_limited(node, '429')

    state = manager.get_runtime_state(node)
    assert state is not None
    state.cooldown_until = Timestamp(int(time.time()) - 1)

    assert manager.is_node_in_cooldown(node) is False
    assert state.status == 'ready'
    assert state.cooldown_until is None


def test_mark_node_failure_preserves_ready_status() -> None:
    node = _make_node('test', 'https://rpc.example.com')
    manager = _make_manager([])
    manager.mark_node_failure(node, 'connection error')
    state = manager.get_runtime_state(node)
    assert state is not None
    assert state.status == 'ready'
    assert state.consecutive_failures == 1
    assert state.last_error_kind == 'failure'


def test_consecutive_failures_accumulate() -> None:
    node = _make_node('test', 'https://rpc.example.com')
    manager = _make_manager([])
    for _ in range(3):
        manager.mark_node_failure(node, 'error')
    assert manager.get_runtime_state(node).consecutive_failures == 3  # type: ignore[union-attr]


def test_mark_node_success_resets_consecutive_failures() -> None:
    node = _make_node('test', 'https://rpc.example.com')
    manager = _make_manager([])
    manager.mark_node_failure(node, 'err')
    manager.mark_node_failure(node, 'err')
    manager.mark_node_success(node)
    assert manager.get_runtime_state(node).consecutive_failures == 0  # type: ignore[union-attr]


def test_get_runtime_state_returns_none_for_unknown_node() -> None:
    node = _make_node('unknown', 'https://new.example.com')
    manager = _make_manager([])
    assert manager.get_runtime_state(node) is None
    assert manager.is_node_in_cooldown(node) is False


def test_clear_runtime_state_removes_entry() -> None:
    node = _make_node('test', 'https://rpc.example.com')
    manager = _make_manager([])
    manager.mark_node_rate_limited(node, '429')
    assert manager.get_runtime_state(node) is not None
    manager.clear_runtime_state(node)
    assert manager.get_runtime_state(node) is None
    assert manager.is_node_in_cooldown(node) is False


def test_cooldown_shared_across_endpoint_aliases() -> None:
    """Two nodes with different names but same endpoint share cooldown state."""
    node_a = _make_node('flashbots', 'https://rpc.flashbots.net/')
    node_b = _make_node('Flashbots', 'https://rpc.flashbots.net')
    manager = _make_manager([])
    manager.mark_node_rate_limited(node_a, '429')
    assert manager.is_node_in_cooldown(node_b) is True


def test_success_on_alias_clears_cooldown_for_other() -> None:
    node_a = _make_node('a', 'https://rpc.example.com/')
    node_b = _make_node('b', 'https://rpc.example.com')
    manager = _make_manager([])
    manager.mark_node_rate_limited(node_a, '429')
    manager.mark_node_success(node_b)
    assert manager.is_node_in_cooldown(node_a) is False


def test_configured_nodes_cache_avoids_db_on_repeated_calls() -> None:
    node = _make_weighted_node('test', 'https://rpc.example.com')
    manager = _make_manager([node])
    db_mock = MagicMock()
    manager.database = db_mock

    manager._get_configured_nodes()
    manager._get_configured_nodes()
    manager._get_configured_nodes()

    db_mock.get_rpc_nodes.assert_not_called()


def test_configured_nodes_cache_invalidation_forces_db_reload() -> None:
    node = _make_weighted_node('test', 'https://rpc.example.com')
    manager = _make_manager([node])
    db_mock = MagicMock()
    db_mock.get_rpc_nodes.return_value = [node]
    manager.database = db_mock
    manager.blockchain = SupportedBlockchain.ETHEREUM

    manager.invalidate_nodes_cache()
    manager._get_configured_nodes()

    db_mock.get_rpc_nodes.assert_called_once()


def test_configured_nodes_cache_loads_from_db_when_empty() -> None:
    manager = _make_manager([])
    manager._configured_nodes_cache = None
    db_mock = MagicMock()
    db_mock.get_rpc_nodes.return_value = []
    manager.database = db_mock
    manager.blockchain = SupportedBlockchain.ETHEREUM

    result = manager._get_configured_nodes()
    assert result == []
    db_mock.get_rpc_nodes.assert_called_once_with(
        blockchain=SupportedBlockchain.ETHEREUM,
        only_active=True,
    )


def test_default_call_order_excludes_cooling_node() -> None:
    nodes = [
        _make_weighted_node('good', 'https://good.example.com', weight=0.5),
        _make_weighted_node('bad', 'https://bad.example.com', weight=0.5),
    ]
    manager = _make_manager(nodes)
    bad_node = _make_node('bad', 'https://bad.example.com')
    manager.mark_node_rate_limited(bad_node, '429')

    for _ in range(20):  # repeat to rule out random false negatives
        order = manager.default_call_order()
        names = [w.node_info.name for w in order]
        assert 'bad' not in names
        assert 'good' in names


def test_default_call_order_expired_cooldown_node_returns() -> None:
    nodes = [
        _make_weighted_node('good', 'https://good.example.com', weight=0.5),
        _make_weighted_node('bad', 'https://bad.example.com', weight=0.5),
    ]
    manager = _make_manager(nodes)
    bad_node = _make_node('bad', 'https://bad.example.com')
    manager.mark_node_rate_limited(bad_node, '429')

    state = manager.get_runtime_state(bad_node)
    assert state is not None
    state.cooldown_until = Timestamp(int(time.time()) - 1)

    names_seen: set[str] = set()
    for _ in range(20):
        names_seen.update(w.node_info.name for w in manager.default_call_order())
    assert 'bad' in names_seen


def test_default_call_order_owned_node_comes_first() -> None:
    nodes = [
        _make_weighted_node('mynode', 'https://mine.example.com', weight=1.0, owned=True),
        _make_weighted_node('public', 'https://pub.example.com', weight=1.0),
    ]
    manager = _make_manager(nodes)

    for _ in range(10):
        assert manager.default_call_order()[0].node_info.name == 'mynode'


def test_default_call_order_excludes_cooling_owned_node() -> None:
    nodes = [
        _make_weighted_node('mynode', 'https://mine.example.com', weight=1.0, owned=True),
        _make_weighted_node('public', 'https://pub.example.com', weight=1.0),
    ]
    manager = _make_manager(nodes)
    manager.mark_node_rate_limited(
        _make_node('mynode', 'https://mine.example.com', owned=True),
        '429',
    )

    for _ in range(10):
        names = [w.node_info.name for w in manager.default_call_order()]
        assert 'mynode' not in names
        assert names == ['public']


def test_maybe_connect_to_nodes_refreshes_stale_configured_nodes_cache() -> None:
    stale_node = _make_weighted_node('stale', 'https://stale.example.com', weight=1.0)
    fresh_node = _make_weighted_node('fresh', 'https://fresh.example.com', weight=1.0)
    manager = _make_manager([stale_node])
    manager._configured_nodes_cache = [stale_node]

    db_mock = MagicMock()
    db_mock.get_rpc_nodes.return_value = [fresh_node]
    db_mock.get_blockchain_accounts.return_value = {SupportedBlockchain.ETHEREUM: []}
    ctx_mock = MagicMock()
    ctx_mock.__enter__.return_value = MagicMock()
    ctx_mock.__exit__.return_value = None
    db_mock.conn.read_ctx.return_value = ctx_mock
    manager.database = db_mock

    manager.task_supervisor = MagicMock()
    manager.task_supervisor.has_task.return_value = False

    with patch.object(manager, 'connect_to_multiple_nodes') as mock_connect:
        manager.maybe_connect_to_nodes(when_tracked_accounts=False)
        mock_connect.assert_called_once_with([fresh_node])


def _load_nodes_before_refresh(
        loaded: Event,
        release: Event,
        nodes: list[WeightedNode],
        **kwargs: object,
) -> list[WeightedNode]:
    loaded.set()
    assert release.wait(timeout=5)
    return nodes


def test_refresh_waits_for_inflight_cache_load() -> None:
    old_nodes = [_make_weighted_node('provider', 'https://old.example.com')]
    new_nodes = [_make_weighted_node('provider', 'https://new.example.com')]
    manager = _make_manager(old_nodes)
    manager.invalidate_nodes_cache()
    loaded, release = Event(), Event()
    with (
        ThreadPoolExecutor(max_workers=2) as executor,
        patch.object(manager.database, 'get_rpc_nodes', side_effect=partial(
            _load_nodes_before_refresh, loaded, release, old_nodes,
        )),
    ):
        reader = executor.submit(manager._get_configured_nodes)
        assert loaded.wait(timeout=5)
        refresh = executor.submit(
            manager.refresh_nodes,
            added={new_nodes[0].node_info},
            removed={old_nodes[0].node_info},
        )
        with pytest.raises(TimeoutError):
            refresh.result(timeout=0.1)
        release.set()
        reader.result(timeout=5)
        refresh.result(timeout=5)
    with patch.object(manager.database, 'get_rpc_nodes', return_value=new_nodes):
        assert manager._get_configured_nodes() == new_nodes


def test_refresh_allows_explicitly_readded_node() -> None:
    node = _make_node('provider', 'https://rpc.example.com')
    manager = _make_manager([])
    manager.refresh_nodes(added=set(), removed={node})
    manager.mark_node_failure(node, 'old request failed')
    assert manager.get_runtime_state(node) is None
    manager.refresh_nodes(added={node}, removed=set())
    assert node not in manager._removed_nodes
    manager.mark_node_success(node)
    assert manager.get_runtime_state(node) is not None


def _refresh_during_capability_check(
        inquirer: SolanaInquirer,
        old_node: NodeName,
        replacement: NodeName,
) -> bool:
    inquirer.refresh_nodes(added={replacement}, removed={old_node})
    return False


@pytest.mark.parametrize('capability', ['is_archive', 'supports_program_accounts'])
def test_solana_refresh_during_capability_check(capability: str) -> None:
    """An old query must not publish capabilities for a same-name replacement."""
    inquirer = SolanaInquirer(MagicMock(), MagicMock(), MagicMock())
    old = _make_node('provider', 'https://old.example.com')
    replacement = _make_node('provider', 'https://new.example.com')
    rpc = MagicMock()
    setattr(type(rpc), capability, PropertyMock(side_effect=partial(
        _refresh_during_capability_check, inquirer, old, replacement,
    )))
    inquirer.rpc_mapping[old] = rpc
    with pytest.raises(RemoteError):
        inquirer.query(
            method=MagicMock(),
            call_order=[WeightedNode(node_info=old, active=True, weight=FVal(1))],
            only_archive_nodes=capability == 'is_archive',
            only_program_accounts_nodes=capability == 'supports_program_accounts',
        )
    assert old.name not in inquirer.known_node_capabilities
    inquirer.rpc_mapping[replacement] = RPCNode(
        rpc_client=MagicMock(), is_archive=True, is_pruned=False,
        supports_program_accounts=True,
    )
    assert inquirer.query(
        method=MagicMock(return_value=123),
        call_order=[WeightedNode(node_info=replacement, active=True, weight=FVal(1))],
        only_archive_nodes=True, only_program_accounts_nodes=True,
    ) == 123


def _pause_backoff_transition(entered: Event, release: Event, message: str, *args: object) -> None:
    if 'backoff end time is in the future' in message:
        entered.set()
        assert release.wait(timeout=5)


def test_solana_refresh_waits_for_backoff_transition() -> None:
    """Refresh cannot clear backoff between its pop and reinsertion."""
    inquirer = SolanaInquirer(MagicMock(), MagicMock(), MagicMock())
    old = _make_node('provider', 'https://old.example.com')
    healthy = _make_node('healthy', 'https://healthy.example.com')
    replacement = _make_node('provider', 'https://new.example.com')
    inquirer.node_backoff_info[old.name] = (Timestamp(int(time.time()) + 1000), 1, 8)
    inquirer.rpc_mapping[healthy] = RPCNode(
        rpc_client=MagicMock(), is_archive=True, is_pruned=False,
    )
    entered, release = Event(), Event()
    with (
        ThreadPoolExecutor(max_workers=2) as executor,
        patch('rotkehlchen.chain.solana.node_inquirer.log.debug', side_effect=partial(
            _pause_backoff_transition, entered, release,
        )),
    ):
        query = executor.submit(
            inquirer.query, method=MagicMock(return_value=123),
            call_order=[WeightedNode(node_info=node, active=True, weight=FVal(1))
                        for node in (old, healthy)],
        )
        assert entered.wait(timeout=5)
        refresh = executor.submit(inquirer.refresh_nodes, {replacement}, {old})
        try:
            with pytest.raises(TimeoutError):
                refresh.result(timeout=0.1)
        finally:
            release.set()
        assert query.result(timeout=5) == 123
        refresh.result(timeout=5)
    assert old.name not in inquirer.node_backoff_info


class _PausedBackoff(dict):  # noqa: FURB189  # Probe the concrete dict boundary used by the inquirer.
    """Pause after retry membership is checked, before the deadline is indexed."""

    def __init__(self, name: str, entered: Event, release: Event) -> None:
        super().__init__({name: (Timestamp(int(time.time()) + 1000), 1, 8)})
        self.entered = entered
        self.release = release

    def __contains__(self, key: object) -> bool:
        present = super().__contains__(key)
        self.entered.set()
        assert self.release.wait(timeout=5)
        return present


def _wait_for_refresh(finished: Event, seconds: float) -> None:
    assert finished.wait(timeout=5)


def test_solana_refresh_waits_for_retry_snapshot() -> None:
    """Refresh cannot clear a retry entry between membership and deadline lookup."""
    inquirer = SolanaInquirer(MagicMock(), MagicMock(), MagicMock())
    old = _make_node('provider', 'https://old.example.com')
    entered, release, finished = Event(), Event(), Event()
    inquirer.node_backoff_info = _PausedBackoff(old.name, entered, release)
    with (
        ThreadPoolExecutor(max_workers=2) as executor,
        patch('rotkehlchen.chain.solana.node_inquirer.cancellable_sleep', side_effect=partial(
            _wait_for_refresh, finished,
        )),
    ):
        query = executor.submit(
            inquirer.query, method=MagicMock(),
            call_order=[WeightedNode(node_info=old, active=True, weight=FVal(1))],
        )
        assert entered.wait(timeout=5)
        refresh = executor.submit(inquirer.refresh_nodes, set(), {old})
        try:
            with pytest.raises(TimeoutError):
                refresh.result(timeout=0.1)
        finally:
            release.set()
        refresh.result(timeout=5)
        finished.set()
        with pytest.raises(RemoteError):
            query.result(timeout=5)
