from http import HTTPStatus
from typing import List, Tuple

import pytest
import requests

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USD
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)
from rotkehlchen.typing import Location


def _populate_ignored_actions(rotkehlchen_api_server) -> List[Tuple[str, List[str]]]:
    data = [
        ('trade', ['1', '2', '3']),
        ('asset movement', ['1', '4', '5', '7']),
        ('ethereum transaction', ['5a', 'aa', 'ba']),
        ('ledger action', ['1', '2', '3']),
    ]

    for action_type, action_ids in data:
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                "ignoredactionsresource",
            ), json={'action_type': action_type, 'action_ids': action_ids},
        )
        result = assert_proper_response_with_result(response)
        assert result == {action_type: action_ids}

    return data


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_get_ignored_actions(rotkehlchen_api_server):
    data = _populate_ignored_actions(rotkehlchen_api_server)

    # get only one type via json args
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "ignoredactionsresource",
        ), json={'action_type': data[1][0]},
    )
    result = assert_proper_response_with_result(response)
    assert result == {data[1][0]: data[1][1]}

    # get only one type via query args
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "ignoredactionsresource",
        ) + f'?action_type={data[2][0]}',
    )
    result = assert_proper_response_with_result(response)
    assert result == {data[2][0]: data[2][1]}

    # get all entries
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "ignoredactionsresource",
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == {entry[0]: entry[1] for entry in data}

    # try to add at least one already existing id
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "ignoredactionsresource",
        ), json={'action_type': 'trade', 'action_ids': ['1', '9', '11']},
    )
    result = assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='One of the given action ids already exists in the dataase',
    )

    # get all entries again and make sure nothing new slipped in
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "ignoredactionsresource",
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == {entry[0]: entry[1] for entry in data}


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_remove_ignored_actions(rotkehlchen_api_server):
    data = _populate_ignored_actions(rotkehlchen_api_server)

    # get all entries and make sure they are there
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "ignoredactionsresource",
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == {entry[0]: entry[1] for entry in data}

    # remove a few entries of one type
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "ignoredactionsresource",
        ), json={'action_type': 'asset movement', 'action_ids': ['1', '7']},
    )
    result = assert_proper_response_with_result(response)
    assert result == {'asset movement': ['4', '5']}

    # remove all entries of one type
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "ignoredactionsresource",
        ), json={'action_type': 'ethereum transaction', 'action_ids': data[2][1]},
    )
    result = assert_proper_response_with_result(response)
    assert result == {}

    # try to remove non existing entries
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "ignoredactionsresource",
        ), json={'action_type': 'ledger action', 'action_ids': ['1', '5', '2']},
    )
    result = assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='Tried to remove 1 ignored actions that do not exist',
    )

    # get all entries again and make sure deleted ones do not appear
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "ignoredactionsresource",
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == {
        'asset movement': ['4', '5'],
        'ledger action': ['1', '2', '3'],
        'trade': ['1', '2', '3'],
    }


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_ignore_ledger_actions_in_accountant(rotkehlchen_api_server, accountant):
    """Test that ignored ledger actions are correctly ignored by the accountant"""
    ledger_actions_list = [
        LedgerAction(
            identifier=1,
            timestamp=1467279735,
            action_type=LedgerActionType.INCOME,
            location=Location.BLOCKCHAIN,
            amount=FVal(1000),
            asset=A_ETH,
            rate=FVal(100),
            rate_asset=A_USD,
            link=None,
            notes=None,
        ), LedgerAction(
            identifier=2,
            timestamp=1467279735,
            action_type=LedgerActionType.EXPENSE,
            location=Location.BLOCKCHAIN,
            amount=FVal(5),
            asset=A_DAI,
            rate=None,
            rate_asset=None,
            link='foo',
            notes='boo',
        ),
    ]

    # Set the server to ignore second ledger action
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'action_type': 'ledger action', 'action_ids': ['2']},
    )
    result = assert_proper_response_with_result(response)
    assert result == {'ledger action': ['2']}

    # Retrieve ignored actions mapping. Should contain 2
    ignored_actions = accountant.db.get_ignored_action_ids(action_type=None)
    ignored = []
    # Call the should_ignore method used in the accountant
    for action in ledger_actions_list:
        should_ignore, _ = accountant._should_ignore_action(
            action=action,
            action_type='ledger_action',
            ignored_actionids_mapping=ignored_actions,
        )
        ignored.append(should_ignore)

    assert ignored == [False, True]
