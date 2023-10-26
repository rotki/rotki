from http import HTTPStatus
from typing import get_args
import pytest
import requests

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.db.constants import LINKABLE_ACCOUNTING_PROPERTIES
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
)


@pytest.mark.parametrize('db_settings', [{'include_crypto2crypto': False}])
def test_manage_rules(rotkehlchen_api_server, db_settings):
    """Test basic operations in the endpoint for managing accounting rules"""
    rule_1 = {
        'taxable': {'value': True, 'linked_setting': 'include_crypto2crypto'},
        'count_entire_amount_spend': {
            'value': False,
            'linked_setting': 'include_crypto2crypto',
        },
        'count_cost_basis_pnl': {'value': True},
        'event_type': HistoryEventType.DEPOSIT.serialize(),
        'event_subtype': HistoryEventSubType.SPEND.serialize(),
        'counterparty': 'uniswap',
    }
    rule_2 = {
        'taxable': {'value': True},
        'count_entire_amount_spend': {'value': False},
        'count_cost_basis_pnl': {'value': True},
        'event_type': HistoryEventType.STAKING.serialize(),
        'event_subtype': HistoryEventSubType.SPEND.serialize(),
        'counterparty': None,
        'accounting_treatment': 'swap',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ), json=rule_1,
    )
    assert_proper_response_with_result(response)
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ), json=rule_2,
    )
    assert_proper_response_with_result(response)

    # now try to query them
    rule_1_copy = rule_1.copy()
    rule_1_copy['taxable']['value'] = db_settings['include_crypto2crypto']
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result['entries'] == [
        {'identifier': 2, **rule_2},
        {'identifier': 1, **rule_1_copy, 'accounting_treatment': None},
    ]
    assert result['entries_found'] == 2
    assert result['entries_total'] == 2

    # try to filter
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ), json={
            'event_types': ['deposit', 'withdrawal'],
        },
    )
    result = assert_proper_response_with_result(response)
    assert result['entries'] == [
        {'identifier': 1, **rule_1, 'accounting_treatment': None},
    ]
    assert result['entries_found'] == 1
    assert result['entries_total'] == 2

    # filter by a type that is not present in the database
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ), json={
            'event_types': ['adjustment'],
        },
    )
    result = assert_proper_response_with_result(response)
    assert result['entries'] == []
    assert result['entries_found'] == 0
    assert result['entries_total'] == 2

    # update rule 2
    rule_2['counterparty'] = 'compound'
    rule_2['accounting_treatment'] = None
    rule_2['taxable'] = {'value': False}
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ), json={
            'identifier': 2,
            **rule_2,
        },
    )
    assert_simple_ok_response(response)

    # query the data and see that it got updated
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result['entries'] == [
        {'identifier': 2, **rule_2},
        {'identifier': 1, **rule_1, 'accounting_treatment': None},
    ]

    # update rule 2 to a combination that already exists
    rule_2['event_type'] = rule_1['event_type']
    rule_2['event_subtype'] = rule_1['event_subtype']
    rule_2['counterparty'] = rule_1['counterparty']
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ), json={
            'identifier': 2,
            **rule_2,
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='already exists in the database',
        status_code=HTTPStatus.CONFLICT,
    )

    # try to delete now rule 1
    # query the data and see that it got updated
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ), json={'identifier': 1},
    )
    assert_simple_ok_response(response)

    # query the data and see that it got updated
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 1
    assert len(result['entries']) == 1
    assert result['entries_total'] == 1


def test_rules_info(rotkehlchen_api_server):
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'accountinglinkablepropertiesresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert set(result.keys()) == set(get_args(LINKABLE_ACCOUNTING_PROPERTIES))
