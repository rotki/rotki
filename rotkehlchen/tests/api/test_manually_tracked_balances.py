import random
from contextlib import ExitStack
from copy import deepcopy
from http import HTTPStatus
from operator import itemgetter
from typing import TYPE_CHECKING, Any, Literal
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.assets.asset import Asset, AssetResolver
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BNB, A_ETH, A_EUR
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.constants import A_RDN
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def _populate_tags(api_server: 'APIServer') -> None:
    tag1 = {
        'name': 'Public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            api_server,
            'tagsresource',
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
            'tagsresource',
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
            'tagsresource',
        ), json=tag3,
    )
    assert_proper_response(response)


def assert_balances_match(
        expected_balances: list[dict[str, Any]],
        returned_balances: list[dict[str, Any]],
        expect_found_price: bool = True,
) -> None:
    assert len(returned_balances) == len(expected_balances)
    expected_balances.sort(key=itemgetter('label'))
    returned_balances.sort(key=itemgetter('label'))
    for idx, entry in enumerate(returned_balances):
        for key, val in entry.items():
            if key == 'value':
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
            if key == 'asset_is_missing':
                continue
            if key == 'usd_value':
                continue  # TODO(isaac): remove once usd_value -> migration is complete

            msg = f'Expected balances {key} is {expected_balances[idx][key]} but got {val}'
            assert expected_balances[idx][key] == val, msg


def _populate_initial_balances(api_server: 'APIServer') -> list[dict[str, Any]]:
    # Now add some balances
    balances: list[dict[str, Any]] = [{
        'asset': 'XMR',
        'label': 'My monero wallet',
        'amount': '50.315',
        'tags': ['public', 'mInEr'],
        'location': 'blockchain',
        'balance_type': 'asset',
    }, {
        'asset': 'BTC',
        'label': 'My XPUB BTC wallet',
        'amount': '1.425',
        'location': 'blockchain',
        'balance_type': 'asset',
    }, {
        'asset': A_BNB.identifier,
        'label': 'My BNB in binance',
        'amount': '155',
        'location': 'binance',
        'tags': ['private'],
        'balance_type': 'asset',
    }, {
        'asset': 'ETH',
        'label': 'The ETH I owe to Siretfel. Must pay money or with my life',
        'amount': '1',
        'tags': ['private'],
        'location': 'blockchain',
        'balance_type': 'liability',
    }, {
        'asset': 'ETH',
        'label': 'ETH owed to the Finanzamt',
        'amount': '1',
        'tags': ['private'],
        'location': 'blockchain',
        'balance_type': 'liability',
    }, {
        'asset': 'USD',
        'label': 'My gambling debt',
        'amount': '100',
        'tags': None,
        'location': 'external',
        'balance_type': 'liability',
    }]
    response = requests.put(
        api_url_for(
            api_server,
            'manuallytrackedbalancesresource',
        ), json={'balances': balances},
    )
    result = assert_proper_sync_response_with_result(response)
    expected_balances = []
    for new_id, balance in enumerate(balances, start=1):
        new_balance = balance.copy()
        new_balance['identifier'] = new_id
        expected_balances.append(new_balance)
    result_balances = sorted(result['balances'], key=itemgetter('identifier'))
    assert_balances_match(expected_balances=expected_balances, returned_balances=result_balances)

    return expected_balances


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_add_and_query_manually_tracked_balances(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
        globaldb: GlobalDBHandler,
) -> None:
    """Test that adding and querying manually tracked balances via the API works fine"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=None)
    _populate_tags(rotkehlchen_api_server)
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_sync_response_with_result(response)
    assert result['balances'] == [], 'In the beginning we should have no entries'

    balances = _populate_initial_balances(rotkehlchen_api_server)

    # now query and make sure the added balances are returned
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_sync_response_with_result(response)
    assert_balances_match(expected_balances=balances, returned_balances=result['balances'])

    now = ts_now()
    # Also now test for https://github.com/rotki/rotki/issues/942 by querying for all balances
    # causing all balances to be saved and making sure the manual balances also got saved
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'allbalancesresource',
            ), json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            result = outcome['result']
        else:
            result = assert_proper_sync_response_with_result(response)

    assets = result['assets']
    assert len(assets) == 5
    assert assets['BTC']['amount'] == '1.425'
    assert assets['XMR']['amount'] == '50.315'
    assert assets[A_BNB.identifier]['amount'] == '155'
    assert assets['ETH']['amount'] == '0.000000000003'  # from ethereum on-chain balances
    assert assets[A_RDN.identifier]['amount'] == '0.000000000004'  # ethereum on-chain balances
    liabilities = result['liabilities']
    assert len(liabilities) == 2
    assert liabilities['ETH']['amount'] == '2'
    assert liabilities['USD']['amount'] == '100'

    # Check DB to make sure a save happened
    with rotki.data.db.conn.read_ctx() as cursor:
        assert rotki.data.db.get_last_balance_save_time(cursor) >= now
        assert set(rotki.data.db.query_owned_assets(cursor)) == {
            'BTC',
            'XMR',
            A_BNB.identifier,
            'ETH',
            A_RDN.identifier,
        }

    # delete an asset and check that all the entries are returned but the one with the
    # deleted asset is marked with the flag
    globaldb.delete_asset_by_identifier(A_ETH.identifier)
    AssetResolver.clean_memory_cache()
    with patch.object(globaldb, '_packaged_db_conn', globaldb.conn):
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'manuallytrackedbalancesresource',
            ),
        )

    result = assert_proper_sync_response_with_result(response)
    for entry in result['balances']:
        assert entry['asset_is_missing'] == (entry['asset'] == A_ETH.identifier)


A_CYFM = Asset('eip155:1/erc20:0x3f06B5D78406cD97bdf10f5C420B241D32759c80')


@pytest.mark.parametrize('mocked_current_prices', [{(A_CYFM.identifier, A_EUR.identifier): ZERO}])
def test_add_manually_tracked_balances_no_price(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that adding a manually tracked balance of an asset for which we cant
    query a price is handled properly both in the adding and querying part

    Regression test for https://github.com/rotki/rotki/issues/896"""
    async_query = random.choice([False, True])
    _populate_tags(rotkehlchen_api_server)
    balances: list[dict[str, Any]] = [{
        'asset': A_CYFM.identifier,
        'label': 'CYFM account',
        'amount': '50.315',
        'tags': ['public'],
        'location': 'blockchain',
        'balance_type': 'asset',
    }]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'async_query': async_query, 'balances': balances},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_sync_response_with_result(response)
    expected_balances = []
    for new_id, balance in enumerate(balances, start=1):
        new_balance = balance.copy()
        new_balance['identifier'] = new_id
        expected_balances.append(new_balance)
    assert_balances_match(
        expected_balances=expected_balances,
        returned_balances=result['balances'],
        expect_found_price=False,
    )

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_sync_response_with_result(response)
    assert_balances_match(
        expected_balances=expected_balances,
        returned_balances=result['balances'],
        expect_found_price=False,
    )


