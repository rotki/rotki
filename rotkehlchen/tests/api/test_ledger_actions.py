from http import HTTPStatus
from typing import Dict, List

import pytest
import requests

from rotkehlchen.history.events import FREE_LEDGER_ACTIONS_LIMIT
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)


def _add_ledger_actions(server) -> List[Dict]:
    actions = [{
        'timestamp': 1,
        'action_type': 'income',
        'location': 'blockchain',
        'amount': '1.5',
        'asset': 'ETH',
        'link': 'explorer link',
        'notes': 'donation for something',
    }, {
        'timestamp': 2,
        'action_type': 'expense',
        'location': 'blockchain',
        'amount': '5',
        'asset': 'DAI',
        'link': 'explorer link',
        'notes': 'Spent 5 DAI for something',
    }, {
        'timestamp': 3,
        'action_type': 'loss',
        'location': 'external',
        'amount': '100',
        'asset': 'EUR',
        'link': '',
        'notes': 'Got robbed',
    }, {
        'timestamp': 4,
        'action_type': 'dividends income',
        'location': 'external',
        'amount': '75',
        'asset': 'EUR',
        'link': '',
        'notes': 'Income from APPL dividends',
    }]

    for action in actions:
        response = requests.put(
            api_url_for(server, "ledgeractionsresource"),
            json=action,
        )
        result = assert_proper_response_with_result(response)
        assert 'identifier' in result
        action['identifier'] = int(result['identifier'])

    return actions


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_and_query_ledger_actions(rotkehlchen_api_server):
    """Test that querying the ledger actions endpoint works as expected
    """
    actions = _add_ledger_actions(rotkehlchen_api_server)

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "ledgeractionsresource",
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 4
    assert result['entries_limit'] == FREE_LEDGER_ACTIONS_LIMIT
    assert all(x['ignored_in_accounting'] is False for x in result['entries']), 'by default nothing should be ignored'  # noqa: E501
    result = [x['entry'] for x in result['entries']]
    assert result == actions

    # now let's ignore some ledger actions for accounting
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "ignoredactionsresource",
        ), json={'action_type': 'ledger action', 'action_ids': ['3', '4']},  # external ones
    )
    result = assert_proper_response_with_result(response)
    assert result == {'ledger action': [str(a['identifier']) for a in actions[2:]]}

    # Now filter by location with json body
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "ledgeractionsresource",
        ), json={'location': 'external'},
    )
    result = assert_proper_response_with_result(response)
    result = result['entries']
    assert all(x['ignored_in_accounting'] for x in result), 'all external should be ignored'
    result = [x['entry'] for x in result]
    assert result == actions[2:]

    # Now filter by location with query param
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "ledgeractionsresource",
        ) + '?location=external',
    )
    result = assert_proper_response_with_result(response)
    result = result['entries']
    assert all(x['ignored_in_accounting'] for x in result), 'all external should be ignored'
    result = [x['entry'] for x in result]
    assert result == actions[2:]

    # Now filter by time
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "ledgeractionsresource",
        ), json={'from_timestamp': 1, 'to_timestamp': 2},
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == actions[:2]

    # and finally filter by both time and location
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "ledgeractionsresource",
        ), json={'from_timestamp': 2, 'to_timestamp': 3, 'location': 'blockchain'},
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == actions[1:2]


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_edit_ledger_actions(rotkehlchen_api_server):
    """Test that editing the ledger actions endpoint works as expected"""
    actions = _add_ledger_actions(rotkehlchen_api_server)

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "ledgeractionsresource",
        ),
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == actions

    new_action = actions[1]
    new_action['timestamp'] = 1337
    new_action['location'] = 'kraken'
    new_action['action_type'] = 'airdrop'
    new_action['amount'] = '10'
    new_action['asset'] = 'ETH'
    new_action['link'] = 'a link'
    new_action['notes'] = 'new notes'

    # Now get the actions and make sure that one is edited
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "ledgeractionsresource",
        ), json={'action': new_action},
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == [actions[0], actions[2], actions[3], actions[1]]

    # Try to edit unknown identifier and see it fails
    new_action['identifier'] = 666
    new_action['action_type'] = 'loss'
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "ledgeractionsresource",
        ), json={'action': new_action},
    )
    assert_error_response(
        response,
        contained_in_msg=(
            f'Tried to edit ledger action with identifier {new_action["identifier"]}'
            f' but it was not found in the DB',
        ),
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_delete_ledger_actions(rotkehlchen_api_server):
    """Test that deleting from the ledger actions endpoint works as expected"""
    actions = _add_ledger_actions(rotkehlchen_api_server)

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "ledgeractionsresource",
        ),
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == actions

    # Now delete one
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "ledgeractionsresource",
        ), json={'identifier': 2},
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == [actions[0], actions[2], actions[3]]

    # Try to delete unknown identifier and see it fails
    identifier = 666
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "ledgeractionsresource",
        ), json={'identifier': identifier},
    )
    assert_error_response(
        response,
        contained_in_msg=(
            f'Tried to remove ledger action with identifier {identifier}'
            f' but it was not found in the DB',
        ),
        status_code=HTTPStatus.CONFLICT,
    )
