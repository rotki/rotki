import json
from http import HTTPStatus
from pathlib import Path
from typing import Literal, get_args

import pytest
import requests

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.api.server import APIServer
from rotkehlchen.db.constants import LINKABLE_ACCOUNTING_PROPERTIES
from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
)


def _update_rules(rotki: Rotkehlchen, latest_accounting_rules: Path) -> None:
    """Pull remote accounting rules and save them"""
    data_updater = RotkiDataUpdater(msg_aggregator=rotki.msg_aggregator, user_db=rotki.data.db)
    with open(latest_accounting_rules, encoding='utf-8') as f:
        data_updater.update_accounting_rules(
            data=json.loads(f.read())['accounting_rules'],
            version=999999,
        )


def _setup_conflict_tests(
        rotkehlchen_api_server: APIServer,
        latest_accounting_rules: Path,
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rule_1 = {
        'taxable': {'value': True, 'linked_setting': 'include_crypto2crypto'},
        'count_entire_amount_spend': {
            'value': False,
            'linked_setting': 'include_crypto2crypto',
        },
        'count_cost_basis_pnl': {'value': True},
        'event_type': HistoryEventType.SPEND.serialize(),
        'event_subtype': HistoryEventSubType.RETURN_WRAPPED.serialize(),
        'counterparty': 'compound',
    }
    rule_2 = {
        'taxable': {'value': True, 'linked_setting': 'include_crypto2crypto'},
        'count_entire_amount_spend': {'value': False},
        'count_cost_basis_pnl': {'value': True},
        'event_type': HistoryEventType.STAKING.serialize(),
        'event_subtype': HistoryEventSubType.DEPOSIT_ASSET.serialize(),
        'counterparty': None,
    }
    for rule in (rule_1, rule_2):
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'accountingrulesresource',
            ), json=rule,
        )
        assert_simple_ok_response(response)

    # pull remote updates
    _update_rules(rotki=rotki, latest_accounting_rules=latest_accounting_rules)

    # check the conflicts
    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute('SELECT local_id FROM unresolved_remote_conflicts')
        assert cursor.fetchall() == [(1,), (2,)]


@pytest.mark.parametrize('db_settings', [{'include_crypto2crypto': False}])
@pytest.mark.parametrize('initialize_accounting_rules', [False])
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


@pytest.mark.parametrize('initialize_accounting_rules', [False])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_solving_conflicts(
        rotkehlchen_api_server: APIServer,
        latest_accounting_rules: Path,
):
    """Test solving conflicts using a different method for each rule"""
    _setup_conflict_tests(rotkehlchen_api_server, latest_accounting_rules)
    conflict_resolution = [
        {'local_id': 1, 'solve_using': 'remote'},
        {'local_id': 2, 'solve_using': 'local'},
    ]
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesconflictsresource',
        ), json={'conflicts': conflict_resolution},
    )
    assert_simple_ok_response(response)

    # check that we don't have conflicts
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*) FROM unresolved_remote_conflicts')
        assert cursor.fetchone()[0] == 0  # there shouldn't be any conflict
        cursor.execute('SELECT taxable FROM accounting_rules WHERE identifier=?', (1,))
        assert cursor.fetchone()[0] == 0  # remote version has it as false
        cursor.execute('SELECT taxable FROM accounting_rules WHERE identifier=?', (2,))
        assert cursor.fetchone()[0] == 1  # local version has it as true


@pytest.mark.parametrize('initialize_accounting_rules', [False])
@pytest.mark.parametrize('solve_all_using', ['remote', 'local'])
def test_solving_conflicts_all(
        rotkehlchen_api_server: APIServer,
        latest_accounting_rules: Path,
        solve_all_using: Literal['remote', 'local'],
):
    """Test that solving all the conflicts using either local or remote works"""
    _setup_conflict_tests(rotkehlchen_api_server, latest_accounting_rules)
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesconflictsresource',
        ), json={'solve_all_using': solve_all_using},
    )
    assert_simple_ok_response(response)

    # check that we don't have conflicts
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*) FROM unresolved_remote_conflicts')
        assert cursor.fetchone()[0] == 0  # there shouldn't be any conflict

        if solve_all_using == 'local':
            cursor.execute('SELECT taxable FROM accounting_rules WHERE identifier=?', (1,))
            assert cursor.fetchone()[0] == 1  # remote version has it as false
            cursor.execute('SELECT taxable FROM accounting_rules WHERE identifier=?', (2,))
            assert cursor.fetchone()[0] == 1  # local version has it as true
        else:
            cursor.execute('SELECT taxable FROM accounting_rules WHERE identifier=?', (1,))
            assert cursor.fetchone()[0] == 0  # remote version has it as false
            cursor.execute('SELECT taxable FROM accounting_rules WHERE identifier=?', (2,))
            assert cursor.fetchone()[0] == 0  # local version has it as true


@pytest.mark.parametrize('initialize_accounting_rules', [False])
def test_listing_conflicts(
        rotkehlchen_api_server: APIServer,
        latest_accounting_rules: Path,
):
    """Test that serialization for conflicts works as expected"""
    _setup_conflict_tests(rotkehlchen_api_server, latest_accounting_rules)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesconflictsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result['entries'] == [
        {
            'local_id': 2,
            'local_data': {
                'taxable': {'value': True, 'linked_setting': 'include_crypto2crypto'},
                'count_cost_basis_pnl': {'value': True},
                'count_entire_amount_spend': {'value': False},
                'accounting_treatment': None,
                'event_type': 'staking',
                'event_subtype': 'deposit asset',
                'counterparty': None,
            },
            'remote_data': {
                'taxable': {'value': False},
                'count_cost_basis_pnl': {'value': False},
                'count_entire_amount_spend': {'value': False},
                'accounting_treatment': None,
                'event_type': 'staking',
                'event_subtype': 'deposit asset',
                'counterparty': None,
            },
        }, {
            'local_id': 1,
            'local_data': {
                'taxable': {'value': True, 'linked_setting': 'include_crypto2crypto'},
                'count_cost_basis_pnl': {'value': True},
                'count_entire_amount_spend': {
                    'value': False,
                    'linked_setting': 'include_crypto2crypto',
                },
                'accounting_treatment': None,
                'event_type': 'spend',
                'event_subtype': 'return wrapped',
                'counterparty': 'compound',
            },
            'remote_data': {
                'taxable': {'value': False},
                'count_cost_basis_pnl': {'value': False},
                'count_entire_amount_spend': {'value': False},
                'accounting_treatment': 'swap',
                'event_type': 'spend',
                'event_subtype': 'return wrapped',
                'counterparty': 'compound',
            },
        },
    ]
    assert result['entries_total'] == 2