def test_edit_manually_tracked_balances(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that editing manually tracked balances via the API works fine"""
    async_query = random.choice([False, True])
    _populate_tags(rotkehlchen_api_server)
    balances = _populate_initial_balances(rotkehlchen_api_server)

    balances_to_edit = balances[0:3]
    # Give only 2/3 balances for editing to make sure non-given balances are not touched
    balances_to_edit[0]['amount'] = '165.1'
    balances_to_edit[0]['location'] = 'kraken'
    balances_to_edit[0]['tags'] = None
    balances_to_edit[1]['tags'] = ['prIvaTe', 'mIneR']
    balances_to_edit[2]['tags'] = ['mIneR', 'public']
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'async_query': async_query, 'balances': balances_to_edit},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_sync_response_with_result(response)

    expected_balances = balances_to_edit + balances[3:]
    assert_balances_match(
        expected_balances=expected_balances,
        returned_balances=result['balances'],
    )

    # now query and make sure the added balances are returned
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_sync_response_with_result(response)
    assert_balances_match(
        expected_balances=expected_balances,
        returned_balances=result['balances'],
    )


@pytest.mark.parametrize('verb', ['PUT', 'PATCH'])
def test_add_edit_manually_tracked_balances_errors(
        rotkehlchen_api_server: 'APIServer',
        verb: Literal['PUT', 'PATCH'],
) -> None:
    """Test that errors in input data while adding/editing manually tracked balances
    are handled properly"""
    _populate_tags(rotkehlchen_api_server)
    balances: dict[str, list[dict[str, Any]]] = {'balances': [{
        'asset': 'XMR',
        'label': 'My monero wallet',
        'amount': '50.315',
        'tags': ['public', 'mInEr'],
        'location': 'blockchain',
    }, {
        'asset': 'BTC',
        'label': 'My XPUB BTC wallet',
        'amount': '1.425',
        'location': 'blockchain',
    }]}

    # invalid initial input type
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json=[1, 2, 3],
    )
    assert_error_response(
        response=response,
        contained_in_msg='Invalid input type',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # missing balances
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
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
            'manuallytrackedbalancesresource',
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
            'manuallytrackedbalancesresource',
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
            'manuallytrackedbalancesresource',
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
            'manuallytrackedbalancesresource',
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
            'manuallytrackedbalancesresource',
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
            'manuallytrackedbalancesresource',
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
            'manuallytrackedbalancesresource',
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
            'manuallytrackedbalancesresource',
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize value entry',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # missing location entry
    data = deepcopy(balances)
    del data['balances'][0]['location']
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
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
            'manuallytrackedbalancesresource',
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize Location value from non string value',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # invalid location
    data = deepcopy(balances)
    data['balances'][0]['location'] = 'foo'
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize Location value foo',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # empty list for tags
    data = deepcopy(balances)
    data['balances'][0]['tags'] = []
    if verb == 'PATCH':
        for idx, entry in enumerate(data['balances']):
            entry['identifier'] = idx  # just to have a valid id in the request
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Provided empty list for tags. Use null',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # wrong type for tags
    data = deepcopy(balances)
    data['balances'][0]['tags'] = 55
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
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
            'manuallytrackedbalancesresource',
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='"tags": {"1": ["Not a valid string."',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_add_edit_unknown_tags(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that using unknown tags in manually tracked balances is handled properly"""
    _populate_tags(rotkehlchen_api_server)
    initial_balances = _populate_initial_balances(rotkehlchen_api_server)

    # Try adding a new balance but with an unknown tag
    balances = [{
        'asset': 'ETC',
        'label': 'My ETC wallet',
        'amount': '500.115',
        'tags': ['notexisting', 'mInEr'],
        'location': 'blockchain',
    }]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'balances': balances},
    )
    msg = 'When adding manually tracked balances, unknown tags notexisting were found'
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.CONFLICT,
    )

    balances = initial_balances[:1]
    balances[0]['tags'] = ['notexisting', 'mInEr']
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'balances': balances},
    )
    msg = 'When editing manually tracked balances, unknown tags notexisting were found'
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.CONFLICT,
    )


