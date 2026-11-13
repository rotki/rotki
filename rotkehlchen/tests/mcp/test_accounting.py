import asyncio
import selectors
from http import HTTPStatus
from typing import Any

import pytest
from mcp import types
from mcp.shared.memory import create_connected_server_and_client_session

from rotkehlchen.mcp import accounting, analytics, server
from rotkehlchen.mcp.backend import BackendOutcome
from rotkehlchen.mcp.references import (
    UnknownReferenceError,
    get_reference_registry,
    sanitize,
)
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1

USDC = 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
TX_HASH = '0x' + 'ab' * 32
PLAN_ID = 'f' * 32
DIAGNOSIS = {
    'bucket': {
        'location': 'ethereum',
        'location_label': TEST_ADDR1,
        'protocol': None,
        'asset': USDC,
    },
    'event_identifier': 5,
    'group_identifier': f'1{TX_HASH}',
    'tx_ref': TX_HASH,
    'detail': f'Transfer to {TEST_ADDR1} failed',
    'balance_after': '-0.000000000000000001',
}


def _run(coroutine: Any) -> Any:
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()


def test_sanitize_hides_identifiers_and_hands_out_references() -> None:
    sanitized = sanitize(DIAGNOSIS, privacy_mode='balanced')
    assert TEST_ADDR1 not in str(sanitized) and TX_HASH[2:] not in str(sanitized)
    assert sanitized['bucket']['asset'] == USDC  # public token address, not the user's
    assert sanitized['event_identifier'] == 5
    assert sanitized['balance_after'] == '-0.000000000000000001'
    assert sanitized['detail'].startswith('Transfer to anon_')

    registry = get_reference_registry()
    assert registry.resolve(sanitized['group_identifier'], 'balanced') == f'1{TX_HASH}'
    assert registry.resolve(sanitized['bucket']['location_label'], 'balanced') == TEST_ADDR1
    assert registry.resolve_bucket(sanitized['bucket']['bucket_ref']) == DIAGNOSIS['bucket']
    with pytest.raises(accounting.UnknownReferenceError):
        registry.resolve('anon_0000000000000000', 'balanced')
    with pytest.raises(accounting.UnknownReferenceError):
        registry.resolve(f'1{TX_HASH}', 'balanced')  # raw values are only accepted in raw mode

    raw = sanitize(DIAGNOSIS, privacy_mode='raw')
    assert raw['bucket']['location_label'] == TEST_ADDR1
    assert raw['bucket']['bucket_ref'] == sanitized['bucket']['bucket_ref']
    assert registry.resolve(f'1{TX_HASH}', 'raw') == f'1{TX_HASH}'

    venue = {'location_label': 'kraken'}
    assert sanitize(venue, privacy_mode='balanced') == venue
    assert sanitize(venue, privacy_mode='strict')['location_label'].startswith('anon_')


def test_trace_bucket_resolves_the_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def query_backend(**kwargs: Any) -> BackendOutcome:
        calls.append(kwargs)
        return BackendOutcome(ok=True, result=DIAGNOSIS, message='', status_code=HTTPStatus.OK)

    monkeypatch.setattr(accounting, 'query_backend', query_backend)
    monkeypatch.setattr(accounting, '_privacy_mode', lambda: 'balanced')
    bucket_ref = sanitize(DIAGNOSIS, privacy_mode='balanced')['bucket']['bucket_ref']

    result = accounting.trace_bucket(bucket_ref=bucket_ref, from_timestamp=None, limit=10, offset=None)  # noqa: E501
    assert calls[0]['json_data'] == {
        'location': 'ethereum',
        'location_label': TEST_ADDR1,
        'protocol': None,
        'asset': USDC,
        'limit': 10,
    }
    assert TEST_ADDR1 not in str(result)
    assert accounting.trace_bucket(bucket_ref='bucket_nope', from_timestamp=None, limit=10, offset=None) == {  # noqa: E501
        'error': {
            'type': 'unknown_reference',
            'message': 'Unknown or expired bucket reference. Get a fresh one from a diagnosis tool',  # noqa: E501
        },
    }
    assert accounting.verify_remediation_plan('../../users')['error']['type'] == 'unknown_plan'
    assert len(calls) == 1


