from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import gevent
import pytest
import requests

from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ONE
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.factories import (
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    make_btc_tx_hash,
)
from rotkehlchen.types import BTCAddress, Location, SupportedBlockchain, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.tests.fixtures.networking import ConfigurableSession

EXPECTED_XPUB_ADDRESSES = [
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


def _check_xpub_addition_outcome(outcome: dict[str, Any], xpub: str) -> None:
    """Checks the outcome of the xpub additions for the following test.
    Both results should be the same since the 2nd xpub derives no mainnet addresses
    """
    btc = outcome['per_account']['btc']
    assert len(btc['standalone']) == 2
    assert UNIT_BTC_ADDRESS1 in btc['standalone']
    assert UNIT_BTC_ADDRESS2 in btc['standalone']

    assert len(btc['xpubs']) == 1
    xpub_data = btc['xpubs'][0]
    assert xpub_data['xpub'] == xpub
    assert xpub_data['derivation_path'] is None
    for address in EXPECTED_XPUB_ADDRESSES:
        assert address in xpub_data['addresses']
        assert xpub_data['addresses'][address]['amount'] is not None
        assert xpub_data['addresses'][address]['usd_value'] is not None

    totals = outcome['totals']['assets']
    assert totals['BTC'][DEFAULT_BALANCE_LABEL]['amount'] is not None
    assert totals['BTC'][DEFAULT_BALANCE_LABEL]['usd_value'] is not None


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('btc_accounts', [[
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    # Also have an address derived from an xpub preset. This way we make sure
    # in the test that it is detected as belonging to the xpub
    '1KZB7aFfuZE2skJQPHH56VhSxUpUBjouwQ',
]])
def test_add_delete_xpub(rotkehlchen_api_server: 'APIServer') -> None:
    """This test uses real world data (queries actual BTC balances)

    Test data from here:
    https://github.com/LedgerHQ/bitcoin-keychain-svc/blob/744736af1819cdab0a46ea7faf834008aeade6b1/integration/p2pkh_keychain_test.go#L40-L95
    """
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
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
        'async_query': True,
        'xpub': TEST_BITCOIN_XPUB_1,
        'label': xpub1_label,
        'tags': xpub1_tags,
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    task_id = assert_ok_async_response(response)
    wait_for_async_task(rotkehlchen_api_server, task_id, timeout=180)

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainbalancesresource',
    ))
    result = assert_proper_sync_response_with_result(response)
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
        'async_query': True,
        'xpub': TEST_BITCOIN_XPUB_2,
        'label': xpub2_label,
        'tags': xpub2_tags,
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    task_id = assert_ok_async_response(response)
    wait_for_async_task(rotkehlchen_api_server, task_id, timeout=180)

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainbalancesresource',
    ))
    result = assert_proper_sync_response_with_result(response)
    _check_xpub_addition_outcome(result, TEST_BITCOIN_XPUB_1)

    # Also make sure that blockchain account data endpoint returns everything correctly
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='BTC',
    ))
    outcome = assert_proper_sync_response_with_result(response)
    assert len(outcome['standalone']) == 2
    for entry in outcome['standalone']:
        assert entry['address'] in (UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2)
        assert entry['tags'] is None
        assert entry['label'] is None

    assert len(outcome['xpubs']) == 2
    for entry in outcome['xpubs']:
        assert len(entry) == 6
        if entry['xpub'] == TEST_BITCOIN_XPUB_1:
            for address_data in entry['addresses']:
                assert address_data['address'] in EXPECTED_XPUB_ADDRESSES
                assert address_data['label'] is None
                assert address_data['tags'] == xpub1_tags
                assert entry['blockchain'] == 'btc'
        else:
            assert entry['xpub'] == TEST_BITCOIN_XPUB_2
            assert entry['addresses'] is None
            assert entry['label'] is None
            assert entry['tags'] is None
            assert entry['blockchain'] == 'btc'

    # Now delete the xpub and make sure all derived addresses are gone
    json_data = {
        'async_query': True,
        'xpub': TEST_BITCOIN_XPUB_1,
        'derivation_path': None,
    }
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    task_id = assert_ok_async_response(response)
    wait_for_async_task(rotkehlchen_api_server, task_id, timeout=180)

    assert set(rotki.chains_aggregator.accounts.btc[:2]) == {UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2}
    assert set(rotki.chains_aggregator.accounts.btc) == {UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2}

    # Also make sure all mappings are gone from the DB
    cursor = rotki.data.db.conn.cursor()
    result = cursor.execute('SELECT object_reference from tag_mappings;').fetchall()
    assert len(result) == 0, 'all tag mappings should have been deleted'
    result = cursor.execute('SELECT * from xpub_mappings WHERE xpub=?', (TEST_BITCOIN_XPUB_1,)).fetchall()  # noqa: E501
    assert len(result) == 0, 'all xpub mappings should have been deleted'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_delete_xpub_multiple_chains(rotkehlchen_api_server: 'APIServer') -> None:
    """Test adding xpub for multiple bitcoin chains (BTC/BCH)

    This test actually has a VCR cassette in test-caching. It's not used at
    the moment since for some weird, arcane, fucked up, demented reason
    it fails only in the CI when using VCR.

    And it fails in a way that's ugly as it forces the entire CI run to time out
    at the max runtime which is currently set to 90 mins.
    TODO: Perhaps see if we can figure out why and fix, as this may hit us in
    other tests too if we don't know what it is.
    """
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
    assert rotki.task_manager is not None
    rotki.task_manager.should_schedule = False

    # Test that adding a BCH xpub works
    xpub = 'xpub6By8JDaPr5L6oHfgQDc47quD69qH1hTwnFYbuia8paiYxSE9u84KZfYqn6xLMUqxKK3wNpsgP4Kwu1gzXHD5xBxj5HrLposEYL6PwZzpAMZ'  # noqa: E501
    json_data = {
        'async_query': False,
        'xpub': xpub,
        'derivation_path': None,
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BCH',
    ), json=json_data)
    assert_proper_response(response)

    # Check that periodic derivation doesn't break anything
    # Testing here since test_tasks_manager.py only tests scheduling
    rotki.task_manager.last_xpub_derivation_ts = 0   # to be sure that the task will be scheduled
    with patch('rotkehlchen.tasks.manager.XpubManager.check_for_new_xpub_addresses') as patch_method:  # noqa: E501
        rotki.task_manager._maybe_schedule_xpub_derivation()
        gevent.sleep(0)
        assert patch_method.call_count == 1

    # Check that bch accounts were detected while btc accounts were not affected
    assert len(rotki.chains_aggregator.accounts.bch) != 0
    assert len(rotki.chains_aggregator.accounts.btc) == 0
    with rotki.data.db.conn.read_ctx() as cursor:
        mapping_result = rotki.data.db.get_addresses_to_xpub_mapping(
            cursor=cursor,
            blockchain=SupportedBlockchain.BITCOIN_CASH,
            addresses=rotki.chains_aggregator.accounts.bch,
        )
        assert len(mapping_result) == len(rotki.chains_aggregator.accounts.bch)
        mapping_result = rotki.data.db.get_addresses_to_xpub_mapping(
            cursor=cursor,
            blockchain=SupportedBlockchain.BITCOIN,
            addresses=rotki.chains_aggregator.accounts.bch,
        )
        assert len(mapping_result) == 0

    # test that adding the same xpub for BTC works
    json_data = {
        'async_query': False,
        'xpub': xpub,
        'derivation_path': None,
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    assert_proper_response(response)

    assert len(rotki.chains_aggregator.accounts.btc) != 0, 'should be populated after api call'
    # Check that addresses that have balances on both bitcoin and bitcoin cash are stored properly
    with rotki.data.db.conn.read_ctx() as cursor:  # type: ignore  # this is reachable lol mypy
        mutual_in_chains_aggregator = 0
        for btc_addr in rotki.chains_aggregator.accounts.btc:
            if btc_addr in rotki.chains_aggregator.accounts.bch:
                mutual_in_chains_aggregator += 1
        # get mutual by querying BCH accounts from known BTC accounts
        # this checks that bitcoin mappings in the db are not broken
        mutual_in_db_1 = len(rotki.data.db.get_addresses_to_xpub_mapping(
            cursor=cursor,
            blockchain=SupportedBlockchain.BITCOIN,
            addresses=rotki.chains_aggregator.accounts.bch,
        ))
        # get mutual by querying BTC accounts from known BCH accounts
        # this checks that bitcoin cash mappings in the db are not broken
        mutual_in_db_2 = len(rotki.data.db.get_addresses_to_xpub_mapping(
            cursor=cursor,
            blockchain=SupportedBlockchain.BITCOIN_CASH,
            addresses=rotki.chains_aggregator.accounts.btc,
        ))
        # Check that there are some accounts that are used on both btc and bch
        assert mutual_in_chains_aggregator > 0
        # Check that information about these accounts matches between chain manager and the db
        assert mutual_in_chains_aggregator == mutual_in_db_1 == mutual_in_db_2

    # Test that editing one xpub doesn't affect other if the only difference is chain
    json_data_patch = {
        'xpub': xpub,
        'label': 'qwerty',
    }
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data_patch)
    assert_proper_response(response)

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='BTC',
    ))
    result = assert_proper_sync_response_with_result(response)

    assert len(result['xpubs']) == 1
    xpub_return = result['xpubs'][0]
    assert xpub_return['label'] == 'qwerty'
    assert xpub_return['blockchain'] == 'btc'

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='BCH',
    ))
    result = assert_proper_sync_response_with_result(response)

    assert len(result['xpubs']) == 1
    xpub_return = result['xpubs'][0]
    assert xpub_return['label'] is None
    assert xpub_return['blockchain'] == 'bch'

    # Test that deleting a BCH xpub works as expected
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BCH',
    ), json=json_data)
    assert_proper_response(response)

    # Also make sure mappings are gone from the DB
    cursor = rotki.data.db.conn.cursor()
    result = cursor.execute('SELECT object_reference from tag_mappings;').fetchall()
    assert len(result) == 0, 'all tag mappings should have been deleted'
    result = cursor.execute('SELECT * from xpub_mappings WHERE xpub=?', (xpub,)).fetchall()
    assert len(rotki.chains_aggregator.accounts.bch) == 0
    # Check that we still have derived BTC addresses
    assert len(result) >= 23
    for address, xpub_result, _, _, _, blockchain in result:
        assert address in rotki.chains_aggregator.accounts.btc
        assert xpub == xpub_result
        assert blockchain == 'BTC'

    # test that adding a btc p2tr xpub works
    btc_xpub3 = 'xpub6D8VW7U5pTXMsuyyj3NRFP5QbzENbMijxAqy596niQTdc3PVBWcFEPYF8ZZBzeKopsN5Dvk3psNRRwwZAUhwhhzaaX6QV6izd189YmQ6DR6'  # noqa: E501
    json_data = {
        'async_query': False,
        'xpub': btc_xpub3,
        'xpub_type': 'p2tr',
        'derivation_path': 'm/86/0/0',
    }
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    assert_proper_response(response)

    # test that deleting a btc p2tr xpub works
    json_data = {
        'async_query': False,
        'xpub': btc_xpub3,
        'derivation_path': 'm/86/0/0',
    }
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data)
    assert_proper_response(response)

    # Also make sure all mappings are gone from the DB
    cursor = rotki.data.db.conn.cursor()
    result = cursor.execute('SELECT object_reference from tag_mappings;').fetchall()
    assert len(result) == 0, 'all tag mappings should have been deleted'
    result = cursor.execute('SELECT * from xpub_mappings WHERE xpub=?', (btc_xpub3,)).fetchall()
    assert len(result) == 0, 'all xpub mappings should have been deleted'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('btc_accounts', [[
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
]])
def test_delete_nonexisting_xpub(rotkehlchen_api_server: 'APIServer') -> None:
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0

    xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
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
        contained_in_msg=f'Tried to remove non existing xpub {xpub} for {SupportedBlockchain.BITCOIN!s} with no derivation path',  # noqa: E501
        status_code=HTTPStatus.BAD_REQUEST,
    )

    xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
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
        contained_in_msg=f'Tried to remove non existing xpub {xpub} for {SupportedBlockchain.BITCOIN!s} with derivation path {path}',  # noqa: E501
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('test_timeout', [60])  # needs longer timeout
def test_add_xpub_with_conversion_works(
        rotkehlchen_api_server: 'APIServer',
        test_session: 'ConfigurableSession',
) -> None:
    """Test that an xpub is being converted to ypub/zpub if the prefix does not match"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0

    # Test xpub asking conversion to ypub
    xpub = 'xpub6CjniigyzMWgVDHvDpgvsroPkTJeqUbrHJaLHARHmAM8zuAbCjmHpp3QhKTcnnscd6iBDrqmABCJjnpwUW42cQjtvKjaEZRcShHKEVh35Y8'  # noqa: E501
    json_data = {
        'xpub': xpub,
        'xpub_type': 'p2sh_p2wpkh',
    }
    with test_session.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json=json_data) as response:
        assert_proper_response(response)

    with rotki.data.db.conn.read_ctx() as cursor:
        saved_xpubs = rotki.data.db.get_bitcoin_xpub_data(cursor, SupportedBlockchain.BITCOIN)
        assert len(saved_xpubs) == 1
        assert saved_xpubs[0].xpub.hint == 'ypub'
        assert saved_xpubs[0].xpub.xpub == 'ypub6Xa42PMu934ALWV34BUZ5wttvRT6n6bMCR6Z4ZKB9Aj23zypTPvrSshYiXRCnhXY2jpyyLSKcqYrd5SWCCU3QeRVnfRzpUF6iRLxd55duzL'  # noqa: E501

        # Test xpub asking conversion to zpub
        json_data['xpub_type'] = 'wpkh'
        with test_session.put(api_url_for(
            rotkehlchen_api_server,
            'btcxpubresource',
            blockchain='BTC',
        ), json=json_data) as response:
            assert_proper_response(response)
        saved_xpubs = rotki.data.db.get_bitcoin_xpub_data(cursor, SupportedBlockchain.BITCOIN)

    assert len(saved_xpubs) == 2
    assert saved_xpubs[1].xpub.hint == 'zpub'
    assert saved_xpubs[1].xpub.xpub == 'zpub6rQKL42pHibeBog9tYGBJ2zQ6PbYiiar7XcmqxD4XB6u76o3i46R4wMgjjNnncBTSNwnip2t5VuQWN44utt4Ct76f18RQP4az9Qc1eUEkSY'  # noqa: E501


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_xpub_addition_errors(
        rotkehlchen_api_server: 'APIServer',
        test_session: 'ConfigurableSession',
) -> None:
    """Test that errors at xpub addition are handled correctly"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0

    # illegal xpub type
    xpub = 'xpub6CjniigyzMWgVDHvDpgvsroPkTJeqUbrHJaLHARHmAM8zuAbCjmHpp3QhKTcnnscd6iBDrqmABCJjnpwUW42cQjtvKjaEZRcShHKEVh35Y8'  # noqa: E501
    with test_session.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json={
        'xpub': xpub,
        'xpub_type': 'whatever',
    }) as response:
        assert_error_response(
            response=response,
            contained_in_msg='Unknown xpub type whatever found at deserialization',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    # invalid derivation path
    xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
    derivation_path = "49'/0'/0'"
    with test_session.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json={
        'xpub': xpub,
        'derivation_path': derivation_path,
    }) as response:
        assert_error_response(
            response=response,
            contained_in_msg='Derivation paths accepted by rotki should start with m',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    # not a valid xpub string
    xpub = 'foo'
    with test_session.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json={'xpub': xpub}) as response:
        assert_error_response(
            response=response,
            contained_in_msg='"xpub": ["Failed to initialize an xpub due to Given XPUB foo is too small"',  # noqa: E501
            status_code=HTTPStatus.BAD_REQUEST,
        )

    # tags empty list
    xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
    with test_session.put(api_url_for(
        rotkehlchen_api_server,
        'btcxpubresource',
        blockchain='BTC',
    ), json={
        'xpub': xpub,
        'tags': [],
    }) as response:
        assert_error_response(
            response=response,
            contained_in_msg='Provided empty list for tags. Use null',
            status_code=HTTPStatus.BAD_REQUEST,
        )


