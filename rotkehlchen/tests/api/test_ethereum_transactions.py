import os
import random
from contextlib import ExitStack
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import _Call, _patch, call, patch

import gevent
import pytest
import requests
from requests import Response

from rotkehlchen.accounting.types import EventAccountingRuleStatus
from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.monerium.constants import CPT_MONERIUM
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import CPT_GNOSIS_PAY
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH, A_EUR, A_MKR, A_USDT, A_WETH
from rotkehlchen.constants.limits import FREE_HISTORY_EVENTS_LIMIT
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import (
    EvmEventFilterQuery,
    EvmTransactionsFilterQuery,
    HistoryEventFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.fixtures.websockets import WebsocketReader
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.checks import assert_serialized_lists_equal
from rotkehlchen.tests.utils.constants import GRAPH_QUERY_CRED, TXHASH_HEX_TO_BYTES
from rotkehlchen.tests.utils.ethereum import (
    TEST_ADDR1,
    TEST_ADDR2,
    get_decoded_events_of_transaction,
    setup_ethereum_transactions_test,
    txreceipt_to_data,
)
from rotkehlchen.tests.utils.factories import (
    generate_events_response,
    make_eth_withdrawal_and_block_events,
    make_ethereum_event,
    make_ethereum_transaction,
    make_evm_address,
    make_evm_tx_hash,
)
from rotkehlchen.tests.utils.mock import MockResponse, mock_evm_chains_with_transactions
from rotkehlchen.types import (
    ApiKey,
    ChainID,
    ChecksumEvmAddress,
    EvmTransaction,
    ExternalService,
    ExternalServiceApiCredentials,
    Location,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen


EXPECTED_AFB7_TXS = [
    EvmTransaction(
        tx_hash=deserialize_evm_tx_hash('0x13684203a4bf07aaed0112983cb380db6004acac772af2a5d46cb2a28245fbad'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1439984408),
        block_number=111083,
        from_address=string_to_evm_address('0xC47Aaa860008be6f65B58c6C6E02a84e666EfE31'),
        to_address=string_to_evm_address('0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7'),
        value=37451082560000003241,
        gas=90000,
        gas_price=58471444665,
        gas_used=21000,
        input_data=b'',
        nonce=100,
    ), EvmTransaction(
        tx_hash=deserialize_evm_tx_hash('0xe58af420fd8430c061303e4c5bd2668fafbc0fd41078fa6aa01d7781c1dadc7a'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1461221228),
        block_number=1375816,
        from_address=string_to_evm_address('0x9e6316f44BaEeeE5d41A1070516cc5fA47BAF227'),
        to_address=string_to_evm_address('0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7'),
        value=389359660000000000,
        gas=250000,
        gas_price=20000000000,
        gas_used=21000,
        input_data=b'',
        nonce=326,
    ), EvmTransaction(
        tx_hash=deserialize_evm_tx_hash('0x0ae8b470b4a69c7f6905b9ec09f50c8772821080d11ba0acc83ac23a7ccb4ad8'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1461399856),
        block_number=1388248,
        from_address=string_to_evm_address('0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7'),
        to_address=string_to_evm_address('0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2'),
        value=37840020860000003241,
        gas=21068,
        gas_price=20000000000,
        gas_used=21068,
        input_data=b'\x01',
        nonce=0,
    ), EvmTransaction(
        tx_hash=deserialize_evm_tx_hash('0x2f6f167e32e9cb1bef40b92e831c3f1d1cd0348bb72dcc723bde94f51944ebd6'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1494458609),
        block_number=3685519,
        from_address=string_to_evm_address('0x4aD11d04CCd80A83d48096478b73D1E8e0ed49D6'),
        to_address=string_to_evm_address('0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7'),
        value=6000000000000000000,
        gas=21000,
        gas_price=21000000000,
        gas_used=21000,
        input_data=b'',
        nonce=1,
    ), EvmTransaction(
        tx_hash=deserialize_evm_tx_hash('0x5d81f937ad37349f89dc6e9926988855bb6c6e1e00c683ee3b7cb7d7b09b5567'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1494458861),
        block_number=3685532,
        from_address=string_to_evm_address('0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7'),
        to_address=string_to_evm_address('0xFa52274DD61E1643d2205169732f29114BC240b3'),
        value=5999300000000000000,
        gas=35000,
        gas_price=20000000000,
        gas_used=30981,
        input_data=b'\xf7eAv',
        nonce=1,
    )]

EXPECTED_4193_TXS = [EvmTransaction(
    tx_hash=deserialize_evm_tx_hash('0x2964f3a91408337b05aeb8f8f670f4107999be05376e630742404664c96a5c31'),
    chain_id=ChainID.ETHEREUM,
    timestamp=Timestamp(1439979000),
    block_number=110763,
    from_address=string_to_evm_address('0x976349705b839e2F5719387Fb27D2519d519da03'),
    to_address=string_to_evm_address('0x4193122032b38236825BBa166F42e54fc3F4A1EE'),
    value=100000000000000000,
    gas=90000,
    gas_price=57080649960,
    gas_used=21000,
    input_data=b'',
    nonce=30,
), EvmTransaction(
    tx_hash=deserialize_evm_tx_hash('0xb99a6e0b40f38c4887617bc1df560fde1d0456b712cb2bb1b52fdb8880d3cd74'),
    chain_id=ChainID.ETHEREUM,
    timestamp=Timestamp(1439984825),
    block_number=111111,
    from_address=string_to_evm_address('0x4193122032b38236825BBa166F42e54fc3F4A1EE'),
    to_address=string_to_evm_address('0x1177848589133f5C4E69EdFcb18bBCd9cACE72D1'),
    value=20000000000000000,
    gas=90000,
    gas_price=59819612547,
    gas_used=21000,
    input_data=b'',
    nonce=0,
), EvmTransaction(
    tx_hash=deserialize_evm_tx_hash('0xfadf1f12281ee2c0311055848b4ffc0046ac80afae4a9d3640b5f57bb8a7795a'),
    chain_id=ChainID.ETHEREUM,
    timestamp=Timestamp(1507291254),
    block_number=4341870,
    from_address=string_to_evm_address('0x4193122032b38236825BBa166F42e54fc3F4A1EE'),
    to_address=string_to_evm_address('0x2B06E2ea21e184589853225888C93b9b8e0642f6'),
    value=78722788136513000,
    gas=21000,
    gas_price=1000000000,
    gas_used=21000,
    input_data=b'',
    nonce=1,
)]


def assert_txlists_equal(l1: list[EvmTransaction], l2: list[EvmTransaction]) -> None:
    l1.sort(key=lambda x: x.timestamp)
    l2.sort(key=lambda x: x.timestamp)

    for idx, tx1 in enumerate(l1):
        for attr_name in tx1.__annotations__:
            if attr_name == 'db_id':
                continue

            assert getattr(tx1, attr_name) == getattr(l2[idx], attr_name)


def query_events(
        server: 'APIServer',
        json: dict[str, Any],
        expected_num_with_grouping: int,
        expected_totals_with_grouping: int,
        entries_limit: int = -1,
) -> list[dict[str, Any]]:
    """Query history events as frontend would have, with grouped identifiers

    First query all events with grouping enabled. Then if any events have more,
    take those events and ask for the extras. Return the full set.
    """
    extra_json = json.copy() | {'group_by_event_ids': True}
    response = requests.post(
        api_url_for(server, 'historyeventresource'),
        json=extra_json,
    )
    result = assert_proper_sync_response_with_result(response)
    entries = result['entries']
    assert result['entries_limit'] == entries_limit
    assert result['entries_found'] == expected_num_with_grouping
    assert result['entries_total'] == expected_totals_with_grouping
    assert len(entries) == expected_num_with_grouping

    augmented_entries = []
    for entry in entries:
        if entry['grouped_events_num'] != 1:
            extra_json = json.copy() | {'event_identifiers': [entry['entry']['event_identifier']]}
            response = requests.post(
                api_url_for(server, 'historyeventresource'),
                json=extra_json,
            )
            result = assert_proper_sync_response_with_result(response)
            augmented_entries.extend(result['entries'])
        else:
            entry.pop('grouped_events_num')
            augmented_entries.append(entry)

    return remove_added_event_fields(augmented_entries)


def assert_force_redecode_txns_works(api_server: 'APIServer') -> None:
    rotki = api_server.rest_api.rotkehlchen
    get_eth_txns_patch = patch.object(
        rotki.chains_aggregator.ethereum.transactions_decoder.transactions,
        'get_or_create_transaction',
        wraps=rotki.chains_aggregator.ethereum.transactions_decoder.transactions.get_or_create_transaction,
    )
    get_or_decode_txn_events_patch = patch.object(
        rotki.chains_aggregator.ethereum.transactions_decoder,
        '_get_or_decode_transaction_events',
        wraps=rotki.chains_aggregator.ethereum.transactions_decoder._get_or_decode_transaction_events,
    )
    with ExitStack() as stack:
        function_call_counters: list = []
        function_call_counters.extend((
            stack.enter_context(get_or_decode_txn_events_patch),
            stack.enter_context(get_eth_txns_patch)),
        )

        response = requests.post(
            api_url_for(
                api_server,
                'evmpendingtransactionsdecodingresource',
            ), json={
                'async_query': False,
                'ignore_cache': True,
                'chains': ['ethereum'],
            },
        )
        assert_proper_response(response)
        for fn in function_call_counters:
            assert fn.call_count == 14


def _write_transactions_to_db(
        db: 'DBHandler',
        transactions: list[EvmTransaction],
        extra_transactions: list[EvmTransaction],
        ethereum_accounts: list[ChecksumEvmAddress],
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> None:
    """Common function to replicate writing transactions in the DB for tests in this file"""
    with db.user_write() as cursor:
        dbevmtx = DBEvmTx(db)
        dbevmtx.add_evm_transactions(cursor, transactions, relevant_address=ethereum_accounts[0])
        dbevmtx.add_evm_transactions(cursor, extra_transactions, relevant_address=ethereum_accounts[1])  # noqa: E501
        # Also make sure to update query ranges so as not to query etherscan at all
        for address in ethereum_accounts:
            for prefix in (SupportedBlockchain.ETHEREUM.to_range_prefix('txs'), SupportedBlockchain.ETHEREUM.to_range_prefix('internaltxs'), SupportedBlockchain.ETHEREUM.to_range_prefix('tokentxs')):  # noqa: E501
                DBQueryRanges(db).update_used_query_range(
                    write_cursor=cursor,
                    location_string=f'{prefix}_{address}',
                    queried_ranges=[(start_ts, end_ts)],
                )


def remove_added_event_fields(returned_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """removes any fields added to events during serialization"""
    for event in returned_events:
        event.pop('missing_accounting_rule', None)
    return returned_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2024-02-07 23:00:00 GMT')
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xaFB7ed3beBE50E0b62Fa862FAba93e7A46e59cA7',
    '0x4193122032b38236825BBa166F42e54fc3F4A1EE',
]])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1.5)])
def test_query_transactions(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that querying the ethereum transactions endpoint works as expected.
    Also tests that requesting for transaction decoding works.

    This test uses real data.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # Check that we get all transactions
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ), json={'async_query': True},
    )
    task_id = assert_ok_async_response(response)
    outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert outcome['message'] == ''
    assert outcome['result'] is True

    dbevmtx = DBEvmTx(rotki.data.db)
    with rotki.data.db.conn.read_ctx() as cursor:
        transactions = dbevmtx.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(), True)  # noqa: E501

    assert_txlists_equal(transactions[0:8], EXPECTED_AFB7_TXS + EXPECTED_4193_TXS)

    hashes = [EXPECTED_AFB7_TXS[0].tx_hash.hex(), EXPECTED_4193_TXS[0].tx_hash.hex()]
    for tx_hash in hashes:
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'evmtransactionsresource',
            ), json={
                'async_query': True,
                'transactions': [{
                    'evm_chain': 'ethereum',
                    'tx_hash': tx_hash,
                }],
            },
        )

        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['message'] == ''
        result = outcome['result']
        assert result is True

    dbevmtx = DBEvmTx(rotki.data.db)
    dbevents = DBHistoryEvents(rotki.data.db)
    event_ids = set()
    with rotki.data.db.conn.read_ctx() as cursor:
        for tx_hash_hex in hashes:
            receipt = dbevmtx.get_receipt(cursor, deserialize_evm_tx_hash(hexstring_to_bytes(tx_hash_hex)), ChainID.ETHEREUM)  # noqa: E501
            assert isinstance(receipt, EvmTxReceipt) and receipt.tx_hash == hexstring_to_bytes(tx_hash_hex)  # noqa: E501
            events = dbevents.get_history_events(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(
                    tx_hashes=[TXHASH_HEX_TO_BYTES[tx_hash_hex]],
                ),
                has_premium=True,  # for this function we don't limit. We only limit txs.
            )
            event_ids.add(events[0].identifier)
            assert len(events) == 1

    assert_force_redecode_txns_works(rotkehlchen_api_server)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_request_transaction_decoding_errors(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that the request transaction decoding endpoint handles input errors"""
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'evmtransactionsresource',
        ), json={
            'async_query': False,
            'transactions': [{
                'evm_chain': 'ethereum',
                'tx_hash': 1,
            }],
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Transaction hash should be a string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'evmtransactionsresource',
        ), json={
            'async_query': False,
            'transactions': [{
                'evm_chain': 'ethereum',
                'tx_hash': 'dasd',
            }],
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Could not turn transaction hash dasd to bytes',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'evmtransactionsresource',
        ), json={
            'async_query': False,
            'transactions': [{
                'evm_chain': 'ethereum',
                'tx_hash': '0x34af01',
            }],
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='EVM transaction hashes should be 32 bytes in length',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    nonexisting_hash = '0x1c4f300f4d9e6436825ed0dc85716df4648a64a29570280c6e6261acf041aa41'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'evmtransactionsresource',
        ), json={
            'async_query': False,
            'transactions': [{
                'evm_chain': 'ethereum',
                'tx_hash': nonexisting_hash,
            }],
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'hash {nonexisting_hash} does not correspond to a transaction',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='SLOW TEST -- run locally from time to time',
)
@pytest.mark.parametrize('ethereum_accounts', [['0xe62193Bc1c340EF2205C0Bd71691Fad5e5072253']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_over_10k_transactions(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that querying for an address with over 10k transactions works

    This test uses real etherscan queries and an address that we found that has > 10k transactions.

    Etherscan has a limit for 1k transactions per query and we need to make
    sure that we properly pull all data by using pagination
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    original_get = requests.get

    def mock_some_etherscan_queries(etherscan: Etherscan) -> _patch:
        """Just hit etherscan for the actual transactions and mock all else.
        This test just needs to see that pagination works on the tx endpoint
        """
        def mocked_request_dict(url: str, *_args: Any, **_kwargs: Any) -> Response | MockResponse:
            if '=txlistinternal&' in url or '=tokentx&' in url:
                # don't return any internal or token transactions
                payload = '{"status":"1","message":"OK","result":[]}'
            elif '=getblocknobytime&' in url or '=txlist&' in url:
                # we don't really care about this in this test so return original
                return original_get(url)
            else:
                raise AssertionError(f'Unexpected etherscan query {url} at test mock')
            return MockResponse(200, payload)

        return patch.object(etherscan.session, 'get', wraps=mocked_request_dict)

    expected_at_least = 16097  # 30/08/2020
    with mock_some_etherscan_queries(rotki.chains_aggregator.ethereum.node_inquirer.etherscan):
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'blockchaintransactionsresource',
            ),
        )

    result = assert_proper_sync_response_with_result(response)
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


@pytest.mark.vcr(filter_query_parameters=['apikey'], allow_playback_repeats=True)
@pytest.mark.freeze_time('2024-02-07 23:00:00 GMT')
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [[  # just 2 random addresses
    '0x21c4E3dDf1b6EcbC32C883dbe2e360fCb5848689',
    '0xf2C7D395Ac78FB6868aB449B64969B3500938A4d',
]])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_transactions_removed_address(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Make sure that if an address is removed so are the transactions from the DB.
    Also assure that a transaction is not deleted so long as it touches a tracked
    address, even if one of the touched address is removed.
    """
    start_ts = Timestamp(0)
    end_ts = Timestamp(1598453214)
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    transactions = [EvmTransaction(
        tx_hash=deserialize_evm_tx_hash(b'1'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(0),
        block_number=0,
        from_address=ethereum_accounts[0],
        to_address=make_evm_address(),
        value=1,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=0,
    ), EvmTransaction(
        tx_hash=deserialize_evm_tx_hash(b'2'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(0),
        block_number=0,
        from_address=ethereum_accounts[0],
        to_address=make_evm_address(),
        value=1,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=1,
    ), EvmTransaction(  # should remain after deleting account[0]
        tx_hash=deserialize_evm_tx_hash(b'3'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(0),
        block_number=0,
        from_address=make_evm_address(),
        to_address=ethereum_accounts[1],
        value=1,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=55,
    ), EvmTransaction(  # should remain after deleting account[0]
        tx_hash=deserialize_evm_tx_hash(b'4'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(0),
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
        tx_hash=deserialize_evm_tx_hash(b'5'),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(0),
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

    _write_transactions_to_db(db=db, transactions=transactions[0:2] + transactions[3:], extra_transactions=transactions[2:], ethereum_accounts=ethereum_accounts, start_ts=start_ts, end_ts=end_ts)  # noqa: E501

    # Now remove the first account
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [ethereum_accounts[0]]})
    assert_proper_sync_response_with_result(response)

    # Check that only the 3 remaining transactions from the other account are returned
    dbevmtx = DBEvmTx(rotki.data.db)
    with rotki.data.db.conn.read_ctx() as cursor:
        transactions = dbevmtx.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(), True)  # noqa: E501
    assert len(transactions) == 3


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_transaction_same_hash_same_nonce_two_tracked_accounts(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Make sure that if we track two addresses and they send one transaction
    to each other it's not counted as duplicate in the DB but is returned
    every time by both addresses"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    def mock_etherscan_transaction_response(
            etherscan: Etherscan,
            eth_accounts: list['ChecksumEvmAddress'],
    ) -> _patch:
        def mocked_request_dict(url: str, params: dict[str, str], *_args: Any, **_kwargs: Any) -> MockResponse:  # noqa: E501

            addr1_tx = f"""{{"blockNumber":"1","timeStamp":"1","hash":"0x9c81f44c29ff0226f835cd0a8a2f2a7eca6db52a711f8211b566fd15d3e0e8d4","nonce":"0","blockHash":"0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159","transactionIndex":"0","from":"{eth_accounts[0]}","to":"{eth_accounts[1]}","value":"1","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"0x","contractAddress":"","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"1"}}"""  # noqa: E501
            addr2_txs = f"""{addr1_tx}, {{"blockNumber":"2","timeStamp":"2","hash":"0x1c81f54c29ff0226f835cd0a2a2f2a7eca6db52a711f8211b566fd15d3e0e8d4","nonce":"1","blockHash":"0xd1cabad2adab0b56ea632c386ea19403680571e682c62cb589b5abcd76de2159","transactionIndex":"0","from":"{eth_accounts[1]}","to":"{make_evm_address()}","value":"1","gas":"2000000","gasPrice":"10000000000000","isError":"0","txreceipt_status":"","input":"0x","contractAddress":"","cumulativeGasUsed":"1436963","gasUsed":"1436963","confirmations":"1"}}"""  # noqa: E501
            if (action := params.get('action')) in ('txlistinternal', 'tokentx'):
                # don't return any internal or token transactions
                payload = '{"status":"1","message":"OK","result":[]}'
            elif action == 'txlist':
                if (address := params.get('address')) == eth_accounts[0]:
                    tx_str = addr1_tx
                elif address == eth_accounts[1]:
                    tx_str = addr2_txs
                else:
                    raise AssertionError(
                        'Requested etherscan transactions for unknown address in tests',
                    )
                payload = f'{{"status":"1","message":"OK","result":[{tx_str}]}}'
            elif action == 'getblocknobytime':
                # we don't really care about this so just return whatever
                payload = '{"status":"1","message":"OK","result": "1"}'
            else:
                raise AssertionError('Got in unexpected section during test')

            return MockResponse(200, payload)

        return patch.object(etherscan.session, 'get', wraps=mocked_request_dict)

    with mock_etherscan_transaction_response(rotki.chains_aggregator.ethereum.node_inquirer.etherscan, ethereum_accounts):  # noqa: E501
        # Check that we get transaction both when we query all accounts and each one individually
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'blockchaintransactionsresource',
            ),
        )
        assert_simple_ok_response(response)
        dbevmtx = DBEvmTx(rotki.data.db)
        with rotki.data.db.conn.read_ctx() as cursor:
            transactions = dbevmtx.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(), True)  # noqa: E501

        assert len(transactions) == 2


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2022-01-21 22:19:26 GMT')
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [['0x6e15887E2CEC81434C16D587709f64603b39b545']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_transactions_check_decoded_events(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that transactions and associated events can be queried via their respective endpoints.

    Also test that if an event is edited or added to a transaction that transaction and
    event are not purged when the ethereum transactions are purged. And if transactions
    are required the edited events are there.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    start_ts = Timestamp(0)
    end_ts = Timestamp(1642803566)  # time of test writing
    dbevents = DBHistoryEvents(rotki.data.db)

    def query_transactions(rotki: 'Rotkehlchen') -> None:
        rotki.chains_aggregator.ethereum.transactions.single_address_query_transactions(
            address=ethereum_accounts[0],
            start_ts=start_ts,
            end_ts=end_ts,
        )
        assert rotki.task_manager is not None
        with mock_evm_chains_with_transactions():
            rotki.task_manager._maybe_schedule_evm_txreceipts()
            gevent.joinall(rotki.greenlet_manager.greenlets)
            rotki.task_manager._maybe_decode_evm_transactions()
            gevent.joinall(rotki.greenlet_manager.greenlets)
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'blockchaintransactionsresource'),
            json={'from_timestamp': start_ts, 'to_timestamp': end_ts},
        )
        assert_simple_ok_response(response)

    query_transactions(rotki)
    dbevmtx = DBEvmTx(rotki.data.db)
    with rotki.data.db.conn.read_ctx() as cursor:
        transactions = dbevmtx.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(), True)  # noqa: E501

    assert len(transactions) == 4

    returned_events = query_events(rotkehlchen_api_server, json={'location': 'ethereum'}, expected_num_with_grouping=4, expected_totals_with_grouping=4)  # noqa: E501
    tx1_events: list[dict] = [{
        'entry': {
            'identifier': 5,
            'entry_type': 'evm event',
            'asset': 'ETH',
            'amount': '0.00863351371344',
            'counterparty': CPT_GAS,
            'address': None,
            'event_identifier': '10x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f',  # noqa: E501
            'event_subtype': 'fee',
            'event_type': 'spend',
            'location': 'ethereum',
            'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
            'user_notes': 'Burn 0.00863351371344 ETH for gas',
            'product': None,
            'sequence_index': 0,
            'timestamp': 1642802807000,
            'tx_hash': '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f',
            'extra_data': None,
        },
        'event_accounting_rule_status': 'not processed',
    }, {
        'entry': {
            'identifier': 6,
            'entry_type': 'evm event',
            'asset': 'ETH',
            'amount': '0.096809163374771208',
            'counterparty': None,
            'address': '0xA090e606E30bD747d4E6245a1517EbE430F0057e',
            'event_identifier': '10x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f',  # noqa: E501
            'event_subtype': 'none',
            'event_type': 'spend',
            'location': 'ethereum',
            'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
            'user_notes': 'Send 0.096809163374771208 ETH to 0xA090e606E30bD747d4E6245a1517EbE430F0057e',  # noqa: E501
            'product': None,
            'sequence_index': 1,
            'timestamp': 1642802807000,
            'tx_hash': '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f',
            'extra_data': None,
        },
        'event_accounting_rule_status': 'not processed',
    }]
    assert returned_events[:2] == tx1_events
    tx2_events: list[dict] = [{
        'entry': {
            'identifier': 3,
            'entry_type': 'evm event',
            'asset': 'ETH',
            'address': None,
            'amount': '0.017690836625228792',
            'counterparty': CPT_GAS,
            'event_identifier': '10x38ed9c2d4f0855f2d88823d502f8794b993d28741da48724b7dfb559de520602',  # noqa: E501
            'event_subtype': 'fee',
            'event_type': 'spend',
            'location': 'ethereum',
            'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
            'user_notes': 'Burn 0.017690836625228792 ETH for gas',
            'product': None,
            'sequence_index': 0,
            'timestamp': 1642802735000,
            'tx_hash': '0x38ed9c2d4f0855f2d88823d502f8794b993d28741da48724b7dfb559de520602',
            'extra_data': None,
        },
        'event_accounting_rule_status': 'not processed',
    }, {
        'entry': {
            'identifier': 4,
            'entry_type': 'evm event',
            'asset': A_USDT.identifier,
            'address': '0xb5d85CBf7cB3EE0D56b3bB207D5Fc4B82f43F511',
            'amount': '1166',
            'counterparty': None,
            'event_identifier': '10x38ed9c2d4f0855f2d88823d502f8794b993d28741da48724b7dfb559de520602',  # noqa: E501
            'event_subtype': 'none',
            'event_type': 'spend',
            'location': 'ethereum',
            'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
            'user_notes': 'Send 1166 USDT from 0x6e15887E2CEC81434C16D587709f64603b39b545 to 0xb5d85CBf7cB3EE0D56b3bB207D5Fc4B82f43F511',  # noqa: E501
            'product': None,
            'sequence_index': 308,
            'timestamp': 1642802735000,
            'tx_hash': '0x38ed9c2d4f0855f2d88823d502f8794b993d28741da48724b7dfb559de520602',
            'extra_data': None,
        },
        'event_accounting_rule_status': 'not processed',
    }]
    assert returned_events[2:4] == tx2_events
    tx3_events: list[dict] = [{
        'entry': {
            'identifier': 2,
            'entry_type': 'evm event',
            'asset': 'ETH',
            'address': '0xeB2629a2734e272Bcc07BDA959863f316F4bD4Cf',
            'amount': '0.125',
            'counterparty': None,
            'event_identifier': '10x6c27ea39e5046646aaf24e1bb451caf466058278685102d89979197fdb89d007',  # noqa: E501
            'event_subtype': 'none',
            'event_type': 'receive',
            'location': 'ethereum',
            'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
            'user_notes': 'Receive 0.125 ETH from 0xeB2629a2734e272Bcc07BDA959863f316F4bD4Cf',
            'product': None,
            'sequence_index': 0,
            'timestamp': 1642802651000,
            'tx_hash': '0x6c27ea39e5046646aaf24e1bb451caf466058278685102d89979197fdb89d007',
            'extra_data': None,
        },
        'event_accounting_rule_status': 'not processed',
    }]
    assert returned_events[4:5] == tx3_events
    tx4_events: list[dict] = [{
        'entry': {
            'identifier': 1,
            'entry_type': 'evm event',
            'asset': A_USDT.identifier,
            'address': '0xE21c192cD270286DBBb0fBa10a8B8D9957d431E5',
            'amount': '1166',
            'counterparty': None,
            'event_identifier': '10xccb6a445e136492b242d1c2c0221dc4afd4447c96601e88c156ec4d52e993b8f',  # noqa: E501
            'event_subtype': 'none',
            'event_type': 'receive',
            'location': 'ethereum',
            'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
            'user_notes': 'Receive 1166 USDT from 0xE21c192cD270286DBBb0fBa10a8B8D9957d431E5 to 0x6e15887E2CEC81434C16D587709f64603b39b545',  # noqa: E501
            'product': None,
            'sequence_index': 385,
            'timestamp': 1642802286000,
            'tx_hash': '0xccb6a445e136492b242d1c2c0221dc4afd4447c96601e88c156ec4d52e993b8f',
            'extra_data': None,
        },
        'event_accounting_rule_status': 'not processed',
    }]
    assert returned_events[5:6] == tx4_events

    # Now let's edit 1 event and add another one
    event = tx2_events[1]['entry']
    event['asset'] = A_DAI.identifier
    event['amount'] = '2500'
    event['event_type'] = 'spend'
    event['event_subtype'] = 'payback debt'
    event['user_notes'] = 'Edited event'
    tx2_events[1]['customized'] = True
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json={key: value for key, value in event.items() if key != 'event_identifier'},
    )
    assert_simple_ok_response(response)

    tx4_events.insert(0, {
        'entry': {
            'entry_type': 'evm event',
            'asset': 'ETH',
            'address': '0xE21c192cD270286DBBb0fBa10a8B8D9957d431E5',
            'amount': '1',
            'counterparty': CPT_CURVE,
            'event_identifier': '10xccb6a445e136492b242d1c2c0221dc4afd4447c96601e88c156ec4d52e993b8f',  # noqa: E501
            'event_subtype': 'deposit asset',
            'event_type': 'deposit',
            'location': 'ethereum',
            'location_label': '0x6e15887E2CEC81434C16D587709f64603b39b545',
            'user_notes': 'Some kind of deposit',
            'product': 'pool',
            'sequence_index': 1,
            'timestamp': 1642802286000,
            'tx_hash': '0xccb6a445e136492b242d1c2c0221dc4afd4447c96601e88c156ec4d52e993b8f',
            'extra_data': None,
        },
        'customized': True,
        'event_accounting_rule_status': 'not processed',
    })
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json={key: value for key, value in tx4_events[0]['entry'].items() if key != 'event_identifier'},  # noqa: E501
    )
    result = assert_proper_sync_response_with_result(response)
    tx4_events[0]['entry']['identifier'] = result['identifier']

    # Also add a cache entry for a transaction
    with rotki.data.db.user_write() as write_cursor:
        random_receiver_in_cache = make_evm_address()
        random_user_address = make_evm_address()
        rotki.data.db.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.EXTRA_INTERNAL_TX,
            value=random_user_address,
            chain_id=1,
            tx_hash='0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f',
            receiver=random_receiver_in_cache,
        )
        assert rotki.data.db.get_dynamic_cache(  # ensure it's properly set
            cursor=write_cursor,
            name=DBCacheDynamic.EXTRA_INTERNAL_TX,
            chain_id=1,
            tx_hash='0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f',
            receiver=random_receiver_in_cache,
        ) == random_user_address

    # Now let's check DB tables to see they will get modified at purging
    with rotki.data.db.conn.read_ctx() as cursor:
        for name, count in (
                ('evm_transactions', 4), ('evm_internal_transactions', 0),
                ('evmtx_receipts', 4), ('evmtx_receipt_log_topics', 6),
                ('evmtx_address_mappings', 4), ('evm_tx_mappings', 4),
                ('history_events_mappings', 2),
        ):
            assert cursor.execute(f'SELECT COUNT(*) from {name}').fetchone()[0] == count

    # Now purge all transactions of this address and see data is deleted BUT that
    # the edited/added event and all it's tied to is not
    dbevmtx = DBEvmTx(rotki.data.db)
    with rotki.data.db.user_write() as write_cursor:
        dbevmtx.delete_transactions(write_cursor, ethereum_accounts[0], SupportedBlockchain.ETHEREUM)  # noqa: E501

    with rotki.data.db.conn.read_ctx() as cursor:
        for name, count in (
                ('evm_transactions', 2), ('evm_internal_transactions', 0),
                ('evmtx_receipts', 2), ('evmtx_receipt_log_topics', 6),
                ('evmtx_address_mappings', 2), ('evm_tx_mappings', 0),
                ('history_events_mappings', 2),
        ):
            assert cursor.execute(f'SELECT COUNT(*) from {name}').fetchone()[0] == count
        customized_events = dbevents.get_history_events(cursor, EvmEventFilterQuery.make(), True)

        # Check if related cache is removed
        assert rotki.data.db.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.EXTRA_INTERNAL_TX,
            chain_id=1,
            tx_hash='0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f',
            receiver=random_receiver_in_cache,
        ) is None

    assert customized_events[0].serialize() == tx4_events[0]['entry']
    assert customized_events[1].serialize() == tx2_events[1]['entry']
    # requery all transactions and events. Assert they are the same (different event id though)
    query_transactions(rotki)
    with rotki.data.db.conn.read_ctx() as cursor:
        transactions = dbevmtx.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(), True)  # noqa: E501

    assert len(transactions) == 4
    returned_events = query_events(rotkehlchen_api_server, json={'location': 'ethereum'}, expected_num_with_grouping=4, expected_totals_with_grouping=4)  # noqa: E501

    assert len(returned_events) == 7
    assert_serialized_lists_equal(returned_events[0:2], tx1_events, ignore_keys=['identifier'])
    assert_serialized_lists_equal(remove_added_event_fields(returned_events[2:4]), tx2_events, ignore_keys=['identifier'])  # noqa: E501
    assert_serialized_lists_equal(returned_events[4:5], tx3_events, ignore_keys=['identifier'])
    assert_serialized_lists_equal(returned_events[5:7], tx4_events, ignore_keys=['identifier'])

    # explicitly delete the customized (added/edited) transactions
    dbevents.delete_history_events_by_identifier([x.identifier for x in customized_events if x.identifier is not None])  # noqa: E501

    with rotki.data.db.user_write() as write_cursor:
        # and now purge all transactions again and see everything is deleted
        dbevmtx.delete_transactions(write_cursor, ethereum_accounts[0], SupportedBlockchain.ETHEREUM)  # noqa: E501

    with rotki.data.db.conn.read_ctx() as cursor:
        for name in (
                'evm_transactions', 'evm_internal_transactions',
                'evmtx_receipts', 'evmtx_receipt_log_topics',
                'evmtx_address_mappings', 'evm_tx_mappings',
                'history_events_mappings',
        ):
            assert cursor.execute(f'SELECT COUNT(*) from {name}').fetchone()[0] == 0
        assert dbevents.get_history_events(cursor, EvmEventFilterQuery.make(), True) == []


