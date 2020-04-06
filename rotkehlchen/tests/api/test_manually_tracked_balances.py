from typing import Any, Dict, List

import requests

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_response,
    assert_proper_response_with_result,
)


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
) -> None:
    assert len(returned_balances) == len(expected_balances)
    for idx, entry in enumerate(reversed(returned_balances)):
        for key, val in entry.items():
            if key == 'usd_value':
                assert FVal(val) > ZERO
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
    balances = [{
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


def test_add_and_query_manually_tracked_balances(
        rotkehlchen_api_server,
):
    """Test that adding and querying manually tracked balances via the API works fine"""
    _populate_tags(rotkehlchen_api_server)
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        )
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert data['result']['balances'] == [], 'In the beginning we should have no entries'

    balances = _populate_initial_balances(rotkehlchen_api_server)

    # now query and make sure the added balances are returned
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        )
    )
    result = assert_proper_response_with_result(response)
    assert_balances_match(expected_balances=balances, returned_balances=result['balances'])


def test_edit_manually_tracked_balances(
        rotkehlchen_api_server,
):
    """Test that editing manually tracked balances via the API works fine"""
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
        ), json={'balances': balances_to_edit},
    )
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
        )
    )
    result = assert_proper_response_with_result(response)
    assert_balances_match(
        expected_balances=expected_balances,
        returned_balances=result['balances'],
    )
