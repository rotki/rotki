import logging
import os
import random
from contextlib import ExitStack
from http import HTTPStatus
from typing import List, Optional
from unittest.mock import patch

import gevent
import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.ethereum.constants import (
    RANGE_PREFIX_ETHINTERNALTX,
    RANGE_PREFIX_ETHTOKENTX,
    RANGE_PREFIX_ETHTX,
)
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH, A_MKR, A_USDT, A_WETH
from rotkehlchen.constants.limits import FREE_ETH_TX_LIMIT
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.checks import assert_serialized_lists_equal
from rotkehlchen.tests.utils.constants import TXHASH_HEX_TO_BYTES
from rotkehlchen.tests.utils.factories import (
    generate_tx_entries_response,
    make_ethereum_address,
    make_ethereum_event,
    make_ethereum_transaction,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import EvmTransaction, EVMTxHash, Timestamp, make_evm_tx_hash
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

EXPECTED_AFB7_TXS = [{
    'tx_hash': '0x13684203a4bf07aaed0112983cb380db6004acac772af2a5d46cb2a28245fbad',
    'timestamp': 1439984408,
    'block_number': 111083,
    'from_address': '0xC47Aaa860008be6f65B58c6C6E02a84e666EfE31',
    'to_address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
    'value': '37451082560000003241',
    'gas': '90000',
    'gas_price': '58471444665',
    'gas_used': '21000',
    'input_data': '0x',
    'nonce': 100,
}, {
    'tx_hash': '0xe58af420fd8430c061303e4c5bd2668fafbc0fd41078fa6aa01d7781c1dadc7a',
    'timestamp': 1461221228,
    'block_number': 1375816,
    'from_address': '0x9e6316f44BaEeeE5d41A1070516cc5fA47BAF227',
    'to_address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
    'value': '389359660000000000',
    'gas': '250000',
    'gas_price': '20000000000',
    'gas_used': '21000',
    'input_data': '0x',
    'nonce': 326,
}, {
    'tx_hash': '0x0ae8b470b4a69c7f6905b9ec09f50c8772821080d11ba0acc83ac23a7ccb4ad8',
    'timestamp': 1461399856,
    'block_number': 1388248,
    'from_address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
    'to_address': '0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2',
    'value': '37840020860000003241',
    'gas': '21068',
    'gas_price': '20000000000',
    'gas_used': '21068',
    'input_data': '0x01',
    'nonce': 0,
}, {
    'tx_hash': '0x2f6f167e32e9cb1bef40b92e831c3f1d1cd0348bb72dcc723bde94f51944ebd6',
    'timestamp': 1494458609,
    'block_number': 3685519,
    'from_address': '0x4aD11d04CCd80A83d48096478b73D1E8e0ed49D6',
    'to_address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
    'value': '6000000000000000000',
    'gas': '21000',
    'gas_price': '21000000000',
    'gas_used': '21000',
    'input_data': '0x',
    'nonce': 1,
}, {
    'tx_hash': '0x5d81f937ad37349f89dc6e9926988855bb6c6e1e00c683ee3b7cb7d7b09b5567',
    'timestamp': 1494458861,
    'block_number': 3685532,
    'from_address': '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
    'to_address': '0xFa52274DD61E1643d2205169732f29114BC240b3',
    'value': '5999300000000000000',
    'gas': '35000',
    'gas_price': '20000000000',
    'gas_used': '30981',
    'input_data': '0xf7654176',
    'nonce': 1,
}]

EXPECTED_4193_TXS = [{
    'tx_hash': '0x2964f3a91408337b05aeb8f8f670f4107999be05376e630742404664c96a5c31',
    'timestamp': 1439979000,
    'block_number': 110763,
    'from_address': '0x976349705b839e2F5719387Fb27D2519d519da03',
    'to_address': '0x4193122032b38236825BBa166F42e54fc3F4A1EE',
    'value': '100000000000000000',
    'gas': '90000',
    'gas_price': '57080649960',
    'gas_used': '21000',
    'input_data': '0x',
    'nonce': 30,
}, {
    'tx_hash': '0xb99a6e0b40f38c4887617bc1df560fde1d0456b712cb2bb1b52fdb8880d3cd74',
    'timestamp': 1439984825,
    'block_number': 111111,
    'from_address': '0x4193122032b38236825BBa166F42e54fc3F4A1EE',
    'to_address': '0x1177848589133f5C4E69EdFcb18bBCd9cACE72D1',
    'value': '20000000000000000',
    'gas': '90000',
    'gas_price': '59819612547',
    'gas_used': '21000',
    'input_data': '0x',
    'nonce': 0,
}, {
    'tx_hash': '0xfadf1f12281ee2c0311055848b4ffc0046ac80afae4a9d3640b5f57bb8a7795a',
    'timestamp': 1507291254,
    'block_number': 4341870,
    'from_address': '0x4193122032b38236825BBa166F42e54fc3F4A1EE',
    'to_address': '0x2B06E2ea21e184589853225888C93b9b8e0642f6',
    'value': '78722788136513000',
    'gas': '21000',
    'gas_price': '1000000000',
    'gas_used': '21000',
    'input_data': '0x',
    'nonce': 1,
}]


def assert_force_redecode_txns_works(api_server: APIServer, hashes: Optional[List[EVMTxHash]]):
    rotki = api_server.rest_api.rotkehlchen
    get_eth_txns_patch = patch.object(
        rotki.eth_tx_decoder.dbethtx,
        'get_ethereum_transactions',
        wraps=rotki.eth_tx_decoder.dbethtx.get_ethereum_transactions,
    )
    get_or_decode_txn_events_patch = patch.object(
        rotki.eth_tx_decoder,
        'get_or_decode_transaction_events',
        wraps=rotki.eth_tx_decoder.get_or_decode_transaction_events,
    )
    get_or_query_txn_receipt_patch = patch('rotkehlchen.chain.ethereum.transactions.EthTransactions.get_or_query_transaction_receipt')  # noqa: 501
    with ExitStack() as stack:
        function_call_counters = []
        function_call_counters.append(stack.enter_context(get_or_decode_txn_events_patch))
        function_call_counters.append(stack.enter_context(get_eth_txns_patch))
        function_call_counters.append(stack.enter_context(get_or_query_txn_receipt_patch))

        response = requests.post(
            api_url_for(
                api_server,
                'ethereumtransactionsresource',
            ), json={
                'async_query': False,
                'ignore_cache': True,
                'tx_hashes': hashes,
            },
        )
        assert_proper_response(response)
        if hashes is None:
            for fn in function_call_counters:
                assert fn.call_count == 14
        else:
            txn_hashes_len = len(hashes)
            for fn in function_call_counters:
                assert fn.call_count == txn_hashes_len


@pytest.mark.parametrize('ethereum_accounts', [[
    '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
    '0x4193122032b38236825BBa166F42e54fc3F4A1EE',
]])
def test_query_transactions(rotkehlchen_api_server):
    """Test that querying the ethereum transactions endpoint works as expected.
    Also tests that requesting for transaction decoding works.

    This test uses real data.
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # Check that we get all transactions
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)
    expected_result = EXPECTED_AFB7_TXS + EXPECTED_4193_TXS
    expected_result.sort(key=lambda x: x['timestamp'])
    expected_result.reverse()

    # Make sure that all of the transactions we expect are there and in order
    # There can be more transactions (since the address can make more)
    # but this check ignores them
    previous_index = 0
    result_entries = [x['entry'] for x in result['entries']]
    assert all(x['ignored_in_accounting'] is False for x in result['entries']), 'by default nothing should be ignored'  # noqa: E501
    for entry in expected_result:
        assert entry in result_entries
        entry_idx = result_entries.index(entry)
        if previous_index != 0:
            assert entry_idx == previous_index + 1
        previous_index = entry_idx

    assert result['entries_found'] >= len(expected_result)
    assert result['entries_limit'] == FREE_ETH_TX_LIMIT

    # now let's ignore two transactions
    ignored_ids = [
        EXPECTED_AFB7_TXS[2]['tx_hash'],
        EXPECTED_AFB7_TXS[3]['tx_hash'],
    ]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "ignoredactionsresource",
        ), json={'action_type': 'ethereum_transaction', 'action_ids': ignored_ids},
    )
    result = assert_proper_response_with_result(response)
    assert result == {'ethereum_transaction': ignored_ids}

    # Check that transactions per address and in a specific time range can be
    # queried and that this is from the DB and not etherscan
    def mock_etherscan_get(url, *args, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, "{}")
    etherscan_patch = patch.object(rotki.etherscan.session, 'get', wraps=mock_etherscan_get)
    with etherscan_patch as mock_call:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'per_address_ethereum_transactions_resource',
                address='0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
            ), json={
                'async_query': async_query,
                'from_timestamp': 1461399856,
                'to_timestamp': 1494458860,
            },
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

        assert mock_call.call_count == 0

    result_entries = [x['entry'] for x in result['entries']]
    assert result_entries == EXPECTED_AFB7_TXS[2:4][::-1]
    msg = 'the transactions we ignored have not been ignored for accounting'
    assert all(x['ignored_in_accounting'] is True for x in result['entries']), msg

    # Also check that requesting decoding of tx_hashes gets receipts and decodes events
    hashes = [EXPECTED_AFB7_TXS[0]['tx_hash'], EXPECTED_4193_TXS[0]['tx_hash']]
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ), json={
            'async_query': async_query,
            'tx_hashes': hashes,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)
    assert result is True

    dbethtx = DBEthTx(rotki.data.db)
    dbevents = DBHistoryEvents(rotki.data.db)
    event_ids = set()
    with rotki.data.db.conn.read_ctx() as cursor:
        for tx_hash_hex in hashes:
            receipt = dbethtx.get_receipt(cursor, hexstring_to_bytes(tx_hash_hex))
            assert isinstance(receipt, EthereumTxReceipt) and receipt.tx_hash == hexstring_to_bytes(tx_hash_hex)  # noqa: E501
            events = dbevents.get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    event_identifier=TXHASH_HEX_TO_BYTES[tx_hash_hex],
                ),
                has_premium=True,  # for this function we don't limit. We only limit txs.
            )
            event_ids.add(events[0].identifier)
            assert len(events) == 1

    # see that if same transaction hash is requested for decoding events are not re-decoded
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ), json={
            'async_query': False,
            'tx_hashes': hashes,
        },
    )

    with rotki.data.db.conn.read_ctx() as cursor:
        result = assert_proper_response_with_result(response)
        for tx_hash_hex in hashes:
            receipt = dbethtx.get_receipt(cursor, hexstring_to_bytes(tx_hash_hex))
            assert isinstance(receipt, EthereumTxReceipt) and receipt.tx_hash == hexstring_to_bytes(tx_hash_hex)  # noqa: E501
            events = dbevents.get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    event_identifier=TXHASH_HEX_TO_BYTES[tx_hash_hex],
                ),
                has_premium=True,  # for this function we don't limit. We only limit txs.
            )
            assert len(events) == 1
            assert events[0].identifier in event_ids  # pylint: disable=unsubscritable-object

    # Check that force re-requesting the events works
    assert_force_redecode_txns_works(rotkehlchen_api_server, hashes)
    # check that passing no transaction hashes, decodes all transaction
    assert_force_redecode_txns_works(rotkehlchen_api_server, None)

    # see that empty list of hashes to decode is an error
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ), json={'async_query': False, 'tx_hashes': []},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Empty list of hashes is a noop. Did you mean to omit the list?',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_request_transaction_decoding_errors(rotkehlchen_api_server):
    """Test that the request transaction decoding endpoint handles input errors"""
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ), json={
            'async_query': False,
            'tx_hashes': [1, '0xfc4f300f4d9e6436825ed0dc85716df4648a64a29570280c6e6261acf041aa4b'],  # noqa: E501
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Transaction hash should be a string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ), json={
            'async_query': False,
            'tx_hashes': ['dasd', '0xfc4f300f4d9e6436825ed0dc85716df4648a64a29570280c6e6261acf041aa4b'],  # noqa: E501
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Could not turn transaction hash dasd to bytes',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ), json={
            'async_query': False,
            'tx_hashes': ['0x34af01', '0xfc4f300f4d9e6436825ed0dc85716df4648a64a29570280c6e6261acf041aa4b'],  # noqa: E501
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Transaction hashes should be 32 bytes in length',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    nonexisting_hash = '0x1c4f300f4d9e6436825ed0dc85716df4648a64a29570280c6e6261acf041aa41'
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ), json={
            'async_query': False,
            'tx_hashes': [nonexisting_hash],  # noqa: E501
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Hash {nonexisting_hash} does not correspond to a transaction',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='SLOW TEST -- run locally from time to time',
)
@pytest.mark.parametrize('ethereum_accounts', [['0xe62193Bc1c340EF2205C0Bd71691Fad5e5072253']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_query_over_10k_transactions(rotkehlchen_api_server):
    """Test that querying for an address with over 10k transactions works

    This test uses real etherscan queries and an address that we found that has > 10k transactions.

    Etherscan has a limit for 1k transactions per query and we need to make
    sure that we properly pull all data by using pagination
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    original_get = requests.get

    def mock_some_etherscan_queries(etherscan: Etherscan):
        """Just hit etherscan for the actual transations and mock all else.
        This test just needs to see that pagination works on the tx endpoint
        """
        def mocked_request_dict(url, *_args, **_kwargs):
            if '=txlistinternal&' in url:
                # don't return any internal transactions
                payload = '{"status":"1","message":"OK","result":[]}'
            elif '=tokentx&' in url:
                # don't return any token transactions
                payload = '{"status":"1","message":"OK","result":[]}'
            elif '=getblocknobytime&' in url:
                # we don't really care about this in this test so return whatever
                # payload = '{"status":"1","message":"OK","result": "1"}'
                return original_get(url)
            elif '=txlist&' in url:
                return original_get(url)
            else:
                raise AssertionError(f'Unexpected etherscan query {url} at test mock')
            return MockResponse(200, payload)

        return patch.object(etherscan.session, 'get', wraps=mocked_request_dict)

    expected_at_least = 16097  # 30/08/2020
    with mock_some_etherscan_queries(rotki.etherscan):
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'ethereumtransactionsresource',
            ),
        )

    result = assert_proper_response_with_result(response)
    assert len(result['entries']) >= expected_at_least
    assert result['entries_found'] >= expected_at_least
    assert result['entries_limit'] == -1

    # Also check some entries in the list that we know of to see that they exist
    rresult = [x['entry'] for x in result['entries'][::-1]]

    assert rresult[1]['tx_hash'] == '0xec72748b8b784380ff6fcca9b897d649a0992eaa63b6c025ecbec885f64d2ac9'  # noqa: E501
    assert rresult[1]['nonce'] == 0
    assert rresult[11201]['tx_hash'] == '0x118edf91d6d47fcc6bc9c7ceefe2ee2344e0ff3b5a1805a804fa9c9448efb746'  # noqa: E501
    assert rresult[11201]['nonce'] == 11198
    assert rresult[16172]['tx_hash'] == '0x92baec6dbf3351a1aea2371453bfcb5af898ffc8172fcf9577ca2e5335df4c71'  # noqa: E501
    assert rresult[16172]['nonce'] == 16169


