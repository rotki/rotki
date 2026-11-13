"""Accounting diagnosis and repair over the rotki backend, privacy filtered for the agent.

Every function here returns a JSON-serializable dict: the backend's diagnosis passed
through references.sanitize, or ``{'error': {...}}``. Errors carry a ``type`` the agent can
act on and a message scrubbed of identifiers.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Final, Literal

from rotkehlchen.mcp.analytics import _scrub_identifiers, sync_privacy_mode
from rotkehlchen.mcp.backend import (
    BackendOutcome,
    BackendQueryError,
    get_backend_config,
    query_backend,
    run_backend_task,
)
from rotkehlchen.mcp.references import (
    UnknownReferenceError,
    get_reference_registry,
    sanitize,
)

if TYPE_CHECKING:
    from collections.abc import Callable

PLAN_ID_RE: Final = re.compile(r'[0-9a-f]{32}')
DIAGNOSIS_TIMEOUT_SECONDS: Final = 120
PREVIEW_WAIT_SECONDS: Final = 300
APPLY_WAIT_SECONDS: Final = 600
DATA_ISSUES_PAGE: Final = 'rotki: History > Data issues'


def error_result(error_type: str, message: str, **details: Any) -> dict[str, Any]:
    return {'error': {'type': error_type, 'message': _scrub_identifiers(message), **details}}


def _privacy_mode() -> Any:
    sync_privacy_mode()
    return get_backend_config().privacy_mode


def _outcome(outcome: BackendOutcome, privacy_mode: Any) -> dict[str, Any]:
    if outcome.pending_task_id is not None:
        return error_result(
            'still_running',
            'The backend is still working on it. Call the verification tool later',
            task_id=outcome.pending_task_id,
        )
    if not outcome.ok:
        code = outcome.result.get('code') if isinstance(outcome.result, dict) else None
        return error_result(code or f'backend_http_{outcome.status_code}', outcome.message)
    return {
        'result': sanitize(outcome.result, privacy_mode=privacy_mode),
        'privacy_mode': privacy_mode,
    }


def _call(
        fn: Callable[[Any], dict[str, Any]],
        plan_id: str | None = None,
) -> dict[str, Any]:
    """Run fn with the current privacy mode, turning transport and reference failures into
    structured errors. A plan id goes into the endpoint path, so its format is checked."""
    if plan_id is not None and PLAN_ID_RE.fullmatch(plan_id) is None:
        return error_result('unknown_plan', 'Not a remediation plan id')
    try:
        return fn(_privacy_mode())
    except UnknownReferenceError as e:
        return error_result('unknown_reference', str(e))
    except BackendQueryError as e:
        return error_result('backend_unavailable', str(e))


def get_accounting_health() -> dict[str, Any]:
    return _call(lambda privacy_mode: _outcome(query_backend(
        endpoint='data_issues/diagnostics/health',
        timeout=DIAGNOSIS_TIMEOUT_SECONDS,
    ), privacy_mode) | {'ui': DATA_ISSUES_PAGE})


def list_data_issues(
        kinds: list[str] | None,
        states: list[str] | None,
        asset: str | None,
        location: str | None,
        account: str | None,
        limit: int,
        offset: int,
) -> dict[str, Any]:
    def run(privacy_mode: Any) -> dict[str, Any]:
        params: dict[str, Any] = {'limit': limit, 'offset': offset}
        if kinds:
            params['kind'] = ','.join(kinds)
        if states:
            params['state'] = ','.join(states)
        if asset is not None:
            params['asset'] = asset
        if location is not None:
            params['location'] = location
        if account is not None:
            params['location_label'] = get_reference_registry().resolve(account, privacy_mode)
        return _outcome(query_backend(
            endpoint='data_issues/diagnostics/issues',
            params=params,
            timeout=DIAGNOSIS_TIMEOUT_SECONDS,
        ), privacy_mode)

    return _call(run)


def explain_data_issue(issue_id: int) -> dict[str, Any]:
    return _call(lambda privacy_mode: _outcome(query_backend(
        endpoint=f'data_issues/{issue_id}/explanation',
        timeout=DIAGNOSIS_TIMEOUT_SECONDS,
    ), privacy_mode))


def trace_bucket(
        bucket_ref: str,
        from_timestamp: int | None,
        limit: int,
        offset: int | None,
) -> dict[str, Any]:
    def run(privacy_mode: Any) -> dict[str, Any]:
        bucket = get_reference_registry().resolve_bucket(bucket_ref)
        body: dict[str, Any] = {
            'location': bucket['location'],
            'location_label': bucket['location_label'],
            'protocol': bucket['protocol'],
            'asset': bucket['asset'],
            'limit': limit,
        }
        if from_timestamp is not None:
            body['from_timestamp'] = from_timestamp
        if offset is not None:
            body['offset'] = offset
        return _outcome(query_backend(
            endpoint='data_issues/diagnostics/bucket_trace',
            method='POST',
            json_data=body,
            timeout=DIAGNOSIS_TIMEOUT_SECONDS,
        ), privacy_mode)

    return _call(run)


def inspect_transaction(group_identifier: str) -> dict[str, Any]:
    return _call(lambda privacy_mode: _outcome(query_backend(
        endpoint='data_issues/diagnostics/transaction',
        method='POST',
        json_data={'group_identifier': get_reference_registry().resolve(
            group_identifier,
            privacy_mode,
        )},
        timeout=DIAGNOSIS_TIMEOUT_SECONDS,
    ), privacy_mode))


def explain_bridge_match(event_identifier: int) -> dict[str, Any]:
    return _call(lambda privacy_mode: _outcome(query_backend(
        endpoint='data_issues/diagnostics/bridge_match',
        method='POST',
        json_data={'event_identifier': event_identifier},
        timeout=DIAGNOSIS_TIMEOUT_SECONDS,
    ), privacy_mode))


def preview_remediation(
        kind: Literal['redecode', 'bridge_link'],
        group_identifiers: list[str] | None,
        replace_customized: bool,
        bridge_event_identifier: int | None,
        matched_event_identifier: int | None,
) -> dict[str, Any]:
    def run(privacy_mode: Any) -> dict[str, Any]:
        body: dict[str, Any] = {'kind': kind, 'replace_customized': replace_customized}
        if group_identifiers is not None:
            registry = get_reference_registry()
            body['group_identifiers'] = [
                registry.resolve(group, privacy_mode) for group in group_identifiers
            ]
        if bridge_event_identifier is not None:
            body['bridge_event_identifier'] = bridge_event_identifier
        if matched_event_identifier is not None:
            body['matched_event_identifier'] = matched_event_identifier
        return _outcome(run_backend_task(
            endpoint='data_issues/remediation_plans',
            json_data=body,
            wait_seconds=PREVIEW_WAIT_SECONDS,
        ), privacy_mode)

    return _call(run)


def get_remediation_plan(plan_id: str) -> dict[str, Any]:
    return _call(lambda privacy_mode: _outcome(query_backend(
        endpoint=f'data_issues/remediation_plans/{plan_id}',
    ), privacy_mode), plan_id=plan_id)


def reject_remediation_plan(plan_id: str, reason: str) -> dict[str, Any]:
    return _call(lambda privacy_mode: _outcome(query_backend(
        endpoint=f'data_issues/remediation_plans/{plan_id}/reject',
        method='PATCH',
        json_data={'reason': reason},
    ), privacy_mode), plan_id=plan_id)


def apply_remediation_plan(plan_id: str, approved_at: int) -> dict[str, Any]:
    """Apply a plan the user approved through an MCP elicitation. Only the apply tool, after
    the user accepted, calls this."""
    return _call(lambda privacy_mode: _outcome(run_backend_task(
        endpoint=f'data_issues/remediation_plans/{plan_id}/apply',
        json_data={'approval_method': 'mcp_elicitation', 'approved_at': approved_at},
        wait_seconds=APPLY_WAIT_SECONDS,
    ), privacy_mode), plan_id=plan_id)


def verify_remediation_plan(plan_id: str) -> dict[str, Any]:
    return _call(lambda privacy_mode: _outcome(query_backend(
        endpoint=f'data_issues/remediation_plans/{plan_id}/verification',
        timeout=DIAGNOSIS_TIMEOUT_SECONDS,
    ), privacy_mode), plan_id=plan_id)


def describe_plan_for_approval(plan: dict[str, Any]) -> str:
    """A plain summary of a sanitized plan, for the user to approve or decline.

    It names assets, locations and exact amounts but no account or transaction identifier,
    since an approval prompt may be shown to the model as well as to the user.
    """
    body = plan['plan']
    lines = [
        f'rotki wants to apply a {plan["kind"].replace("_", " ")} repair to your history.',
        f'Applicable changes: {body.get("applicable_items", 0)} of {len(body["items"])}.',
    ]
    for item in body['items']:
        if item.get('status') != 'ready':
            continue
        if item.get('replace_customized'):
            lines.append('- Replaces events you customized in one transaction.')
        if item.get('has_matched_events'):
            lines.append('- Drops matched links of one transaction; they must be matched again.')
        lines.extend(
            f'- {entry["bucket"]["asset"]} on {entry["bucket"]["location"]}'
            f'{" in " + entry["bucket"]["protocol"] if entry["bucket"].get("protocol") else ""}'
            f': net effect {entry["current_net"]} -> {entry["proposed_net"]}'
            for entry in item.get('bucket_effect_diff', [])
        )
    lines.append(
        'The affected range is reprocessed afterwards. Review the exact changes in rotki '
        'before approving if unsure.',
    )
    return '\n'.join(lines)
