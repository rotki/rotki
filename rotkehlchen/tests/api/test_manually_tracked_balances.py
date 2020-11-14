import random
from contextlib import ExitStack
from copy import deepcopy
from http import HTTPStatus
from typing import Any, Dict, List

import pytest
import requests

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.utils.misc import ts_now


def _populate_tags(api_server):
    tag1 = {
        'name': 'Public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            api_server,
            "tagsresource",
        ), json=tag1,
    )
    assert_proper_response(response)
    tag2 = {
        'name': 'private',
        'description': 'My private accounts',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            api_server,
            "tagsresource",
        ), json=tag2,
    )
    assert_proper_response(response)
    tag3 = {
        'name': 'miner',
        'description': 'My miner accounts',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            api_server,
            "tagsresource",
        ), json=tag3,
    )
    assert_proper_response(response)


def assert_balances_match(
        expected_balances: List[Dict[str, Any]],
        returned_balances: List[Dict[str, Any]],
        expect_found_price: bool = True,
) -> None:
    assert len(returned_balances) == len(expected_balances)
    for idx, entry in enumerate(reversed(returned_balances)):
        for key, val in entry.items():
            if key == 'usd_value':
                if expect_found_price:
                    assert FVal(val) > ZERO
                else:
                    assert FVal(val) == ZERO
                continue
            if key == 'tags':
                if val is None:
                    assert key not in expected_balances[idx] or expected_balances[idx][key] is None
                else:
                    assert set(val) == set(expected_balances[idx][key])
                continue

            msg = f'Expected balances {key} is {expected_balances[idx][key]} but got {val}'
            assert expected_balances[idx][key] == val, msg


def _populate_initial_balances(api_server) -> List[Dict[str, Any]]:
    # Now add some balances
    balances: List[Dict[str, Any]] = [{
        "asset": "XMR",
        "label": "My monero wallet",
        "amount": "50.315",
        "tags": ["public", "mInEr"],
        "location": "blockchain",
    }, {
        "asset": "BTC",
        "label": "My XPUB BTC wallet",
        "amount": "1.425",
        "location": "blockchain",
    }, {
        "asset": "BNB",
        "label": "My BNB in binance",
        "amount": "155",
        "location": "binance",
        "tags": ["private"],
    }]
    response = requests.put(
        api_url_for(
            api_server,
            "manuallytrackedbalancesresource",
        ), json={'balances': balances},
    )
    result = assert_proper_response_with_result(response)
    assert_balances_match(expected_balances=balances, returned_balances=result['balances'])

    return balances


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_add_and_query_manually_tracked_balances(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    """Test that adding and querying manually tracked balances via the API works fine"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=None)
    _populate_tags(rotkehlchen_api_server)
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)

    assert result['balances'] == [], 'In the beginning we should have no entries'

    balances = _populate_initial_balances(rotkehlchen_api_server)

    # now query and make sure the added balances are returned
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)
    assert_balances_match(expected_balances=balances, returned_balances=result['balances'])

    now = ts_now()
    # Also now test for https://github.com/rotki/rotki/issues/942 by querying for all balances
    # causing all balances to be saved and making sure the manual balances also got saved
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                "allbalancesresource",
            ), json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    result = result['assets']
    assert result['BTC']['amount'] == '1.425'
    assert result['XMR']['amount'] == '50.315'
    assert result['BNB']['amount'] == '155'
    # Check DB to make sure a save happened
    assert rotki.data.db.get_last_balance_save_time() >= now
    assert set(rotki.data.db.query_owned_assets()) == {'BTC', 'XMR', 'BNB', 'ETH', 'RDN'}


@pytest.mark.parametrize('mocked_current_prices', [{'CYFM': FVal(0)}])
def test_add_manually_tracked_balances_no_price(rotkehlchen_api_server):
    """Test that adding a manually tracked balance of an asset for which we cant
    query a price is handled properly both in the adding and querying part

    Regression test for https://github.com/rotki/rotki/issues/896"""
    async_query = random.choice([False, True])
    _populate_tags(rotkehlchen_api_server)
    balances: List[Dict[str, Any]] = [{
        "asset": "CYFM",
        "label": "CYFM account",
        "amount": "50.315",
        "tags": ["public"],
        "location": "blockchain",
    }]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'async_query': async_query, 'balances': balances},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)
    assert_balances_match(
        expected_balances=balances,
        returned_balances=result['balances'],
        expect_found_price=False,
    )

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)
    assert_balances_match(
        expected_balances=balances,
        returned_balances=result['balances'],
        expect_found_price=False,
    )


def test_edit_manually_tracked_balances(rotkehlchen_api_server):
    """Test that editing manually tracked balances via the API works fine"""
    async_query = random.choice([False, True])
    _populate_tags(rotkehlchen_api_server)
    balances = _populate_initial_balances(rotkehlchen_api_server)

    balances_to_edit = balances[:-1]
    # Give only 2/3 balances for editing to make sure non-given balances are not touched
    balances_to_edit[0]['amount'] = '165.1'
    balances_to_edit[0]['location'] = 'kraken'
    balances_to_edit[0]['tags'] = None
    balances_to_edit[1]['tags'] = ['prIvaTe', 'mIneR']
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'async_query': async_query, 'balances': balances_to_edit},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)
    expected_balances = balances_to_edit + balances[2:]
    assert_balances_match(
        expected_balances=expected_balances,
        returned_balances=result['balances'],
    )

    # now query and make sure the added balances are returned
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)
    assert_balances_match(
        expected_balances=expected_balances,
        returned_balances=result['balances'],
    )