def test_query_transactions_errors(rotkehlchen_api_server):
    # Malformed address
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_address_ethereum_transactions_resource',
            address='0xasdasd',
        ),
    )
    assert_error_response(
        response=response,
        contained_in_msg='address": ["Given value 0xasdasd is not an ethereum address',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Malformed from_timestamp
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_address_ethereum_transactions_resource',
            address='0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
        ), json={'from_timestamp': 'foo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a timestamp entry from string foo',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Malformed to_timestamp
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_address_ethereum_transactions_resource',
            address='0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
        ), json={'to_timestamp': 'foo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a timestamp entry from string foo',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid order_by_attribute
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'per_address_ethereum_transactions_resource',
            address='0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
        ), json={'order_by_attributes': ['tim3'], 'ascending': [False]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='order_by_attributes for transactions can not be tim3',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('start_with_valid_premium', [False, True])
@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_query_transactions_over_limit(
        rotkehlchen_api_server,
        ethereum_accounts,
        start_with_valid_premium,
):
    start_ts = 0
    end_ts = 1598453214
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    all_transactions_num = FREE_ETH_TX_LIMIT + 50
    transactions = [EvmTransaction(
        tx_hash=make_evm_tx_hash(x.to_bytes(2, byteorder='little')),
        timestamp=x,
        block_number=x,
        from_address=ethereum_accounts[0],
        to_address=make_ethereum_address(),
        value=x,
        gas=x,
        gas_price=x,
        gas_used=x,
        input_data=x.to_bytes(2, byteorder='little'),
        nonce=x,
    ) for x in range(FREE_ETH_TX_LIMIT - 10)]
    extra_transactions = [EvmTransaction(
        tx_hash=make_evm_tx_hash((x + 500).to_bytes(2, byteorder='little')),
        timestamp=x,
        block_number=x,
        from_address=ethereum_accounts[1],
        to_address=make_ethereum_address(),
        value=x,
        gas=x,
        gas_price=x,
        gas_used=x,
        input_data=x.to_bytes(2, byteorder='little'),
        nonce=x,
    ) for x in range(60)]

    with db.user_write() as cursor:
        dbethtx = DBEthTx(db)
        dbethtx.add_ethereum_transactions(cursor, transactions, relevant_address=ethereum_accounts[0])  # noqa: E501
        dbethtx.add_ethereum_transactions(cursor, extra_transactions, relevant_address=ethereum_accounts[1])  # noqa: E501
        # Also make sure to update query ranges so as not to query etherscan at all
        for address in ethereum_accounts:
            for prefix in (RANGE_PREFIX_ETHTX, RANGE_PREFIX_ETHINTERNALTX, RANGE_PREFIX_ETHTOKENTX):  # noqa: E501
                DBQueryRanges(db).update_used_query_range(
                    write_cursor=cursor,
                    location_string=f'{prefix}_{address}',
                    queried_ranges=[(start_ts, end_ts)],
                )

    free_expected_entries_total = [FREE_ETH_TX_LIMIT - 35, 35]
    free_expected_entries_found = [FREE_ETH_TX_LIMIT - 10, 60]
    premium_expected_entries = [FREE_ETH_TX_LIMIT - 10, 60]

    # Check that we get all transactions correctly even if we query two times
    for _ in range(2):
        for idx, address in enumerate(ethereum_accounts):
            response = requests.get(
                api_url_for(
                    rotkehlchen_api_server,
                    'ethereumtransactionsresource',
                ), json={
                    'from_timestamp': start_ts,
                    'to_timestamp': end_ts,
                    'address': address,
                },
            )
            result = assert_proper_response_with_result(response)
            if start_with_valid_premium:
                assert len(result['entries']) == premium_expected_entries[idx]
                assert result['entries_total'] == all_transactions_num
                assert result['entries_found'] == premium_expected_entries[idx]
                assert result['entries_limit'] == -1
            else:
                assert len(result['entries']) == free_expected_entries_total[idx]
                assert result['entries_total'] == all_transactions_num
                assert result['entries_found'] == free_expected_entries_found[idx]
                assert result['entries_limit'] == FREE_ETH_TX_LIMIT


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_query_transactions_from_to_address(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    """Make sure that if a transaction is just being sent to an address it's also returned."""
    start_ts = 0
    end_ts = 1598453214
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    transactions = [EvmTransaction(
        tx_hash=make_evm_tx_hash(b'1'),
        timestamp=0,
        block_number=0,
        from_address=ethereum_accounts[0],
        to_address=make_ethereum_address(),
        value=1,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=0,
    ), EvmTransaction(
        tx_hash=make_evm_tx_hash(b'2'),
        timestamp=0,
        block_number=0,
        from_address=ethereum_accounts[0],
        to_address=ethereum_accounts[1],
        value=1,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=1,
    ), EvmTransaction(
        tx_hash=make_evm_tx_hash(b'3'),
        timestamp=0,
        block_number=0,
        from_address=make_ethereum_address(),
        to_address=ethereum_accounts[0],
        value=1,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=55,
    )]

    with db.user_write() as cursor:
        dbethtx = DBEthTx(db)
        dbethtx.add_ethereum_transactions(cursor, transactions, relevant_address=ethereum_accounts[0])  # noqa: E501
        dbethtx.add_ethereum_transactions(cursor, [transactions[1]], relevant_address=ethereum_accounts[1])  # noqa: E501
        # Also make sure to update query ranges so as not to query etherscan at all
        for address in ethereum_accounts:
            for prefix in (RANGE_PREFIX_ETHTX, RANGE_PREFIX_ETHINTERNALTX, RANGE_PREFIX_ETHTOKENTX):  # noqa: E501
                DBQueryRanges(db).update_used_query_range(
                    write_cursor=cursor,
                    location_string=f'{prefix}_{address}',
                    queried_ranges=[(start_ts, end_ts)],
                )

    expected_entries = {ethereum_accounts[0]: 3, ethereum_accounts[1]: 1}
    # Check that we get all transactions correctly even if we query two times
    for _ in range(2):
        for address in ethereum_accounts:
            response = requests.get(
                api_url_for(
                    rotkehlchen_api_server,
                    'ethereumtransactionsresource',
                ), json={
                    'from_timestamp': start_ts,
                    'to_timestamp': end_ts,
                    'address': address,
                },
            )
            result = assert_proper_response_with_result(response)
            assert len(result['entries']) == expected_entries[address]
            assert result['entries_limit'] == FREE_ETH_TX_LIMIT
            assert result['entries_found'] == expected_entries[address]
            assert result['entries_total'] == 3


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_query_transactions_removed_address(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    """Make sure that if an address is removed so are the transactions from the DB.
    Also assure that a transaction is not deleted so long as it touches a tracked
    address, even if one of the touched address is removed.
    """
    start_ts = 0
    end_ts = 1598453214
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    transactions = [EvmTransaction(
        tx_hash=make_evm_tx_hash(b'1'),
        timestamp=0,
        block_number=0,
        from_address=ethereum_accounts[0],
        to_address=make_ethereum_address(),
        value=1,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=0,
    ), EvmTransaction(
        tx_hash=make_evm_tx_hash(b'2'),
        timestamp=0,
        block_number=0,
        from_address=ethereum_accounts[0],
        to_address=make_ethereum_address(),
        value=1,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=1,
    ), EvmTransaction(  # should remain after deleting account[0]
        tx_hash=make_evm_tx_hash(b'3'),
        timestamp=0,
        block_number=0,
        from_address=make_ethereum_address(),
        to_address=ethereum_accounts[1],
        value=1,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=55,
    ), EvmTransaction(  # should remain after deleting account[0]
        tx_hash=make_evm_tx_hash(b'4'),
        timestamp=0,
        block_number=0,
        from_address=ethereum_accounts[1],
        to_address=ethereum_accounts[0],
        value=1,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=0,
    ), EvmTransaction(  # should remain after deleting account[0]
        tx_hash=make_evm_tx_hash(b'5'),
        timestamp=0,
        block_number=0,
        from_address=ethereum_accounts[0],
        to_address=ethereum_accounts[1],
        value=1,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=0,
    )]
    dbethtx = DBEthTx(db)
    with db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, transactions[0:2] + transactions[3:], relevant_address=ethereum_accounts[0])  # noqa: E501
        dbethtx.add_ethereum_transactions(cursor, transactions[2:], relevant_address=ethereum_accounts[1])  # noqa: E501
        # Also make sure to update query ranges so as not to query etherscan at all
        for address in ethereum_accounts:
            for prefix in (RANGE_PREFIX_ETHTX, RANGE_PREFIX_ETHINTERNALTX, RANGE_PREFIX_ETHTOKENTX):  # noqa: E501
                DBQueryRanges(db).update_used_query_range(
                    write_cursor=cursor,
                    location_string=f'{prefix}_{address}',
                    queried_ranges=[(start_ts, end_ts)],
                )

    # Now remove the first account (do the mocking to not query etherscan for balances)
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=[],
        eth_balances=['10000', '10000'],
    )
    with ExitStack() as stack:
        setup.enter_ethereum_patches(stack)
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain='ETH',
        ), json={'accounts': [ethereum_accounts[0]]})
    assert_proper_response_with_result(response)

    # Check that only the 3 remaining transactions from the other account are returned
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 3
    assert result['entries_found'] == 3


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_transaction_same_hash_same_nonce_two_tracked_accounts(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    """Make sure that if we track two addresses and they send one transaction
    to each other it's not counted as duplicate in the DB but is returned
    every time by both addresses"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    def mock_etherscan_transaction_response(etherscan: Etherscan, eth_accounts):
        def mocked_request_dict(url, *_args, **_kwargs):

            addr1_tx = f"""{{"blockNumber":"1","timeStamp":"1","hash":"0x9c81f44c29ff0226f835cd0a8a2f2a7eca6db52a711f8211b566fd15d3e0e8d4","nonce":"0","blockHash":"0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159","transactionIndex":"0","from":"{eth_accounts[0]}","to":"{eth_accounts[1]}","value":"1","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"0x","contractAddress":"","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"1"}}"""  # noqa: E501
            addr2_txs = f"""{addr1_tx}, {{"blockNumber":"2","timeStamp":"2","hash":"0x1c81f54c29ff0226f835cd0a2a2f2a7eca6db52a711f8211b566fd15d3e0e8d4","nonce":"1","blockHash":"0xd1cabad2adab0b56ea632c386ea19403680571e682c62cb589b5abcd76de2159","transactionIndex":"0","from":"{eth_accounts[1]}","to":"{make_ethereum_address()}","value":"1","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"0x","contractAddress":"","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"1"}}"""  # noqa: E501
            if '=txlistinternal&' in url:
                # don't return any internal transactions
                payload = '{"status":"1","message":"OK","result":[]}'
            elif 'action=tokentx&' in url:
                # don't return any token transactions
                payload = '{"status":"1","message":"OK","result":[]}'
            elif '=txlist&' in url:
                if eth_accounts[0] in url:
                    tx_str = addr1_tx
                elif eth_accounts[1] in url:
                    tx_str = addr2_txs
                else:
                    raise AssertionError(
                        'Requested etherscan transactions for unknown address in tests',
                    )
                payload = f'{{"status":"1","message":"OK","result":[{tx_str}]}}'
            elif '=getblocknobytime&' in url:
                # we don't really care about this so just return whatever
                payload = '{"status":"1","message":"OK","result": "1"}'
            else:
                raise AssertionError('Got in unexpected section during test')

            return MockResponse(200, payload)

        return patch.object(etherscan.session, 'get', wraps=mocked_request_dict)

    with mock_etherscan_transaction_response(rotki.etherscan, ethereum_accounts):
        # Check that we get transaction both when we query all accounts and each one individually
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'ethereumtransactionsresource',
            ),
        )
        result = assert_proper_response_with_result(response)
        assert len(result['entries']) == 2
        assert result['entries_found'] == 2
        assert result['entries_total'] == 2

        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'per_address_ethereum_transactions_resource',
                address=ethereum_accounts[0],
            ),
        )
        result = assert_proper_response_with_result(response)
        assert len(result['entries']) == 1
        assert result['entries_found'] == 1
        assert result['entries_total'] == 2
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'per_address_ethereum_transactions_resource',
                address=ethereum_accounts[1],
            ),
        )
        result = assert_proper_response_with_result(response)
        assert len(result['entries']) == 2
        assert result['entries_found'] == 2
        assert result['entries_total'] == 2


@pytest.mark.parametrize('ethereum_accounts', [['0x6e15887E2CEC81434C16D587709f64603b39b545']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_query_transactions_check_decoded_events(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    """Test that querying for an address's transactions after the events have been
    decoded also includes said events

    Also test that if an event is edited or added to a transaction that transaction and
    event are not purged when the ethereum transactions are purged. And if transactions
    are requeried the edited events are there.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    start_ts = Timestamp(0)
    end_ts = Timestamp(1642803566)  # time of test writing

    def query_transactions(rotki) -> None:
        rotki.eth_transactions.single_address_query_transactions(
            address=ethereum_accounts[0],
            start_ts=start_ts,
            end_ts=end_ts,
        )
        rotki.task_manager._maybe_schedule_ethereum_txreceipts()
        gevent.joinall(rotki.greenlet_manager.greenlets)
        rotki.task_manager._maybe_decode_evm_transactions()
        gevent.joinall(rotki.greenlet_manager.greenlets)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'ethereumtransactionsresource',
            ),
            json={
                'from_timestamp': start_ts,
                'to_timestamp': end_ts,
            },
        )
        return assert_proper_response_with_result(response)

    result = query_transactions(rotki)
    entries = result['entries']
    assert len(entries) == 4
    tx1_events = [{'entry': {
        'identifier': 4,
        'asset': 'ETH',
        'balance': {'amount': '0.00863351371344', 'usd_value': '0'},
        'counterparty': CPT_GAS,
        'event_identifier': '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f',
        'event_subtype': 'fee',
        'event_type': 'spend',
        'location': 'blockchain',
        'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
        'notes': 'Burned 0.00863351371344 ETH in gas from 0x6e15887E2CEC81434C16D587709f64603b39b545',  # noqa: E501
        'sequence_index': 0,
        'timestamp': 1642802807,
    }, 'customized': False}, {'entry': {
        'identifier': 5,
        'asset': 'ETH',
        'balance': {'amount': '0.096809163374771208', 'usd_value': '0'},
        'counterparty': '0xA090e606E30bD747d4E6245a1517EbE430F0057e',
        'event_identifier': '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f',
        'event_subtype': None,
        'event_type': 'spend',
        'location': 'blockchain',
        'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
        'notes': 'Send 0.096809163374771208 ETH 0x6e15887E2CEC81434C16D587709f64603b39b545 to 0xA090e606E30bD747d4E6245a1517EbE430F0057e',  # noqa: E501
        'sequence_index': 1,
        'timestamp': 1642802807,
    }, 'customized': False}]
    assert entries[0]['decoded_events'] == tx1_events
    tx2_events = [{'entry': {
        'identifier': 1,
        'asset': 'ETH',
        'balance': {'amount': '0.017690836625228792', 'usd_value': '0'},
        'counterparty': CPT_GAS,
        'event_identifier': '0x38ed9c2d4f0855f2d88823d502f8794b993d28741da48724b7dfb559de520602',
        'event_subtype': 'fee',
        'event_type': 'spend',
        'location': 'blockchain',
        'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
        'notes': 'Burned 0.017690836625228792 ETH in gas from 0x6e15887E2CEC81434C16D587709f64603b39b545',  # noqa: E501
        'sequence_index': 0,
        'timestamp': 1642802735,
    }, 'customized': False}, {'entry': {
        'identifier': 2,
        'asset': A_USDT.identifier,
        'balance': {'amount': '1166', 'usd_value': '0'},
        'counterparty': '0xb5d85CBf7cB3EE0D56b3bB207D5Fc4B82f43F511',
        'event_identifier': '0x38ed9c2d4f0855f2d88823d502f8794b993d28741da48724b7dfb559de520602',
        'event_subtype': None,
        'event_type': 'spend',
        'location': 'blockchain',
        'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
        'notes': 'Send 1166 USDT from 0x6e15887E2CEC81434C16D587709f64603b39b545 to 0xb5d85CBf7cB3EE0D56b3bB207D5Fc4B82f43F511',  # noqa: E501
        'sequence_index': 308,
        'timestamp': 1642802735,
    }, 'customized': False}]
    assert entries[1]['decoded_events'] == tx2_events
    tx3_events = [{'entry': {
        'identifier': 3,
        'asset': 'ETH',
        'balance': {'amount': '0.125', 'usd_value': '0'},
        'counterparty': '0xeB2629a2734e272Bcc07BDA959863f316F4bD4Cf',
        'event_identifier': '0x6c27ea39e5046646aaf24e1bb451caf466058278685102d89979197fdb89d007',
        'event_subtype': None,
        'event_type': 'receive',
        'location': 'blockchain',
        'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
        'notes': 'Receive 0.125 ETH 0xeB2629a2734e272Bcc07BDA959863f316F4bD4Cf from 0x6e15887E2CEC81434C16D587709f64603b39b545',  # noqa: E501
        'sequence_index': 0,
        'timestamp': 1642802651,
    }, 'customized': False}]
    assert entries[2]['decoded_events'] == tx3_events
    tx4_events = [{'entry': {
        'identifier': 6,
        'asset': A_USDT.identifier,
        'balance': {'amount': '1166', 'usd_value': '0'},
        'counterparty': '0xE21c192cD270286DBBb0fBa10a8B8D9957d431E5',
        'event_identifier': '0xccb6a445e136492b242d1c2c0221dc4afd4447c96601e88c156ec4d52e993b8f',
        'event_subtype': None,
        'event_type': 'receive',
        'location': 'blockchain',
        'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
        'notes': 'Receive 1166 USDT from 0xE21c192cD270286DBBb0fBa10a8B8D9957d431E5 to 0x6e15887E2CEC81434C16D587709f64603b39b545',  # noqa: E501
        'sequence_index': 385,
        'timestamp': 1642802286,
    }, 'customized': False}]
    assert entries[3]['decoded_events'] == tx4_events

    # Now let's edit 1 event and add another one
    event = tx2_events[1]['entry']
    event['asset'] = A_DAI.identifier
    event['balance'] = {'amount': '2500', 'usd_value': '2501.1'}
    event['event_type'] = 'spend'
    event['event_subtype'] = 'payback debt'
    event['notes'] = 'Edited event'
    tx2_events[1]['customized'] = True
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'historybaseentryresource'),
        json=event,
    )
    assert_simple_ok_response(response)

    tx4_events.insert(0, {'entry': {
        'asset': 'ETH',
        'balance': {'amount': '1', 'usd_value': '1500.1'},
        'counterparty': '0xE21c192cD270286DBBb0fBa10a8B8D9957d431E5',
        'event_identifier': '0xccb6a445e136492b242d1c2c0221dc4afd4447c96601e88c156ec4d52e993b8f',
        'event_subtype': 'deposit asset',
        'event_type': 'spend',
        'location': 'blockchain',
        'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
        'notes': 'Some kind of deposit',
        'sequence_index': 1,
        'timestamp': 1642802286,
    }, 'customized': True})
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'historybaseentryresource'),
        json=tx4_events[0]['entry'],
    )
    result = assert_proper_response_with_result(response)
    tx4_events[0]['entry']['identifier'] = result['identifier']

    # Now let's check DB tables to see they will get modified at purging
    with rotki.data.db.user_write() as cursor:
        for name, count in (
                ('ethereum_transactions', 4), ('ethereum_internal_transactions', 0),
                ('ethtx_receipts', 4), ('ethtx_receipt_log_topics', 6),
                ('ethtx_address_mappings', 4), ('evm_tx_mappings', 4),
                ('history_events_mappings', 2),
        ):
            assert cursor.execute(f'SELECT COUNT(*) from {name}').fetchone()[0] == count
        # Now purge all transactions of this address and see data is deleted BUT that
        # the edited/added event and all it's tied to is not
        dbethtx = DBEthTx(rotki.data.db)
        dbethtx.delete_transactions(cursor, ethereum_accounts[0])

        for name, count in (
                ('ethereum_transactions', 2), ('ethereum_internal_transactions', 0),
                ('ethtx_receipts', 2), ('ethtx_receipt_log_topics', 6),
                ('ethtx_address_mappings', 2), ('evm_tx_mappings', 0),
                ('history_events_mappings', 2),
        ):
            assert cursor.execute(f'SELECT COUNT(*) from {name}').fetchone()[0] == count
        dbevents = DBHistoryEvents(rotki.data.db)
        customized_events = dbevents.get_history_events(cursor, HistoryEventFilterQuery.make(), True)  # noqa: E501
        assert customized_events[0].serialize() == tx4_events[0]['entry']  # pylint: disable=unsubscriptable-object  # noqa: E501
        assert customized_events[1].serialize() == tx2_events[1]['entry']  # pylint: disable=unsubscriptable-object  # noqa: E501

        # requery all transactions and events. Assert they are the same (different event id though)
        result = query_transactions(rotki)
        entries = result['entries']
        assert len(entries) == 4

        assert_serialized_lists_equal(entries[0]['decoded_events'], tx1_events, ignore_keys='identifier')  # noqa: E501
        assert_serialized_lists_equal(entries[1]['decoded_events'], tx2_events, ignore_keys='identifier')  # noqa: E501
        assert_serialized_lists_equal(entries[2]['decoded_events'], tx3_events, ignore_keys='identifier')  # noqa: E501
        assert_serialized_lists_equal(entries[3]['decoded_events'], tx4_events, ignore_keys='identifier')  # noqa: E501

        # explicitly delete the customized (added/edited) transactions
        dbevents.delete_history_events_by_identifier([x.identifier for x in customized_events])  # noqa: E501
        # and now purge all transactions again and see everything is deleted
        dbethtx.delete_transactions(cursor, ethereum_accounts[0])
        for name in (
                'ethereum_transactions', 'ethereum_internal_transactions',
                'ethtx_receipts', 'ethtx_receipt_log_topics',
                'ethtx_address_mappings', 'evm_tx_mappings',
                'history_events_mappings',
        ):
            assert cursor.execute(f'SELECT COUNT(*) from {name}').fetchone()[0] == 0
        assert dbevents.get_history_events(cursor, HistoryEventFilterQuery.make(), True) == []


