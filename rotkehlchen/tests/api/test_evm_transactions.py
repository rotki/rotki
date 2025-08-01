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
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.db.history_events import (
    EVM_EVENT_FIELDS,
    EVM_EVENT_JOIN,
    HISTORY_BASE_ENTRY_FIELDS,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
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
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    Location,
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


@pytest.mark.parametrize('ethereum_accounts', [[
    '0xb8553D9ee35dd23BB96fbd679E651B929821969B',
]])
@pytest.mark.parametrize('optimism_accounts', [[
    '0xb8553D9ee35dd23BB96fbd679E651B929821969B',
]])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1.5)])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.freeze_time('2022-12-29 10:10:00 GMT')
@pytest.mark.vcr(filter_query_parameters=['apikey'])
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
        transactions = dbevmtx.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(), True)  # noqa: E501

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
@pytest.mark.parametrize('have_decoders', [[True]])
def test_evm_transaction_hash_addition(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that adding an evm transaction by hash works as expected."""
    is_async_query = random.choice([True, False])
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    tx_hash = '0xf7049668cb7cbb9c00d80092b2dce7ea59984f4c52c83e5c0940535a93f3d5a0'
    random_tx_hash = '0x4ad739488421162a45bf28aa66df580d8d1c790307d637e798e2180d71f12fd8'
    chain_id = ChainID.ETHEREUM
    expected_decoded_events = [
        # gas transaction is only added for tracked accounts.
        EvmEvent(
            identifier=1,
            tx_hash=deserialize_evm_tx_hash(tx_hash),
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
            'evmtransactionshashresource',
        ), json={
            'async_query': is_async_query,
            'evm_chain': chain_id.to_name(),
            'tx_hash': tx_hash,
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
        cursor.execute(f'SELECT {HISTORY_BASE_ENTRY_FIELDS}, {EVM_EVENT_FIELDS} {EVM_EVENT_JOIN} WHERE tx_hash=?', (hexstring_to_bytes(tx_hash),))  # noqa: E501
        events = [EvmEvent.deserialize_from_db(entry[1:]) for entry in cursor]
        assert expected_decoded_events == events

    # check for errors
    # use an unsupported evm chain and see that it fails
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'evmtransactionshashresource',
        ), json={
            'async_query': is_async_query,
            'evm_chain': ChainID.FANTOM.to_name(),
            'tx_hash': tx_hash,
            'associated_address': ADDY,
        },
    )
    assert_error_response(response, 'Given chain_id fantom is not one of ethereum,optimism,polygon_pos,arbitrum_one,base,gnosis,scroll,binance_sc as needed by the endpoint')  # noqa: E501

    # add an already existing transaction
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'evmtransactionshashresource',
        ), json={
            'async_query': is_async_query,
            'evm_chain': chain_id.to_name(),
            'tx_hash': tx_hash,
            'associated_address': ADDY,
        },
    )
    assert_error_response(response, f'tx_hash {tx_hash} for {chain_id.to_name()} already present in the database')  # noqa: E501

    # use an associated address that is not tracked by rotki
    random_address = make_evm_address()
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'evmtransactionshashresource',
        ), json={
            'async_query': is_async_query,
            'evm_chain': chain_id.to_name(),
            'tx_hash': random_tx_hash,
            'associated_address': random_address,
        },
    )
    assert_error_response(response, f'address {random_address} provided is not tracked by rotki for {chain_id.to_name()}')  # noqa: E501

    # use a tx_hash that does not exist on-chain
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'evmtransactionshashresource',
        ), json={
            'async_query': is_async_query,
            'evm_chain': chain_id.to_name(),
            'tx_hash': random_tx_hash,
            'associated_address': ADDY,
        },
    )
    if is_async_query:
        task_id = assert_ok_async_response(response)
        response_data = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert_error_async_response(response_data, f'{random_tx_hash} not found on chain.', status_code=HTTPStatus.NOT_FOUND)  # noqa: E501
    else:
        assert_error_response(response, f'{random_tx_hash} not found on chain.', status_code=HTTPStatus.NOT_FOUND)  # noqa: E501


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
            'refetchevmtransactionsresource',
        ), json={
            'async_query': False,
            'from_timestamp': four_days_ago,
            'to_timestamp': now,
            'evm_chain': ChainID.ETHEREUM.to_name(),
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
            'refetchevmtransactionsresource',
        ), json={
            'async_query': False,
            'from_timestamp': four_days_ago,
            'to_timestamp': now,
            'address': ZERO_ADDRESS,
            'evm_chain': ChainID.ETHEREUM.to_name(),
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
            'refetchevmtransactionsresource',
        ), json={
            'async_query': False,
            'from_timestamp': four_days_ago,
            'to_timestamp': now,
            'address': ethereum_accounts[0],
            'evm_chain': ChainID.ARBITRUM_ONE.to_name(),
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not tracked by rotki',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_evm_transactions_status(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that querying the evm transactions status endpoint works correctly.
    Checks both with and without txs and queried ranges in the DB.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'evmtransactionsstatusresource'),
        json={'async_query': (async_query := random.choice([False, True]))},
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)
    assert result == {'last_queried_ts': 0, 'undecoded_tx_count': 0, 'has_evm_accounts': True}

    # Add some undecoded txs to the db
    setup_ethereum_transactions_test(
        database=rotki.data.db,
        transaction_already_queried=True,
        one_receipt_in_db=True,
        second_receipt_in_db=True,
    )
    # Run tx query logic to ensure we get the last queried timestamp correctly.
    rotki.chains_aggregator.ethereum.transactions.single_address_query_transactions(
        address=ethereum_accounts[0],
        start_ts=Timestamp(0),
        end_ts=(last_queried_ts := Timestamp(100)),  # use a small range that doesn't get anything
    )
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'evmtransactionsstatusresource'),
        json={'async_query': async_query},
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)
    assert result == {'last_queried_ts': last_queried_ts, 'undecoded_tx_count': 2, 'has_evm_accounts': True}  # noqa: E501

    # Remove all ethereum accounts to test has_evm_accounts: False
    with rotki.data.db.conn.write_ctx() as write_cursor:
        rotki.data.db.remove_single_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=ethereum_accounts,
        )

    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'evmtransactionsstatusresource'),
        json={'async_query': async_query},
    )
    result = assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)
    assert result == {'last_queried_ts': 0, 'undecoded_tx_count': 0, 'has_evm_accounts': False}