@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
def test_delete_btc_account(
        rotkehlchen_api_server: 'APIServer',
        btc_accounts: list[BTCAddress],
) -> None:
    """Test that when a btc account is deleted any related uncustomized events are removed,
    as well as the cached last queried block number for that account.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.write_ctx() as write_cursor:
        for address in btc_accounts:
            for mapping_values in (
                {HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED},
                None,
            ):  # Add both a normal event and a customized event for each address
                dbevents.add_history_event(
                    write_cursor=write_cursor,
                    event=HistoryEvent(
                        event_identifier=make_btc_tx_hash(),
                        sequence_index=0,
                        timestamp=TimestampMS(1500000000000),
                        location=Location.BITCOIN,
                        event_type=HistoryEventType.RECEIVE,
                        event_subtype=HistoryEventSubType.NONE,
                        asset=A_BTC,
                        amount=ONE,
                        location_label=address,
                    ),
                    mapping_values=mapping_values,
                )

            rotki.data.db.set_dynamic_cache(
                write_cursor=write_cursor,
                name=DBCacheDynamic.LAST_BTC_TX_BLOCK,
                address=address,
                value=12345,
            )

    response = requests.delete(
        api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain='BTC'),
        json={'accounts': [btc_accounts[0]]},
    )
    assert_proper_response(response)

    with rotki.data.db.conn.read_ctx() as cursor:
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            entries_limit=None,
        )
        assert len(events) == 3  # Events remaining are the customized event from address1 and both events from address2  # noqa: E501
        assert events[0].location_label == btc_accounts[0]
        assert events[0].identifier in dbevents.get_customized_event_identifiers(
            cursor=cursor,
            location=Location.BITCOIN,
        )
        assert events[1].location_label == btc_accounts[1]
        assert events[2].location_label == btc_accounts[1]
        for address, expected_value in (
            (btc_accounts[0], None),
            (btc_accounts[1], 12345),
        ):
            assert rotki.data.db.get_dynamic_cache(
                cursor=cursor,
                name=DBCacheDynamic.LAST_BTC_TX_BLOCK,
                address=address,
            ) == expected_value
