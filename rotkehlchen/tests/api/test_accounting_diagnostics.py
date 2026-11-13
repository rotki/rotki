from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM, LOCATION_OPTIMISM
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import TimestampMS
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer

pytestmark = pytest.mark.accounting_update


def test_diagnosis_endpoints(rotkehlchen_api_server: APIServer) -> None:
    health = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'accountinghealthresource'),
    ))
    assert health['status'] == 'unprocessed'
    assert health['capabilities']['diagnosis_uses_network'] is False
    assert 'archive_nodes_by_chain' in health['capabilities']

    trace = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'buckettraceresource'),
        json={'location': 'ethereum', 'location_label': TEST_ADDR1, 'asset': 'ETH'},
    ))
    assert trace['rows'] == []
    assert trace['stop'] is None

    issues = assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'dataissuesdiagnosisresource'),
    ))
    assert issues == {'entries': [], 'entries_found': 0, 'groups': []}

    for response in (
        requests.get(api_url_for(rotkehlchen_api_server, 'dataissueexplanationresource', issue_id=99)),  # noqa: E501
        requests.post(
            api_url_for(rotkehlchen_api_server, 'transactiondiagnosisresource'),
            json={'group_identifier': 'missing'},
        ),
        requests.post(
            api_url_for(rotkehlchen_api_server, 'bridgematchdiagnosisresource'),
            json={'event_identifier': 99},
        ),
        requests.get(api_url_for(
            rotkehlchen_api_server,
            'remediationplanresource',
            plan_id='0' * 32,
        )),
    ):
        assert_error_response(response, status_code=HTTPStatus.NOT_FOUND)


def test_remediation_plan_endpoints(rotkehlchen_api_server: APIServer) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with database.user_write() as write_cursor:
        _, bridge_id, matched_id = (DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(timestamp),
                location=location,
                event_type=event_type,
                event_subtype=event_subtype,
                asset=A_ETH,
                amount=FVal(amount),
                location_label=TEST_ADDR1,
            ),
        ) for timestamp, location, event_type, event_subtype, amount in (
            (1_000, LOCATION_ETHEREUM, HistoryEventType.RECEIVE, HistoryEventSubType.NONE, '2'),
            (1_000_000, LOCATION_ETHEREUM, HistoryEventType.DEPOSIT, HistoryEventSubType.BRIDGE, '1'),  # noqa: E501
            (1_060_000, LOCATION_OPTIMISM, HistoryEventType.RECEIVE, HistoryEventSubType.NONE, '0.995'),  # noqa: E501
        ))

    plans_url = api_url_for(rotkehlchen_api_server, 'remediationplansresource')
    assert_error_response(
        requests.post(plans_url, json={'kind': 'redecode'}),
        contained_in_msg='needs group_identifiers',
    )
    assert_error_response(
        requests.post(plans_url, json={
            'kind': 'bridge_link',
            'bridge_event_identifier': bridge_id,
            'matched_event_identifier': 999,
        }),
        contained_in_msg='Both events of the link must exist',
        status_code=HTTPStatus.CONFLICT,
        result_exists=True,
    )

    plan = assert_proper_response_with_result(
        response=requests.post(plans_url, json={
            'kind': 'bridge_link',
            'bridge_event_identifier': bridge_id,
            'matched_event_identifier': matched_id,
            'async_query': True,
        }),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=True,
    )
    assert plan['state'] == 'pending'
    apply_url = api_url_for(
        rotkehlchen_api_server,
        'remediationplanapplyresource',
        plan_id=plan['plan_id'],
    )
    assert_error_response(
        requests.post(apply_url, json={'approval_method': 'agent', 'approved_at': ts_now()}),
        contained_in_msg='Must be one of',
    )

    applied = assert_proper_sync_response_with_result(requests.post(
        apply_url,
        json={'approval_method': 'mcp_elicitation', 'approved_at': ts_now()},
    ))
    assert applied['state'] == 'applied'
    assert applied['verification']['reevaluated'] is True
    assert assert_proper_sync_response_with_result(requests.get(api_url_for(
        rotkehlchen_api_server,
        'remediationplanverificationresource',
        plan_id=plan['plan_id'],
    )))['verification']['verdict'] == applied['verification']['verdict']
    assert_error_response(
        requests.patch(
            api_url_for(rotkehlchen_api_server, 'remediationplanrejectresource', plan_id=plan['plan_id']),  # noqa: E501
            json={},
        ),
        contained_in_msg='The plan is applied',
        status_code=HTTPStatus.CONFLICT,
        result_exists=True,
    )