@pytest.mark.parametrize('verb', ('PUT', 'PATCH'))
def test_add_edit_manually_tracked_balances_errors(
        rotkehlchen_api_server,
        verb,
):
    """Test that errors in input data while adding/editing manually tracked balances
    are handled properly"""
    _populate_tags(rotkehlchen_api_server)
    balances = {'balances': [{
        "asset": "XMR",
        "label": "My monero wallet",
        "amount": "50.315",
        "tags": ["public", "mInEr"],
        "location": "blockchain",
    }, {
        "asset": "BTC",
        "label": "My XPUB BTC wallet",
        "amount": "1.425",
        "location": "blockchain",
    }]}

    # invalid initial input type
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=[1, 2, 3],
    )
    assert_error_response(
        response=response,
        contained_in_msg="Invalid input type",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # missing balances
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'foo': 1},
    )
    assert_error_response(
        response=response,
        contained_in_msg='balances": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # wrong type for balances
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'balances': 'foo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='balances": ["Not a valid list',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # missing asset entry
    data = deepcopy(balances)
    del data['balances'][0]['asset']
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type for asset
    data = deepcopy(balances)
    data['balances'][0]['asset'] = 123
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to initialize an asset out of a non-string identifier',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # unknown asset
    data = deepcopy(balances)
    data['balances'][0]['asset'] = 'SDSFFGFA'
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset SDSFFGFA provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # missing label entry
    data = deepcopy(balances)
    del data['balances'][0]['label']
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # wrong type for label
    data = deepcopy(balances)
    data['balances'][0]['label'] = 55
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='label": ["Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # missing amount entry
    data = deepcopy(balances)
    del data['balances'][0]['amount']
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # wrong type for amount
    data = deepcopy(balances)
    data['balances'][0]['amount'] = 'gra'
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize an amount entry',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # missing location entry
    data = deepcopy(balances)
    del data['balances'][0]['location']
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # wrong type for location
    data = deepcopy(balances)
    data['balances'][0]['location'] = 55
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize location symbol from',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # invalid location
    data = deepcopy(balances)
    data['balances'][0]['location'] = 'foo'
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize location symbol. Unknown symbol foo for location',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # wrong type for tags
    data = deepcopy(balances)
    data['balances'][0]['tags'] = 55
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='tags": ["Not a valid list',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # wrong type in list of tags
    data = deepcopy(balances)
    data['balances'][0]['tags'] = ['foo', 55]
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='"tags": {"1": ["Not a valid string."',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_add_edit_unknown_tags(rotkehlchen_api_server):
    """Test that using unknown tags in manually tracked balances is handled properly"""
    _populate_tags(rotkehlchen_api_server)
    initial_balances = _populate_initial_balances(rotkehlchen_api_server)

    # Try adding a new balance but with an unknown tag
    balances = [{
        "asset": "ETC",
        "label": "My ETC wallet",
        "amount": "500.115",
        "tags": ["notexisting", "mInEr"],
        "location": "blockchain",
    }]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'balances': balances},
    )
    msg = 'When adding manually tracked balances, unknown tags notexisting were found'
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.CONFLICT,
    )

    balances = initial_balances[:1]
    balances[0]['tags'] = ["notexisting", "mInEr"]
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'balances': balances},
    )
    msg = 'When editing manually tracked balances, unknown tags notexisting were found'
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.CONFLICT,
    )


def test_delete_manually_tracked_balances(rotkehlchen_api_server):
    """Test that deleting manually tracked balances via the API works fine"""
    async_query = random.choice([False, True])
    _populate_tags(rotkehlchen_api_server)
    balances = _populate_initial_balances(rotkehlchen_api_server)

    labels_to_delete = ['My monero wallet', 'My BNB in binance']
    expected_balances = balances[1:2]
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'async_query': async_query, 'labels': labels_to_delete},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)
    expected_balances = balances[1:2]
    assert_balances_match(
        expected_balances=expected_balances,
        returned_balances=result['balances'],
    )

    # now query and make sure the remaining balances are returned
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)
    assert_balances_match(
        expected_balances=expected_balances,
        returned_balances=result['balances'],
    )


def test_delete_manually_tracked_balances_errors(rotkehlchen_api_server):
    """Test that errors at deleting manually tracked balances in the API are handled"""
    _populate_tags(rotkehlchen_api_server)
    _populate_initial_balances(rotkehlchen_api_server)

    # invalid initial input type
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json=[],
    )
    assert_error_response(
        response=response,
        contained_in_msg="Invalid input type",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # missing labels
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={},
    )
    assert_error_response(
        response=response,
        contained_in_msg='labels": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # wrong type for labels
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'labels': 1},
    )
    assert_error_response(
        response=response,
        contained_in_msg='"labels": ["Not a valid list',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # wrong type for label entries
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'labels': ['My monero wallet', 55]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='"labels": {"1": ["Not a valid string."',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # delete non-existing label
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'labels': ['My monero wallet', 'nonexisting']},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to remove 1 manually tracked balance labels that do not exist',
        status_code=HTTPStatus.BAD_REQUEST,
    )
