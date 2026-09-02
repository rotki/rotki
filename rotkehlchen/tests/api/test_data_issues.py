from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.types import Location, TimestampMS

pytestmark = pytest.mark.accounting_update

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def _write_issue(
        server: APIServer,
        event_identifier: int = 1,
        kind: IssueKind = IssueKind.NEGATIVE_BALANCE,
        state: IssueState = IssueState.OPEN,
        location: Location = Location.ETHEREUM,
        location_label: str = '0x0000000000000000000000000000000000000001',
        asset: str = 'ETH',
        ts_start: int = 1000,
        ts_end: int | None = None,
) -> int:
    manager = DataIssuesManager(server.rest_api.rotkehlchen.data.db)
    issue_id = manager.write_issue(
        kind,
        location=location.serialize_for_db(),
        location_label=location_label,
        protocol=None,
        asset=asset,
        payload={
            'block_number': 1,
            'event_identifier': event_identifier,
            'reason': 'archive_node_unavailable',
        } if kind == IssueKind.REBASING_TOKEN else {
            'event_identifier': event_identifier,
            'in_memory_negative_amount': '-1',
            'derived_balance_before_event': '1',
        },
        ts_start=ts_start,
        ts_end=ts_start if ts_end is None else ts_end,
    )
    if state == IssueState.AUTO_REMEDIATING:
        manager.update_state(issue_id, IssueState.AUTO_REMEDIATING, attempt={'step': 1})
    elif state == IssueState.UNRESOLVED:
        manager.update_state(issue_id, IssueState.AUTO_REMEDIATING)
        manager.update_state(issue_id, IssueState.UNRESOLVED)
    elif state == IssueState.RESOLVED:
        manager.resolve_manually(issue_id, note='done')
    elif state == IssueState.DISMISSED:
        manager.dismiss(issue_id)

    return issue_id


def test_data_issues_list_detail_and_pagination(rotkehlchen_api_server: APIServer) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    group_identifier = 'negative-balance-group'
    with database.user_write() as write_cursor:
        event_identifier = DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                group_identifier=group_identifier,
                sequence_index=0,
                timestamp=TimestampMS(1_000_000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
            ),
        )
    assert event_identifier is not None

    first_id = _write_issue(
        rotkehlchen_api_server,
        event_identifier=event_identifier,
        ts_start=1000,
    )
    _write_issue(
        rotkehlchen_api_server,
        event_identifier=2,
        state=IssueState.RESOLVED,
        asset='BTC',
        ts_start=2000,
    )
    third_id = _write_issue(
        rotkehlchen_api_server,
        event_identifier=3,
        state=IssueState.UNRESOLVED,
        location=Location.OPTIMISM,
        location_label='0x0000000000000000000000000000000000000002',
        ts_start=3000,
    )

    result = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'dataissuesresource'),
    ))
    assert result['entries_found'] == 2  # resolved is terminal and filtered out by default
    assert result['entries_limit'] == -1
    assert [entry['id'] for entry in result['entries']] == [third_id, first_id]
    assert [entry['group_identifier'] for entry in result['entries']] == [
        None,
        group_identifier,
    ]

    result = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'dataissuesresource'),
        json={'limit': 1, 'offset': 1},
    ))
    assert result['entries_found'] == 2
    assert result['entries_limit'] == -1
    assert [entry['id'] for entry in result['entries']] == [first_id]
    assert result['entries'][0]['group_identifier'] == group_identifier

    result = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'dataissuesresource'),
        json={
            'state': ['unresolved'],
            'kind': ['negative_balance'],
            'location': 'optimism',
            'location_label': '0x0000000000000000000000000000000000000002',
            'asset': 'ETH',
            'from_timestamp': 2500,
            'to_timestamp': 3500,
        },
    ))
    assert result['entries_found'] == 1
    assert result['entries'][0]['id'] == third_id

    result = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'dataissuesresource'),
        json={'asset': 'BTC'},
    ))
    assert result['entries_found'] == 0
    assert result['entries'] == []

    assert_error_response(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'dataissuesresource'),
            json={'from_timestamp': 3000, 'to_timestamp': 2000},
        ),
        contained_in_msg='from_timestamp must be less than or equal to to_timestamp',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    result = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'dataissueresource', issue_id=first_id),
    ))
    assert result['payload']['event_identifier'] == event_identifier
    assert result['group_identifier'] == group_identifier
    assert result['protocol'] is None
    assert result['auto_remediation_attempts'] == []

    assert_error_response(
        response=requests.get(api_url_for(
            rotkehlchen_api_server,
            'dataissueresource',
            issue_id=999,
        )),
        contained_in_msg='Data issue with id 999 not found',
        status_code=HTTPStatus.NOT_FOUND,
    )


