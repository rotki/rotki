import json
from http import HTTPStatus
from pathlib import Path
from typing import Literal, get_args

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.ethereum.modules.compound.constants import CPT_COMPOUND
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment
from rotkehlchen.constants.assets import A_CUSDC, A_USDC
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.constants import LINKABLE_ACCOUNTING_PROPERTIES
from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.tests.utils.history_base_entry import store_and_retrieve_events
from rotkehlchen.types import Location, TimestampMS


def _update_rules(rotki: Rotkehlchen, latest_accounting_rules: Path) -> None:
    """Pull remote accounting rules and save them"""
    data_updater = RotkiDataUpdater(msg_aggregator=rotki.msg_aggregator, user_db=rotki.data.db)
    data_updater.update_accounting_rules(
        data=json.loads(latest_accounting_rules.read_text(encoding='utf-8'))['accounting_rules'],
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


@pytest.mark.parametrize('initialize_accounting_rules', [False])
def test_cache_invalidation(rotkehlchen_api_server: APIServer):
    """
    Test that the cache for events affected by an accounting rule gets correctly invalidated
    when operations happen modifying the rule that affects them.
    """
    rest = rotkehlchen_api_server.rest_api
    rotki = rest.rotkehlchen
    database = rotki.data.db

    tx_hash = make_evm_tx_hash()
    return_wrapped = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_CUSDC,
        balance=Balance(amount=ONE),
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        counterparty=CPT_COMPOUND,
        notes='my notes',
    )
    remove_asset = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_USDC,
        balance=Balance(amount=ONE),
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        counterparty=CPT_COMPOUND,
        notes='my notes',
    )
    events = store_and_retrieve_events([return_wrapped, remove_asset], database)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ), json={'event_identifiers': [events[0].event_identifier]},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 2
    assert all(entry['missing_accounting_rule'] for entry in result['entries'])

    # add a rule for the return event and check that the cache was updated
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ), json={
            'event_type': HistoryEventType.DEPOSIT.serialize(),
            'event_subtype': HistoryEventSubType.DEPOSIT_ASSET.serialize(),
            'counterparty': CPT_COMPOUND,
            'taxable': {'value': True},
            'count_entire_amount_spend': {'value': True},
            'count_cost_basis_pnl': {'value': True},
            'accounting_treatment': None,
        },
    )
    assert_simple_ok_response(response)

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ), json={'event_identifiers': [events[0].event_identifier]},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 2
    assert 'missing_accounting_rule' not in result['entries'][0]
    assert result['entries'][1]['missing_accounting_rule'] is True

    # update a rule to check that it removes the cache from the second event too
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ), json={
            'identifier': 1,
            'event_type': HistoryEventType.DEPOSIT.serialize(),
            'event_subtype': HistoryEventSubType.DEPOSIT_ASSET.serialize(),
            'counterparty': CPT_COMPOUND,
            'taxable': {'value': True},
            'count_entire_amount_spend': {'value': True},
            'count_cost_basis_pnl': {'value': True},
            'accounting_treatment': TxAccountingTreatment.SWAP.serialize(),
        },
    )
    assert_simple_ok_response(response)

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ), json={'event_identifiers': [events[0].event_identifier]},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 2
    for entry in result['entries']:
        assert 'missing_accounting_rule' not in entry

    # delete accounting rule and check that both events will not be processed now
    # update a rule to check that it removes the cache from the second event too
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ), json={'identifier': 1},
    )
    assert_simple_ok_response(response)

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ), json={'event_identifiers': [events[0].event_identifier]},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 2
    all(entry['missing_accounting_rule'] for entry in result['entries'])
