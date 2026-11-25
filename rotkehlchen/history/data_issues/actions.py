"""Dynamic computation of machine-readable suggested remediation actions for data issues.

Actions are computed at read/serialization time rather than persisted in ``payload_json``
so that:
1. Actions can reference ``issue.id`` (unavailable before the row is inserted).
2. Refining endpoint hints or action metadata never alters the persisted payload and
   therefore never invalidates ``DataIssuesManager._is_unchanged_manual_resolution``.
"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.types import SuggestedAction
from rotkehlchen.types import TimestampMS
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.history.data_issues.types import DataIssue


def _make_action(
        action: str,
        params: dict[str, Any],
        endpoint: str,
        requires_input: list[str] | None = None,
) -> SuggestedAction:
    return SuggestedAction(
        action=action,
        params=params,
        endpoint=endpoint,
        requires_input=[] if requires_input is None else requires_input,
    )


def build_suggested_actions(issue: DataIssue) -> list[SuggestedAction]:
    """Return the ordered list of actionable remediation hints for ``issue``.

    Terminal issues (``resolved`` or ``dismissed``) return an empty list.
    """
    if issue.state in {IssueState.RESOLVED, IssueState.DISMISSED}:
        return []

    payload = issue.payload
    event_id = (
        issue.event_identifier
        if issue.event_identifier is not None
        else payload.get('event_identifier')
    )
    group_id = issue.group_identifier or payload.get('group_identifier')
    timestamp_s = int(ts_ms_to_sec(TimestampMS(issue.ts_start)))

    if issue.kind == IssueKind.MISSING_PRICE:
        actions: list[SuggestedAction] = [
            _make_action(
                action='set_manual_price',
                params={
                    'from_asset': issue.asset,
                    'to_asset': payload.get('to_asset'),
                    'timestamp': timestamp_s,
                    'source_type': 'manual',
                },
                endpoint='PUT /api/1/assets/prices/historical',
                requires_input=['price'],
            ),
            _make_action(
                action='ignore_asset',
                params={'assets': [issue.asset]},
                endpoint='PUT /api/1/assets/ignored',
            ),
        ]
        if group_id is not None:
            actions.append(_make_action(
                action='ignore_action',
                params={'data': [group_id]},
                endpoint='PUT /api/1/actions/ignored',
            ))
        return actions

    if issue.kind == IssueKind.MISSING_COST_BASIS:
        return [
            _make_action(
                action='add_acquisition',
                params={
                    'asset': issue.asset,
                    'amount': payload.get('uncovered_amount'),
                    'timestamp': issue.ts_start,
                    'location': issue.location,
                    'location_label': issue.location_label or None,
                },
                endpoint='PUT /api/1/history/events',
                requires_input=[
                    'entry_type',
                    'sequence_index',
                    'timestamp',
                    'event_type',
                    'event_subtype',
                    'amount',
                ],
            ),
            _make_action(
                action='match_transfer',
                params={'external': False},
                endpoint='PUT /api/1/history/events/match/asset_movements',
                requires_input=['asset_movement', 'matched_events'],
            ),
            _make_action(
                action='confirm_zero_basis',
                params={'disposition': 'confirm_zero_basis'},
                endpoint=f'PATCH /api/1/data_issues/{issue.id}/resolve_manually',
            ),
        ]

    if issue.kind == IssueKind.INCOMPLETE_SWAP:
        actions = []
        if group_id is not None:
            actions.append(_make_action(
                action='ignore_group',
                params={'data': [group_id]},
                endpoint='PUT /api/1/actions/ignored',
            ))
        excluded_assets = payload.get('excluded_assets') or []
        if (
            payload.get('missing_or_excluded_reason') == 'ignored_asset' and
            len(excluded_assets) > 0
        ):
            actions.append(_make_action(
                action='unignore_asset',
                params={'assets': list(excluded_assets)},
                endpoint='DELETE /api/1/assets/ignored',
            ))
        if event_id is not None:
            edit_params: dict[str, Any] = {'identifier': event_id}
            if group_id is not None:
                edit_params['group_identifier'] = group_id
            actions.append(_make_action(
                action='edit_event',
                params=edit_params,
                endpoint='PATCH /api/1/history/events',
                requires_input=['entry_type'],
            ))
        actions.append(_make_action(
            action='dismiss_as_standalone',
            params={'disposition': 'dismiss_as_standalone'},
            endpoint=f'PATCH /api/1/data_issues/{issue.id}/resolve_manually',
        ))
        return actions

    if issue.kind == IssueKind.UNMATCHED_EXCHANGE_TRANSFER:
        actions = [
            _make_action(
                action='auto_match_exchange_transfer',
                params={},
                endpoint=f'POST /api/1/data_issues/{issue.id}/retry_auto_remediation',
            ),
        ]
        if event_id is not None:
            actions.extend([
                _make_action(
                    action='manual_match_event',
                    params={
                        'asset_movement': event_id,
                        'external': False,
                    },
                    endpoint='PUT /api/1/history/events/match/asset_movements',
                    requires_input=['matched_events'],
                ),
                _make_action(
                    action='resolve_as_external',
                    params={
                        'asset_movement': event_id,
                        'matched_events': [],
                        'external': True,
                    },
                    endpoint='PUT /api/1/history/events/match/asset_movements',
                ),
            ])
        return actions

    if issue.kind == IssueKind.REBASING_TOKEN:
        return [
            _make_action(
                action='retry_auto_remediation',
                params={},
                endpoint=f'POST /api/1/data_issues/{issue.id}/retry_auto_remediation',
            ),
        ]

    return []