def test_data_issue_write_endpoints(rotkehlchen_api_server: APIServer) -> None:
    issue_id = _write_issue(rotkehlchen_api_server)

    result = assert_proper_sync_response_with_result(requests.patch(api_url_for(
        rotkehlchen_api_server,
        'dataissuedismissresource',
        issue_id=issue_id,
    )))
    assert result['state'] == 'dismissed'

    assert_error_response(
        response=requests.patch(
            api_url_for(
                rotkehlchen_api_server,
                'dataissueresolvemanuallyresource',
                issue_id=issue_id,
            ),
            json={'note': 'nope'},
        ),
        contained_in_msg='Current state is dismissed',
        status_code=HTTPStatus.CONFLICT,
    )
    assert_error_response(
        response=requests.post(api_url_for(
            rotkehlchen_api_server,
            'dataissueretryautoremediationresource',
            issue_id=issue_id,
        )),
        contained_in_msg='Auto-remediation is not supported for negative_balance data issues',
        status_code=HTTPStatus.CONFLICT,
    )
    assert_error_response(
        response=requests.patch(api_url_for(
            rotkehlchen_api_server,
            'dataissuedismissresource',
            issue_id=999,
        )),
        contained_in_msg='Data issue with id 999 not found',
        status_code=HTTPStatus.NOT_FOUND,
    )

    issue_id = _write_issue(rotkehlchen_api_server, event_identifier=2)
    result = assert_proper_sync_response_with_result(requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'dataissueresolvemanuallyresource',
            issue_id=issue_id,
        ),
        json={'note': 'fixed'},
    ))
    assert result['state'] == 'resolved'
    assert result['payload']['resolution'] == {'manual': True, 'note': 'fixed'}

    assert_error_response(
        response=requests.patch(
            api_url_for(
                rotkehlchen_api_server,
                'dataissueresolvemanuallyresource',
                issue_id=issue_id,
            ),
            json={'note': 'updated'},
        ),
        contained_in_msg='Cannot resolve an already resolved data issue',
        status_code=HTTPStatus.CONFLICT,
    )

    assert_error_response(
        response=requests.post(api_url_for(
            rotkehlchen_api_server,
            'dataissueretryautoremediationresource',
            issue_id=issue_id,
        )),
        contained_in_msg='Auto-remediation is not supported for negative_balance data issues',
        status_code=HTTPStatus.CONFLICT,
    )

    rebasing_issue_id = _write_issue(
        rotkehlchen_api_server,
        event_identifier=4,
        kind=IssueKind.REBASING_TOKEN,
    )
    task_manager = rotkehlchen_api_server.rest_api.rotkehlchen.task_manager
    assert task_manager is not None
    with patch.object(
        task_manager,
        'retry_data_issue_auto_remediation',
        return_value=True,
    ) as retry_task:
        result = assert_proper_sync_response_with_result(requests.post(api_url_for(
            rotkehlchen_api_server,
            'dataissueretryautoremediationresource',
            issue_id=rebasing_issue_id,
        )))
        assert result['state'] == 'auto_remediating'
        retry_task.assert_called_once_with(issue_id=rebasing_issue_id, from_ts=TimestampMS(1000))

        result = assert_proper_sync_response_with_result(requests.post(api_url_for(
            rotkehlchen_api_server,
            'dataissueretryautoremediationresource',
            issue_id=rebasing_issue_id,
        )))
        assert result['state'] == 'auto_remediating'
        retry_task.assert_called_once()

    busy_issue_id = _write_issue(
        rotkehlchen_api_server,
        event_identifier=5,
        kind=IssueKind.REBASING_TOKEN,
    )
    with patch.object(
        task_manager,
        'retry_data_issue_auto_remediation',
        return_value=False,
    ):
        assert_error_response(
            response=requests.post(api_url_for(
                rotkehlchen_api_server,
                'dataissueretryautoremediationresource',
                issue_id=busy_issue_id,
            )),
            contained_in_msg='Historical balance processing is already running',
            status_code=HTTPStatus.CONFLICT,
        )
    busy_issue = DataIssuesManager(
        rotkehlchen_api_server.rest_api.rotkehlchen.data.db,
    ).get_issue(busy_issue_id)
    assert busy_issue.state == IssueState.UNRESOLVED
    assert busy_issue.auto_remediation_attempts[0]['reason'] == 'processing_already_running'

    resolved_issue_id = _write_issue(
        rotkehlchen_api_server,
        event_identifier=3,
        state=IssueState.RESOLVED,
    )
    result = assert_proper_sync_response_with_result(requests.patch(api_url_for(
        rotkehlchen_api_server,
        'dataissuedismissresource',
        issue_id=resolved_issue_id,
    )))
    assert result['state'] == 'dismissed'
    assert result['resolved_at'] is None
    assert 'resolution' not in result['payload']

    assert_error_response(
        response=requests.post(api_url_for(
            rotkehlchen_api_server,
            'dataissueretryautoremediationresource',
            issue_id=999,
        )),
        contained_in_msg='Data issue with id 999 not found',
        status_code=HTTPStatus.NOT_FOUND,
    )
