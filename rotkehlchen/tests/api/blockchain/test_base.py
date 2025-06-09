import logging
import random
from contextlib import ExitStack
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.accounts import SingleBlockchainAccountData
from rotkehlchen.chain.gnosis.constants import BRIDGE_QUERIED_ADDRESS_PREFIX
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.filtering import AddressbookFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.blockchain import (
    assert_btc_balances_result,
    assert_eth_balances_result,
    compare_account_data,
)
from rotkehlchen.tests.utils.constants import A_RDN
from rotkehlchen.tests.utils.factories import (
    ADDRESS_ETH,
    ADDRESS_MULTICHAIN,
    ADDRESS_OP,
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    UNIT_BTC_ADDRESS3,
    make_evm_address,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import ChainType, SupportedBlockchain, Timestamp
from rotkehlchen.utils.gevent_compat import Timeout, sleep

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.tests.fixtures.networking import ConfigurableSession
    from rotkehlchen.tests.fixtures.websockets import WebsocketReader
    from rotkehlchen.types import BTCAddress, ChecksumEvmAddress


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_query_empty_blockchain_balances(rotkehlchen_api_server: 'APIServer') -> None:
    """Make sure that querying balances for all blockchains works when no accounts are tracked

    Regression test for https://github.com/rotki/rotki/issues/848
    """
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'named_blockchain_balances_resource',
        blockchain='ETH',
    ))
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert data['result'] == {'per_account': {}, 'totals': {'assets': {}, 'liabilities': {}}}

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'named_blockchain_balances_resource',
        blockchain='BTC',
    ))
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert data['result'] == {'per_account': {}, 'totals': {'assets': {}, 'liabilities': {}}}

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainbalancesresource',
    ))
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert data['result'] == {'per_account': {}, 'totals': {'assets': {}, 'liabilities': {}}}


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('btc_accounts', [[
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    'bc1qhkje0xfvhmgk6mvanxwy09n45df03tj3h3jtnf',
]])
def test_query_bitcoin_blockchain_bech32_balances(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        btc_accounts: list['BTCAddress'],
        caplog: 'pytest.LogCaptureFixture',
) -> None:
    """Test that querying Bech32 bitcoin addresses works fine"""
    caplog.set_level(logging.DEBUG)
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0

    btc_balances = ['111110', '3232223', '555555333']
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        btc_balances=btc_balances,
    )

    # query all balances
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'blockchainbalancesresource',
        ))
    result = assert_proper_sync_response_with_result(response)
    assert_btc_balances_result(
        result=result,
        btc_accounts=btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=False,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('mocked_current_prices', [{
    'RDN': FVal('0.1135'),
    'ETH': FVal('212.92'),
    'BTC': FVal('8849.04'),
}])
def test_query_blockchain_balances(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        btc_accounts: list['BTCAddress'],
) -> None:
    """Test that the query blockchain balances endpoint works when queried asynchronously
    """
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0

    async_query = random.choice([False, True])
    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=btc_accounts)

    # First query only ETH and token balances
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain='ETH',
        ), json={'async_query': async_query})
        outcome = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 5,
        )

    assert_eth_balances_result(
        rotki=rotki,
        result=outcome,
        eth_accounts=ethereum_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=False,
    )

    # Then query only BTC balances
    with setup.bitcoin_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain='BTC',
        ), json={'async_query': async_query})
        outcome = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
        )

    assert_btc_balances_result(
        result=outcome,
        btc_accounts=btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=False,
    )

    # Finally query all balances
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'blockchainbalancesresource',
        ), json={'async_query': async_query})
        outcome = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 5,
        )

    assert_eth_balances_result(
        rotki=rotki,
        result=outcome,
        eth_accounts=ethereum_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=True,
    )
    assert_btc_balances_result(
        result=outcome,
        btc_accounts=btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=True,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_query_blockchain_balances_ignore_cache(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        btc_accounts: list['BTCAddress'],
) -> None:
    """Test that the query blockchain balances endpoint can ignore the cache"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=btc_accounts)
    eth_query = patch.object(
        rotki.chains_aggregator,
        'query_eth_balances',
        wraps=rotki.chains_aggregator.query_eth_balances,
    )
    tokens_query = patch.object(
        rotki.chains_aggregator,
        'query_evm_tokens',
        wraps=rotki.chains_aggregator.query_evm_tokens,
    )

    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        eth_mock = stack.enter_context(eth_query)
        tokens_mock = stack.enter_context(tokens_query)
        # Query ETH and token balances once
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain='ETH',
        ))
        result = assert_proper_sync_response_with_result(response)
        assert_eth_balances_result(
            rotki=rotki,
            result=result,
            eth_accounts=ethereum_accounts,
            eth_balances=setup.eth_balances,
            token_balances=setup.token_balances,
            also_btc=False,
        )
        assert eth_mock.call_count == 1
        assert tokens_mock.call_count == 1

        # Query again and make sure this time cache is used
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain='ETH',
        ))
        result = assert_proper_sync_response_with_result(response)
        assert_eth_balances_result(
            rotki=rotki,
            result=result,
            eth_accounts=ethereum_accounts,
            eth_balances=setup.eth_balances,
            token_balances=setup.token_balances,
            also_btc=False,
        )
        assert eth_mock.call_count == 1
        assert tokens_mock.call_count == 1

        # Finally query with ignoring the cache
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain='ETH',
        ), json={'ignore_cache': True})
        result = assert_proper_sync_response_with_result(response)
        assert_eth_balances_result(
            rotki=rotki,
            result=result,
            eth_accounts=ethereum_accounts,
            eth_balances=setup.eth_balances,
            token_balances=setup.token_balances,
            also_btc=False,
        )
        assert eth_mock.call_count == 2
        assert tokens_mock.call_count == 2


def _add_blockchain_accounts_test_start(
        api_server: 'APIServer',
        query_balances_before_first_modification: bool,
        ethereum_accounts: list['ChecksumEvmAddress'],
        btc_accounts: list['BTCAddress'],
        async_query: bool,
) -> tuple[list['ChecksumEvmAddress'], list[str], dict[Any, list[str]]]:
    # Disable caching of query results
    rotki = api_server.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
    rdn_evm_token = A_RDN.resolve_to_evm_token()
    if query_balances_before_first_modification:
        # Also test by having balances queried before adding an account
        eth_balances = ['1000000', '2000000']
        token_balances = {rdn_evm_token: ['0', '4000000']}
        setup = setup_balances(
            rotki,
            ethereum_accounts=ethereum_accounts,
            btc_accounts=btc_accounts,
            eth_balances=eth_balances,
            token_balances=token_balances,
        )
        with ExitStack() as stack:
            setup.enter_blockchain_patches(stack)
            requests.get(api_url_for(
                api_server,
                'blockchainbalancesresource',
            ))

    new_eth_accounts = [make_evm_address(), make_evm_address()]
    all_eth_accounts = ethereum_accounts + new_eth_accounts
    eth_balances = ['1000000', '2000000', '3000000', '4000000']
    token_balances = {rdn_evm_token: ['0', '4000000', '0', '250000000']}
    setup = setup_balances(
        rotki,
        ethereum_accounts=all_eth_accounts,
        btc_accounts=btc_accounts,
        eth_balances=eth_balances,
        token_balances=token_balances,
    )

    with rotki.data.db.user_write() as write_cursor:  # add block production with new account as recpient  # noqa: E501
        write_cursor.execute(
            'INSERT INTO history_events(identifier, entry_type, event_identifier, sequence_index, timestamp, location, location_label, asset, amount, notes, type, subtype) '  # noqa: E501
            "VALUES(1, 4, 'BP1_17153311', 0, 1682911787000, 'f', ?, 'ETH', '0.1', ?, ?, 'block production')",  # noqa: E501
            (
                new_eth_accounts[0],
                f'Validator 4242 produced block 17153311 with 0.1 ETH going to {new_eth_accounts[0]} as the block reward',  # noqa: E501
                HistoryEventType.INFORMATIONAL.serialize(),
            ),
        )
        write_cursor.execute('INSERT INTO eth_staking_events_info(identifier, validator_index, is_exit_or_blocknumber) VALUES(1, 4242, 17153311)')  # noqa: E501

    # The application has started only with 2 ethereum accounts. Let's add two more
    data = {
        'accounts': [{'address': x} for x in new_eth_accounts],
        'async_query': async_query,
    }
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.put(api_url_for(
            api_server,
            'blockchainsaccountsresource',
            blockchain='ETH',
        ), json=data)

        result = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=api_server,
            async_query=async_query,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 4,
        )

        assert result == new_eth_accounts
        response = requests.get(api_url_for(
            api_server,
            'blockchainbalancesresource',
        ))
        result = assert_proper_sync_response_with_result(response)

    assert_eth_balances_result(
        rotki=rotki,
        result=result,
        eth_accounts=all_eth_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=True,
    )
    # Also make sure that DB has been properly modified
    with rotki.data.db.conn.read_ctx() as cursor:
        # accounts should be added in the DB
        accounts = rotki.data.db.get_blockchain_accounts(cursor)
        assert len(accounts.eth) == 4
        assert all(acc in accounts.eth for acc in all_eth_accounts)
        assert len(accounts.btc) == 2
        assert all(acc in accounts.btc for acc in btc_accounts)
        # The block production event type for the fee recipient we start tracking should change
        assert cursor.execute('SELECT type from history_events WHERE identifier=1').fetchone()[0] == HistoryEventType.STAKING.serialize()  # noqa: E501

    # Now try to query all balances to make sure the result is the stored
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(api_url_for(
            api_server,
            'blockchainbalancesresource',
        ))
    result = assert_proper_sync_response_with_result(response)
    assert_eth_balances_result(
        rotki=rotki,
        result=result,
        eth_accounts=all_eth_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=True,
    )

    return all_eth_accounts, eth_balances, token_balances


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('query_balances_before_first_modification', [True, False])
def test_add_blockchain_accounts(  # hard to VCR, the order of requests is not always the same
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        btc_accounts: list['BTCAddress'],
        query_balances_before_first_modification: bool,
) -> None:
    """Test that the endpoint adding blockchain accounts works properly"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    all_eth_accounts, eth_balances, token_balances = _add_blockchain_accounts_test_start(
        api_server=rotkehlchen_api_server,
        query_balances_before_first_modification=query_balances_before_first_modification,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        async_query=async_query,
    )
    # Now we will try to add a new BTC account. Setup the mocking infrastructure again
    all_btc_accounts = btc_accounts + [UNIT_BTC_ADDRESS3]
    setup = setup_balances(
        rotki,
        ethereum_accounts=all_eth_accounts,
        btc_accounts=all_btc_accounts,
        eth_balances=eth_balances,
        token_balances=token_balances,
        btc_balances=['3000000', '5000000', '600000000'],
    )
    # add the new BTC account
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain='BTC',
        ), json={
            'accounts': [{'address': UNIT_BTC_ADDRESS3}],
            'async_query': async_query,
        })
        result = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
        )
        assert result == [UNIT_BTC_ADDRESS3]
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'blockchainbalancesresource',
            blockchain=SupportedBlockchain.BITCOIN.value,
        ))
        result = assert_proper_sync_response_with_result(response)

    assert_btc_balances_result(
        result=result,
        btc_accounts=all_btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=False,
    )

    assert rotki.chains_aggregator.accounts.btc[-1] == UNIT_BTC_ADDRESS3
    # Also make sure it's added in the DB
    with rotki.data.db.conn.read_ctx() as cursor:
        accounts = rotki.data.db.get_blockchain_accounts(cursor)
    assert len(accounts.eth) == 4
    assert all(acc in accounts.eth for acc in all_eth_accounts)
    assert len(accounts.btc) == 3
    assert all(acc in accounts.btc for acc in all_btc_accounts)

    # Now try to query all balances to make sure the result is also stored
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'blockchainbalancesresource',
        ), json={'async_query': async_query})
        outcome = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 3,
        )

    assert_btc_balances_result(
        result=outcome,
        btc_accounts=all_btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=True,
    )

    # now try to add an already existing account and see an error is returned
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain='ETH',
        ), json={'accounts': [{'address': ethereum_accounts[0]}]})
        assert_error_response(
            response=response,
            status_code=HTTPStatus.BAD_REQUEST,
            contained_in_msg=f'Blockchain account/s {ethereum_accounts[0]} already exist',
        )

    # Add a BCH account
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='BCH',
    ), json={'accounts': [
        {'address': 'prettyirrelevant.eth'},
        {'address': '12tkqA9xSoowkzoERHMWNKsTey55YEBqkv'},
        {'address': 'pp8skudq3x5hzw8ew7vzsw8tn4k8wxsqsv0lt0mf3g'},
    ]})
    assert_proper_response(response)
    assert set(rotki.chains_aggregator.accounts.bch) == {
        '1H9EndxvYSibvnDSsxZRYvuqZaCcRXdRcB',
        '12tkqA9xSoowkzoERHMWNKsTey55YEBqkv',
        'pp8skudq3x5hzw8ew7vzsw8tn4k8wxsqsv0lt0mf3g',
    }

    # Check that the BCH accounts are present in the DB
    with rotki.data.db.conn.read_ctx() as cursor:
        accounts = rotki.data.db.get_blockchain_accounts(cursor)
    assert len(accounts.bch) == 3

    # Try adding an already saved BCH address in different format
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='BCH',
    ), json={'accounts': [
        # 12tkqA9xSoowkzoERHMWNKsTey55YEBqkv
        {'address': 'bitcoincash:qq2vrmtj6zg4pw897jwef4fswrfvruwmxcfxq3r9dt'},
        # pp8skudq3x5hzw8ew7vzsw8tn4k8wxsqsv0lt0mf3g
        {'address': '38ty1qB68gHsiyZ8k3RPeCJ1wYQPrUCPPr'},
    ]})
    assert_error_response(response, 'Blockchain account/s bitcoincash:qq2vrmtj6zg4pw897jwef4fswrfvruwmxcfxq3r9dt,38ty1qB68gHsiyZ8k3RPeCJ1wYQPrUCPPr already exist')  # noqa: E501

    # Try adding a segwit BTC address
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='BCH',
    ), json={'accounts': [
        {'address': 'bc1qazcm763858nkj2dj986etajv6wquslv8uxwczt'},
    ]})
    assert_error_response(response, 'Given value bc1qazcm763858nkj2dj986etajv6wquslv8uxwczt is not a valid bitcoin cash address')  # noqa: E501

    # Try adding same BCH address but in different formats
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='BCH',
    ), json={
        'accounts': [
            {'address': '1Mnwij9Zkk6HtmdNzyEUFgp6ojoLaZekP8'},
            {'address': 'bitcoincash:qrjp962nn74p57w0gaf77d335upghk220yceaxqxwa'},
        ],
    })
    assert_error_response(response, 'appears multiple times in the request data')

    # adding a taproot btc address
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='BTC',
    ), json={'accounts': [
        {'address': 'bc1pqyqszqgpqyqszqgpqyqszqgpqyqszqgpqyqszqgpqyqszqgpqyqsyjer9e'},
    ]})
    assert_proper_response(response)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('btc_accounts', [[]])