def test_events_filter_params(rotkehlchen_api_server, ethereum_accounts):
    """Tests filtering by transaction's events' properties
    Test cases:
        - Filtering by asset
        - Filtering by protocol (counterparty)
        - Filtering by both asset and a protocol
        - Transaction has multiple related events
        - Transaction has no related events
        - Multiple transactions are queried
    """
    logging.getLogger('rotkehlchen.externalapis.etherscan').disabled = True
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    tx1 = make_ethereum_transaction(tx_hash=b'1')
    tx2 = make_ethereum_transaction(tx_hash=b'2')
    tx3 = make_ethereum_transaction(tx_hash=b'3')
    event1 = make_ethereum_event(tx_hash=b'1', index=1, asset=A_ETH)
    event2 = make_ethereum_event(tx_hash=b'1', index=2, asset=A_ETH, counterparty='EXAMPLE_PROTOCOL')  # noqa: E501
    event3 = make_ethereum_event(tx_hash=b'1', index=3, asset=A_WETH, counterparty='EXAMPLE_PROTOCOL')  # noqa: E501
    event4 = make_ethereum_event(tx_hash=b'2', index=4, asset=A_WETH)
    dbethtx = DBEthTx(db)
    dbevents = DBHistoryEvents(db)
    with db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [tx1, tx2], relevant_address=ethereum_accounts[0])  # noqa: E501
        dbethtx.add_ethereum_transactions(cursor, [tx3], relevant_address=ethereum_accounts[1])
        dbevents.add_history_events(cursor, [event1, event2, event3, event4])

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ),
        json={
            'asset': A_WETH.serialize(),
            'protocols': [],
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='{"protocols": ["protocols have to be either not passed or contain at least one item"]}',  # noqa: E501
    )

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ),
        json={
            'asset': A_WETH.serialize(),
            'address': ethereum_accounts[0],
        },
    )
    result = assert_proper_response_with_result(response)
    expected = generate_tx_entries_response([(tx1, [event3]), (tx2, [event4])])
    assert result['entries'] == expected

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ),
        json={'asset': A_ETH.serialize()},
    )
    result = assert_proper_response_with_result(response)
    expected = generate_tx_entries_response([(tx1, [event1, event2])])
    assert result['entries'] == expected

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ),
        json={'asset': A_WETH.serialize()},
    )
    result = assert_proper_response_with_result(response)
    expected = generate_tx_entries_response([(tx1, [event3]), (tx2, [event4])])
    assert result['entries'] == expected

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ),
        json={'protocols': ['EXAMPLE_PROTOCOL']},
    )
    result = assert_proper_response_with_result(response)
    expected = generate_tx_entries_response([(tx1, [event2, event3])])
    assert result['entries'] == expected

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ),
        json={
            'asset': A_WETH.serialize(),
            'protocols': ['EXAMPLE_PROTOCOL'],
        },
    )
    result = assert_proper_response_with_result(response)
    expected = generate_tx_entries_response([(tx1, [event3])])
    assert result['entries'] == expected