@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@patch.object(EthereumTransactions, '_get_transactions_for_range', lambda *args, **kargs: None)
@patch.object(EthereumTransactions, '_get_internal_transactions_for_ranges', lambda *args, **kargs: None)  # noqa: E501
@patch.object(EthereumTransactions, '_get_erc20_transfers_for_ranges', lambda *args, **kargs: None)
@pytest.mark.parametrize('start_with_valid_premium', [True])  # TODO: Test for whichever filters we allow in free  # noqa: E501
def test_events_filter_params(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        start_with_valid_premium: bool,
) -> None:
    """Tests filtering by transaction's events' properties
    Test cases:
        - Filtering by asset
        - Filtering by protocol (counterparty)
        - Filtering by both asset and a protocol
        - Transaction has multiple related events
        - Transaction has no related events
        - Multiple transactions are queried
        - Filtering by event type
        - Filtering by event subtype
    since the transactions filtered here are created in here and don't come from etherscan
    remove any external query that is not needed
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    tx1 = make_ethereum_transaction(tx_hash=b'1', timestamp=Timestamp(1))
    tx2 = make_ethereum_transaction(tx_hash=b'2', timestamp=Timestamp(2))
    tx3 = make_ethereum_transaction(tx_hash=b'3', timestamp=Timestamp(3))
    tx4 = make_ethereum_transaction(tx_hash=b'4', timestamp=Timestamp(4))
    test_contract_address = make_evm_address()
    event1 = make_ethereum_event(tx_hash=b'1', index=1, asset=A_ETH, timestamp=TimestampMS(1), location_label=ethereum_accounts[0], product=EvmProduct.STAKING)  # noqa: E501
    event2 = make_ethereum_event(tx_hash=b'1', index=2, asset=A_ETH, counterparty='EXAMPLE_PROTOCOL', timestamp=TimestampMS(1), location_label=ethereum_accounts[0])  # noqa: E501
    event3 = make_ethereum_event(tx_hash=b'1', index=3, asset=A_WETH, counterparty='EXAMPLE_PROTOCOL', timestamp=TimestampMS(1), location_label=ethereum_accounts[0])  # noqa: E501
    event4 = make_ethereum_event(tx_hash=b'2', index=4, asset=A_WETH, timestamp=TimestampMS(2), location_label=ethereum_accounts[0])  # noqa: E501
    event5 = make_ethereum_event(tx_hash=b'4', index=5, asset=A_DAI, event_type=HistoryEventType.STAKING, event_subtype=HistoryEventSubType.DEPOSIT_ASSET, timestamp=TimestampMS(4), location_label=ethereum_accounts[2], address=test_contract_address)  # noqa: E501
    event6 = make_ethereum_event(tx_hash=b'4', index=6, asset=A_DAI, event_type=HistoryEventType.STAKING, event_subtype=HistoryEventSubType.REMOVE_ASSET, timestamp=TimestampMS(4), location_label=ethereum_accounts[2])  # noqa: E501
    dbevmtx = DBEvmTx(db)
    dbevents = DBHistoryEvents(db)
    with db.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [tx1, tx2], relevant_address=ethereum_accounts[0])
        dbevmtx.add_evm_transactions(cursor, [tx3], relevant_address=ethereum_accounts[1])
        dbevmtx.add_evm_transactions(cursor, [tx4], relevant_address=ethereum_accounts[2])
        dbevents.add_history_events(cursor, [event1, event2, event3, event4, event5, event6])

    for attribute in ('counterparties', 'products'):
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'historyeventresource',
            ),
            json={
                'location': 'ethereum',
                'asset': A_WETH.serialize(),
                attribute: [],
            },
        )
        assert_error_response(
            response=response,
            contained_in_msg=f'{{"{attribute}": ["List cant be empty"]}}',
        )

    entries_limit = -1 if start_with_valid_premium else FREE_HISTORY_EVENTS_LIMIT
    returned_events = query_events(
        rotkehlchen_api_server,
        json={
            'location': 'ethereum',
            'asset': A_WETH.serialize(),
            'location_labels': [ethereum_accounts[0]],
        },
        expected_num_with_grouping=2,
        expected_totals_with_grouping=3,
        entries_limit=entries_limit,
    )
    expected = generate_events_response([event4, event3])
    assert returned_events == expected

    returned_events = query_events(
        rotkehlchen_api_server,
        json={'asset': A_ETH.serialize(), 'location': 'ethereum'},
        expected_num_with_grouping=1,
        expected_totals_with_grouping=3,
        entries_limit=entries_limit,
    )
    expected = generate_events_response([event1, event2])
    assert returned_events == expected

    returned_events = query_events(
        rotkehlchen_api_server,
        json={'asset': A_WETH.serialize(), 'location': 'ethereum'},
        expected_num_with_grouping=2,
        expected_totals_with_grouping=3,
        entries_limit=entries_limit,
    )
    expected = generate_events_response([event4, event3])
    assert returned_events == expected

    returned_events = query_events(
        rotkehlchen_api_server,
        json={'counterparties': ['EXAMPLE_PROTOCOL'], 'location': 'ethereum'},
        expected_num_with_grouping=1,
        expected_totals_with_grouping=3,
        entries_limit=entries_limit,
    )
    expected = generate_events_response([event2, event3])
    assert returned_events == expected

    returned_events = query_events(
        rotkehlchen_api_server,
        json={
            'location': 'ethereum',
            'asset': A_WETH.serialize(),
            'counterparties': ['EXAMPLE_PROTOCOL'],
        },
        expected_num_with_grouping=1,
        expected_totals_with_grouping=3,
        entries_limit=entries_limit,
    )
    expected = generate_events_response([event3])
    assert returned_events == expected

    # test that filtering by type works
    returned_events = query_events(
        rotkehlchen_api_server,
        json={
            'location': 'ethereum',
            'event_types': ['staking'],
        },
        expected_num_with_grouping=1,
        expected_totals_with_grouping=3,
        entries_limit=entries_limit,
    )
    expected = generate_events_response(
        data=[event5, event6],
        accounting_status=EventAccountingRuleStatus.NOT_PROCESSED,
    )
    assert returned_events == expected

    # test that filtering by subtype works
    returned_events = query_events(
        rotkehlchen_api_server,
        json={
            'location': 'ethereum',
            'event_types': ['staking'],
            'event_subtypes': ['deposit_asset'],
        },
        expected_num_with_grouping=1,
        expected_totals_with_grouping=3,
        entries_limit=entries_limit,
    )
    expected = generate_events_response(
        data=[event5],
        accounting_status=EventAccountingRuleStatus.NOT_PROCESSED,
    )
    assert returned_events == expected

    # test filtering by products
    returned_events = query_events(
        rotkehlchen_api_server,
        json={
            'products': [EvmProduct.STAKING.serialize()],
        },
        expected_num_with_grouping=1,
        expected_totals_with_grouping=3,
        entries_limit=entries_limit,
    )
    expected = generate_events_response([event1])
    assert returned_events == expected

    # test filtering by address
    returned_events = query_events(
        rotkehlchen_api_server,
        json={
            'addresses': [test_contract_address],
        },
        expected_num_with_grouping=1,
        expected_totals_with_grouping=3,
        entries_limit=entries_limit,
    )
    expected = generate_events_response(
        data=[event5],
        accounting_status=EventAccountingRuleStatus.NOT_PROCESSED,
    )
    assert returned_events == expected


@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_ignored_assets(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """This test tests that transactions with ignored assets are excluded when needed"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    with db.user_write() as write_cursor:
        db.add_to_ignored_assets(write_cursor, A_BTC)
        db.add_to_ignored_assets(write_cursor, A_DAI)

    dbevmtx = DBEvmTx(db)
    dbevents = DBHistoryEvents(db)
    tx1 = make_ethereum_transaction(timestamp=Timestamp(1))
    tx2 = make_ethereum_transaction(timestamp=Timestamp(2))
    tx3 = make_ethereum_transaction(timestamp=Timestamp(3))
    event1 = make_ethereum_event(tx_hash=tx1.tx_hash, index=1, asset=A_ETH, timestamp=TimestampMS(1))  # noqa: E501
    event2 = make_ethereum_event(tx_hash=tx1.tx_hash, index=2, asset=A_BTC, timestamp=TimestampMS(1))  # noqa: E501
    event3 = make_ethereum_event(tx_hash=tx2.tx_hash, index=3, asset=A_MKR, timestamp=TimestampMS(1))  # noqa: E501
    event4 = make_ethereum_event(tx_hash=tx3.tx_hash, index=4, asset=A_DAI, timestamp=TimestampMS(2))  # noqa: E501
    with db.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [tx1, tx2, tx3], relevant_address=ethereum_accounts[0])  # noqa: E501
        dbevents.add_history_events(cursor, [event1, event2, event3, event4])

    returned_events = query_events(
        rotkehlchen_api_server,
        json={
            'exclude_ignored_assets': False,
            'location': 'ethereum',
        },
        expected_num_with_grouping=3,
        expected_totals_with_grouping=3,
        entries_limit=100,
    )
    expected = generate_events_response([event4, event1, event2, event3])
    assert returned_events == expected

    returned_events = query_events(
        rotkehlchen_api_server,  # test that default exclude_ignored_assets is True
        json={'location': 'ethereum'},
        expected_num_with_grouping=2,
        expected_totals_with_grouping=3,
        entries_limit=100,
    )
    expected = generate_events_response([event1, event3])
    assert returned_events == expected


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [['0x59ABf3837Fa962d6853b4Cc0a19513AA031fd32b']])
@patch.object(EthereumTransactions, '_get_internal_transactions_for_ranges', lambda *args, **kargs: None)  # noqa: E501
@patch.object(EthereumTransactions, '_get_erc20_transfers_for_ranges', lambda *args, **kargs: None)
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1.5)])
def test_no_value_eth_transfer(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that eth transactions with no value are correctly decoded and returned in the API.
    In this case we don't need any erc20 or internal transaction, this is why they are omitted
    in this test.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    tx_str = '0x6cbae2712ded4254cc0dbd3daa9528b049c27095b5216a4c52e2e3be3d6905a5'
    # Make sure that the transactions get decoded
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'evmtransactionsresource',
        ), json={
            'async_query': False,
            'transactions': [{
                'evm_chain': 'ethereum',
                'tx_hash': tx_str,
            }],
        },
    )
    assert_simple_ok_response(response)

    # retrieve the transaction
    response = requests.post(api_url_for(
        rotkehlchen_api_server,
        'blockchaintransactionsresource',
    ), json={'async_query': False, 'from_timestamp': 1668407732, 'to_timestamp': 1668407737})

    assert_simple_ok_response(response)
    dbevmtx = DBEvmTx(rotki.data.db)
    with rotki.data.db.conn.read_ctx() as cursor:
        transactions = dbevmtx.get_evm_transactions(cursor, EvmTransactionsFilterQuery.make(), True)  # noqa: E501

    assert len(transactions) == 1
    assert transactions[0].tx_hash.hex() == tx_str
    # retrieve the event
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'tx_hashes': [tx_str]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries'][0]['entry']['asset'] == A_ETH
    assert result['entries'][0]['entry']['amount'] == '0'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_decoding_missing_transactions(
        rotkehlchen_api_server: 'APIServer',
        websocket_connection: WebsocketReader,
) -> None:
    """Test that decoding all pending transactions works fine"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    transactions, _ = setup_ethereum_transactions_test(
        database=rotki.data.db,
        transaction_already_queried=True,
        one_receipt_in_db=True,
        second_receipt_in_db=True,
    )
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'evmpendingtransactionsdecodingresource',
        ), json={'async_query': False, 'chains': ['ethereum']},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['decoded_tx_number']['ethereum'] == len(transactions)

    websocket_connection.wait_until_messages_num(num=4, timeout=4)
    assert websocket_connection.pop_message() == {'type': 'progress_updates', 'data': {'chain': 'ethereum', 'total': 2, 'processed': 0, 'subtype': 'evm_undecoded_transactions'}}  # noqa: E501
    assert websocket_connection.pop_message()
    assert websocket_connection.pop_message()
    assert websocket_connection.pop_message() == {'type': 'progress_updates', 'data': {'chain': 'ethereum', 'total': 2, 'processed': 2, 'subtype': 'evm_undecoded_transactions'}}  # noqa: E501

    dbevents = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.read_ctx() as cursor:
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(
                tx_hashes=[transactions[0].tx_hash],
            ),
            has_premium=True,
        )
        assert len(events) == 3
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(
                tx_hashes=[transactions[1].tx_hash],
            ),
            has_premium=True,
        )
        assert len(events) == 2

    # call again and no new transaction should be decoded
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'evmpendingtransactionsdecodingresource',
        ), json={'async_query': True},
    )
    result = assert_proper_sync_response_with_result(response)
    outcome = wait_for_async_task(rotkehlchen_api_server, result['task_id'])
    assert outcome['result']['decoded_tx_number'] == {}


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_count_transactions_missing_decoding(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that we can correctly count the number of transactions not decoded yet"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    async_query = random.choice([False, True])
    # setup 2 ethereum transactions, 1 OP transaction and 1 Base transaction not decoded
    dbevmtx = DBEvmTx(rotki.data.db)
    eth_transactions, _ = setup_ethereum_transactions_test(
        database=rotki.data.db,
        transaction_already_queried=True,
        one_receipt_in_db=True,
        second_receipt_in_db=True,
    )
    optimism_transaction_hash = make_evm_tx_hash()
    base_transaction_hash = make_evm_tx_hash()

    for chain, tx_hash in (
        (ChainID.BASE, base_transaction_hash),
        (ChainID.OPTIMISM, optimism_transaction_hash),
    ):
        transaction = EvmTransaction(
            tx_hash=tx_hash,
            chain_id=chain,
            timestamp=Timestamp(1631013757),
            block_number=13178342,
            from_address=TEST_ADDR2,
            to_address=string_to_evm_address('0xEaDD9B69F96140283F9fF75DA5FD33bcF54E6296'),
            value=0,
            gas=77373,
            gas_price=int(0.000000100314697497 * 10**18),
            gas_used=46782,
            input_data=hexstring_to_bytes('0xa9059cbb00000000000000000000000020c8032d4f7d4a380385f87aeadf05bed84504cb000000000000000000000000000000000000000000000000000000003b9deec6'),
            nonce=3,
        )
        with rotki.data.db.user_write() as cursor:
            dbevmtx.add_evm_transactions(cursor, evm_transactions=[transaction], relevant_address=TEST_ADDR2)  # noqa: E501

        expected_receipt = EvmTxReceipt(
            tx_hash=tx_hash,
            chain_id=chain,
            contract_address=None,
            status=True,
            tx_type=2,
            logs=[
                EvmTxReceiptLog(
                    log_index=438,
                    data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000003b9deec6'),
                    address=string_to_evm_address('0xEaDD9B69F96140283F9fF75DA5FD33bcF54E6296'),
                    topics=[
                        hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                        hexstring_to_bytes('0x000000000000000000000000442068f934be670adab81242c87144a851d56d16'),
                        hexstring_to_bytes('0x00000000000000000000000020c8032d4f7d4a380385f87aeadf05bed84504cb'),
                    ],
                ),
            ],
        )

        with rotki.data.db.user_write() as cursor:
            dbevmtx.add_or_ignore_receipt_data(cursor, chain, txreceipt_to_data(expected_receipt))

    get_decoded_events_of_transaction(
        evm_inquirer=rotki.chains_aggregator.ethereum.node_inquirer,
        tx_hash=eth_transactions[0].tx_hash,
    )  # decode 1 transaction in ethereum

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'evmpendingtransactionsdecodingresource',
        ), json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_sync_response_with_result(response)

    assert result == {
        'base': {'undecoded': 1, 'total': 1},
        'ethereum': {'undecoded': 1, 'total': 2},
        'optimism': {'undecoded': 1, 'total': 1},
    }


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_repulling_transaction_with_internal_txs(rotkehlchen_api_server: 'APIServer') -> None:
    """Check that re-decoding a transaction that has internal ETH transfers correctly
    repulls them"""
    tx_hash = deserialize_evm_tx_hash('0x4ea72ae535e32d5edc543a9ace5f736c7037cc63e4088de38511297c764049b5')  # noqa: E501
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    database = rotki.data.db
    with database.user_write() as write_cursor:
        database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.THEGRAPH,
                api_key=ApiKey(GRAPH_QUERY_CRED),
            )])

    dbevents = DBHistoryEvents(database)
    ethereum_inquirer = rotki.chains_aggregator.ethereum
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer.node_inquirer,
        tx_hash=tx_hash,
    )

    # When querying the API endpoint, it returns historical events, which also include prices.
    # However, when manually decoding the data, the prices are not retrieved.This means that
    # if you want to compare the lists before and after you need to query prices for the events
    # manually decoded
    filter_query = EvmEventFilterQuery.make(tx_hashes=[tx_hash])
    with database.conn.read_ctx() as cursor:
        events_before_redecoding = dbevents.get_history_events(
            cursor=cursor,
            filter_query=filter_query,
            group_by_event_ids=False,
            has_premium=True,
        )

    # trigger the deletion of the transaction's data by redecoding it
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'evmtransactionsresource'),
        json={
            'async_query': False,
            'transactions': [{
                'evm_chain': 'ethereum',
                'tx_hash': tx_hash.hex(),  # pylint: disable=no-member  # pylint doesn't detect the .hex attribute here
            }],
        },
    )
    assert_proper_response(response)

    # query the redecoded eventss
    with database.conn.read_ctx() as cursor:
        events_after_redecoding = dbevents.get_history_events(
            cursor=cursor,
            filter_query=filter_query,
            group_by_event_ids=False,
            has_premium=True,
        )
    assert events_before_redecoding == events_after_redecoding


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1]])
def test_force_redecode_evm_transactions(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that forcefully redecoding transactions does not remove EthWithdrawalEvent or EthBlockEvent instances.
    Regression test for https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=111708772"
    """  # noqa: E501
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dbevents = DBHistoryEvents(rotki.data.db)
    eth_transactions, _ = setup_ethereum_transactions_test(
        database=rotki.data.db,
        transaction_already_queried=True,
        one_receipt_in_db=True,
        second_receipt_in_db=True,
    )

    for tx in eth_transactions:
        get_decoded_events_of_transaction(
            evm_inquirer=rotki.chains_aggregator.ethereum.node_inquirer,
            tx_hash=tx.tx_hash,
        )
    with rotki.data.db.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=make_eth_withdrawal_and_block_events(),
        )
        assert dbevents.get_history_events_count(
            cursor=write_cursor,
            query_filter=HistoryEventFilterQuery.make(),
        )[0] == 5

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'evmpendingtransactionsdecodingresource',
        ), json={'async_query': False, 'ignore_cache': True},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == {'decoded_tx_number': {'ethereum': 2}}
    with rotki.data.db.conn.read_ctx() as cursor:
        assert dbevents.get_history_events_count(
            cursor=cursor,
            query_filter=HistoryEventFilterQuery.make(),
        )[0] == 5


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('start_with_valid_premium', [True, False])
def test_monerium_gnosis_pay_events_update(
        rotkehlchen_api_server: 'APIServer',
        monerium_credentials: None,
        gnosispay_credentials: None,
        start_with_valid_premium: bool,
) -> None:
    """Test that monerium and gnosis pay event are properly updated when decoding/redecoding.
    Also check that this functionality is only available for valid premium users.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT OR REPLACE INTO gnosispay_data(tx_hash, timestamp, merchant_name, '
            'merchant_city, country, mcc, transaction_symbol, transaction_amount, '
            'billing_symbol, billing_amount, reversal_symbol, reversal_amount) '
            'VALUES(?, ?, ?, ?, ? ,?, ?, ?, ?, ?, ?, ?)',
            (
                (gnosis_pay_tx_1 := make_evm_tx_hash()),
                (gnosis_pay_ts_1 := TimestampMS(1600000000)),
                'SomeCompany', 'Sevilla', 'ES', 6666,
                'EUR', '50', None, None, 'EUR', '5',
            ),
        )
        # We can go ahead and add these events, and they won't be removed when re-decoding since
        # there aren't any corresponding txs in the evm_transactions table.
        DBHistoryEvents(rotki.data.db).add_history_events(
            write_cursor=write_cursor,
            history=[(gnosispay_event1 := EvmEvent(
                tx_hash=gnosis_pay_tx_1,
                sequence_index=0,
                timestamp=gnosis_pay_ts_1,
                location=Location.GNOSIS,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_EUR,
                amount=ONE,
                counterparty=CPT_GNOSIS_PAY,
            )), (gnosispay_event2 := EvmEvent(
                tx_hash=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1610000000),
                location=Location.GNOSIS,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_EUR,
                amount=ONE,
                counterparty=CPT_GNOSIS_PAY,
            )), (monerium_event := EvmEvent(
                tx_hash=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1620000000),
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
                counterparty=CPT_MONERIUM,
            )), EvmEvent(
                tx_hash=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1630000000),
                location=Location.GNOSIS,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
            )],
        )

    def assert_calls(monerium_call: _Call, gnosis_pay_call: _Call) -> None:
        """Test that the calls are properly made depending on whether premium is active."""
        if start_with_valid_premium:
            assert mock_monerium.call_count == 1
            assert mock_monerium.call_args_list == [monerium_call]
            assert mock_gnosis_pay.call_count == 1
            assert mock_gnosis_pay.call_args_list == [gnosis_pay_call]
        else:
            assert mock_monerium.call_count == mock_gnosis_pay.call_count == 0

    # Check that redecoding specific transactions works correctly
    with (
        patch('rotkehlchen.externalapis.monerium.Monerium.get_and_process_orders') as mock_monerium,  # noqa: E501
        patch('rotkehlchen.externalapis.gnosispay.GnosisPay.query_remote_for_tx_and_update_events') as mock_gnosis_pay,  # noqa: E501
        patch.object(rotki.chains_aggregator.gnosis.transactions, 'get_or_query_transaction_receipt'),  # noqa: E501
        patch.object(rotki.chains_aggregator.arbitrum_one.transactions, 'get_or_query_transaction_receipt'),  # noqa: E501
        patch.object(
            rotki.chains_aggregator.gnosis.transactions_decoder,
            'decode_and_get_transaction_hashes',
            side_effect=lambda **kwargs: [gnosispay_event1, gnosispay_event2],
        ),
        patch.object(
            rotki.chains_aggregator.arbitrum_one.transactions_decoder,
            'decode_and_get_transaction_hashes',
            side_effect=lambda **kwargs: [monerium_event],
        ),
    ):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'evmtransactionsresource'),
            json={
                'transactions': [
                    {'evm_chain': 'gnosis', 'tx_hash': gnosispay_event1.tx_hash.hex()},
                    {'evm_chain': 'gnosis', 'tx_hash': gnosispay_event2.tx_hash.hex()},
                    {'evm_chain': 'arbitrum_one', 'tx_hash': monerium_event.tx_hash.hex()},
                ],
            },
        )
        assert_proper_response(response)

    assert_calls(
        monerium_call=call(tx_hash=monerium_event.tx_hash),
        gnosis_pay_call=call(tx_timestamp=ts_ms_to_sec(gnosispay_event2.timestamp)),
    )  # only the ts of the second event is queried since there's already gnosis pay data in the db for the first event.  # noqa: E501

    # Check that when redecoding all events, the APIs are simply queried once for all data.
    with (
        patch('rotkehlchen.externalapis.monerium.Monerium.get_and_process_orders') as mock_monerium,  # noqa: E501
        patch('rotkehlchen.externalapis.gnosispay.GnosisPay.get_and_process_transactions') as mock_gnosis_pay,  # noqa: E501
    ):
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'evmpendingtransactionsdecodingresource'),
            json={'async_query': False, 'ignore_cache': True, 'chains': ['gnosis']},
        )
        assert_proper_response(response)

    assert_calls(
        monerium_call=call(),  # no tx_hash specified, querying all data.
        gnosis_pay_call=call(after_ts=Timestamp(0)),  # ts of zero, querying all data.
    )

    # Check that when only decoding new transactions, only the data for the new events is queried.
    with rotki.data.db.user_write() as write_cursor:
        DBHistoryEvents(rotki.data.db).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_hash=(new_gnosispay_tx_hash := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=(new_gnosispay_ts := TimestampMS(1640000000)),
                location=Location.GNOSIS,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_EUR,
                amount=ONE,
                counterparty=CPT_GNOSIS_PAY,
            ), EvmEvent(
                tx_hash=(new_monerium_tx_hash := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=TimestampMS(1650000000),
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
                counterparty=CPT_MONERIUM,
            )],
        )

    with (
        patch('rotkehlchen.externalapis.monerium.Monerium.get_and_process_orders') as mock_monerium,  # noqa: E501
        patch('rotkehlchen.externalapis.gnosispay.GnosisPay.get_and_process_transactions') as mock_gnosis_pay,  # noqa: E501
        patch('rotkehlchen.db.evmtx.DBEvmTx.count_hashes_not_decoded', side_effect=lambda **kwargs: 2),  # noqa: E501
        patch.object(
            rotki.chains_aggregator.gnosis.transactions_decoder,
            'get_and_decode_undecoded_transactions',
            side_effect=lambda **kwargs: [new_gnosispay_tx_hash, new_monerium_tx_hash],
        ),
    ):
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'evmpendingtransactionsdecodingresource'),
            json={'async_query': False, 'chains': ['gnosis']},
        )
        assert_proper_response(response)

    assert_calls(
        monerium_call=call(tx_hash=new_monerium_tx_hash),
        gnosis_pay_call=call(after_ts=Timestamp(ts_ms_to_sec(new_gnosispay_ts) - 1)),
    )
