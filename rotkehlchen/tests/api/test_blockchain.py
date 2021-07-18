import logging
import random
from contextlib import ExitStack
from http import HTTPStatus
from unittest.mock import patch

import gevent
import pytest
import requests
from eth_utils import to_checksum_address

from rotkehlchen.chain.substrate.typing import KusamaAddress
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.blockchain import (
    assert_btc_balances_result,
    assert_eth_balances_result,
    compare_account_data,
)
from rotkehlchen.tests.utils.constants import A_GNO, A_RDN
from rotkehlchen.tests.utils.ens import ENS_BRUNO, ENS_BRUNO_BTC_ADDR, ENS_BRUNO_KSM_ADDR
from rotkehlchen.tests.utils.factories import (
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    UNIT_BTC_ADDRESS3,
    make_ethereum_address,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.tests.utils.substrate import (
    KUSAMA_TEST_NODES,
    SUBSTRATE_ACC1_DOT_ADDR,
    SUBSTRATE_ACC1_KSM_ADDR,
    SUBSTRATE_ACC2_KSM_ADDR,
)
from rotkehlchen.typing import BlockchainAccountData, SupportedBlockchain
from rotkehlchen.utils.misc import from_wei

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_query_empty_blockchain_balances(rotkehlchen_api_server):
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
        "named_blockchain_balances_resource",
        blockchain='BTC',
    ))
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert data['result'] == {'per_account': {}, 'totals': {'assets': {}, 'liabilities': {}}}

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "blockchainbalancesresource",
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
        rotkehlchen_api_server,
        ethereum_accounts,
        btc_accounts,
        caplog,
):
    """Test that querying Bech32 bitcoin addresses works fine"""
    caplog.set_level(logging.DEBUG)
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0

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
            "blockchainbalancesresource",
        ))
    result = assert_proper_response_with_result(response)
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
        rotkehlchen_api_server,
        ethereum_accounts,
        btc_accounts,
):
    """Test that the query blockchain balances endpoint works when queried asynchronously
    """
    # Disable caching of query results
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0

    async_query = random.choice([False, True])
    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=btc_accounts)

    # First query only ETH and token balances
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "named_blockchain_balances_resource",
            blockchain='ETH',
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task_with_result(
                server=rotkehlchen_api_server,
                task_id=task_id,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 5,
            )
        else:
            outcome = assert_proper_response_with_result(response)

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
            "named_blockchain_balances_resource",
            blockchain='BTC',
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        else:
            outcome = assert_proper_response_with_result(response)

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
            "blockchainbalancesresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task_with_result(
                server=rotkehlchen_api_server,
                task_id=task_id,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 5,
            )
        else:
            outcome = assert_proper_response_with_result(response)

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
        rotkehlchen_api_server,
        ethereum_accounts,
        btc_accounts,
):
    """Test that the query blockchain balances endpoint can ignore the cache"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=btc_accounts)
    eth_query = patch.object(
        rotki.chain_manager,
        'query_ethereum_balances',
        wraps=rotki.chain_manager.query_ethereum_balances,
    )
    tokens_query = patch.object(
        rotki.chain_manager,
        'query_ethereum_tokens',
        wraps=rotki.chain_manager.query_ethereum_tokens,
    )

    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        eth_mock = stack.enter_context(eth_query)
        tokens_mock = stack.enter_context(tokens_query)
        # Query ETH and token balances once
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "named_blockchain_balances_resource",
            blockchain='ETH',
        ))
        result = assert_proper_response_with_result(response)
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
            "named_blockchain_balances_resource",
            blockchain='ETH',
        ))
        result = assert_proper_response_with_result(response)
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
            "named_blockchain_balances_resource",
            blockchain='ETH',
        ), json={'ignore_cache': True})
        result = assert_proper_response_with_result(response)
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
        api_server,
        query_balances_before_first_modification,
        ethereum_accounts,
        btc_accounts,
        async_query,
):
    # Disable caching of query results
    rotki = api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0

    if query_balances_before_first_modification:
        # Also test by having balances queried before adding an account
        eth_balances = ['1000000', '2000000']
        token_balances = {A_RDN: ['0', '4000000']}
        setup = setup_balances(
            rotki,
            ethereum_accounts=ethereum_accounts,
            btc_accounts=btc_accounts,
            eth_balances=eth_balances,
            token_balances=token_balances,
        )
        with ExitStack() as stack:
            setup.enter_blockchain_patches(stack)
            response = requests.get(api_url_for(
                api_server,
                "blockchainbalancesresource",
            ))

    new_eth_accounts = [make_ethereum_address(), make_ethereum_address()]
    all_eth_accounts = ethereum_accounts + new_eth_accounts
    eth_balances = ['1000000', '2000000', '3000000', '4000000']
    token_balances = {A_RDN: ['0', '4000000', '0', '250000000']}
    setup = setup_balances(
        rotki,
        ethereum_accounts=all_eth_accounts,
        btc_accounts=btc_accounts,
        eth_balances=eth_balances,
        token_balances=token_balances,
    )

    # The application has started only with 2 ethereum accounts. Let's add two more
    data = {'accounts': [{'address': x} for x in new_eth_accounts]}
    if async_query:
        data['async_query'] = True
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.put(api_url_for(
            api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json=data)

        if async_query:
            task_id = assert_ok_async_response(response)
            result = wait_for_async_task_with_result(
                api_server,
                task_id,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 4,
            )
        else:
            result = assert_proper_response_with_result(response)

    assert_eth_balances_result(
        rotki=rotki,
        result=result,
        eth_accounts=all_eth_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=query_balances_before_first_modification,
    )
    # Also make sure they are added in the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 4
    assert all(acc in accounts.eth for acc in all_eth_accounts)
    assert len(accounts.btc) == 2
    assert all(acc in accounts.btc for acc in btc_accounts)

    # Now try to query all balances to make sure the result is the stored
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(api_url_for(
            api_server,
            "blockchainbalancesresource",
        ))
    result = assert_proper_response_with_result(response)
    assert_eth_balances_result(
        rotki=rotki,
        result=result,
        eth_accounts=all_eth_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=True,
    )

    return all_eth_accounts, eth_balances, token_balances


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('query_balances_before_first_modification', [True, False])
def test_add_blockchain_accounts(
        rotkehlchen_api_server,
        ethereum_accounts,
        btc_accounts,
        query_balances_before_first_modification,
):
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
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={
            'accounts': [{'address': UNIT_BTC_ADDRESS3}],
            'async_query': async_query,
        })
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        else:
            outcome = assert_proper_response_with_result(response)

    assert_btc_balances_result(
        result=outcome,
        btc_accounts=all_btc_accounts,
        btc_balances=setup.btc_balances,
        also_eth=True,
    )
    # Also make sure it's added in the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 4
    assert all(acc in accounts.eth for acc in all_eth_accounts)
    assert len(accounts.btc) == 3
    assert all(acc in accounts.btc for acc in all_btc_accounts)

    # Now try to query all balances to make sure the result is also stored
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task_with_result(
                server=rotkehlchen_api_server,
                task_id=task_id,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 3,
            )
        else:
            outcome = assert_proper_response_with_result(response)

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
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json={'accounts': [{'address': ethereum_accounts[0]}]})
        assert_error_response(
            response=response,
            status_code=HTTPStatus.BAD_REQUEST,
            contained_in_msg=f'Blockchain account/s {ethereum_accounts[0]} already exist',
        )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('btc_accounts', [[]])
def test_add_blockchain_accounts_concurrent(
        rotkehlchen_api_server,
):
    """
    Test reproducing the erroneous behaviour in token totals seen here:
    https://github.com/rotki/rotki/issues/2603
    """
    ethereum_accounts = [make_ethereum_address(), make_ethereum_address(), make_ethereum_address()]
    account_to_idx = {ethereum_accounts[0]: 0, ethereum_accounts[1]: 1, ethereum_accounts[2]: 2}
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    eth_balances = ['1000000', '2000000', '3000000']
    token_balances = {
        A_RDN: ['0', '4000000', '0'],
        A_GNO: ['555555', '0', '0'],
        A_DAI: ['0', '0', '666666666'],
    }
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        eth_balances=eth_balances,
        token_balances=token_balances,
        btc_balances=None,
    )

    task_ids = {}
    query_accounts = ethereum_accounts.copy()
    for _ in range(5):
        query_accounts.extend(ethereum_accounts)
    with ExitStack() as stack:
        # Fire all requests almost concurrently. And don't wait for them
        setup.enter_ethereum_patches(stack)
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
        task_ids = {idx: account for idx, account in enumerate(query_accounts)}

        with gevent.Timeout(ASYNC_TASK_WAIT_TIMEOUT):
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
                    gevent.sleep(.1)  # not started yet
                    continue

                assert_proper_response(response, status_code=None)  # do not check status code here
                result = response.json()['result']
                status = result['status']
                if status == 'pending':
                    gevent.sleep(.1)
                    continue
                if status == 'completed':
                    result = result['outcome']
                else:
                    raise AssertionError('Should not happen at this point')

                task_ids.pop(task_id)
                if result['result'] is None:
                    assert 'already exist' in result['message']
                    continue

                result = result['result']
                per_acc = result['per_account']['ETH'].get(account, None)
                totals = result['totals']['assets']
                idx = account_to_idx[account]
                if per_acc is None:
                    # As mentioned above this may happen only if our expectation of sequential
                    # task indices breaks. In that case ignore this entry
                    continue

                assert FVal(per_acc['assets']['ETH']['amount']) == from_wei(FVal(eth_balances[idx]))  # noqa: E501

                rdn = from_wei(FVal(token_balances[A_RDN][idx]))
                if rdn != ZERO:
                    assert FVal(per_acc['assets'][A_RDN.identifier]['amount']) == rdn
                    assert FVal(totals[A_RDN.identifier]['amount']) == rdn
                gno = from_wei(FVal(token_balances[A_GNO][idx]))
                if gno != ZERO:
                    assert FVal(per_acc['assets'][A_GNO.identifier]['amount']) == gno
                    assert FVal(totals[A_GNO.identifier]['amount']) == gno
                dai = from_wei(FVal(token_balances[A_DAI][idx]))
                if dai != ZERO:
                    assert FVal(per_acc['assets'][A_DAI.identifier]['amount']) == dai
                    assert FVal(totals[A_DAI.identifier]['amount']) == dai


@pytest.mark.parametrize('include_etherscan_key', [False])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_no_etherscan_is_detected(rotkehlchen_api_server):
    """Make sure that interacting with ethereum without an etherscan key is given a warning"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    new_address = make_ethereum_address()
    setup = setup_balances(rotki, ethereum_accounts=[new_address], btc_accounts=None)

    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json={'accounts': [{'address': new_address}]})
    assert_proper_response(response)
    warnings = rotki.msg_aggregator.consume_warnings()
    assert len(warnings) == 1
    assert 'You do not have an Etherscan API key configured' in warnings[0]


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_adding_non_checksummed_eth_account_works(rotkehlchen_api_server):
    """Test that adding a non checksummed eth account can be handled properly"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    account = '0x7bd904a3db59fa3879bd4c246303e6ef3ac3a4c6'
    new_eth_accounts = [to_checksum_address(account)]
    eth_balances = ['1000000']
    setup = setup_balances(
        rotki,
        ethereum_accounts=new_eth_accounts,
        btc_accounts=None,
        eth_balances=eth_balances,
        token_balances=None,
    )
    request_data = {'accounts': [{'address': account}]}
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json=request_data)
    assert_proper_response(response)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_adding_editing_ens_account_works(rotkehlchen_api_server):
    """Test that adding an ENS eth account can be handled properly

    This test mocks all etherscan queries apart from the ENS ones
    """
    resolved_account = '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=[resolved_account],
        btc_accounts=None,
        eth_balances=['10000'],
        token_balances=None,
    )
    # Add an account and see it resolves
    request_data = {'accounts': [{'address': 'rotki.eth'}]}
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json=request_data)

    result = assert_proper_response_with_result(response)
    assert resolved_account in result['per_account']['ETH']

    # Add an unresolvable account and see it errors
    request_data = {'accounts': [{'address': 'ishouldnotexistforrealz.eth'}]}
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Given ENS address ishouldnotexistforrealz.eth could not be resolved',
    )

    # Edit the resolvable account
    label = 'foo'
    request_data = {'accounts': [{'address': 'rotki.eth', 'label': label}]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    result = assert_proper_response_with_result(response)[0]
    assert result['address'] == '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    assert result['label'] == label

    # Edit an unresolvable account
    label = 'foo'
    request_data = {'accounts': [{'address': 'ishouldnotexistforrealz.eth', 'label': label}]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Given ENS address ishouldnotexistforrealz.eth could not be resolved',
    )


@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_deleting_ens_account_works(rotkehlchen_api_server, ethereum_accounts):
    """Test that deleting an ENS eth account can be handled properly

    This test mocks all etherscan queries apart from the ENS ones
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        eth_balances=None,
        token_balances=None,
    )
    request_data = {'accounts': ['rotki.eth']}
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json=request_data)
    result = assert_proper_response_with_result(response)
    assert result['per_account'] == {}

    request_data = {'accounts': ['ishouldnotexistforrealz.eth']}
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Given ENS address ishouldnotexistforrealz.eth could not be resolved',
    )