def test_delete_manually_tracked_balances(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that deleting manually tracked balances via the API works fine"""
    async_query = random.choice([False, True])
    _populate_tags(rotkehlchen_api_server)
    balances = _populate_initial_balances(rotkehlchen_api_server)

    ids_to_delete = [1, 4]
    expected_balances = [b for b in balances if b['identifier'] not in ids_to_delete]
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'async_query': async_query, 'ids': ids_to_delete},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_sync_response_with_result(response)
    assert_balances_match(
        expected_balances=expected_balances,
        returned_balances=result['balances'],
    )

    # now query and make sure the remaining balances are returned
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        result = outcome['result']
    else:
        result = assert_proper_sync_response_with_result(response)
    assert_balances_match(
        expected_balances=expected_balances,
        returned_balances=result['balances'],
    )


def test_delete_manually_tracked_balances_errors(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that errors at deleting manually tracked balances in the API are handled"""
    _populate_tags(rotkehlchen_api_server)
    _populate_initial_balances(rotkehlchen_api_server)

    # invalid initial input type
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json=[],
    )
    assert_error_response(
        response=response,
        contained_in_msg='Invalid input type',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # missing ids
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={},
    )
    assert_error_response(
        response=response,
        contained_in_msg='ids": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # wrong type for ids
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'ids': 'asdf'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='"ids": ["Not a valid list',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # wrong type for ids entries
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'ids': [2, 'My monero wallet']},
    )
    assert_error_response(
        response=response,
        contained_in_msg='"ids": {"1": ["Not a valid integer."',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # delete non-existing id
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={'ids': [1, 23]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to remove 1 manually tracked balance ids that do not exist',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_update_manual_balance_label(rotkehlchen_api_server: 'APIServer') -> None:
    _populate_tags(rotkehlchen_api_server)
    balances = _populate_initial_balances(rotkehlchen_api_server)
    balances.sort(key=itemgetter('identifier'))
    balance_to_patch_1 = balances.pop()
    balance_to_patch_1['label'] = 'NEW PATCHED LABEL 1'
    balance_to_patch_2 = balances.pop()
    balance_to_patch_2['label'] = 'NEW PATCHED LABEL 2'
    expected_balances = balances + [balance_to_patch_2, balance_to_patch_1]
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ), json={
            'balances': [balance_to_patch_1, balance_to_patch_2],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert_balances_match(
        expected_balances=expected_balances,
        returned_balances=result['balances'],
    )

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'manuallytrackedbalancesresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert_balances_match(
        expected_balances=expected_balances,
        returned_balances=result['balances'],
    )
