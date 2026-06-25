from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.types import Location

pytestmark = pytest.mark.accounting_update

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def _write_issue(
        server: 'APIServer',
        event_identifier: int = 1,
        state: IssueState = IssueState.OPEN,
        location: Location = Location.ETHEREUM,
        location_label: str = '0x0000000000000000000000000000000000000001',
        asset: str = 'ETH',
        ts_start: int = 1000,
        ts_end: int | None = None,
) -> int:
    manager = DataIssuesManager(server.rest_api.rotkehlchen.data.db)
    issue_id = manager.write_issue(
        IssueKind.NEGATIVE_BALANCE,
        location=location.serialize_for_db(),
        location_label=location_label,
        protocol=None,
        asset=asset,
        payload={
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


def test_data_issues_list_detail_and_pagination(rotkehlchen_api_server: 'APIServer') -> None:
    first_id = _write_issue(rotkehlchen_api_server, event_identifier=1, ts_start=1000)
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

    result = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'dataissuesresource'),
        json={'limit': 1, 'offset': 1},
    ))
    assert result['entries_found'] == 2
    assert result['entries_limit'] == 1
    assert [entry['id'] for entry in result['entries']] == [first_id]

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
    assert result['payload']['event_identifier'] == 1
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


def test_data_issue_write_endpoints(rotkehlchen_api_server: 'APIServer') -> None:
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
        contained_in_msg='Cannot retry auto-remediation for dismissed data issue',
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

    result = assert_proper_sync_response_with_result(requests.post(api_url_for(
        rotkehlchen_api_server,
        'dataissueretryautoremediationresource',
        issue_id=issue_id,
    )))
    assert result['state'] == 'open'
    assert result['resolved_at'] is None
    assert 'resolution' not in result['payload']

    result = assert_proper_sync_response_with_result(requests.post(api_url_for(
        rotkehlchen_api_server,
        'dataissueretryautoremediationresource',
        issue_id=issue_id,
    )))
    assert result['state'] == 'open'

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
