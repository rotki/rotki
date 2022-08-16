import random
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    wait_for_async_task,
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
    '1DNg5csVnUkheYczaBECsfby8ZcmZkYnJK',
]

TEST_BITCOIN_XPUB_1 = 'xpub6DCi5iJ57ZPd5qPzvTm5hUt6X23TJdh9H4NjNsNbt7t7UuTMJfawQWsdWRFhfLwkiMkB1rQ4ZJWLB9YBnzR7kbs9N8b2PsKZgKUHQm1X4or'  # noqa: E501
TEST_BITCOIN_XPUB_2 = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501


def _check_xpub_addition_outcome(outcome, xpub):
    """Checks the outcome of the xpub additions for the following test.
    Both results should be the same since the 2nd xpub derives no mainnet addresses
    """
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

    totals = outcome['totals']['assets']
    assert totals['BTC']['amount'] is not None
    assert totals['BTC']['usd_value'] is not None


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('btc_accounts', [[
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    # Also have an address derived from an xpub preset. This way we make sure
    # in the test that it is detected as belonging to the xpub
    '1KZB7aFfuZE2skJQPHH56VhSxUpUBjouwQ',
]])
def test_add_delete_xpub(rotkehlchen_api_server):
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
    requests.put(
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
    xpub1_label = 'ledger_test_xpub'
    xpub1_tags = ['ledger', 'public']
    json_data = {
        'async_query': async_query,
        'xpub': TEST_BITCOIN_XPUB_1,
        'label': xpub1_label,
        'tags': xpub1_tags,
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    if async_query:
        task_id = assert_ok_async_response(response)
        wait_for_async_task(rotkehlchen_api_server, task_id, timeout=180)
    else:
        assert_proper_response(response)

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainbalancesresource',
    ))
    result = assert_proper_response_with_result(response)
    _check_xpub_addition_outcome(result, TEST_BITCOIN_XPUB_1)

    # Make sure that adding existing xpub fails
    json_data = {
        'async_query': False,
        'xpub': TEST_BITCOIN_XPUB_1,
        'label': xpub1_label,
        'tags': xpub1_tags,
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    assert_error_response(
        response=response,
        contained_in_msg=f'Xpub {TEST_BITCOIN_XPUB_1} for BTC with derivation path None is already tracked',  # noqa: E501
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Add an xpub with no derived addresses
    xpub2_label = None
    xpub2_tags = None
    json_data = {
        'async_query': async_query,
        'xpub': TEST_BITCOIN_XPUB_2,
        'label': xpub2_label,
        'tags': xpub2_tags,
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    if async_query:
        task_id = assert_ok_async_response(response)
        wait_for_async_task(rotkehlchen_api_server, task_id, timeout=180)
    else:
        assert_proper_response(response)

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainbalancesresource',
    ))
    result = assert_proper_response_with_result(response)
    _check_xpub_addition_outcome(result, TEST_BITCOIN_XPUB_1)

    # Also make sure that blockchain account data endpoint returns everything correctly
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='BTC',
    ))
    outcome = assert_proper_response_with_result(response)
    assert len(outcome['standalone']) == 2
    for entry in outcome['standalone']:
        assert entry['address'] in (UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2)
        assert entry['tags'] is None
        assert entry['label'] is None

    assert len(outcome['xpubs']) == 2
    for entry in outcome['xpubs']:
        assert len(entry) == 5
        if entry['xpub'] == TEST_BITCOIN_XPUB_1:
            for address_data in entry['addresses']:
                assert address_data['address'] in EXPECTED_XPUB_ADDESSES
                assert address_data['label'] is None
                assert address_data['tags'] == xpub1_tags
        else:
            assert entry['xpub'] == TEST_BITCOIN_XPUB_2
            assert entry['addresses'] is None
            assert entry['label'] is None
            assert entry['tags'] is None

    # Now delete the xpub and make sure all derived addresses are gone
    json_data = {
        'async_query': async_query,
        'xpub': TEST_BITCOIN_XPUB_1,
        'derivation_path': None,
    }
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    if async_query:
        task_id = assert_ok_async_response(response)
        wait_for_async_task(rotkehlchen_api_server, task_id, timeout=180)
    else:
        assert_proper_response(response)

    assert rotki.chain_manager.accounts.btc[:2] == [UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]
    assert rotki.chain_manager.accounts.btc == [UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]

    # Also make sure all mappings are gone from the DB
    cursor = rotki.data.db.conn.cursor()
    result = cursor.execute('SELECT object_reference from tag_mappings;').fetchall()
    assert len(result) == 0, 'all tag mappings should have been deleted'
    result = cursor.execute('SELECT * from xpub_mappings WHERE xpub=?', (TEST_BITCOIN_XPUB_1,)).fetchall()  # noqa: E501
    assert len(result) == 0, 'all xpub mappings should have been deleted'

    # Test that adding a BCH xpub works
    bch_xpub1 = 'xpub6By8JDaPr5L6oHfgQDc47quD69qH1hTwnFYbuia8paiYxSE9u84KZfYqn6xLMUqxKK3wNpsgP4Kwu1gzXHD5xBxj5HrLposEYL6PwZzpAMZ'  # noqa: 501
    json_data = {
        'async_query': async_query,
        'xpub': bch_xpub1,
        'derivation_path': None,
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BCH',
    ), json=json_data)
    if async_query:
        task_id = assert_ok_async_response(response)
        wait_for_async_task(rotkehlchen_api_server, task_id, timeout=180)
    else:
        assert_proper_response(response)

    # test that adding the same BCH xpub for BTC works
    json_data = {
        'async_query': async_query,
        'xpub': bch_xpub1,
        'derivation_path': None,
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    if async_query:
        task_id = assert_ok_async_response(response)
        wait_for_async_task(rotkehlchen_api_server, task_id, timeout=180)
    else:
        assert_proper_response(response)

    # Test that deleting a BCH xpub works as expected
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BCH',
    ), json=json_data)
    if async_query:
        task_id = assert_ok_async_response(response)
        wait_for_async_task(rotkehlchen_api_server, task_id, timeout=180)
    else:
        assert_proper_response(response)

    # Also make sure all mappings are gone from the DB
    cursor = rotki.data.db.conn.cursor()
    result = cursor.execute('SELECT object_reference from tag_mappings;').fetchall()
    assert len(result) == 0, 'all tag mappings should have been deleted'
    result = cursor.execute('SELECT * from xpub_mappings WHERE xpub=?', (bch_xpub1,)).fetchall()
    assert len(result) == 0, 'all xpub mappings should have been deleted'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('btc_accounts', [[
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
]])
def test_delete_nonexisting_xpub(rotkehlchen_api_server):
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0

    xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa : E501
    json_data = {
        'xpub': xpub,
        'derivation_path': None,
    }
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    assert_error_response(
        response=response,
        contained_in_msg=f'Tried to remove non existing xpub {xpub} for BTC with no derivation path',  # noqa: 501
        status_code=HTTPStatus.BAD_REQUEST,
    )

    xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa : E501
    path = 'm/0/21'
    json_data = {
        'xpub': xpub,
        'derivation_path': path,
    }
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    assert_error_response(
        response=response,
        contained_in_msg=f'Tried to remove non existing xpub {xpub} for BTC with derivation path {path}',  # noqa: 501
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_xpub_with_conversion_works(rotkehlchen_api_server):
    """Test that an xpub is being converted to ypub/zpub if the prefix does not match"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0

    # Test xpub asking conversion to ypub
    xpub = 'xpub6CjniigyzMWgVDHvDpgvsroPkTJeqUbrHJaLHARHmAM8zuAbCjmHpp3QhKTcnnscd6iBDrqmABCJjnpwUW42cQjtvKjaEZRcShHKEVh35Y8'  # noqa : E501
    json_data = {
        'xpub': xpub,
        'xpub_type': 'p2sh_p2wpkh',
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    assert_proper_response(response)
    with rotki.data.db.conn.read_ctx() as cursor:
        saved_xpubs = rotki.data.db.get_bitcoin_xpub_data(cursor)
        assert len(saved_xpubs) == 1
        assert saved_xpubs[0].xpub.hint == 'ypub'
        assert saved_xpubs[0].xpub.xpub == 'ypub6Xa42PMu934ALWV34BUZ5wttvRT6n6bMCR6Z4ZKB9Aj23zypTPvrSshYiXRCnhXY2jpyyLSKcqYrd5SWCCU3QeRVnfRzpUF6iRLxd55duzL'  # noqa: E501

        # Test xpub asking conversion to zpub
        json_data['xpub_type'] = 'wpkh'
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'btcxpubresource',
            blockchain='BTC',
        ), json=json_data)
        assert_proper_response(response)
        saved_xpubs = rotki.data.db.get_bitcoin_xpub_data(cursor)

    assert len(saved_xpubs) == 2
    assert saved_xpubs[1].xpub.hint == 'zpub'
    assert saved_xpubs[1].xpub.xpub == 'zpub6rQKL42pHibeBog9tYGBJ2zQ6PbYiiar7XcmqxD4XB6u76o3i46R4wMgjjNnncBTSNwnip2t5VuQWN44utt4Ct76f18RQP4az9Qc1eUEkSY'  # noqa: E501


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_xpub_addition_errors(rotkehlchen_api_server):
    """Test that errors at xpub addition are handled correctly"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0

    # illegal xpub type
    xpub = 'xpub6CjniigyzMWgVDHvDpgvsroPkTJeqUbrHJaLHARHmAM8zuAbCjmHpp3QhKTcnnscd6iBDrqmABCJjnpwUW42cQjtvKjaEZRcShHKEVh35Y8'  # noqa : E501
    json_data = {
        'xpub': xpub,
        'xpub_type': 'whatever',
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    assert_error_response(
        response=response,
        contained_in_msg='"xpub_type": ["Must be one of: p2pkh, p2sh_p2wpkh, wpkh."]}',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid derivation path
    xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa : E501
    derivation_path = "49'/0'/0'"
    json_data = {
        'xpub': xpub,
        'derivation_path': derivation_path,
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    assert_error_response(
        response=response,
        contained_in_msg='Derivation paths accepted by rotki should start with m',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # not a valid xpub string
    xpub = 'foo'
    json_data = {'xpub': xpub}
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    assert_error_response(
        response=response,
        contained_in_msg='"xpub": ["Failed to initialize an xpub due to Given XPUB foo is too small"',  # noqa: E501
        status_code=HTTPStatus.BAD_REQUEST,
    )
