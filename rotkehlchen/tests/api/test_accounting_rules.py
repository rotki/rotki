import json
import random
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal, get_args

import pytest
import requests

from rotkehlchen.accounting.types import EventAccountingRuleStatus
from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.ethereum.modules.compound.constants import CPT_COMPOUND
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment
from rotkehlchen.constants.assets import A_CUSDC, A_USDC
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.constants import (
    LINKABLE_ACCOUNTING_PROPERTIES,
    NO_ACCOUNTING_COUNTERPARTY,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.tests.utils.history_base_entry import add_entries, store_and_retrieve_events
from rotkehlchen.types import Location, TimestampMS


def _update_rules(rotki: Rotkehlchen, latest_accounting_rules: list[tuple[int, Path]]) -> None:
    """Pull remote accounting rules and save them"""
    data_updater = RotkiDataUpdater(msg_aggregator=rotki.msg_aggregator, user_db=rotki.data.db)
    for version, jsonfile in latest_accounting_rules:
        data_updater.update_accounting_rules(
            data=json.loads(jsonfile.read_text(encoding='utf-8'))['accounting_rules'],
            version=version,
            force_updates=False,  # TODO: This should adjust / go away. Related to https://github.com/orgs/rotki/projects/11?pane=issue&itemId=96831912  # noqa: E501
        )


def _setup_conflict_tests(
        rotkehlchen_api_server: APIServer,
        latest_accounting_rules: list[tuple[int, Path]],
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
        'accounting_treatment': TxAccountingTreatment.SWAP.serialize(),
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

    # pull only the first remote update (so that new rules don't mess with our tests)
    _update_rules(rotki=rotki, latest_accounting_rules=latest_accounting_rules[:1])

    # check the conflicts
    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute('SELECT local_id FROM unresolved_remote_conflicts')
        assert cursor.fetchall() == [(1,), (2,)]


@pytest.mark.parametrize('initialize_accounting_rules', [True])
def test_query_rules(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that querying accounting rules works fine"""
    response = requests.post(
        api_url_for(  # test matching counterparty None
            rotkehlchen_api_server,
            'accountingrulesresource',
        ), json={
            'event_types': ['deposit'],
            'event_subtypes': ['deposit_asset'],
            'counterparties': [None],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 1
    assert result['entries_found'] == 1
    assert result['entries_total'] != 0


@pytest.mark.parametrize('db_settings', [{'include_crypto2crypto': False}])
@pytest.mark.parametrize('initialize_accounting_rules', [False])
def test_manage_rules(rotkehlchen_api_server: 'APIServer', db_settings: dict[str, bool]) -> None:
    """Test basic operations in the endpoint for managing accounting rules"""
    rule_1: dict[str, Any] = {
        'taxable': {'value': True, 'linked_setting': 'include_crypto2crypto'},
        'count_entire_amount_spend': {
            'value': False,
            'linked_setting': 'include_crypto2crypto',
        },
        'count_cost_basis_pnl': {'value': True},
        'event_type': HistoryEventType.DEPOSIT.serialize(),
        'event_subtype': HistoryEventSubType.SPEND.serialize(),
        'counterparty': 'uniswap',
        'event_ids': None,
    }
    rule_2: dict[str, Any] = {
        'taxable': {'value': True},
        'count_entire_amount_spend': {'value': False},
        'count_cost_basis_pnl': {'value': True},
        'event_type': HistoryEventType.STAKING.serialize(),
        'event_subtype': HistoryEventSubType.SPEND.serialize(),
        'counterparty': None,
        'event_ids': None,
        'accounting_treatment': 'swap',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ), json=rule_1,
    )
    assert_proper_sync_response_with_result(response)
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ), json=rule_2,
    )
    assert_proper_sync_response_with_result(response)

    # now try to query them
    rule_1_copy = rule_1.copy()
    rule_1_copy['taxable']['value'] = db_settings['include_crypto2crypto']
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_found'] == 1
    assert len(result['entries']) == 1
    assert result['entries_total'] == 1


def test_rules_info(rotkehlchen_api_server: 'APIServer') -> None:
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'accountinglinkablepropertiesresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert set(result.keys()) == set(get_args(LINKABLE_ACCOUNTING_PROPERTIES))


@pytest.mark.parametrize('initialize_accounting_rules', [False])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_solving_conflicts(
        rotkehlchen_api_server: APIServer,
        latest_accounting_rules: list[tuple[int, Path]],
) -> None:
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
        latest_accounting_rules: list[tuple[int, Path]],
        solve_all_using: Literal['remote', 'local'],
) -> None:
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
        latest_accounting_rules: list[tuple[int, Path]],
) -> None:
    """Test that serialization for conflicts works as expected"""
    _setup_conflict_tests(rotkehlchen_api_server, latest_accounting_rules)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'accountingrulesconflictsresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
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
                'accounting_treatment': 'swap',
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
def test_cache_invalidation(rotkehlchen_api_server: APIServer) -> None:
    """
    Test that the cache for events affected by an accounting rule gets correctly invalidated
    when operations happen modifying the rule that affects them.
    """
    rest = rotkehlchen_api_server.rest_api
    rotki = rest.rotkehlchen
    database = rotki.data.db

    tx_hash = make_evm_tx_hash()
    return_wrapped = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_CUSDC,
        amount=ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        counterparty=CPT_COMPOUND,
        notes='my notes',
    )
    remove_asset = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(16433333000),
        location=Location.ETHEREUM,
        asset=A_USDC,
        amount=ONE,
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
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 2
    assert all(
        entry['event_accounting_rule_status'] == EventAccountingRuleStatus.NOT_PROCESSED.serialize()  # noqa: E501
        for entry in result['entries']
    )

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
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 2
    assert result['entries'][0]['event_accounting_rule_status'] == EventAccountingRuleStatus.HAS_RULE.serialize()  # noqa: E501
    assert result['entries'][1]['event_accounting_rule_status'] == EventAccountingRuleStatus.NOT_PROCESSED.serialize()  # noqa: E501

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
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 2
    assert result['entries'][0]['event_accounting_rule_status'] == EventAccountingRuleStatus.HAS_RULE.serialize()  # noqa: E501
    assert result['entries'][1]['event_accounting_rule_status'] == EventAccountingRuleStatus.PROCESSED.serialize()  # noqa: E501

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
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 2
    all(
        entry['event_accounting_rule_status'] == EventAccountingRuleStatus.NOT_PROCESSED.serialize()  # noqa: E501
        for entry in result['entries']
    )


@pytest.mark.parametrize('initialize_accounting_rules', [False])
def test_manage_rules_with_event_ids(rotkehlchen_api_server: 'APIServer') -> None:
    """Test operations with accounting rules that have event_ids"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    existing_entries = add_entries(DBHistoryEvents(rotki.data.db))

    base_rule: dict[str, Any] = {
        'taxable': {'value': True},
        'count_entire_amount_spend': {'value': False},
        'count_cost_basis_pnl': {'value': True},
        'event_type': HistoryEventType.INFORMATIONAL.serialize(),
        'event_subtype': HistoryEventSubType.APPROVE.serialize(),
        'counterparty': 'uniswap-v2',
        'accounting_treatment': TxAccountingTreatment.SWAP.serialize(),
    }

    # Test various invalid event field cases
    for event_ids, expected_error in [
        ([50_000], 'Event identifiers {50000} are nonexistent or do not match the specified event type/subtype combination.'),  # noqa: E501
        ([-100], 'Must be greater than or equal to 0'),
        (['420'], 'Not a valid integer'),
    ]:
        invalid_rule = base_rule.copy()
        invalid_rule['event_ids'] = event_ids
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
            json=invalid_rule,
        )
        assert_error_response(
            response=response,
            contained_in_msg=expected_error,
            status_code=HTTPStatus.BAD_REQUEST,
        )

    # Test adding rule with valid event_id and sequence_index
    valid_rule = base_rule.copy()
    valid_rule['event_ids'] = [existing_entries[0].identifier]
    assert_proper_sync_response_with_result(requests.put(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
        json=valid_rule,
    ))
    valid_rule.update({'identifier': 1})
    assert (entries := assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
    ))['entries']) == [valid_rule]

    # Test updating rule with event_id and sequence_index
    updated_rule = valid_rule.copy()
    another_event = existing_entries[1]  # Use another INFORMATIONAL/APPROVE event
    updated_rule['event_ids'].append(another_event.identifier)
    updated_rule['taxable'] = {'value': False}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
        json={
            'identifier': (rule_id := entries[0]['identifier']),  # since we've only added one entry  # noqa: E501
            **updated_rule,
        },
    )
    assert_simple_ok_response(response)
    updated_rule['identifier'] = rule_id
    assert assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
    ))['entries'] == [updated_rule]

    # Test removing the rule
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
        json={'identifier': rule_id},
    )
    assert_simple_ok_response(response)
    assert len(assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
    ))['entries']) == 0


