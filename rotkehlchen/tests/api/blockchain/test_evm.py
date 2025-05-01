import operator
from collections.abc import Callable
from contextlib import ExitStack
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal
from unittest.mock import patch

import gevent
import pytest
import requests
from eth_utils import to_checksum_address

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_AVAX, A_ETH
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.avalanche import AVALANCHE_ACC1_AVAX_ADDR
from rotkehlchen.tests.utils.blockchain import setup_evm_addresses_activity_mock
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import ChecksumEvmAddress, ListOfBlockchainAddresses, SupportedBlockchain
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.tests.fixtures.websockets import WebsocketReader

ADDY = string_to_evm_address('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_add_same_evm_account_for_multiple_chains(rotkehlchen_api_server: 'APIServer') -> None:
    """Test adding an Avalanche blockchain account when the same account is input
    in Ethereum works fine
    """
    setup = setup_balances(
        rotki=rotkehlchen_api_server.rest_api.rotkehlchen,
        ethereum_accounts=[string_to_evm_address(AVALANCHE_ACC1_AVAX_ADDR)],
        btc_accounts=None,
        eth_balances=['10000000000'],
        token_balances=None,
        btc_balances=None,
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'blockchainsaccountsresource',
                blockchain=SupportedBlockchain.ETHEREUM.value,
            ),
            json={
                'accounts': [{'address': AVALANCHE_ACC1_AVAX_ADDR}],
            },
        )
        assert_proper_response(response)
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'blockchainsaccountsresource',
                blockchain=SupportedBlockchain.AVALANCHE.value,
            ),
            json={
                'accounts': [{'address': AVALANCHE_ACC1_AVAX_ADDR}],
            },
        )
        assert_proper_response(response)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'blockchainbalancesresource',
        ))
        result = assert_proper_sync_response_with_result(response)

    for chain, native_token in ((SupportedBlockchain.ETHEREUM, A_ETH), (SupportedBlockchain.AVALANCHE, A_AVAX)):  # noqa: E501
        # Check per account
        account_balances = result['per_account'][chain.serialize()][AVALANCHE_ACC1_AVAX_ADDR]
        assert 'liabilities' in account_balances
        asset_token = account_balances['assets'][native_token.identifier]
        assert FVal(asset_token['amount']) >= ZERO
        assert FVal(asset_token['usd_value']) >= ZERO

        # Check totals
        assert 'liabilities' in result['totals']
        total_token = result['totals']['assets'][native_token.identifier]
        assert FVal(total_token['amount']) >= ZERO
        assert FVal(total_token['usd_value']) >= ZERO


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_deleting_ens_account_works(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that deleting an ENS eth account can be handled properly

    This test mocks all etherscan queries apart from the ENS ones
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    request_data = {'accounts': ['rotki.eth']}
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    assert_proper_response(response)
    assert rotki.chains_aggregator.accounts.eth == ()

    request_data = {'accounts': ['ishouldnotexistforrealz.eth']}
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Given ENS name ishouldnotexistforrealz.eth could not be resolved',
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_adding_non_checksummed_eth_account_works(rotkehlchen_api_server: 'APIServer') -> None:
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
            'blockchainsaccountsresource',
            blockchain='ETH',
        ), json=request_data)
    assert_proper_response(response)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_adding_editing_ens_account_works(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that adding an ENS eth account can be handled properly"""
    resolved_account = '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # Add an account and see it resolves
    request_data = {'accounts': [{'address': 'rotki.eth'}]}
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)

    result = assert_proper_sync_response_with_result(response)
    assert result == [resolved_account]
    assert rotki.chains_aggregator.accounts.eth[-1] == resolved_account

    # Add an unresolvable account and see it errors
    request_data = {'accounts': [{'address': 'ishouldnotexistforrealz.eth'}]}
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Given ENS name ishouldnotexistforrealz.eth could not be resolved',
    )

    # Edit the resolvable account
    label = 'foo'
    request_data = {'accounts': [{'address': 'rotki.eth', 'label': label}]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    result = assert_proper_sync_response_with_result(response)[0]
    assert result['address'] == '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    assert result['label'] == label

    # Edit an unresolvable account
    label = 'foo'
    request_data = {'accounts': [{'address': 'ishouldnotexistforrealz.eth', 'label': label}]}
    response = requests.patch(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=request_data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Given ENS name ishouldnotexistforrealz.eth could not be resolved',
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('gnosis_accounts', [['0x7277F7849966426d345D8F6B9AFD1d3d89183083']])
def test_add_multievm_accounts(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that adding accounts to multiple evm chains works fine

    TODO: Needs mocking with the data at the time of test writing
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    common_account = string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    contract_account = string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41')
    failing_account = string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')
    no_activity_account = string_to_evm_address('0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa')
    already_added_to_all_chains = string_to_evm_address('0x7277F7849966426d345D8F6B9AFD1d3d89183083')  # noqa: E501

    # Add a tag
    tag1 = {
        'name': 'metamask',
        'description': 'Metamask stuff',
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

    # patch modify_blockchain_accounts to check that we handle failures correctly when
    # adding new accounts
    original_modify_blockchain_accounts = rotki.chains_aggregator.modify_blockchain_accounts

    def new_modify_blockchain_accounts(
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
            append_or_remove: Literal['append', 'remove'],
    ) -> Callable:  # pylint: disable=unused-argument
        """Make the logic fail when adding new accounts if failing_account is given as argument"""
        if failing_account in accounts:
            raise RemoteError('Mocking a failure when adding addresses')

        return original_modify_blockchain_accounts

    patched_modify_blockchain_accounts = patch.object(
        target=rotki.chains_aggregator,
        attribute='modify_blockchain_accounts',
        new=new_modify_blockchain_accounts,
    )

    with ExitStack() as stack:
        setup_evm_addresses_activity_mock(
            stack=stack,
            chains_aggregator=rotki.chains_aggregator,
            eth_contract_addresses=[contract_account],
            ethereum_addresses=[contract_account, common_account],
            avalanche_addresses=[common_account],
            optimism_addresses=[common_account],
            polygon_pos_addresses=[common_account, failing_account],
            arbitrum_one_addresses=[common_account, failing_account],
            base_addresses=[common_account, failing_account],
            gnosis_addresses=[common_account, failing_account, already_added_to_all_chains],
            scroll_addresses=[common_account, failing_account],
            binance_sc_addresses=[common_account, failing_account],
            zksync_lite_addresses=[common_account],
        )
        stack.enter_context(patched_modify_blockchain_accounts)

        # add two addresses for all evm chains, one with tag
        label = 'rotki account'
        request_data = {
            'accounts': [
                {
                    'address': common_account,
                    'label': label,
                    'tags': ['metamask'],
                },
                {'address': contract_account},
                {'address': failing_account},
                {'address': no_activity_account},
                {'address': already_added_to_all_chains},
            ],
        }
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'evmaccountsresource',
        ), json=request_data)

    result = assert_proper_sync_response_with_result(response)

    assert result == {
        'added': {
            '0x9531C059098e3d194fF87FebB587aB07B30B1306': ['all'],
        },
        'failed': {
            '0xc37b40ABdB939635068d3c5f13E7faF686F03B65': [
                'polygon_pos',
                'arbitrum_one',
                'base',
                'gnosis',
                'scroll',
                'binance_sc',
            ],
        },
        'existed': {'0x7277F7849966426d345D8F6B9AFD1d3d89183083': ['gnosis']},
        'no_activity': {
            '0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa': ['all'],
            '0x7277F7849966426d345D8F6B9AFD1d3d89183083': [
                'eth',
                'optimism',
                'avax',
                'polygon_pos',
                'arbitrum_one',
                'base',
                'scroll',
                'binance_sc',
                'zksync_lite',
            ],
        },
        'evm_contracts': {
            '0x9008D19f58AAbD9eD0D60971565AA8510560ab41': ['all'],
        },
    }

    # Now get accounts to make sure they are all input correctly
    # TODO: As per the note in tags we may need to change this when tags
    # go per address/chain. We need to achieve a functionality where a
    # tag can either go to all accounts or a single chain/account. Right now
    # it only maps to an address so it mirrors to all.
    # Also perhaps we should have an all blockchains
    # version of this endpoint
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ))
    result = assert_proper_sync_response_with_result(response)
    assert result == [
        {'address': common_account, 'label': label, 'tags': ['metamask']},
    ]
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='AVAX',
    ))
    result = assert_proper_sync_response_with_result(response)
    assert result == [
        {'address': common_account, 'label': label, 'tags': ['metamask']},
    ]
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='OPTIMISM',
    ))
    result = assert_proper_sync_response_with_result(response)
    assert result == [
        {'address': common_account, 'label': label, 'tags': ['metamask']},
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'], allow_playback_repeats=True)
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('ethereum_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_detect_evm_accounts(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
        websocket_connection: 'WebsocketReader',
) -> None:
    """
    Test that the endpoint to detect new evm addresses works properly
    and sends the ws messages

    The given account is everywhere.
    """
    response = requests.post(api_url_for(
        rotkehlchen_api_server,
        'evmaccountsresource',
    ))
    assert_proper_response(response)
    websocket_connection.wait_until_messages_num(num=1, timeout=10)
    assert websocket_connection.messages_num() == 1
    msg = websocket_connection.pop_message()
    assert msg['type'] == 'evmlike_accounts_detection'
    assert sorted(msg['data'], key=operator.itemgetter('chain', 'address')) == sorted([
        {'chain': SupportedBlockchain.POLYGON_POS.serialize(), 'address': ethereum_accounts[0]},
        {'chain': SupportedBlockchain.OPTIMISM.serialize(), 'address': ethereum_accounts[0]},
        {'chain': SupportedBlockchain.ARBITRUM_ONE.serialize(), 'address': ethereum_accounts[0]},
        {'chain': SupportedBlockchain.BASE.serialize(), 'address': ethereum_accounts[0]},
        {'chain': SupportedBlockchain.GNOSIS.serialize(), 'address': ethereum_accounts[0]},
        {'chain': SupportedBlockchain.SCROLL.serialize(), 'address': ethereum_accounts[0]},
        {'chain': SupportedBlockchain.BINANCE_SC.serialize(), 'address': ethereum_accounts[0]},
        {'chain': SupportedBlockchain.ZKSYNC_LITE.serialize(), 'address': ethereum_accounts[0]},
        {'chain': SupportedBlockchain.AVALANCHE.serialize(), 'address': ethereum_accounts[0]},
    ], key=operator.itemgetter('chain', 'address'))
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    with db.conn.read_ctx() as cursor:
        blockchain_accounts = db.get_blockchain_accounts(cursor)
    assert ethereum_accounts[0] in blockchain_accounts.eth
    assert ethereum_accounts[0] in blockchain_accounts.polygon_pos
    assert ethereum_accounts[0] in blockchain_accounts.optimism
    assert ethereum_accounts[0] in blockchain_accounts.arbitrum_one
    assert ethereum_accounts[0] in blockchain_accounts.base
    assert ethereum_accounts[0] in blockchain_accounts.gnosis
    assert ethereum_accounts[0] in blockchain_accounts.scroll
    assert ethereum_accounts[0] in blockchain_accounts.binance_sc
    assert ethereum_accounts[0] in blockchain_accounts.zksync_lite
    assert ethereum_accounts[0] in blockchain_accounts.avax


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address() for _ in range(3)]])
def test_evm_account_deletion_does_not_wait_for_pending_txn_queries(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """
    Test that if transactions for an address are being queried and removal is
    requested for that address, the transactions querying greenlets are killed
    and the account is subsequently deleted.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    task_manager = rotki.task_manager
    assert task_manager is not None
    gevent.killall(task_manager.greenlet_manager.greenlets)
    task_manager.max_tasks_num = 2
    now = ts_now()
    task_manager.potential_tasks = [task_manager._maybe_query_evm_transactions]
    for address in ethereum_accounts[:-1]:  # leave last address to run via task manager
        task_manager.last_evm_tx_query_ts[address, SupportedBlockchain.ETHEREUM] = now
    task_manager_addy = ethereum_accounts[-1]
    api_addies = ethereum_accounts[:2].copy()

    def patch_single_query(**kwargs: Any) -> None:  # pylint: disable=unused-argument
        while True:
            gevent.sleep(2)

    patch_obj = patch('rotkehlchen.chain.evm.transactions.EvmTransactions._get_transactions_for_range', side_effect=patch_single_query)  # noqa: E501
    with patch_obj:

        # schedule last address query through task manager
        task_manager.schedule()
        assert len(task_manager.running_greenlets) == 1
        greenlets = task_manager.running_greenlets[task_manager._maybe_query_evm_transactions]
        assert len(greenlets) == 1
        assert not greenlets[0].dead
        # query first two addresses via the api
        for idx, address in enumerate(api_addies):
            response = requests.post(
                api_url_for(
                    rotkehlchen_api_server,
                    'evmtransactionsresource',
                ), json={
                    'async_query': True,
                    'accounts': [{'address': address, 'evm_chain': 'ethereum'}],
                    'evm_chain': 'ethereum',
                },
            )
            assert_ok_async_response(response)
            api_task_greenlets = rotkehlchen_api_server.rest_api.rotkehlchen.api_task_greenlets
            assert len(api_task_greenlets) == idx + 1  # the transactions fetching greenlets
            assert not api_task_greenlets[idx].dead

    # now delete one address from api task and 1 from periodic task manager and see it's immediate
    with gevent.Timeout(5):
        for address in (api_addies[0], task_manager_addy):
            response = requests.delete(
                api_url_for(
                    rotkehlchen_api_server,
                    'blockchainsaccountsresource',
                    blockchain='eth',
                ), json={
                    'accounts': [address],
                },
            )
            assert_proper_response(response)

    # Check that the 1 api greenlet and 1 task manager greenlet got killed
    assert len(api_task_greenlets) == 2
    assert api_task_greenlets[0].dead
    assert len(task_manager.running_greenlets) == 1
    assert task_manager.running_greenlets[task_manager._maybe_query_evm_transactions][0].dead
    assert not api_task_greenlets[1].dead, 'The other address api greenlet should still run'

    # retrieve ethereum accounts from the DB and see they are deleted
    with rotki.data.db.conn.read_ctx() as cursor:
        accounts = rotki.data.db.get_blockchain_accounts(cursor)
        assert set(accounts.eth) == {api_addies[1]}


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_evm_address_async(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that doing async validation for the evm addresses endpoints works"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    common_account = string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    contract_account = string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41')

    with ExitStack() as stack:
        setup_evm_addresses_activity_mock(
            stack=stack,
            chains_aggregator=rotki.chains_aggregator,
            eth_contract_addresses=[contract_account],
            ethereum_addresses=[contract_account, common_account],
            avalanche_addresses=[common_account],
            optimism_addresses=[common_account],
            polygon_pos_addresses=[common_account],
            arbitrum_one_addresses=[common_account],
            base_addresses=[common_account],
            gnosis_addresses=[common_account],
            scroll_addresses=[common_account],
            binance_sc_addresses=[common_account],
            zksync_lite_addresses=[common_account],
        )

        # add an address with an invalid ens name
        label = 'rotki account'
        request_data = {
            'accounts': [{
                'address': 'rotki.ethe',
                'label': label,
            }],
            'async_query': True,
        }
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'evmaccountsresource',
        ), json=request_data)

        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['result'] is None
        assert outcome['status_code'] == HTTPStatus.BAD_REQUEST
        assert 'Given ENS name rotki.ethe could not be resolved for Ethereum' in outcome['message']

        # add an address that should be correctly added
        label = 'rotki account'
        request_data = {
            'accounts': [{
                'address': 'rotki.eth',
                'label': label,
            }],
            'async_query': True,
        }
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'evmaccountsresource',
        ), json=request_data)

        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['result']['added'][common_account] == ['all']


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_argent_names(rotkehlchen_api_server: 'APIServer') -> None:
    name, address = 'mysticryuujin.argent.xyz', '0xeA6457DeA80349063cA9eBEfa450E8C4637e33A2'
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [{'address': name}]})

    result = assert_proper_sync_response_with_result(response)
    assert result == [address]

    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [name]})
    assert_proper_response(response)
    assert rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.accounts.eth == ()


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_adding_safe(rotkehlchen_api_server: 'APIServer') -> None:
    """Test adding a safe proxy. The address is deployed on arb and base only"""
    safe_address = string_to_evm_address('0x9d25AdBcffE28923E619f4Af88ECDe732c985b63')
    request_data = {'accounts': [{'address': safe_address}]}
    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'evmaccountsresource',
    ), json=request_data)

    result = assert_proper_sync_response_with_result(response)
    assert result == {
        'added': {safe_address: ['arbitrum_one', 'base']},
    }