def test_ignored_assets(rotkehlchen_api_server, ethereum_accounts):
    """This test tests that transactions with ignored assets are excluded when needed"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    db.add_to_ignored_assets(A_BTC)
    db.add_to_ignored_assets(A_DAI)
    dbethtx = DBEthTx(db)
    dbevents = DBHistoryEvents(db)
    tx1 = make_ethereum_transaction()
    tx2 = make_ethereum_transaction()
    tx3 = make_ethereum_transaction()
    event1 = make_ethereum_event(tx_hash=tx1.tx_hash, index=1, asset=A_ETH)
    event2 = make_ethereum_event(tx_hash=tx1.tx_hash, index=2, asset=A_BTC)
    event3 = make_ethereum_event(tx_hash=tx1.tx_hash, index=3, asset=A_MKR)
    event4 = make_ethereum_event(tx_hash=tx2.tx_hash, index=4, asset=A_DAI)
    with db.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [tx1, tx2, tx3], relevant_address=ethereum_accounts[0])  # noqa: E501
        dbevents.add_history_events(cursor, [event1, event2, event3, event4])

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ),
        json={
            'only_cache': True,  # only deal with the DB
            'exclude_ignored_assets': False,
        },
    )
    result = assert_proper_response_with_result(response)
    expected = generate_tx_entries_response(data=[
        (tx1, [event1, event2, event3]),
        (tx2, [event4]),
        (tx3, []),
    ])
    assert result['entries'] == expected
    assert result['entries_found'] == 3
    assert result['entries_total'] == 3
    assert result['entries_limit'] == FREE_ETH_TX_LIMIT

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumtransactionsresource',
        ),
        # Also testing here that default exclude_ignored_assets is True
        json={'only_cache': True},
    )
    result = assert_proper_response_with_result(response)
    expected = generate_tx_entries_response([(tx1, [event1, event3]), (tx3, [])])
    assert result['entries'] == expected
    assert result['entries_found'] == 2
    assert result['entries_total'] == 3
    assert result['entries_limit'] == FREE_ETH_TX_LIMIT
