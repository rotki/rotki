import requests

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response


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
    }]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "manuallytrackedbalancesresource",
        ), json={'balances': balances},
    )
    assert_proper_response(response)
    assert data['message'] == ''
    data = response.json()
    returned_balances = data['result']['balances']
    assert len(returned_balances) == len(balances)
    for idx, entry in enumerate(reversed(returned_balances)):
        for key, val in entry.items():
            if key == 'usd_value':
                assert FVal(val) > ZERO
                continue
            if key == 'tags':
                if val is None:
                    assert key not in balances[idx] or balances[idx][key] is None
                else:
                    assert set(val) == set(balances[idx][key])
                continue

            msg = f'Expected balances {key} is {balances[idx][key]} but got {val}'
            assert balances[idx][key] == val, msg
