import json
import random
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.makerdao.sai.constants import CPT_SAI
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress, Location, TimestampMS
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

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
    count = cursor.execute(
        'SELECT COUNT(*) FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
        (hexstring_to_bytes(tx_hash), chain_id.value),
    ).fetchone()
    assert count[0] == 1 if transaction_should_exist else count[0] == 0

    # and the address was associated with the transaction
    count = cursor.execute(
        'SELECT COUNT(*) FROM evmtx_address_mappings WHERE tx_hash=? AND chain_id=? AND address=?',  # noqa: E501
        (hexstring_to_bytes(tx_hash), chain_id.value, address),
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
def test_query_transactions(rotkehlchen_api_server: 'APIServer'):
    """Test that querying the evm transactions endpoint for an address with
    transactions in multiple chains works fine.

    This test uses real data.

    TODO: Mock network here. Need to mock transaction query for both mainnet and optimism etherscan
    """
    async_query = random.choice([False, True])
    # Ask for all evm transactions (test addy has both optimism and mainnet)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'evmtransactionsresource',
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)

    expected_file = Path(__file__).resolve().parent.parent / 'data' / 'expected' / 'test_evm_transactions-test_query_transactions.json'  # noqa: E501
    with open(expected_file) as f:
        expected_data = json.load(f)

    # check all expected data exists. User has done more transactions since then if we don't
    # mock network, so we need to test like this
    last_ts = result['entries'][0]['entry']['timestamp']
    for entry in expected_data['entries']:
        assert entry in result['entries']
        assert entry['entry']['timestamp'] <= last_ts
        last_ts = entry['entry']['timestamp']

    assert result['entries_found'] >= expected_data['entries_found']
    assert result['entries_total'] >= expected_data['entries_total']
    assert result['entries_limit'] == -1

    # After querying make sure pagination and only_cache work properly for multiple chains
    for evm_chain in ('ethereum', 'optimism'):
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'evmtransactionsresource',
            ), json={
                'async_query': False,
                'limit': 10,
                'offset': 0,
                'ascending': [False],
                'only_cache': True,
                'order_by_attributes': ['timestamp'],
                'evm_chain': evm_chain,
            },
        )
        result = assert_proper_response_with_result(response)
        assert len(result['entries']) != 0, f'Should have had {evm_chain} transactions'
        last_ts = result['entries'][0]['entry']['timestamp']
        for entry in result['entries']:
            assert entry['entry']['timestamp'] <= last_ts
            last_ts = entry['entry']['timestamp']


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_evm_transaction_hash_addition(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that adding an evm transaction by hash works as expected."""
    is_async_query = random.choice([True, False])
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    tx_hash = '0xf7049668cb7cbb9c00d80092b2dce7ea59984f4c52c83e5c0940535a93f3d5a0'
    random_tx_hash = '0x4ad739488421162a45bf28aa66df580d8d1c790307d637e798e2180d71f12fd8'
    chain_id = ChainID.ETHEREUM
    expected_decoded_events = [
        # gas transaction is only added for tracked accounts.
        HistoryBaseEntry(
            identifier=1,
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hash),
            sequence_index=22,
            timestamp=TimestampMS(1513958719000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label='0x01349510117dC9081937794939552463F5616dfb',
            notes='Create CDP 131',
            counterparty=CPT_SAI,
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
    if is_async_query is True:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        assert result is True
    else:
        assert_simple_ok_response(response)

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
        cursor.execute('SELECT * FROM history_events WHERE event_identifier=?', (hexstring_to_bytes(tx_hash),))  # noqa: E501
        events = [HistoryBaseEntry.deserialize_from_db(entry) for entry in cursor]
        assert expected_decoded_events == events

    # check for errors
    # use an unsupported evm chain and see that it fails
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'evmtransactionshashresource',
        ), json={
            'async_query': is_async_query,
            'evm_chain': ChainID.ARBITRUM.to_name(),
            'tx_hash': tx_hash,
            'associated_address': ADDY,
        },
    )
    assert_error_response(response, 'Given chain_id arbitrum is not one of ethereum,optimism as needed by the endpoint')  # noqa: E501

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
