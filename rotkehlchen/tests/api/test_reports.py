from http import HTTPStatus

import pytest
import requests

from rotkehlchen.accounting.constants import FREE_PNL_EVENTS_LIMIT
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.api.server import APIServer
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_DAI, A_ETH
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
)
from rotkehlchen.tests.utils.constants import A_GBP
from rotkehlchen.types import Location, Price, Timestamp
from rotkehlchen.utils.misc import timestamp_to_date


def setup_report_events(database) -> tuple[int, list[ProcessedAccountingEvent]]:
    """Input events to the DB for testing"""
    timestamp_1_secs, timestamp_2_secs, eth_price_ts_1, eth_price_ts_2, half_amount, hundred = Timestamp(1741634066), Timestamp(1741634100), FVal('2000'), FVal('2200'), FVal(0.5), FVal('100')  # noqa: E501
    dbreport = DBAccountingReports(database)
    settings = DBSettings(
        main_currency=A_GBP,
        calculate_past_cost_basis=False,
        include_gas_costs=False,
        pnl_csv_have_summary=False,
        pnl_csv_with_formulas=True,
        taxfree_after_period=15,
    )

    report_id = dbreport.add_report(
        first_processed_timestamp=timestamp_1_secs,
        start_ts=timestamp_1_secs,
        end_ts=timestamp_2_secs,
        settings=settings,
    )

    events = [
        ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Received 1 ETH',
            location=Location.ETHEREUM,
            timestamp=timestamp_1_secs,
            asset=A_ETH,
            free_amount=ONE,
            taxable_amount=ZERO,
            price=Price(eth_price_ts_1),
            pnl=PNL(free=ZERO, taxable=eth_price_ts_1),
            cost_basis=None,
            index=0,
            extra_data={},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Send 0.5 ETH to 0xABC',
            location=Location.ETHEREUM,
            timestamp=timestamp_2_secs,
            asset=A_ETH,
            free_amount=ZERO,
            taxable_amount=half_amount,
            price=Price(eth_price_ts_2),
            pnl=PNL(taxable=half_amount, free=ONE),
            cost_basis=None,
            index=1,
            extra_data={},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Received 100 DAI',
            location=Location.ETHEREUM,
            timestamp=timestamp_2_secs,
            asset=A_DAI,
            free_amount=hundred,
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=hundred),
            cost_basis=None,
            index=0,
            extra_data={},
        ),
    ]

    for event in events:
        dbreport.add_report_data(
            report_id=report_id,
            time=event.timestamp,
            ts_converter=timestamp_to_date,
            event=event,
        )

    return report_id, events


@pytest.mark.parametrize('start_with_valid_premium', [True, False])
def test_get_report_data_with_premium(
        rotkehlchen_api_server: APIServer,
        start_with_valid_premium: bool,
) -> None:
    """Test that getting report data works correctly with premium subscription active"""
    # First create a report and add events
    report_id, events = setup_report_events(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)

    # Query report data with no filters
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'per_report_data_resource', report_id=report_id),
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert 'entries' in data['result']
    assert 'entries_found' in data['result']
    assert 'entries_total' in data['result']
    assert 'entries_limit' in data['result']
    assert len(data['result']['entries']) == len(events)
    assert data['result']['entries_found'] == len(events)
    assert data['result']['entries_total'] == len(events)
    assert data['result']['entries_limit'] == -1 if start_with_valid_premium else FREE_PNL_EVENTS_LIMIT  # noqa: E501

    # Test pagination limits
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'per_report_data_resource', report_id=report_id),
        json={'offset': 0, 'limit': 1},
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']['entries']) == 1
    assert data['result']['entries_found'] == len(events)
    assert data['result']['entries_total'] == len(events)
    assert data['result']['entries_limit'] == -1 if start_with_valid_premium else FREE_PNL_EVENTS_LIMIT  # noqa: E501


def test_get_report_data_invalid_report(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Test that requesting invalid report ID is handled correctly"""
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'per_report_data_resource', report_id=1),
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to get PnL events from non existing report with id 1',
        status_code=HTTPStatus.BAD_REQUEST,
    )
