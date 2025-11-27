import os
import random
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.chain.ethereum.modules.makerdao.sai.constants import CPT_SAI
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import DAY_IN_SECONDS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.constants import CHAIN_EVENT_FIELDS
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EVENTS_WITH_COUNTERPARTY_JOIN, EvmTransactionsFilterQuery
from rotkehlchen.db.history_events import HISTORY_BASE_ENTRY_FIELDS
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_tx_signature
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_async_response,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.ethereum import (
    TEST_ADDR1,
    TEST_ADDR2,
    setup_ethereum_transactions_test,
)
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.optimism import OPTIMISM_MAINNET_NODE
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    Location,
    SolanaAddress,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.db.drivers.gevent import DBCursor

ADDY = string_to_evm_address('0x48ac67dC110BC42FC2D01a68b8E52FD04A5e87AF')


def _assert_evm_transaction_status(
        cursor: 'DBCursor',
        tx_hash: str,
        chain_id: ChainID,
        address: ChecksumEvmAddress,
        transaction_should_exist: bool,
) -> None:
    """Asserts whether an evm transaction is present in the database.

    If `transaction_should_exist` is False, the assertion is negated.
    """
    # check that the transaction was added
    tx_id_query = cursor.execute(
        'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
        (hexstring_to_bytes(tx_hash), chain_id.value),
    ).fetchone()
    assert tx_id_query is not None if transaction_should_exist else tx_id_query is None

    tx_id = -1 if tx_id_query is None else tx_id_query[0]

    # and the address was associated with the transaction
    count = cursor.execute(
        'SELECT COUNT(*) FROM evmtx_address_mappings WHERE tx_id=? AND address=?',
        (tx_id, address),
    ).fetchone()
    assert count[0] == 1 if transaction_should_exist else count[0] == 0