@pytest.mark.parametrize('initialize_accounting_rules', [True])
def test_import_export_accounting_rules(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that exporting and importing accounting rules works fine."""
    async_query = random.choice([True, False])
    with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
        initial_rules = cursor.execute(
            'SELECT * FROM accounting_rules WHERE identifier IN (1, 82);',
        ).fetchall()
        initial_properties = cursor.execute('SELECT * FROM linked_rules_properties').fetchall()

    with TemporaryDirectory() as temp_directory:
        response = requests.post(
            api_url_for(  # export the accounting rules as a response json
                rotkehlchen_api_server,
                'accountingrulesexportresource',
            ), json={'async_query': async_query},
        )
        response_result = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
        )

        response = requests.post(
            api_url_for(  # export the accounting rules into a json file
                rotkehlchen_api_server,
                'accountingrulesexportresource',
            ), json={'async_query': async_query, 'directory_path': temp_directory},
        )
        assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
        )

        rules_file_path = Path(temp_directory) / 'accounting_rules.json'
        with open(rules_file_path, encoding='utf-8') as file:
            rules_data = json.load(file)

        changed_rules, all_rules_num = 2, 119  # changed rules is rules that were modified. This pushes identifier up  # noqa: E501
        assert rules_data == response_result
        assert len(rules_data['accounting_rules']) == all_rules_num
        assert rules_data['accounting_rules']['1'] == {
            'event_type': 'deposit',
            'event_ids': None,
            'event_subtype': 'deposit asset',
            'counterparty': 'aave-v1',
            'rule': {
                'taxable': {'value': False},
                'count_entire_amount_spend': {'value': False},
                'count_cost_basis_pnl': {'value': True},
                'accounting_treatment': 'swap',
            },
        }
        assert rules_data['accounting_rules']['82'] == {
            'event_type': 'deposit',
            'event_subtype': 'fee',
            'event_ids': None,
            'counterparty': None,
            'rule': {
                'taxable': {'value': True},
                'count_entire_amount_spend': {'value': False},
                'count_cost_basis_pnl': {'value': True},
                'accounting_treatment': None,
            },
        }
        assert rules_data['linked_properties'] == {
            '1': {
                'accounting_rule': 46,
                'property_name': 'count_cost_basis_pnl',
                'setting_name': 'include_crypto2crypto',
            },
            '2': {
                'accounting_rule': 65,
                'property_name': 'taxable',
                'setting_name': 'include_gas_costs',
            },
            '3': {
                'accounting_rule': 65,
                'property_name': 'count_entire_amount_spend',
                'setting_name': 'include_gas_costs',
            },
            '4': {
                'accounting_rule': 65,
                'property_name': 'count_cost_basis_pnl',
                'setting_name': 'include_crypto2crypto',
            },
        }

        # edit the rules and setting properties
        with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'UPDATE accounting_rules SET identifier=? WHERE identifier=?',
                (all_rules_num + changed_rules + 1, all_rules_num + changed_rules),
            )
            write_cursor.execute(
                'UPDATE linked_rules_properties SET setting_name=? WHERE identifier=?',
                ('include_gas_costs', '2'),
            )

        response = requests.put(
            api_url_for(  # import the accounting rules from this json file
                rotkehlchen_api_server,
                'accountingrulesimportresource',
            ), json={'async_query': async_query, 'filepath': rules_file_path.as_posix()},
        )
        response_result = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
        )

        with open(rules_file_path, encoding='utf-8') as file:
            response = requests.patch(
                api_url_for(  # also as multipart/form-data
                    rotkehlchen_api_server,
                    'accountingrulesimportresource',
                ), data={'async_query': async_query}, files={'filepath': file},
            )
        response_result = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
        )

    # Check that the imported rules are in the DB
    with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT * FROM accounting_rules WHERE identifier IN (1, 82);',
        ).fetchall() == [
            (1, 'deposit', 'deposit asset', 'aave-v1', 0, 0, 1, 'A', 0),
            (82, 'deposit', 'fee', NO_ACCOUNTING_COUNTERPARTY, 1, 0, 1, None, 0),
        ] == initial_rules

        assert cursor.execute('SELECT * FROM linked_rules_properties').fetchall() == [
            (1, 46, 'count_cost_basis_pnl', 'include_crypto2crypto'),
            (2, 65, 'taxable', 'include_gas_costs'),
            (3, 65, 'count_entire_amount_spend', 'include_gas_costs'),
            (4, 65, 'count_cost_basis_pnl', 'include_crypto2crypto'),
        ] == initial_properties


@pytest.mark.parametrize('initialize_accounting_rules', [False])
def test_query_accounting_rules_by_identifiers(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that querying accounting rules by identifiers works"""
    for rule in (rules := [{  # create three rules
        'taxable': {'value': False},
        'count_entire_amount_spend': {'value': True},
        'count_cost_basis_pnl': {'value': False},
        'event_type': HistoryEventType.WITHDRAWAL.serialize(),
        'event_subtype': HistoryEventSubType.RECEIVE.serialize(),
        'counterparty': 'compound',
    }, {
        'taxable': {'value': True},
        'count_entire_amount_spend': {'value': False},
        'count_cost_basis_pnl': {'value': True},
        'event_type': HistoryEventType.DEPOSIT.serialize(),
        'event_subtype': HistoryEventSubType.SPEND.serialize(),
        'counterparty': 'uniswap',
    }, {
        'taxable': {'value': False},
        'count_entire_amount_spend': {'value': True},
        'count_cost_basis_pnl': {'value': False},
        'event_type': HistoryEventType.WITHDRAWAL.serialize(),
        'event_subtype': HistoryEventSubType.RECEIVE.serialize(),
        'counterparty': 'curve',
    }]):
        assert_simple_ok_response(requests.put(
            api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
            json=rule,
        ))

    response = requests.post(  # get all rules to find their IDs
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == len(rules)

    rule_1_id, rule_2_id = None, None
    for entry in result['entries']:
        if entry['counterparty'] == 'compound':
            rule_1_id = entry['identifier']
        elif entry['counterparty'] == 'uniswap':
            rule_2_id = entry['identifier']

    assert all([rule_1_id, rule_2_id])

    # Test querying by single identifier
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
        json={'identifiers': [rule_1_id]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 1
    assert result['entries'][0]['identifier'] == rule_1_id
    assert result['entries'][0]['counterparty'] == 'compound'

    # Test querying by multiple identifiers
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
        json={'identifiers': [rule_1_id, rule_2_id], 'counterparties': ['uniswap', 'compound']},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == len(rules) - 1
    assert {entry['identifier'] for entry in result['entries']} == {rule_1_id, rule_2_id}

    # Test querying by non-existent identifier
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
        json={'identifiers': [99999]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 0
    assert result['entries_found'] == 0


@pytest.mark.parametrize('initialize_accounting_rules', [False])
def test_query_accounting_rules_with_event_ids_filter(rotkehlchen_api_server: 'APIServer') -> None:
    """Test filtering accounting rules by event ids & custom_rule_handling parameter"""
    # First create some history events using the existing test helper
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    existing_entries = add_entries(DBHistoryEvents(rotki.data.db))
    for rule in [{
        'taxable': {'value': True},
        'count_entire_amount_spend': {'value': False},
        'count_cost_basis_pnl': {'value': True},
        'event_type': HistoryEventType.DEPOSIT.serialize(),
        'event_subtype': HistoryEventSubType.DEPOSIT_ASSET.serialize(),
        'event_ids': [existing_entries[3].identifier],
        'counterparty': 'somewhere',
    }, {
        'taxable': {'value': False},
        'count_entire_amount_spend': {'value': True},
        'count_cost_basis_pnl': {'value': False},
        'event_type': HistoryEventType.WITHDRAWAL.serialize(),
        'event_subtype': HistoryEventSubType.RECEIVE.serialize(),
    }]:
        assert_simple_ok_response(requests.put(
            api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
            json=rule,
        ))

    # Test: Get all rules (default behavior - custom_rule_handling=all)
    response = requests.post(api_url_for(rotkehlchen_api_server, 'accountingrulesresource'))
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 2, 'Should have gotten both rules'

    # Test: Get only rules with event_ids
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
        json={'custom_rule_handling': 'only'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 1, 'Should only get the event-specific rule'
    assert result['entries'][0]['event_ids'] == [existing_entries[3].identifier]
    assert result['entries'][0]['counterparty'] == 'somewhere'
    assert result['entries'][0]['event_type'] == HistoryEventType.DEPOSIT.serialize()

    # Test: Get only rules without event_ids
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
        json={'custom_rule_handling': 'exclude'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 1, 'Should only get the generic rule'
    assert result['entries'][0]['event_ids'] is None
    assert result['entries'][0]['counterparty'] is None
    assert result['entries'][0]['event_type'] == HistoryEventType.WITHDRAWAL.serialize()

    # Test: Get rules by filtering the with event_ids
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
        json={'event_ids': [existing_entries[3].identifier]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 1, 'Should only get the specific rule'
    assert result['entries'][0]['event_ids'] == [existing_entries[3].identifier]
    assert result['entries'][0]['counterparty'] == 'somewhere'
    assert result['entries'][0]['event_type'] == HistoryEventType.DEPOSIT.serialize()

    # Test mutual exclusion validation
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
        json={'custom_rule_handling': 'only', 'event_ids': [existing_entries[3].identifier]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Cannot use both custom_rule_handling and event_ids parameters together',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('initialize_accounting_rules', [False])
def test_pagination_with_multiple_event_ids(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that pagination works correctly with accounting rules that have multiple event IDs"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    existing_entries = add_entries(DBHistoryEvents(rotki.data.db))
    for rule in [{  # Add both rules
        'taxable': {'value': True},
        'count_entire_amount_spend': {'value': False},
        'count_cost_basis_pnl': {'value': True},
        'event_type': HistoryEventType.INFORMATIONAL.serialize(),
        'event_subtype': HistoryEventSubType.APPROVE.serialize(),
        'event_ids': [existing_entries[i].identifier for i in range(2)],
        'counterparty': (event_specific_cpt := 'uniswap'),
    }, {
        'taxable': {'value': False},
        'count_entire_amount_spend': {'value': True},
        'count_cost_basis_pnl': {'value': False},
        'event_type': HistoryEventType.WITHDRAWAL.serialize(),
        'event_subtype': HistoryEventSubType.RECEIVE.serialize(),
        'counterparty': (regular_rule_cpt := 'compound'),
    }]:
        assert_simple_ok_response(requests.put(
            api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
            json=rule,
        ))

    # Test pagination with limit=1 to ensure each rule is counted as 1, not by number of events
    for offset, counterparty in [(0, regular_rule_cpt), (1, event_specific_cpt)]:
        result = assert_proper_sync_response_with_result(requests.post(
            api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
            json={'limit': 1, 'offset': offset},
        ))
        assert len(result['entries']) == 1
        assert result['entries_total'] == 2
        assert result['entries'][0]['counterparty'] == counterparty

    # test getting all rules at once
    result = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'accountingrulesresource'),
        json={'limit': 10, 'offset': 0},
    ))
    assert len(result['entries']) == result['entries_found'] == result['entries_total'] == 2
    # Verify one rule has multiple event IDs and one has none
    rules_by_counterparty = {rule['counterparty']: rule for rule in result['entries']}
    assert len(rules_by_counterparty['uniswap']['event_ids']) == 2
    assert rules_by_counterparty['compound']['event_ids'] is None
