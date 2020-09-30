import random

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2

EXPECTED_XPUB_ADDESSES = [
    '125yorj66rmk82tMAPG7x97iY8D7cashiA',
    '13X9bcSY1UXwAwz6WaScAMFawpeTnPn1VU',
    '13hSrTAvfRzyEcjRcGS5gLEcNVNDhPvvUv',
    '14K3JxsLwhpLiECaoJMsZYyk9peYP1Gtty',
    '151krzHgfkNoH3XHBzEVi6tSn4db7pVjmR',
    '169V9snkmcdzpEDhRyLMnEuhLKyWdjzhfd',
    '16CALmyiNgYDx5gpKAH48Twe7gLBPTV8FJ',
    '16chwxaEiZ2GggzKVroAx31PEAPfYqztd6',
    '16q3r12wBrcPcEwiQXhiBxaahH8U7JE62q',
    '176i78R6TcVm1tCuAk8ZH3d22mJUNhvjYq',
    '17Diz5pbATF7oL3A6UJFGe98Wo2h7kXedD',
    '17YWeEfgXFnD6PGmm7DK5nVB7PtxsP5nvT',
    '18eo3f1pMkpSZH4hRF4bXV9yVSgKasktZo',
    '18tMkbibtxJPQoTPUv8s3mSXqYzEsrbeRb',
    '1918hHSQNsNMRkDCUMy7DUmJ8GJzwfRkUV',
    '19MY4h93edjQs3d2Ld9skxKF3EHS372r2d',
    '1AXwmcAWerEJzZSdhAJES27z9DSzk9DjSJ',
    '1DYvv8T2q2UFv9hQnbLaPZAuQw8mYx3DAD',
    '1DhLhKVDZYAU9fxHWQ99CusKagHm4wkjXL',
    '1F2arsfX5JEDryBVftmzbVFWaGsJaTVwcg',
    '1FBex1BzQbvDTam4M2AG9V5p1bJB8qYtzq',
    '1FmjuQSUaKVVpB3eS5dZ5oPCAgRrsf9SWh',
    '1FyjDvDFcXLMmhMWD6u8bFovLgkhZabhTQ',
    '1GEix38AknUMWH8DYSn43HqodoB7RjyBAJ',
    '1GJr9FHZ1pbR4hjhX24M4L1BDUd2QogYYA',
    '1K6FWtJcww5vnfbYf5sNYebeFEcaAYHu7m',
    '1KZB7aFfuZE2skJQPHH56VhSxUpUBjouwQ',
    '1L36ug5kWFLbMysfkAexh9LeicyMAteuEg',
    '1LNSji8X8YeAkuKGBTQpLb56wLk8xBFfpS',
    '1LR8aAwQbJRMjSDb9a6yfC9eVfZu5SRY3F',
    '1M3VySp8j3VMXvfzv6TaCDiFEvD3uVDNzc',
    '1N1DfsxTX5M2D3iXC4ABt3pTJVEq4pmNJM',
    '1NGp18iPyWfSZz4AWnwT6HptDdVJfTjxnF',
    '1PBMNpERKcK9W836AmkcnBZh4y89ASgxhm',
    '1PMh6pQhRPtRKjJLb9iAzySPdgE7BRDD2z',
    '1PUrJgftNnHvvqVyEsm9DiCDQuZHCn47fQ',
    '1Ps7bkbAfcEFKsUvFTNu61vNTGqTY25Lpz',
    '1Q61WZ6sixTvd8JaH2qimkXAWFBR2MdBwu',
]


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('btc_accounts', [[
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    '1KZB7aFfuZE2skJQPHH56VhSxUpUBjouwQ',  # should belong to the xpub (idx 3)
]])
def test_add_xpub(rotkehlchen_api_server):
    """This test uses real world data (queries actual BTC balances)

    Test data from here:
    https://github.com/LedgerHQ/bitcoin-keychain-svc/blob/744736af1819cdab0a46ea7faf834008aeade6b1/integration/p2pkh_keychain_test.go#L40-L95
    """
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0
    async_query = random.choice([False, True])

    tag1 = {
        'name': 'ledger',
        'description': 'My ledger accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag1,
    )
    tag2 = {
        'name': 'public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag2,
    )
    assert_proper_response(response)
    xpub = 'xpub6DCi5iJ57ZPd5qPzvTm5hUt6X23TJdh9H4NjNsNbt7t7UuTMJfawQWsdWRFhfLwkiMkB1rQ4ZJWLB9YBnzR7kbs9N8b2PsKZgKUHQm1X4or'  # noqa : E501
    json_data = {
        'async_query': async_query,
        'xpub': xpub,
        'label': 'ledger_test_xpub',
        'tags': ['ledger', 'public'],
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        "btcxpubresource",
    ), json=json_data)
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task_with_result(rotkehlchen_api_server, task_id, timeout=180)
    else:
        outcome = assert_proper_response_with_result(response)

    btc = outcome['per_account']['BTC']
    assert len(btc['standalone']) == 2
    assert UNIT_BTC_ADDRESS1 in btc['standalone']
    assert UNIT_BTC_ADDRESS2 in btc['standalone']

    assert len(btc['xpubs']) == 1
    xpub_data = btc['xpubs'][0]
    assert xpub_data['xpub'] == xpub
    assert xpub_data['derivation_path'] is None
    for address in EXPECTED_XPUB_ADDESSES:
        assert address in xpub_data['addresses']
        assert xpub_data['addresses'][address]['amount'] is not None
        assert xpub_data['addresses'][address]['usd_value'] is not None

    assert outcome['totals']['BTC']['amount'] is not None
    assert outcome['totals']['BTC']['usd_value'] is not None