def test_add_blockchain_accounts_concurrent(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that if we add blockchain accounts concurrently we won't get any duplicates"""
    ethereum_accounts = [make_evm_address(), make_evm_address(), make_evm_address()]
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    query_accounts = ethereum_accounts.copy()
    for _ in range(5):
        query_accounts.extend(ethereum_accounts)
    # Fire all requests almost concurrently. And don't wait for them
    for idx, account in enumerate(query_accounts):
        gevent.spawn_later(
            0.01 * idx,
            requests.put,
            api_url_for(
                rotkehlchen_api_server,
                'blockchainsaccountsresource',
                blockchain='ETH',
            ),
            json={'accounts': [{'address': account}], 'async_query': True},
        )
    # We are making an assumption of sequential ids here. This may not always
    # be the case so for that later down the test we will skip the task check
    # if this happens. Can't think of a better way to do this at the moment
    task_ids = dict(enumerate(query_accounts))

    with Timeout(ASYNC_TASK_WAIT_TIMEOUT):
        while len(task_ids) != 0:
            task_id, account = random.choice(list(task_ids.items()))
            response = requests.get(
                api_url_for(
                    rotkehlchen_api_server,
                    'specific_async_tasks_resource',
                    task_id=task_id,
                ),
            )
            if response.status_code == HTTPStatus.NOT_FOUND:
                sleep(.1)  # not started yet
                continue

            assert_proper_response(response, status_code=None)  # do not check status code here
            result = response.json()['result']
            status = result['status']
            if status == 'pending':
                sleep(.1)
                continue
            if status == 'completed':
                result = result['outcome']
            else:
                raise AssertionError('Should not happen at this point')

            task_ids.pop(task_id)
            if result['result'] is None:
                assert 'already exist' in result['message']
                continue

    assert set(rotki.chains_aggregator.accounts.eth) == set(ethereum_accounts)


@pytest.mark.parametrize('include_etherscan_key', [False])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_no_etherscan_is_detected(
        rotkehlchen_api_server: 'APIServer',
        websocket_connection: 'WebsocketReader',
) -> None:
    """Make sure that interacting with ethereum without an etherscan key is given a warning"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    new_address = make_evm_address()
    setup = setup_balances(rotki, ethereum_accounts=[new_address], btc_accounts=None)

    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain='ETH',
        ), json={'accounts': [{'address': new_address}]})
        assert_proper_response(response)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'blockchainbalancesresource',
        ))
        assert_proper_response(response)

    websocket_connection.wait_until_messages_num(num=1, timeout=10)
    msg = websocket_connection.pop_message()
    assert msg == {
        'type': 'missing_api_key',
        'data': {'service': 'etherscan'},
    }


@pytest.mark.parametrize('method', ['PUT', 'DELETE'])
def test_blockchain_accounts_endpoint_errors(
        rotkehlchen_api_server: 'APIServer',
        rest_api_port: int,
        method: str,
        test_session: 'ConfigurableSession',
) -> None:
    """
    Test /api/(version)/blockchains/(name) for edge cases and errors.

    Test for errors when both adding and removing a blockchain account. Both put/delete
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0

    # Provide unsupported blockchain name
    account = '0x00d74c25bbf93df8b2a41d82b0076843b4db0349'
    with test_session.request(
        method,
        api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain='DDASDAS'),
        json={'accounts': [account]},
    ) as response:
        assert_error_response(
            response=response,
            contained_in_msg='Failed to deserialize SupportedBlockchain value DDASDAS',
        )

    # Provide no blockchain name
    with test_session.request(
            method,
            f'http://localhost:{rest_api_port}/api/1/blockchains',
            json={'accounts': [account]},
    ) as response:
        assert_error_response(
            response=response,
            status_code=HTTPStatus.NOT_FOUND,
        )

    # Do not provide accounts
    with test_session.request(
            method,
            api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain='ETH'),
            json={'dsadsad': 'foo'},
    ) as response:
        assert_error_response(
            response=response,
            contained_in_msg='Missing data for required field',
        )

    # Provide wrong type of account
    with test_session.request(
            method,
            api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain='ETH'),
            json={'accounts': 'foo'},
    ) as response:
        if method == 'GET':
            message = "'accounts': ['Not a valid list.'"
        elif method == 'DELETE':
            message = 'Given value foo is not an evm address'
        else:
            message = '"accounts": {"0": {"_schema": ["Invalid input type.'
        assert_error_response(
            response=response,
            contained_in_msg=message,
        )
        assert 'foo' not in rotki.chains_aggregator.accounts.eth

    # Provide empty list
    with test_session.request(
            method,
            api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain='ETH'),
            json={'accounts': []},
    ) as response:
        verb = 'add' if method == 'PUT' else 'remove'
        assert_error_response(
            response=response,
            contained_in_msg=f'Empty list of blockchain accounts to {verb} was given',
        )

    # Provide invalid ETH account (more bytes)
    invalid_eth_account = '0x554FFc77f4251a9fB3c0E3590a6a205f8d4e067d01'
    msg = f'Given value {invalid_eth_account} is not an evm address'
    with test_session.request(
            method,
            api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain='ETH'),
            json={'accounts': [{'address': invalid_eth_account}] if method == 'PUT' else [invalid_eth_account]},  # noqa: E501
    ) as response:
        assert_error_response(
            response=response,
            contained_in_msg=msg,
        )

    # Provide invalid BTC account
    invalid_btc_account = '18ddjB7HWTaxzvTbLp1nWvaixU3U2oTZ1'
    with test_session.request(
            method,
            api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain='BTC'),
            json={'accounts': [{'address': invalid_btc_account}] if method == 'PUT' else [invalid_btc_account]},  # noqa: E501
    ) as response:
        msg = f'Given value {invalid_btc_account} is not a valid bitcoin address'
        assert_error_response(
            response=response,
            contained_in_msg=msg,
        )
        assert_msg = 'Invalid BTC account should not have been added'
        assert invalid_btc_account not in rotki.chains_aggregator.accounts.btc, assert_msg

    # Provide not existing but valid ETH account for removal
    unknown_account = make_evm_address()
    with test_session.delete(
            api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain='ETH'),
            json={'accounts': [unknown_account]},
    ) as response:
        assert_error_response(
            response=response,
            contained_in_msg=f'Tried to remove unknown ETH accounts {unknown_account}',
        )

    # Provide not existing but valid BTC account for removal
    unknown_btc_account = '18ddjB7HWTVxzvTbLp1nWvaBxU3U2oTZF2'
    with test_session.delete(
            api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain='BTC'),
            json={'accounts': [unknown_btc_account]},
    ) as response:
        assert_error_response(
            response=response,
            contained_in_msg=f'Tried to remove unknown BTC accounts {unknown_btc_account}',
        )

    # Provide list with one valid and one invalid account and make sure that nothing
    # is added / removed and the valid one is skipped
    msg = 'Given value 142 is not an evm address'
    if method == 'DELETE':
        # Account should be an existing account
        account = rotki.chains_aggregator.accounts.eth[0]

    with test_session.request(
            method,
            api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain='ETH'),
            json={'accounts': ['142', account] if method == 'DELETE' else [{'address': '142'}, {'address': account}]},  # noqa: E501
    ) as response:
        assert_error_response(
            response=response,
            contained_in_msg=msg,
            status_code=HTTPStatus.BAD_REQUEST,
        )

    # Provide invalid type for accounts
    with test_session.request(
            method,
            api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain='ETH'),
            json={'accounts': [{'address': 15}] if method == 'PUT' else [15]},
    ) as response:
        assert_error_response(
            response=response,
            contained_in_msg='Not a valid string',
        )

    # Test that providing an account more than once in request data is an error
    account = '0x7BD904A3Db59fA3879BD4c246303E6Ef3aC3A4C6'
    with test_session.request(
            method,
            api_url_for(rotkehlchen_api_server, 'blockchainsaccountsresource', blockchain='ETH'),
            json={'accounts': [{'address': account}, {'address': account}] if method == 'PUT' else [account, account]},  # noqa: E501
    ) as response:
        assert_error_response(
            response=response,
            contained_in_msg=f'Address {account} appears multiple times in the request data',
            status_code=HTTPStatus.BAD_REQUEST,
        )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_blockchain_accounts_with_tags_and_label_and_querying_them(rotkehlchen_api_server: 'APIServer') -> None:  # noqa: E501
    """Test that adding account with labels and tags works correctly"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Add three tags
    tag1 = {
        'name': 'public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag1,
    )
    assert_proper_response(response)
    tag2 = {
        'name': 'desktop',
        'description': 'Accounts that are stored in the desktop PC',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag2,
    )
    assert_proper_response(response)
    tag3 = {
        'name': 'hardware',
        'description': 'hardware wallets',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag3,
    )
    assert_proper_response(response)

    # Now add 3 accounts. Some of them use these tags, some dont
    new_eth_accounts = [make_evm_address(), make_evm_address(), make_evm_address()]
    accounts_data: list[dict] = [{
        'address': new_eth_accounts[0],
        'label': 'my metamask',
        'tags': ['public', 'desktop'],
    }, {
        'address': new_eth_accounts[1],
        'label': 'geth account',
    }, {
        'address': new_eth_accounts[2],
        'tags': ['public', 'hardware'],
    }]
    # Make sure that even adding accounts with label and tags, balance query works fine
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': accounts_data})
    assert_proper_response(response)
    with rotki.data.db.conn.read_ctx() as cursor:
        accounts_in_db = rotki.data.db.get_blockchain_accounts(cursor).eth
        assert set(accounts_in_db) == set(new_eth_accounts)

    # Now query the ethereum account data to see that tags and labels are added
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ))
    response_data: list[dict] = assert_proper_sync_response_with_result(response)
    assert len(response_data) == len(accounts_data)
    for entry in response_data:
        # find the corresponding account in accounts data
        compare_account = None
        for account in accounts_data:
            if entry['address'] == account['address']:
                compare_account = account
                break
        assert compare_account, 'Found unexpected address {entry["address"]} in response'

        assert entry['address'] == compare_account['address']
        assert entry['label'] == compare_account.get('label', None)
        if entry['tags'] is not None:
            assert set(entry['tags']) == set(compare_account['tags'])
        else:
            assert 'tags' not in compare_account


@pytest.mark.parametrize('number_of_eth_accounts', [3])
@pytest.mark.parametrize('btc_accounts', [[
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
]])
def test_edit_blockchain_accounts(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that the endpoint editing blockchain accounts works properly"""
    # Add 3 tags
    tag1 = {
        'name': 'public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag1,
    )
    assert_proper_response(response)
    tag2 = {
        'name': 'desktop',
        'description': 'Accounts that are stored in the desktop PC',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag2,
    )
    assert_proper_response(response)
    tag3 = {
        'name': 'hardware',
        'description': 'hardware wallets',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag3,
    )
    assert_proper_response(response)

    # Edit 2 out of the 3 accounts so that they have tags
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'Second account in the array',
        'tags': ['public'],
    }, {
        'address': ethereum_accounts[2],
        'label': 'Thirds account in the array',
        'tags': ['public', 'desktop'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)

    result = assert_proper_sync_response_with_result(response)
    expected_result = request_data['accounts'] + [
        {'address': ethereum_accounts[0]},
    ]
    compare_account_data(result, expected_result)

    # Also make sure that when querying the endpoint we get the edited account data
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ))
    result = assert_proper_sync_response_with_result(response)
    compare_account_data(result, expected_result)

    # Edit 1 account so that both a label is edited but also a tag is removed and a tag is edited
    request_data = {'accounts': [{
        'address': ethereum_accounts[2],
        'label': 'Edited label',
        'tags': ['hardware', 'desktop'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ))
    result = assert_proper_sync_response_with_result(response)
    for result_entry in result:  # order of return is not guaranteed
        if result_entry['address'] == ethereum_accounts[2]:
            assert result_entry['address'] == request_data['accounts'][0]['address']
            assert result_entry['label'] == request_data['accounts'][0]['label']
            assert set(result_entry['tags']) == set(request_data['accounts'][0]['tags'])
            break
    else:  # did not find account in the for
        raise AssertionError('Edited account not returned in the result')

    # Edit a BTC account
    request_data = {'accounts': [{
        'address': UNIT_BTC_ADDRESS1,
        'label': 'BTC account label',
        'tags': ['public'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='BTC',
    ), json=request_data)
    result = assert_proper_sync_response_with_result(response)
    assert len(result) == 2
    # Assert the result is in the expected format and is edited
    standalone = result['standalone']
    assert len(standalone) == 2
    assert standalone[0] == {
        'address': UNIT_BTC_ADDRESS1,
        'label': 'BTC account label',
        'tags': ['public'],
    }
    assert standalone[1] == {
        'address': UNIT_BTC_ADDRESS2,
        'label': None,
        'tags': None,
    }
    assert len(result['xpubs']) == 0


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_edit_blockchain_account_errors(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that errors are handled properly in the edit accounts endpoint"""
    # Add two tags
    tag1 = {
        'name': 'public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag1,
    )
    assert_proper_response(response)
    tag2 = {
        'name': 'desktop',
        'description': 'Accounts that are stored in the desktop PC',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag2,
    )
    assert_proper_response(response)

    # Missing accounts
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'foo': ['a']})
    assert_error_response(
        response=response,
        contained_in_msg='"accounts": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for accounts
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': 142})
    assert_error_response(
        response=response,
        contained_in_msg='Invalid input type',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Missing address for an account
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [{
        'label': 'Second account in the array',
        'tags': ['public'],
    }]})
    assert_error_response(
        response=response,
        contained_in_msg='address": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for an account's address
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [{
        'address': 55,
        'label': 'Second account in the array',
        'tags': ['public'],
    }]})
    assert_error_response(
        response=response,
        contained_in_msg='address": ["Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid address for an account's address
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [{
        'address': 'dsadsd',
        'label': 'Second account in the array',
        'tags': ['public'],
    }]})
    assert_error_response(
        response=response,
        contained_in_msg='Given value dsadsd is not an evm address',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for label
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [{
        'address': ethereum_accounts[1],
        'label': 55,
        'tags': ['public'],
    }]})
    assert_error_response(
        response=response,
        contained_in_msg='label": ["Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Empty list for tags
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': [],
    }]})
    assert_error_response(
        response=response,
        contained_in_msg='Provided empty list for tags. Use null',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for tags
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': 231,
    }]})
    assert_error_response(
        response=response,
        contained_in_msg='tags": ["Not a valid list',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for tags list entry
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': [55.221],
    }]})
    assert_error_response(
        response=response,
        contained_in_msg='tags": {"0": ["Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # One non existing tag
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': ['nonexistent'],
    }]})
    assert_error_response(
        response=response,
        contained_in_msg='When editing blockchain accounts, unknown tags nonexistent were found',
        status_code=HTTPStatus.CONFLICT,
    )

    # Mix of existing and non-existing tags
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': ['a', 'public', 'b', 'desktop', 'c'],
    }]})
    assert_error_response(
        response=response,
        contained_in_msg='When editing blockchain accounts, unknown tags ',
        status_code=HTTPStatus.CONFLICT,
    )

    # Provide same account multiple times in request data
    msg = f'Address {ethereum_accounts[1]} appears multiple times in the request data'
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': ['a', 'public', 'b', 'desktop', 'c'],
    }, {
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': ['a', 'public', 'b', 'desktop', 'c'],
    }]})
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )


def _remove_blockchain_accounts_test_start(
        api_server: 'APIServer',
        query_balances_before_first_modification: bool,
        ethereum_accounts: list['ChecksumEvmAddress'],
        btc_accounts: list['BTCAddress'],
        async_query: bool,
) -> tuple[list['ChecksumEvmAddress'], list[str], dict['EvmToken', list[str]]]:
    # Disable caching of query results
    rotki = api_server.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
    removed_eth_accounts = [ethereum_accounts[0], ethereum_accounts[2]]
    eth_accounts_after_removal = [ethereum_accounts[1], ethereum_accounts[3]]
    all_eth_balances = ['1000000', '2000000', '3000000', '4000000']
    token_balances = {A_RDN.resolve_to_evm_token(): ['0', '0', '450000000', '0']}
    eth_balances_after_removal = ['2000000', '4000000']
    token_balances_after_removal: dict[EvmToken, list[str]] = {}
    a_dai_token = A_DAI.resolve_to_evm_token()
    starting_liabilities = {a_dai_token: ['5555555', '1000000', '0', '99999999']}

    if query_balances_before_first_modification:
        # Also test by having balances queried before removing an account
        setup = setup_balances(
            rotki,
            ethereum_accounts=ethereum_accounts,
            btc_accounts=btc_accounts,
            eth_balances=all_eth_balances,
            token_balances=token_balances,
            liabilities=starting_liabilities,
        )
        with ExitStack() as stack:
            setup.enter_blockchain_patches(stack)
            assert_proper_response(requests.get(api_url_for(
                api_server,
                'blockchainbalancesresource',
            )))

    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        eth_balances=all_eth_balances,
        token_balances=token_balances,
        liabilities=starting_liabilities,
    )

    with rotki.data.db.user_write() as write_cursor:  # add block production with removed account as recpient  # noqa: E501
        write_cursor.execute(
            'INSERT INTO history_events(identifier, entry_type, event_identifier, sequence_index, timestamp, location, location_label, asset, amount, notes, type, subtype) '  # noqa: E501
            "VALUES(1, 4, 'BP1_17153311', 0, 1682911787000, 'f', ?, 'ETH', '0.1', ?, ?, 'block production')",  # noqa: E501
            (
                removed_eth_accounts[0],
                f'Validator 4242 produced block 17153311 with 0.1 ETH going to {removed_eth_accounts[0]} as the block reward',  # noqa: E501
                HistoryEventType.STAKING.serialize(),
            ),
        )
        write_cursor.execute('INSERT INTO eth_staking_events_info(identifier, validator_index, is_exit_or_blocknumber) VALUES(1, 4242, 17153311)')  # noqa: E501

    # The application has started with 4 ethereum accounts. Remove two and see that balances match
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.delete(api_url_for(
            api_server,
            'blockchainsaccountsresource',
            blockchain='ETH',
        ), json={'accounts': removed_eth_accounts, 'async_query': async_query})
        result = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=api_server,
            async_query=async_query,
        )

    if query_balances_before_first_modification is True:
        assert_eth_balances_result(
            rotki=rotki,
            result=result,
            eth_accounts=eth_accounts_after_removal,
            eth_balances=eth_balances_after_removal,
            token_balances=token_balances_after_removal,
            also_btc=True,
        )

    # Also make sure that DB has been properly modified
    with rotki.data.db.conn.read_ctx() as cursor:
        # accounts should be removed from the DB
        accounts = rotki.data.db.get_blockchain_accounts(cursor)
        assert len(accounts.eth) == 2
        assert all(acc in accounts.eth for acc in eth_accounts_after_removal)
        assert len(accounts.btc) == 2
        assert all(acc in accounts.btc for acc in btc_accounts)
        # The block production event type for the fee recipient we stopped tracking should change
        assert cursor.execute('SELECT type from history_events WHERE identifier=1').fetchone()[0] == HistoryEventType.INFORMATIONAL.serialize()  # noqa: E501

    # Now try to query all balances to make sure the result is the stored
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(api_url_for(
            api_server,
            'blockchainbalancesresource',
        ))
    result = assert_proper_sync_response_with_result(response)
    assert_eth_balances_result(
        rotki=rotki,
        result=result,
        eth_accounts=eth_accounts_after_removal,
        eth_balances=eth_balances_after_removal,
        token_balances=token_balances_after_removal,
        also_btc=True,
    )

    return eth_accounts_after_removal, eth_balances_after_removal, token_balances_after_removal


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('number_of_eth_accounts', [4])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('query_balances_before_first_modification', [True, False])
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_remove_blockchain_accounts(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        gnosis_accounts: list['ChecksumEvmAddress'],
        btc_accounts: list['BTCAddress'],
        query_balances_before_first_modification: bool,
) -> None:
    """Test that the endpoint removing blockchain accounts works properly"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.write_ctx() as write_cursor:
        rotki.data.db.update_used_query_range(  # add range to see if it gets deleted
            write_cursor=write_cursor,
            name=f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{gnosis_accounts[0]}',
            start_ts=Timestamp(0),
            end_ts=Timestamp(1),
        )

    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain=SupportedBlockchain.GNOSIS.value,
    ), json={'accounts': gnosis_accounts})
    assert_proper_sync_response_with_result(response)
    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM used_query_ranges WHERE name=?',
            (f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{gnosis_accounts[0]}',),
        ).fetchone()[0] == 0

    (
        eth_accounts_after_removal,
        eth_balances_after_removal,
        token_balances_after_removal,
    ) = _remove_blockchain_accounts_test_start(
        api_server=rotkehlchen_api_server,
        query_balances_before_first_modification=query_balances_before_first_modification,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        async_query=async_query,
    )

    # Now we will try to remove a BTC account. Setup the mocking infrastructure again
    all_btc_accounts = [UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]
    btc_accounts_after_removal = [UNIT_BTC_ADDRESS2]
    setup = setup_balances(
        rotki,
        ethereum_accounts=eth_accounts_after_removal,
        btc_accounts=all_btc_accounts,
        eth_balances=eth_balances_after_removal,
        token_balances=token_balances_after_removal,
        btc_balances=['3000000', '5000000'],
    )

    # remove the new BTC account
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=SupportedBlockchain.BITCOIN.value,
        ), json={'accounts': [UNIT_BTC_ADDRESS1], 'async_query': async_query})
        outcome = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
        )
    assert_btc_balances_result(
        result=outcome,
        btc_accounts=btc_accounts_after_removal,
        btc_balances=['5000000'],
        also_eth=True,
    )

    # Also make sure it's removed from the DB
    with rotki.data.db.conn.read_ctx() as cursor:
        accounts = rotki.data.db.get_blockchain_accounts(cursor)
    assert len(accounts.eth) == 2
    assert all(acc in accounts.eth for acc in eth_accounts_after_removal)
    assert len(accounts.btc) == 1
    assert all(acc in accounts.btc for acc in btc_accounts_after_removal)

    # Now try to query all balances to make sure the result is also stored
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'blockchainbalancesresource',
        ), json={'async_query': async_query})
        outcome = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 3,
        )

    assert_btc_balances_result(
        result=outcome,
        btc_accounts=btc_accounts_after_removal,
        btc_balances=['5000000'],
        also_eth=True,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_remove_nonexisting_blockchain_account_along_with_existing(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that if an existing and a non-existing account are given to remove, nothing is"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Add a tag
    tag1 = {
        'name': 'public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag1,
    )
    assert_proper_response(response)
    # Edit the first ethereum account which we will attempt to delete
    # to have this tag so that we see the mapping is still there afterwards
    request_data = {'accounts': [{'address': ethereum_accounts[0], 'label': 'account1', 'tags': ['public']}]}  # noqa: E501
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    assert_proper_response(response)
    expected_data = request_data['accounts'] + [
        {'address': ethereum_accounts[1]},
    ]
    compare_account_data(response.json()['result'], expected_data)

    eth_balances = ['11110', '22222']
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        eth_balances=eth_balances,
        token_balances=None,
    )
    unknown_account = make_evm_address()
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain='ETH',
        ), json={'accounts': [ethereum_accounts[0], unknown_account]})
    assert_error_response(
        response=response,
        contained_in_msg=f'Tried to remove unknown ETH accounts {unknown_account}',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Also make sure that no account was removed from the DB
    with rotki.data.db.conn.read_ctx() as cursor:
        accounts = rotki.data.db.get_blockchain_accounts(cursor)
    assert len(accounts.eth) == 2
    assert all(acc in accounts.eth for acc in ethereum_accounts)
    # Also make sure no tag mappings were removed
    cursor = rotki.data.db.conn.cursor()
    query = cursor.execute('SELECT object_reference, tag_name FROM tag_mappings;').fetchall()
    assert len(query) == 1
    assert query[0][0] == ethereum_accounts[0]
    assert query[0][1] == 'public'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_remove_blockchain_account_with_tags_removes_mapping(rotkehlchen_api_server: 'APIServer') -> None:  # noqa: E501
    """Test that removing an account with tags remove the mappings"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Add two tags
    tag1 = {
        'name': 'public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag1,
    )
    assert_proper_response(response)
    tag2 = {
        'name': 'desktop',
        'description': 'Accounts that are stored in the desktop PC',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag2,
    )
    assert_proper_response(response)

    # Now add 2 accounts both of them using tags
    new_btc_accounts = [UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]
    accounts_data = [{
        'address': new_btc_accounts[0],
        'label': 'my btc miner',
        'tags': ['public', 'desktop'],
    }, {
        'address': new_btc_accounts[1],
        'label': 'other account',
        'tags': ['desktop'],
    }]
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='BTC',
    ), json={'accounts': accounts_data})
    assert_proper_response(response)
    expected_accounts_data = [
        SingleBlockchainAccountData(
            address=new_btc_accounts[0],
            label='my btc miner',
            tags=['desktop', 'public'],
        ),
        SingleBlockchainAccountData(
            address=new_btc_accounts[1],
            label='other account',
            tags=['desktop'],
        ),
    ]
    with rotki.data.db.conn.read_ctx() as cursor:
        accounts_in_db = rotki.data.db.get_blockchain_account_data(
            cursor=cursor,
            blockchain=SupportedBlockchain.BITCOIN,
        )
        assert accounts_in_db == expected_accounts_data

    # now remove one account
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain=SupportedBlockchain.BITCOIN.value,
    ), json={'accounts': [UNIT_BTC_ADDRESS1]})
    assert_proper_response(response)

    assert set(rotki.chains_aggregator.accounts.btc) == {UNIT_BTC_ADDRESS2}

    # Now check the DB directly and see that tag mappings of the deleted account are gone
    cursor = rotki.data.db.conn.cursor()
    query = cursor.execute('SELECT object_reference, tag_name FROM tag_mappings;').fetchall()
    assert len(query) == 1
    assert query[0][0] == UNIT_BTC_ADDRESS2
    assert query[0][1] == 'desktop'


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [[ADDRESS_MULTICHAIN, ADDRESS_ETH]])
@pytest.mark.parametrize('optimism_accounts', [[ADDRESS_MULTICHAIN, ADDRESS_OP]])
@pytest.mark.parametrize('gnosis_accounts', [[ADDRESS_MULTICHAIN]])
@pytest.mark.parametrize('bch_accounts', [[UNIT_BTC_ADDRESS1]])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
def test_remove_chain_agnostic_accounts(rotkehlchen_api_server: 'APIServer') -> None:
    """Test the removal of accounts for all the chains where they are tracked"""
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'chaintypeaccountresource',
            chain_type=ChainType.EVM.serialize(),
        ),
        json={
            'accounts': [ADDRESS_OP, ADDRESS_MULTICHAIN],
        },
    )
    assert_proper_response(response)
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert len(rotki.chains_aggregator.accounts.get(SupportedBlockchain.OPTIMISM)) == 0
    assert len(rotki.chains_aggregator.accounts.get(SupportedBlockchain.GNOSIS)) == 0
    assert rotki.chains_aggregator.accounts.get(SupportedBlockchain.ETHEREUM) == (ADDRESS_ETH,)
    assert rotki.chains_aggregator.accounts.get(SupportedBlockchain.BITCOIN) == (UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2)  # noqa: E501
    assert rotki.chains_aggregator.accounts.get(SupportedBlockchain.BITCOIN_CASH) == (UNIT_BTC_ADDRESS1,)  # noqa: E501

    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'chaintypeaccountresource',
            chain_type=ChainType.EVM.serialize(),
        ),
        json={
            'chain_type': ChainType.EVM.serialize(),
            'accounts': [ADDRESS_OP, ADDRESS_MULTICHAIN],
        },
    )

    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'chaintypeaccountresource',
            chain_type=ChainType.BITCOIN.serialize(),
        ),
        json={
            'accounts': [UNIT_BTC_ADDRESS1],
            'async_query': True,
        },
    )
    assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=True,
    )
    assert rotki.chains_aggregator.accounts.get(SupportedBlockchain.BITCOIN) == (UNIT_BTC_ADDRESS2,)  # noqa: E501
    assert len(rotki.chains_aggregator.accounts.get(SupportedBlockchain.BITCOIN_CASH)) == 0

    response = requests.delete(  # try that errors are raised correctly for an invalid address
        api_url_for(
            rotkehlchen_api_server,
            'chaintypeaccountresource',
            chain_type=ChainType.EVM.serialize(),
        ),
        json={
            'accounts': [ADDRESS_OP],
        },
    )

    assert_error_response(
        response=response,
        contained_in_msg='Tried to delete non tracked addresses',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [1])
def test_edit_blockchain_account_blank_label(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that setting a blank label on a blockchain account deletes the addressbook entry.
    Regression test for https://github.com/rotki/rotki/pull/8863
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db_addressbook = DBAddressbook(rotki.data.db)

    # Add account with a label, adding an addressbook entry
    request_data = {'accounts': [{'address': ethereum_accounts[0], 'label': 'account1'}]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    assert_proper_response(response)

    with rotki.data.db.conn.read_ctx() as cursor:
        assert len(db_addressbook.get_addressbook_entries(
            cursor=cursor,
            filter_query=AddressbookFilterQuery.make(),
        )[0]) == 1  # has an addressbook entry

    # Modify the account setting no label
    request_data = {'accounts': [{'address': ethereum_accounts[0], 'label': ''}]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    assert_proper_response(response)

    with rotki.data.db.conn.read_ctx() as cursor:
        assert len(db_addressbook.get_addressbook_entries(
            cursor=cursor,
            filter_query=AddressbookFilterQuery.make(),
        )[0]) == 0  # addressbook entry has been deleted