@pytest.mark.skipif(
    'CI' in os.environ,
    reason=('This test does a lot of remote queries and fails to VCR properly, '
    'although it works fine when run without VCR. '
    'See https://github.com/orgs/rotki/projects/11/views/3?pane=issue&itemId=141626655'),
)
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xb8553D9ee35dd23BB96fbd679E651B929821969B',
]])
@pytest.mark.parametrize('optimism_accounts', [[
    '0xb8553D9ee35dd23BB96fbd679E651B929821969B',
]])
@pytest.mark.parametrize('optimism_manager_connect_at_start', [(OPTIMISM_MAINNET_NODE,)])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1.5)])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.freeze_time('2022-12-29 10:10:00 GMT')
def test_query_transactions(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that querying the evm transactions endpoint for an address with
    transactions in multiple chains works fine.

    This test uses real data.
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # Ask for all evm transactions (test addy has both optimism and mainnet)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_sync_response_with_result(response)

    assert result is True

    dbevmtx = DBEvmTx(rotki.data.db)
    with rotki.data.db.conn.read_ctx() as cursor:
        transactions = dbevmtx.get_transactions(cursor, EvmTransactionsFilterQuery.make())

    optimism_count, mainnet_count = 0, 0
    for entry in transactions:
        if entry.chain_id == ChainID.ETHEREUM:
            mainnet_count += 1
        elif entry.chain_id == ChainID.OPTIMISM:
            optimism_count += 1
        else:
            raise AssertionError(f'Should not have a {entry.chain_id} transaction')

    assert optimism_count == 31
    assert mainnet_count == 18


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
@pytest.mark.parametrize('solana_accounts', [['4DrfzUpTdNtfr7D1RBVw2WhPshasifw97mH3aj27Skp9']])
@pytest.mark.parametrize('have_decoders', [[True]])
def test_transaction_reference_addition(rotkehlchen_api_server: 'APIServer', solana_accounts: list[SolanaAddress]) -> None:  # noqa: E501
    """Test that adding a transaction by reference works as expected."""
    is_async_query = random.choice([True, False])
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    tx_hash = '0xf7049668cb7cbb9c00d80092b2dce7ea59984f4c52c83e5c0940535a93f3d5a0'
    random_tx_hash = '0x4ad739488421162a45bf28aa66df580d8d1c790307d637e798e2180d71f12fd8'
    chain_id = ChainID.ETHEREUM
    expected_decoded_events = [
        # gas transaction is only added for tracked accounts.
        EvmEvent(
            identifier=1,
            tx_ref=deserialize_evm_tx_hash(tx_hash),
            sequence_index=22,
            timestamp=TimestampMS(1513958719000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x01349510117dC9081937794939552463F5616dfb',
            notes='Create CDP 131',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ),
    ]
    # first check that there's no such transaction in the db
    with database.conn.read_ctx() as cursor:
        _assert_evm_transaction_status(
            cursor=cursor,
            tx_hash=tx_hash,
            chain_id=chain_id,
            address=ADDY,
            transaction_should_exist=False,
        )

    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ), json={
            'async_query': is_async_query,
            'blockchain': (blockchain := str(chain_id.to_blockchain().serialize())),
            'tx_ref': tx_hash,
            'associated_address': ADDY,
        },
    )
    assert assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=is_async_query,
    )

    # now see that the transaction is present in the db
    # and the transaction was decoded properly
    with database.conn.read_ctx() as cursor:
        _assert_evm_transaction_status(
            cursor=cursor,
            tx_hash=tx_hash,
            chain_id=chain_id,
            address=ADDY,
            transaction_should_exist=True,
        )
        cursor.execute(f'SELECT {HISTORY_BASE_ENTRY_FIELDS}, {CHAIN_EVENT_FIELDS} {EVENTS_WITH_COUNTERPARTY_JOIN} WHERE tx_ref=?', (hexstring_to_bytes(tx_hash),))  # noqa: E501
        events = [EvmEvent.deserialize_from_db(entry[1:]) for entry in cursor]
        assert expected_decoded_events == events

    # check for errors
    # use an unsupported blockchain and see that it fails
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ), json={
            'async_query': is_async_query,
            'blockchain': SupportedBlockchain.KUSAMA.serialize(),
            'tx_ref': tx_hash,
            'associated_address': ADDY,
        },
    )
    assert_error_response(response, 'rotki does not support transactions for kusama')

    # add an already existing transaction
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ), json={
            'async_query': is_async_query,
            'blockchain': blockchain,
            'tx_ref': tx_hash,
            'associated_address': ADDY,
        },
    )
    assert_error_response(response, f'tx_ref {tx_hash} for {blockchain} already present in the database')  # noqa: E501

    # use an associated address that is not tracked by rotki
    random_address = make_evm_address()
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ), json={
            'async_query': is_async_query,
            'blockchain': blockchain,
            'tx_ref': random_tx_hash,
            'associated_address': random_address,
        },
    )
    assert_error_response(response, f'address {random_address} provided is not tracked by rotki for {blockchain}')  # noqa: E501

    # use a tx_hash that does not exist on-chain
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ), json={
            'async_query': is_async_query,
            'blockchain': blockchain,
            'tx_ref': random_tx_hash,
            'associated_address': ADDY,
        },
    )
    if is_async_query:
        task_id = assert_ok_async_response(response)
        response_data = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert_error_async_response(response_data, f'{random_tx_hash} not found on chain.', status_code=HTTPStatus.NOT_FOUND)  # noqa: E501
    else:
        assert_error_response(response, f'{random_tx_hash} not found on chain.', status_code=HTTPStatus.NOT_FOUND)  # noqa: E501

    # Test Solana transaction addition
    assert assert_proper_response_with_result(
        response=requests.put(
            api_url_for(rotkehlchen_api_server, 'blockchaintransactionsresource'),
            json={
                'async_query': is_async_query,
                'blockchain': 'solana',
                'tx_ref': (solana_signature := '2RrXcP3MMgjjt46SJ34wT4pXKhCV94psPJnZgVyVRkPZpk5JSmCMgFyd1rwKuz3LMTAi3hhay11N41YPtodav81z'),  # noqa: E501
                'associated_address': solana_accounts[0],
            },
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=is_async_query,
    )
    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM solana_transactions WHERE signature=?', (deserialize_tx_signature(solana_signature).to_bytes(),)).fetchone()[0] == 1  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM history_events WHERE group_identifier=?', (solana_signature,)).fetchone()[0] == 2  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xb8553D9ee35dd23BB96fbd679E651B929821969B']])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.freeze_time('2022-12-30 06:06:00 GMT')