def test_backend_conflict_code_reaches_the_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(accounting, '_privacy_mode', lambda: 'balanced')
    monkeypatch.setattr(accounting, 'run_backend_task', lambda **kwargs: BackendOutcome(
        ok=False,
        result={'code': 'plan_stale'},
        message=f'The events of the plan changed since {TEST_ADDR1}',
        status_code=HTTPStatus.CONFLICT,
    ))
    error = accounting.apply_remediation_plan(plan_id=PLAN_ID, approved_at=1)['error']
    assert error['type'] == 'plan_stale'
    assert TEST_ADDR1 not in error['message']


@pytest.mark.parametrize('client_answer', ['approve', 'decline', 'unsupported'])
def test_apply_remediation_requires_user_approval(
        monkeypatch: pytest.MonkeyPatch,
        client_answer: str,
) -> None:
    """Only an approval the user gives in the client applies a plan; the agent has no way to
    approve it, and a client without approval prompts can't apply plans at all."""
    backend_calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def query_backend(endpoint: str, method: str = 'GET', **kwargs: Any) -> BackendOutcome:
        backend_calls.append((method, endpoint, kwargs.get('json_data')))
        return BackendOutcome(ok=True, result={
            'plan_id': PLAN_ID,
            'kind': 'redecode',
            'state': 'pending',
            'plan': {'applicable_items': 1, 'items': [{
                'status': 'ready',
                'replace_customized': True,
                'bucket_effect_diff': [{
                    'bucket': DIAGNOSIS['bucket'],
                    'current_net': '-1',
                    'proposed_net': '1',
                    'difference': '2',
                }],
            }]},
        }, message='', status_code=HTTPStatus.OK)

    def run_backend_task(endpoint: str, json_data: dict[str, Any], **kwargs: Any) -> BackendOutcome:  # noqa: E501
        backend_calls.append(('TASK', endpoint, json_data))
        return BackendOutcome(ok=True, result={'state': 'applied'}, message='', status_code=HTTPStatus.OK)  # noqa: E501

    monkeypatch.setattr(accounting, 'query_backend', query_backend)
    monkeypatch.setattr(accounting, 'run_backend_task', run_backend_task)
    monkeypatch.setattr(accounting, '_privacy_mode', lambda: 'balanced')
    monkeypatch.setattr(server, 'premium_gate', lambda: None)
    prompts: list[str] = []

    async def elicitation_callback(  # noqa: RUF029  # the client session awaits it
            context: Any,
            params: types.ElicitRequestParams,
    ) -> types.ElicitResult:
        prompts.append(params.message)
        if client_answer == 'approve':
            return types.ElicitResult(action='accept', content={'approve': True})
        return types.ElicitResult(action='decline')

    async def call() -> dict[str, Any]:
        mcp_server = server.setup_server(
            backend_url='http://backend/api/1',
            timeout=3,
            log_level='ERROR',
            privacy_mode='balanced',
        )
        async with create_connected_server_and_client_session(
            mcp_server,
            elicitation_callback=None if client_answer == 'unsupported' else elicitation_callback,
        ) as client:
            result = await client.call_tool('apply_remediation', {'plan_id': PLAN_ID})
        assert result.structuredContent is not None
        return result.structuredContent

    result = _run(call())
    applied = ('TASK', f'data_issues/remediation_plans/{PLAN_ID}/apply')
    if client_answer == 'approve':
        assert result == {'result': {'state': 'applied'}, 'privacy_mode': 'balanced'}
        assert backend_calls[-1][:2] == applied
        assert backend_calls[-1][2]['approval_method'] == 'mcp_elicitation'  # type: ignore[index]
        prompt, = prompts
        assert 'Replaces events you customized' in prompt
        assert 'net effect -1 -> 1' in prompt
        assert TEST_ADDR1 not in prompt
    elif client_answer == 'decline':
        assert result['error']['type'] == 'approval_declined'
        assert backend_calls[-1] == ('PATCH', f'data_issues/remediation_plans/{PLAN_ID}/reject', {'reason': 'user_decline'})  # noqa: E501
    else:
        assert result['error']['type'] == 'approval_unavailable'
        assert backend_calls == []
    assert all(call[:2] != applied for call in backend_calls) or client_answer == 'approve'


