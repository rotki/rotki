from http import HTTPStatus
from typing import Dict, List

import pytest
import requests

from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.constants.limits import FREE_LEDGER_ACTIONS_LIMIT
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now


def _add_ledger_actions(server) -> List[Dict]:
    actions = [{
        'timestamp': 1,
        'action_type': 'income',
        'location': 'blockchain',
        'amount': '1.5',
        'asset': 'ETH',
        'rate': '100',
        'rate_asset': 'USD',
        'link': 'explorer link',
        'notes': 'donation for something',
    }, {
        'timestamp': 2,
        'action_type': 'expense',
        'location': 'blockchain',
        'amount': '5',
        'asset': A_DAI.identifier,
        'rate': '2.353',
        'rate_asset': None,
        'link': 'explorer link',
        'notes': 'Spent 5 DAI for something',
    }, {
        'timestamp': 3,
        'action_type': 'loss',
        'location': 'external',
        'amount': '100',
        'asset': 'EUR',
        'rate': None,
        'rate_asset': None,
        'link': None,
        'notes': 'Got robbed',
    }, {
        'timestamp': 4,
        'action_type': 'dividends income',
        'location': 'external',
        'amount': '75',
        'asset': 'EUR',
        'rate': '1.23',
        'rate_asset': None,
        'link': 'APPL_dividens_income_id',
        'notes': None,
    }]

    for action in actions:
        response = requests.put(
            api_url_for(server, 'ledgeractionsresource'),
            json=action,
        )
        result = assert_proper_response_with_result(response)
        assert 'identifier' in result
        action['identifier'] = int(result['identifier'])

    return actions[::-1]  # return it as the DB would, latest first


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('start_with_valid_premium', [False, True])
def test_add_and_query_ledger_actions(rotkehlchen_api_server, start_with_valid_premium):
    """Test that querying the ledger actions endpoint works as expected"""
    actions = _add_ledger_actions(rotkehlchen_api_server)

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 4
    assert result['entries_total'] == 4
    assert result['entries_limit'] == -1 if start_with_valid_premium else FREE_LEDGER_ACTIONS_LIMIT
    assert all(x['ignored_in_accounting'] is False for x in result['entries']), 'by default nothing should be ignored'  # noqa: E501
    result = [x['entry'] for x in result['entries']]
    assert result == actions

    # now let's ignore some ledger actions for accounting
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'action_type': 'ledger_action', 'action_ids': ['3', '4']},  # external ones
    )
    result = assert_proper_response_with_result(response)
    assert result == {'ledger_action': [str(a['identifier']) for a in actions[0:2][::-1]]}

    # Now filter by location with json body
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json={'location': 'external'},
    )
    result = assert_proper_response_with_result(response)
    result = result['entries']
    assert all(x['ignored_in_accounting'] for x in result), 'all external should be ignored'
    result = [x['entry'] for x in result]
    assert result == actions[0:2]

    # Now filter by location with query param
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ) + '?location=external',
    )
    result = assert_proper_response_with_result(response)
    result = result['entries']
    assert all(x['ignored_in_accounting'] for x in result), 'all external should be ignored'
    result = [x['entry'] for x in result]
    assert result == actions[0:2]

    # Now filter by time
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json={'from_timestamp': 1, 'to_timestamp': 2},
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == actions[2:4]

    # filter by both time and location
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json={'from_timestamp': 2, 'to_timestamp': 3, 'location': 'blockchain'},
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == [actions[2]]

    # filter by ledger action type
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json={'type': 'expense'},
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == [actions[2]]

    # filter by asset
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json={'asset': 'EUR'},
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == [actions[0], actions[1]]

    # filter by asset with timestamp ascending order
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json={'asset': 'EUR', 'order_by_attributes': ['timestamp'], 'ascending': [True]},
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == [actions[1], actions[0]]

    # test offset/limit pagination
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json={'offset': 1, 'limit': 2},
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 4
    assert result['entries_total'] == 4
    result = [x['entry'] for x in result['entries']]
    assert result == [actions[1], actions[2]]

    # test offset/limit pagination with a filter
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json={'offset': 1, 'limit': 2, 'asset': 'EUR'},
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 2
    assert result['entries_total'] == 4
    result = [x['entry'] for x in result['entries']]
    assert result == [actions[1]]

    def assert_order_by(order_by: str):
        """A helper to keep things DRY in the test"""
        data = {'order_by_attributes': [order_by], 'ascending': [False], 'only_cache': True}
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'ledgeractionsresource',
            ), json=data,
        )
        result = assert_proper_response_with_result(response)
        assert result['entries_limit'] == -1 if start_with_valid_premium else FREE_LEDGER_ACTIONS_LIMIT  # noqa: E501
        assert result['entries_total'] == 4
        assert result['entries_found'] == 4
        desc_result = result['entries']
        assert len(desc_result) == 4
        data = {'order_by_attributes': [order_by], 'ascending': [True], 'only_cache': True}
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'ledgeractionsresource',
            ), json=data,
        )
        result = assert_proper_response_with_result(response)
        assert result['entries_limit'] == -1 if start_with_valid_premium else FREE_LEDGER_ACTIONS_LIMIT  # noqa: E501
        assert result['entries_total'] == 4
        assert result['entries_found'] == 4
        asc_result = result['entries']
        assert len(asc_result) == 4
        return desc_result, asc_result

    # test order by location
    desc_result, asc_result = assert_order_by('location')
    assert all(x['entry']['location'] == 'blockchain' for x in desc_result[:2])
    assert all(x['entry']['location'] == 'external' for x in desc_result[2:])
    assert all(x['entry']['location'] == 'external' for x in asc_result[:2])
    assert all(x['entry']['location'] == 'blockchain' for x in asc_result[2:])

    # test order by type
    desc_result, asc_result = assert_order_by('type')
    descending_types = [x['entry']['action_type'] for x in desc_result]
    assert [x['entry']['action_type'] for x in asc_result] == descending_types[::-1]

    # test order by amount
    desc_result, asc_result = assert_order_by('amount')
    for idx, x in enumerate(desc_result):
        if idx < len(desc_result) - 1:
            assert FVal(x['entry']['amount']) >= FVal(desc_result[idx + 1]['entry']['amount'])
    for idx, x in enumerate(asc_result):
        if idx < len(asc_result) - 1:
            assert FVal(x['entry']['amount']) <= FVal(asc_result[idx + 1]['entry']['amount'])

    # test order by rate
    desc_result, asc_result = assert_order_by('rate')
    for idx, x in enumerate(desc_result):
        if idx < len(desc_result) - 1:
            this = FVal(x['entry']['rate']) if x['entry']['rate'] is not None else ZERO
            next_ = FVal(desc_result[idx + 1]['entry']['rate']) if desc_result[idx + 1]['entry']['rate'] is not None else ZERO  # noqa: E501

            assert this >= next_
    for idx, x in enumerate(asc_result):
        if idx < len(asc_result) - 1:
            this = FVal(x['entry']['rate']) if x['entry']['rate'] is not None else ZERO
            next_ = FVal(asc_result[idx + 1]['entry']['rate']) if asc_result[idx + 1]['entry']['rate'] is not None else ZERO  # noqa: E501
            assert this <= next_


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_edit_ledger_actions(rotkehlchen_api_server):
    """Test that editing the ledger actions endpoint works as expected"""
    actions = _add_ledger_actions(rotkehlchen_api_server)

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
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
    new_action['rate'] = '85'
    new_action['rate_asset'] = 'GBP'
    new_action['link'] = 'a link'
    new_action['notes'] = 'new notes'

    # Now get the actions and make sure that one is edited
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json=new_action,
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == [actions[3], actions[2], actions[0], new_action]

    # Try to edit unknown identifier and see it fails
    new_action['identifier'] = 666
    new_action['action_type'] = 'loss'
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json=new_action,
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
            'ledgeractionsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == actions

    # Now delete one
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json={'identifiers': [1, 2]},
    )
    assert_proper_response(response)
    # now check to see that the deleted action is no longer present
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == [actions[0], actions[1]]

    # Try to delete unknown identifier with valid identifiers and see it fails
    identifier = 666
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json={'identifiers': [4, 3, identifier]},
    )
    assert_error_response(
        response,
        contained_in_msg='Tried to delete ledger action(s) but they were not found in the DB',
        status_code=HTTPStatus.CONFLICT,
    )
    # now check to see that the ledger actions were not deleted.
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    result = [x['entry'] for x in result['entries']]
    assert result == [actions[0], actions[1]]


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_edit_ledger_actions_with_timestamp(rotkehlchen_api_server):
    """Test that the user can't pass future dates when creating/editing ledger actions"""
    error_msg = 'Given date cannot be in the future'
    action = {
        'timestamp': Timestamp(ts_now() - 5),
        'action_type': 'dividends income',
        'location': 'external',
        'amount': '75',
        'asset': 'EUR',
        'rate': '1.23',
        'rate_asset': None,
        'link': 'APPL_dividens_income_id',
        'notes': None,
    }

    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'ledgeractionsresource'),
        json=action,
    )
    result = assert_proper_response_with_result(response)
    assert 'identifier' in result
    action['identifier'] = int(result['identifier'])

    # Now add an action with a date after the valid ts_now
    action['timestamp'] = Timestamp(ts_now() + 45)
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'ledgeractionsresource'),
        json=action,
    )
    assert_error_response(
        response,
        contained_in_msg=error_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Try to edit the first action and check that a invalid date fails
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json=action,
    )
    assert_error_response(
        response,
        contained_in_msg=error_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # And finally try to edit with the right date
    action['timestamp'] = Timestamp(ts_now())
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'ledgeractionsresource',
        ), json=action,
    )
    result = assert_proper_response_with_result(response)