@pytest.mark.parametrize('method', ['PUT', 'DELETE'])
def test_blockchain_accounts_endpoint_errors(rotkehlchen_api_server, rest_api_port, method):
    """
    Test /api/(version)/blockchains/(name) for edge cases and errors.

    Test for errors when both adding and removing a blockhain account. Both put/delete
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0

    # Provide unsupported blockchain name
    account = '0x00d74c25bbf93df8b2a41d82b0076843b4db0349'
    data = {'accounts': [account]}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='DDASDAS'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unrecognized value DDASDAS given for blockchain name',
    )

    # Provide no blockchain name
    response = requests.request(
        method,
        f'http://localhost:{rest_api_port}/api/1/blockchains',
        json=data,
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.NOT_FOUND,
    )

    # Do not provide accounts
    data = {'dsadsad': 'foo'}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
    )

    # Provide wrong type of account
    data = {'accounts': 'foo'}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    if method == 'GET':
        message = "'accounts': ['Not a valid list.'"
    elif method == 'DELETE':
        message = 'Given value foo is not an ethereum address'
    else:
        message = '"accounts": {"0": {"_schema": ["Invalid input type.'
    assert_error_response(
        response=response,
        contained_in_msg=message,
    )
    assert 'foo' not in rotki.chain_manager.accounts.eth

    # Provide empty list
    data = {'accounts': []}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    verb = 'add' if method == 'PUT' else 'remove'
    assert_error_response(
        response=response,
        contained_in_msg=f'Empty list of blockchain accounts to {verb} was given',
    )

    # Provide invalid ETH account (more bytes)
    invalid_eth_account = '0x554FFc77f4251a9fB3c0E3590a6a205f8d4e067d01'
    msg = f'Given value {invalid_eth_account} is not an ethereum address'
    if method == 'PUT':
        data = {'accounts': [{'address': invalid_eth_account}]}
    else:
        data = {'accounts': [invalid_eth_account]}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg=msg,
    )

    # Provide invalid BTC account
    invalid_btc_account = '18ddjB7HWTaxzvTbLp1nWvaixU3U2oTZ1'
    if method == 'PUT':
        data = {'accounts': [{'address': invalid_btc_account}]}
    else:
        data = {'accounts': [invalid_btc_account]}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='BTC'),
        json=data,
    )

    msg = f'Given value {invalid_btc_account} is not a valid bitcoin address'
    assert_error_response(
        response=response,
        contained_in_msg=msg,
    )
    assert_msg = 'Invalid BTC account should not have been added'
    assert invalid_btc_account not in rotki.chain_manager.accounts.btc, assert_msg

    # Provide not existing but valid ETH account for removal
    unknown_account = make_ethereum_address()
    data = {'accounts': [unknown_account]}
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Tried to remove unknown ETH accounts {unknown_account}',
    )

    # Provide not existing but valid BTC account for removal
    unknown_btc_account = '18ddjB7HWTVxzvTbLp1nWvaBxU3U2oTZF2'
    data = {'accounts': [unknown_btc_account]}
    response = requests.delete(
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='BTC'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Tried to remove unknown BTC accounts {unknown_btc_account}',
    )

    # Provide list with one valid and one invalid account and make sure that nothing
    # is added / removed and the valid one is skipped
    msg = 'Given value 142 is not an ethereum address'
    if method == 'DELETE':
        # Account should be an existing account
        account = rotki.chain_manager.accounts.eth[0]
        data = {'accounts': ['142', account]}
    else:
        # else keep the new account to add
        data = {'accounts': [{'address': '142'}, {'address': account}]}

    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type for accounts
    if method == 'PUT':
        data = {'accounts': [{'address': 15}]}
    else:
        data = {'accounts': [15]}
    response = requests.request(
        method,
        api_url_for(rotkehlchen_api_server, "blockchainsaccountsresource", blockchain='ETH'),
        json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
    )

    # Test that providing an account more than once in request data is an error
    account = '0x7BD904A3Db59fA3879BD4c246303E6Ef3aC3A4C6'
    if method == 'PUT':
        data = {'accounts': [{'address': account}, {'address': account}]}
    else:
        data = {'accounts': [account, account]}
    response = requests.request(method, api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=data)
    assert_error_response(
        response=response,
        contained_in_msg=f'Address {account} appears multiple times in the request data',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_blockchain_accounts_with_tags_and_label_and_querying_them(rotkehlchen_api_server):
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

    # Now add 3 accounts. Some of them  use these tags, some dont
    new_eth_accounts = [make_ethereum_address(), make_ethereum_address(), make_ethereum_address()]
    eth_balances = ['1000000', '4000000', '2000000']
    token_balances = {A_RDN: ['100000', '350000', '2223']}
    setup = setup_balances(
        rotki,
        ethereum_accounts=new_eth_accounts,
        btc_accounts=None,
        eth_balances=eth_balances,
        token_balances=token_balances,
    )
    accounts_data = [{
        "address": new_eth_accounts[0],
        "label": 'my metamask',
        'tags': ['public', 'desktop'],
    }, {
        "address": new_eth_accounts[1],
        "label": 'geth account',
    }, {
        "address": new_eth_accounts[2],
        'tags': ['public', 'hardware'],
    }]
    # Make sure that even adding accounts with label and tags, balance query works fine
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json={'accounts': accounts_data})
    result = assert_proper_response_with_result(response)
    assert_eth_balances_result(
        rotki=rotki,
        result=result,
        eth_accounts=new_eth_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=False,
    )

    # Now query the ethereum account data to see that tags and labels are added
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ))
    assert_proper_response(response)
    response_data = response.json()['result']
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
        rotkehlchen_api_server,
        ethereum_accounts,
):
    """Test that the endpoint editing blockchain accounts works properly"""
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
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    expected_result = request_data['accounts'] + [
        {'address': ethereum_accounts[0]},
    ]
    compare_account_data(json_data['result'], expected_result)

    # Also make sure that when querying the endpoint we get the edited account data
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ))
    assert_proper_response(response)
    json_data = response.json()
    compare_account_data(json_data['result'], expected_result)

    # Edit a BTC account
    request_data = {'accounts': [{
        'address': UNIT_BTC_ADDRESS1,
        'label': 'BTC account label',
        'tags': ['public'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='BTC',
    ), json=request_data)
    result = assert_proper_response_with_result(response)
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
        rotkehlchen_api_server,
        ethereum_accounts,
):
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

    request_data = {'accounts': [{
        'address': ethereum_accounts[0],
        'label': 'Second account in the array',
        'tags': ['public'],
    }, {
        'address': ethereum_accounts[1],
        'label': 'Thirds account in the array',
        'tags': ['public', 'desktop'],
    }]}

    # Missing accounts
    request_data = {'foo': ['a']}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='"accounts": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for accounts
    request_data = {'accounts': 142}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='Invalid input type',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Missing address for an account
    request_data = {'accounts': [{
        'label': 'Second account in the array',
        'tags': ['public'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='address": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for an account's address
    request_data = {'accounts': [{
        'address': 55,
        'label': 'Second account in the array',
        'tags': ['public'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='address": ["Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid address for an account's address
    request_data = {'accounts': [{
        'address': 'dsadsd',
        'label': 'Second account in the array',
        'tags': ['public'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='Given value dsadsd is not an ethereum address',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for label
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 55,
        'tags': ['public'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='label": ["Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for tags
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': 231,
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='tags": ["Not a valid list',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for tags list entry
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': [55.221],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='tags": {"0": ["Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # One non existing tag
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': ['nonexistant'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='When editing blockchain accounts, unknown tags nonexistant were found',
        status_code=HTTPStatus.CONFLICT,
    )

    # Mix of existing and non-existing tags
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': ['a', 'public', 'b', 'desktop', 'c'],
    }]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg='When editing blockchain accounts, unknown tags ',
        status_code=HTTPStatus.CONFLICT,
    )

    # Provide same account multiple times in request data
    request_data = {'accounts': [{
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': ['a', 'public', 'b', 'desktop', 'c'],
    }, {
        'address': ethereum_accounts[1],
        'label': 'a label',
        'tags': ['a', 'public', 'b', 'desktop', 'c'],
    }]}
    msg = f'Address {ethereum_accounts[1]} appears multiple times in the request data'
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )


def _remove_blockchain_accounts_test_start(
        api_server,
        query_balances_before_first_modification,
        ethereum_accounts,
        btc_accounts,
        async_query,
):
    # Disable caching of query results
    rotki = api_server.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0
    removed_eth_accounts = [ethereum_accounts[0], ethereum_accounts[2]]
    eth_accounts_after_removal = [ethereum_accounts[1], ethereum_accounts[3]]
    all_eth_balances = ['1000000', '2000000', '3000000', '4000000']
    token_balances = {A_RDN: ['0', '0', '450000000', '0']}
    eth_balances_after_removal = ['2000000', '4000000']
    token_balances_after_removal = {}
    starting_liabilities = {A_DAI: ['5555555', '1000000', '0', '99999999']}
    after_liabilities = {A_DAI: ['1000000', '99999999']}

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
            response = requests.get(api_url_for(
                api_server,
                "blockchainbalancesresource",
            ))
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        eth_balances=all_eth_balances,
        token_balances=token_balances,
        liabilities=starting_liabilities,
    )

    # The application has started with 4 ethereum accounts. Remove two and see that balances match
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.delete(api_url_for(
            api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json={'accounts': removed_eth_accounts, 'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            result = wait_for_async_task_with_result(api_server, task_id)
        else:
            result = assert_proper_response_with_result(response)

    assert_eth_balances_result(
        rotki=rotki,
        result=result,
        eth_accounts=eth_accounts_after_removal,
        eth_balances=eth_balances_after_removal,
        token_balances=token_balances_after_removal,
        also_btc=query_balances_before_first_modification,
        expected_liabilities=after_liabilities,
    )
    # Also make sure they are removed from the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 2
    assert all(acc in accounts.eth for acc in eth_accounts_after_removal)
    assert len(accounts.btc) == 2
    assert all(acc in accounts.btc for acc in btc_accounts)

    # Now try to query all balances to make sure the result is the stored
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(api_url_for(
            api_server,
            "blockchainbalancesresource",
        ))
    result = assert_proper_response_with_result(response)
    assert_eth_balances_result(
        rotki=rotki,
        result=result,
        eth_accounts=eth_accounts_after_removal,
        eth_balances=eth_balances_after_removal,
        token_balances=token_balances_after_removal,
        also_btc=True,
        expected_liabilities=after_liabilities,
    )

    return eth_accounts_after_removal, eth_balances_after_removal, token_balances_after_removal


@pytest.mark.parametrize('number_of_eth_accounts', [4])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('query_balances_before_first_modification', [True, False])
def test_remove_blockchain_accounts(
        rotkehlchen_api_server,
        ethereum_accounts,
        btc_accounts,
        query_balances_before_first_modification,
):
    """Test that the endpoint removing blockchain accounts works properly"""

    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
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
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={'accounts': [UNIT_BTC_ADDRESS1], 'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        else:
            outcome = assert_proper_response_with_result(response)

    assert_btc_balances_result(
        result=outcome,
        btc_accounts=btc_accounts_after_removal,
        btc_balances=['5000000'],
        also_eth=True,
    )
    # Also make sure it's removed from the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 2
    assert all(acc in accounts.eth for acc in eth_accounts_after_removal)
    assert len(accounts.btc) == 1
    assert all(acc in accounts.btc for acc in btc_accounts_after_removal)

    # Now try to query all balances to make sure the result is also stored
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "blockchainbalancesresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task_with_result(
                server=rotkehlchen_api_server,
                task_id=task_id,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 3,
            )
        else:
            outcome = assert_proper_response_with_result(response)

    assert_btc_balances_result(
        result=outcome,
        btc_accounts=btc_accounts_after_removal,
        btc_balances=['5000000'],
        also_eth=True,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_remove_nonexisting_blockchain_account_along_with_existing(
        rotkehlchen_api_server,
        ethereum_accounts,
):
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
    request_data = {'accounts': [{'address': ethereum_accounts[0], 'tags': ['public']}]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        "blockchainsaccountsresource",
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
    unknown_account = make_ethereum_address()
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='ETH',
        ), json={'accounts': [ethereum_accounts[0], unknown_account]})
    assert_error_response(
        response=response,
        contained_in_msg=f'Tried to remove unknown ETH accounts {unknown_account}',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Also make sure that no account was removed from the DB
    accounts = rotki.data.db.get_blockchain_accounts()
    assert len(accounts.eth) == 2
    assert all(acc in accounts.eth for acc in ethereum_accounts)
    # Also make sure no tag mappings were removed
    cursor = rotki.data.db.conn.cursor()
    query = cursor.execute('SELECT object_reference, tag_name FROM tag_mappings;').fetchall()
    assert len(query) == 1
    assert query[0][0] == ethereum_accounts[0]
    assert query[0][1] == 'public'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_remove_blockchain_account_with_tags_removes_mapping(rotkehlchen_api_server):
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
    btc_balances = ['10000', '500500000']
    setup = setup_balances(
        rotki,
        ethereum_accounts=None,
        btc_accounts=new_btc_accounts,
        eth_balances=None,
        token_balances=None,
        btc_balances=btc_balances,
    )
    accounts_data = [{
        "address": new_btc_accounts[0],
        "label": 'my btc miner',
        'tags': ['public', 'desktop'],
    }, {
        "address": new_btc_accounts[1],
        'label': 'other account',
        'tags': ['desktop'],
    }]
    with setup.bitcoin_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={'accounts': accounts_data})
    result = assert_proper_response_with_result(response)
    assert_btc_balances_result(
        result=result,
        btc_accounts=new_btc_accounts,
        btc_balances=btc_balances,
        also_eth=False,
    )

    # now remove one account
    with setup.bitcoin_patch:
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={'accounts': [UNIT_BTC_ADDRESS1]})
    result = assert_proper_response_with_result(response)
    assert_btc_balances_result(
        result=result,
        btc_accounts=[UNIT_BTC_ADDRESS2],
        btc_balances=['500500000'],
        also_eth=False,
    )

    # Now check the DB directly and see that tag mappings of the deleted account are gone
    cursor = rotki.data.db.conn.cursor()
    query = cursor.execute('SELECT object_reference, tag_name FROM tag_mappings;').fetchall()
    assert len(query) == 1
    assert query[0][0] == UNIT_BTC_ADDRESS2
    assert query[0][1] == 'desktop'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_btc_blockchain_account_ens_domain(rotkehlchen_api_server):
    """Test adding a Bitcoin blockchain account via ENS domain when there is none
    in the db works as expected.
    """
    async_query = random.choice([False, True])

    setup = setup_balances(
        rotki=rotkehlchen_api_server.rest_api.rotkehlchen,
        ethereum_accounts=None,
        btc_accounts=[ENS_BRUNO_BTC_ADDR],
        eth_balances=None,
        token_balances=None,
        btc_balances=['77700000000'],
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                "blockchainsaccountsresource",
                blockchain=SupportedBlockchain.BITCOIN.value,
            ),
            json={
                'accounts': [{'address': ENS_BRUNO}],
                'async_query': async_query,
            },
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        else:
            result = assert_proper_response_with_result(response)

    # Check per account
    asset_btc = result['per_account']['BTC']['standalone'][ENS_BRUNO_BTC_ADDR]
    assert FVal(asset_btc['amount']) >= FVal('777.00000000')
    assert FVal(asset_btc['usd_value']) >= FVal('1165.500000000')

    # Check totals
    assert 'liabilities' in result['totals']
    total_btc = result['totals']['assets']['BTC']
    assert FVal(total_btc['amount']) >= FVal('777.00000000')
    assert FVal(total_btc['usd_value']) >= FVal('1165.500000000')


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_ksm_blockchain_account_invalid(rotkehlchen_api_server):
    """Test adding an invalid Kusama blockchain account works as expected.
    """
    setup = setup_balances(
        rotki=rotkehlchen_api_server.rest_api.rotkehlchen,
        ethereum_accounts=None,
        btc_accounts=None,
        eth_balances=None,
        token_balances=None,
        btc_balances=None,
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                "blockchainsaccountsresource",
                blockchain=SupportedBlockchain.KUSAMA.value,
            ),
            json={'accounts': [{'address': SUBSTRATE_ACC1_DOT_ADDR}]},
        )

    assert_error_response(
        response=response,
        contained_in_msg=f'{SUBSTRATE_ACC1_DOT_ADDR} is not a valid kusama address',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [KUSAMA_TEST_NODES])
def test_add_ksm_blockchain_account(rotkehlchen_api_server):
    """Test adding a Kusama blockchain account when there is none in the db
    works as expected, by triggering the logic that attempts to connect to the
    nodes.
    """
    async_query = random.choice([False, True])

    setup = setup_balances(
        rotki=rotkehlchen_api_server.rest_api.rotkehlchen,
        ethereum_accounts=None,
        btc_accounts=None,
        eth_balances=None,
        token_balances=None,
        btc_balances=None,
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                "blockchainsaccountsresource",
                blockchain=SupportedBlockchain.KUSAMA.value,
            ),
            json={
                'accounts': [{'address': SUBSTRATE_ACC1_KSM_ADDR}],
                'async_query': async_query,
            },
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        else:
            result = assert_proper_response_with_result(response)

    # Check per account
    account_balances = result['per_account']['KSM'][SUBSTRATE_ACC1_KSM_ADDR]
    assert 'liabilities' in account_balances
    asset_ksm = account_balances['assets']['KSM']
    assert FVal(asset_ksm['amount']) >= ZERO
    assert FVal(asset_ksm['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_ksm = result['totals']['assets']['KSM']
    assert FVal(total_ksm['amount']) >= ZERO
    assert FVal(total_ksm['usd_value']) >= ZERO


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('ksm_accounts', [[SUBSTRATE_ACC1_KSM_ADDR, SUBSTRATE_ACC2_KSM_ADDR]])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [KUSAMA_TEST_NODES])
def test_remove_ksm_blockchain_account(rotkehlchen_api_server):
    """Test removing a Kusama blockchain account works as expected by returning
    only the balances of the other Kusama accounts.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    async_query = random.choice([False, True])

    # Create KSM accounts
    accounts_data = [
        BlockchainAccountData(address=KusamaAddress(SUBSTRATE_ACC1_KSM_ADDR)),
        BlockchainAccountData(address=KusamaAddress(SUBSTRATE_ACC2_KSM_ADDR)),
    ]
    rotki.data.db.add_blockchain_accounts(
        blockchain=SupportedBlockchain.KUSAMA,
        account_data=accounts_data,
    )
    setup = setup_balances(
        rotki=rotki,
        ethereum_accounts=None,
        btc_accounts=None,
        eth_balances=None,
        token_balances=None,
        btc_balances=None,
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.delete(
            api_url_for(
                rotkehlchen_api_server,
                "blockchainsaccountsresource",
                blockchain=SupportedBlockchain.KUSAMA.value,
            ),
            json={
                'accounts': [SUBSTRATE_ACC2_KSM_ADDR],
                'async_query': async_query,
            },
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        else:
            result = assert_proper_response_with_result(response)

    # Check per account
    assert SUBSTRATE_ACC2_KSM_ADDR not in result['per_account']['KSM']
    account_balances = result['per_account']['KSM'][SUBSTRATE_ACC1_KSM_ADDR]
    assert 'liabilities' in account_balances
    asset_ksm = account_balances['assets']['KSM']
    assert FVal(asset_ksm['amount']) >= ZERO
    assert FVal(asset_ksm['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_ksm = result['totals']['assets']['KSM']
    assert FVal(total_ksm['amount']) >= ZERO
    assert FVal(total_ksm['usd_value']) >= ZERO

    # Also make sure it's removed from the DB
    db_accounts = rotki.data.db.get_blockchain_accounts()
    assert db_accounts.ksm[0] == SUBSTRATE_ACC1_KSM_ADDR


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_ksm_blockchain_account_invalid_ens_domain(rotkehlchen_api_server):
    """Test adding an invalid Kusama blockchain account via ENS domain works as
    expected.
    """
    invalid_ens_domain = 'craigwright.eth'
    setup = setup_balances(
        rotki=rotkehlchen_api_server.rest_api.rotkehlchen,
        ethereum_accounts=None,
        btc_accounts=None,
        eth_balances=None,
        token_balances=None,
        btc_balances=None,
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                "blockchainsaccountsresource",
                blockchain=SupportedBlockchain.KUSAMA.value,
            ),
            json={'accounts': [{'address': invalid_ens_domain}]},
        )
    assert_error_response(
        response=response,
        contained_in_msg=(
            f'Given ENS address {invalid_ens_domain} could not be resolved for Kusama'
        ),
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [KUSAMA_TEST_NODES])
def test_add_ksm_blockchain_account_ens_domain(rotkehlchen_api_server):
    """Test adding a Kusama blockchain account via ENS domain when there is none
    in the db works as expected, by triggering the logic that attempts to connect
    to the nodes.
    """
    async_query = random.choice([False, True])
    setup = setup_balances(
        rotki=rotkehlchen_api_server.rest_api.rotkehlchen,
        ethereum_accounts=None,
        btc_accounts=None,
        eth_balances=None,
        token_balances=None,
        btc_balances=None,
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                "blockchainsaccountsresource",
                blockchain=SupportedBlockchain.KUSAMA.value,
            ),
            json={
                'accounts': [{'address': ENS_BRUNO}],
                'async_query': async_query,
            },
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        else:
            result = assert_proper_response_with_result(response)

    # Check per account
    account_balances = result['per_account']['KSM'][ENS_BRUNO_KSM_ADDR]
    assert 'liabilities' in account_balances
    asset_ksm = account_balances['assets']['KSM']
    assert FVal(asset_ksm['amount']) >= ZERO
    assert FVal(asset_ksm['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_ksm = result['totals']['assets']['KSM']
    assert FVal(total_ksm['amount']) >= ZERO
    assert FVal(total_ksm['usd_value']) >= ZERO


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('ksm_accounts', [[SUBSTRATE_ACC1_KSM_ADDR, ENS_BRUNO_KSM_ADDR]])
@pytest.mark.parametrize('kusama_manager_connect_at_start', [KUSAMA_TEST_NODES])
def test_remove_ksm_blockchain_account_ens_domain(rotkehlchen_api_server):
    """Test removing a Kusama blockchain account via ENS domain works as
    expected by returning only the balances of the other Kusama accounts.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    async_query = random.choice([False, True])

    # Create KSM accounts
    accounts_data = [
        BlockchainAccountData(address=KusamaAddress(SUBSTRATE_ACC1_KSM_ADDR)),
        BlockchainAccountData(address=KusamaAddress(ENS_BRUNO_KSM_ADDR)),
    ]
    rotki.data.db.add_blockchain_accounts(
        blockchain=SupportedBlockchain.KUSAMA,
        account_data=accounts_data,
    )
    setup = setup_balances(
        rotki=rotki,
        ethereum_accounts=None,
        btc_accounts=None,
        eth_balances=None,
        token_balances=None,
        btc_balances=None,
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.delete(
            api_url_for(
                rotkehlchen_api_server,
                "blockchainsaccountsresource",
                blockchain=SupportedBlockchain.KUSAMA.value,
            ),
            json={
                'accounts': [ENS_BRUNO],
                'async_query': async_query,
            },
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        else:
            result = assert_proper_response_with_result(response)

    # Check per account
    assert ENS_BRUNO_KSM_ADDR not in result['per_account']['KSM']
    account_balances = result['per_account']['KSM'][SUBSTRATE_ACC1_KSM_ADDR]
    assert 'liabilities' in account_balances
    asset_ksm = account_balances['assets']['KSM']
    assert FVal(asset_ksm['amount']) >= ZERO
    assert FVal(asset_ksm['usd_value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_ksm = result['totals']['assets']['KSM']
    assert FVal(total_ksm['amount']) >= ZERO
    assert FVal(total_ksm['usd_value']) >= ZERO

    # Also make sure it's removed from the DB
    db_accounts = rotki.data.db.get_blockchain_accounts()
    assert db_accounts.ksm[0] == SUBSTRATE_ACC1_KSM_ADDR