def test_force_refetch_evm_transactions_success(
        ethereum_accounts: list['ChecksumEvmAddress'],
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Test that force refetching EVM transactions works successfully"""
    now = ts_now()
    four_days_ago = Timestamp(now - 4 * DAY_IN_SECONDS)
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    db_evmtx = DBEvmTx(db)

    # First, query all transactions to get initial state
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ), json={'async_query': False},
    )
    assert_proper_sync_response_with_result(response)

    # Count initial transactions
    total_transaction_count = db_evmtx.count_evm_transactions(ChainID.ETHEREUM)

    # Delete some transactions to simulate missing data
    with db.conn.write_ctx() as cursor:
        removed_transactions = cursor.execute(
            'DELETE FROM evm_transactions WHERE chain_id = ? AND timestamp >= ? AND timestamp <= ?',  # noqa: E501
            (ChainID.ETHEREUM.serialize_for_db(), four_days_ago, now),
        ).rowcount

    # Count transactions after deletion
    assert db_evmtx.count_evm_transactions(ChainID.ETHEREUM) == 8

    # Now, refetch the transactions
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'refetchtransactionsresource',
        ), json={
            'async_query': False,
            'from_timestamp': four_days_ago,
            'to_timestamp': now,
            'chain': SupportedBlockchain.ETHEREUM.serialize(),
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['new_transactions_count'] == removed_transactions

    # Count transactions after refetch
    assert total_transaction_count == db_evmtx.count_evm_transactions(ChainID.ETHEREUM)

    # check validation errors
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'refetchtransactionsresource',
        ), json={
            'async_query': False,
            'from_timestamp': four_days_ago,
            'to_timestamp': now,
            'address': ZERO_ADDRESS,
            'chain': SupportedBlockchain.ETHEREUM.serialize(),
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not tracked by rotki',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'refetchtransactionsresource',
        ), json={
            'async_query': False,
            'from_timestamp': four_days_ago,
            'to_timestamp': now,
            'address': ethereum_accounts[0],
            'chain': SupportedBlockchain.ARBITRUM_ONE.serialize(),
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not tracked by rotki',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_history_status_summary(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that querying the transactions status endpoint works correctly.
    Checks both with and without txs and queried ranges in the DB.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'historystatussummaryresource'),
        json={'async_query': (async_query := random.choice([False, True]))},
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)
    assert result == {
        'evm_last_queried_ts': 0,
        'exchanges_last_queried_ts': 0,
        'undecoded_tx_count': 0,
        'has_evm_accounts': True,
        'has_exchanges_accounts': False,
    }

    # Add some undecoded txs to the db
    setup_ethereum_transactions_test(
        database=rotki.data.db,
        transaction_already_queried=True,
        one_receipt_in_db=True,
        second_receipt_in_db=True,
    )
    # Manually set query ranges instead of making actual API calls
    last_queried_ts = Timestamp(100)
    with rotki.data.db.user_write() as write_cursor:
        for address in ethereum_accounts:
            write_cursor.execute(
                'INSERT OR REPLACE INTO used_query_ranges(name, start_ts, end_ts) '
                'VALUES (?, ?, ?)',
                (f'ETHtxs_{address}', 0, last_queried_ts),
            )

    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'historystatussummaryresource'),
        json={'async_query': async_query},
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)
    assert result == {
        'evm_last_queried_ts': last_queried_ts,
        'exchanges_last_queried_ts': 0,
        'undecoded_tx_count': 2,
        'has_evm_accounts': True,
        'has_exchanges_accounts': False,
    }

    # Remove all ethereum accounts to test has_evm_accounts: False
    with rotki.data.db.conn.write_ctx() as write_cursor:
        rotki.data.db.remove_single_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=ethereum_accounts,
        )

    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'historystatussummaryresource'),
        json={'async_query': async_query},
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)
    assert result == {
        'evm_last_queried_ts': 0,
        'exchanges_last_queried_ts': 0,
        'undecoded_tx_count': 0,
        'has_evm_accounts': False,
        'has_exchanges_accounts': False,
    }