def test_long_running_task_can_be_checked_and_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only tasks these tools started can be polled or cancelled, and a finished task's
    result is handed out sanitized."""
    task_id = 42
    pending = BackendOutcome(
        ok=False,
        result=None,
        message='still running',
        status_code=HTTPStatus.ACCEPTED,
        pending_task_id=task_id,
    )
    monkeypatch.setattr(accounting, '_privacy_mode', lambda: 'balanced')
    monkeypatch.setattr(accounting, 'run_backend_task', lambda **kwargs: pending)
    assert accounting.apply_remediation_plan(plan_id=PLAN_ID, approved_at=1)['error'] == {
        'type': 'still_running',
        'message': 'The backend is still working on it. Check it with get_remediation_task, or '
                   'stop it with cancel_remediation_task',
        'task_id': task_id,
    }
    assert accounting.get_remediation_task(7)['error']['type'] == 'unknown_task'
    assert accounting.cancel_remediation_task(7)['error']['type'] == 'unknown_task'

    polls = iter((
        pending,
        BackendOutcome(ok=True, result=DIAGNOSIS, message='', status_code=HTTPStatus.OK),
    ))
    monkeypatch.setattr(accounting, 'poll_backend_task', lambda task: next(polls))
    assert accounting.get_remediation_task(task_id)['error']['type'] == 'still_running'
    finished = accounting.get_remediation_task(task_id)
    assert finished['result']['event_identifier'] == 5
    assert TEST_ADDR1 not in str(finished)
    assert accounting.get_remediation_task(task_id)['error']['type'] == 'unknown_task'

    requests: list[str] = []

    def query_backend(endpoint: str, method: str) -> BackendOutcome:
        requests.append(f'{method} {endpoint}')
        return BackendOutcome(ok=True, result=True, message='', status_code=HTTPStatus.OK)

    monkeypatch.setattr(accounting, 'query_backend', query_backend)
    monkeypatch.setattr(accounting, 'run_backend_task', lambda **kwargs: pending)
    accounting.apply_remediation_plan(plan_id=PLAN_ID, approved_at=1)
    assert accounting.cancel_remediation_task(task_id)['result'] == {
        'cancellation_requested': True,
    }
    assert requests == [f'DELETE tasks/{task_id}']
    assert accounting.cancel_remediation_task(task_id)['error']['type'] == 'unknown_task'


def test_bucket_references_are_dropped_when_the_user_changes(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: E501
    monkeypatch.setattr(analytics, 'query_settings', lambda: {'mcp_privacy_mode': 'balanced'})
    monkeypatch.setattr(analytics, 'query_logged_in_user', lambda: 'alice')
    analytics.sync_privacy_mode()
    bucket_ref = sanitize(DIAGNOSIS, privacy_mode='balanced')['bucket']['bucket_ref']
    assert get_reference_registry().resolve_bucket(bucket_ref) == DIAGNOSIS['bucket']

    monkeypatch.setattr(analytics, 'query_logged_in_user', lambda: 'bob')
    analytics.sync_privacy_mode()
    with pytest.raises(UnknownReferenceError):
        get_reference_registry().resolve_bucket(bucket_ref)


def test_ui_route_is_only_handed_out_in_raw_mode() -> None:
    assert sanitize(DIAGNOSIS, privacy_mode='raw')['ui_route'] == (
        f'/history/events?groupIdentifiers=1{TX_HASH}'
    )
    for privacy_mode in ('balanced', 'strict'):
        assert 'ui_route' not in sanitize(DIAGNOSIS, privacy_mode=privacy_mode)

    flags = {'asset_signals': {USDC: ['mixed_scripts', 'link_in_metadata']}}
    assert sanitize(flags, privacy_mode='balanced') == flags
