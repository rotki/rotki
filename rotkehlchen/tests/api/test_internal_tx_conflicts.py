from typing import TYPE_CHECKING, Any, cast

import requests

from rotkehlchen.db.internal_tx_conflicts import (
    INTERNAL_TX_CONFLICT_ACTION_FIX_REDECODE,
    INTERNAL_TX_CONFLICT_ACTION_REPULL,
    INTERNAL_TX_CONFLICT_REDECODE_REASON_DUPLICATE_EXACT_ROWS,
    INTERNAL_TX_CONFLICT_REPULL_REASON_ALL_ZERO_GAS,
)
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import ChainID, Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def test_get_pending_internal_tx_conflicts_endpoint(rotkehlchen_api_server: 'APIServer') -> None:
    tx_hash_pending = make_evm_tx_hash()
    tx_hash_pending_redecode = make_evm_tx_hash()
    tx_hash_done = make_evm_tx_hash()
    tx_hash_failed = make_evm_tx_hash()
    tx_hash_retry_without_error = make_evm_tx_hash()
    with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO evm_internal_tx_conflicts(transaction_hash, chain, action, repull_reason, redecode_reason, fixed, last_retry_ts, last_error) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',  # noqa: E501
            [
                (tx_hash_pending, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL, INTERNAL_TX_CONFLICT_REPULL_REASON_ALL_ZERO_GAS, None, 0, 1700000000, 'rpc timeout'),  # noqa: E501
                (tx_hash_pending_redecode, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_FIX_REDECODE, None, INTERNAL_TX_CONFLICT_REDECODE_REASON_DUPLICATE_EXACT_ROWS, 0, None, None),  # noqa: E501
                (tx_hash_failed, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL, INTERNAL_TX_CONFLICT_REPULL_REASON_ALL_ZERO_GAS, None, 0, 1700000100, 'indexer error'),  # noqa: E501
                (tx_hash_retry_without_error, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL, INTERNAL_TX_CONFLICT_REPULL_REASON_ALL_ZERO_GAS, None, 0, 1700000200, None),  # noqa: E501
                (tx_hash_done, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL, INTERNAL_TX_CONFLICT_REPULL_REASON_ALL_ZERO_GAS, None, 1, None, None),  # noqa: E501
            ],
        )
        write_cursor.execute(
            'INSERT INTO history_events(entry_type, group_identifier, sequence_index, timestamp, location, location_label, asset, amount, notes, type, subtype) '  # noqa: E501
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                HistoryBaseEntryType.EVM_EVENT.value,
                'pending_group',
                0,
                1700000000,
                Location.from_chain_id(ChainID.ETHEREUM).serialize_for_db(),
                '0xabc',
                'ETH',
                '1',
                None,
                HistoryEventType.INFORMATIONAL.serialize(),
                HistoryEventSubType.NONE.serialize(),
            ),
        )
        write_cursor.execute(
            'INSERT INTO chain_events_info(identifier, tx_ref, counterparty, address) VALUES (?, ?, ?, ?)',  # noqa: E501
            (write_cursor.lastrowid, tx_hash_pending, None, None),
        )

    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'internaltxconflictsresource'),
        json={'async_query': False},
    )
    result = cast('dict[str, Any]', assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    ))
    entries = cast('list[dict[str, Any]]', result['entries'])
    expected: list[dict[str, Any]] = [
        {
            'chain': 'ethereum',
            'tx_hash': str(tx_hash_pending),
            'timestamp': None,
            'action': INTERNAL_TX_CONFLICT_ACTION_REPULL,
            'repull_reason': INTERNAL_TX_CONFLICT_REPULL_REASON_ALL_ZERO_GAS,
            'redecode_reason': None,
            'last_retry_ts': 1700000000,
            'last_error': 'rpc timeout',
            'group_identifier': 'pending_group',
        },
        {
            'chain': 'ethereum',
            'tx_hash': str(tx_hash_failed),
            'timestamp': None,
            'action': INTERNAL_TX_CONFLICT_ACTION_REPULL,
            'repull_reason': INTERNAL_TX_CONFLICT_REPULL_REASON_ALL_ZERO_GAS,
            'redecode_reason': None,
            'last_retry_ts': 1700000100,
            'last_error': 'indexer error',
            'group_identifier': None,
        },
        {
            'chain': 'ethereum',
            'tx_hash': str(tx_hash_pending_redecode),
            'timestamp': None,
            'action': INTERNAL_TX_CONFLICT_ACTION_FIX_REDECODE,
            'repull_reason': None,
            'redecode_reason': INTERNAL_TX_CONFLICT_REDECODE_REASON_DUPLICATE_EXACT_ROWS,
            'last_retry_ts': None,
            'last_error': None,
            'group_identifier': None,
        },
        {
            'chain': 'ethereum',
            'tx_hash': str(tx_hash_retry_without_error),
            'timestamp': None,
            'action': INTERNAL_TX_CONFLICT_ACTION_REPULL,
            'repull_reason': INTERNAL_TX_CONFLICT_REPULL_REASON_ALL_ZERO_GAS,
            'redecode_reason': None,
            'last_retry_ts': 1700000200,
            'last_error': None,
            'group_identifier': None,
        },
    ]
    assert {
        (
            entry['chain'],
            entry['tx_hash'],
            entry['timestamp'],
            entry['action'],
            entry['repull_reason'],
            entry['redecode_reason'],
            entry['last_retry_ts'],
            entry['last_error'],
            entry['group_identifier'],
        )
        for entry in entries
    } == {
        (
            entry['chain'],
            entry['tx_hash'],
            entry['timestamp'],
            entry['action'],
            entry['repull_reason'],
            entry['redecode_reason'],
            entry['last_retry_ts'],
            entry['last_error'],
            entry['group_identifier'],
        )
        for entry in expected
    }
    assert result['entries_found'] == 4
    assert result['entries_total'] == 5
    assert result['entries_limit'] == -1

    paged_1 = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'internaltxconflictsresource'),
            json={'async_query': False, 'limit': 1, 'offset': 0},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    paged_2 = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'internaltxconflictsresource'),
            json={'async_query': False, 'limit': 1, 'offset': 1},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    assert paged_1['entries_found'] == 4
    assert paged_1['entries_total'] == 5
    assert paged_1['entries_limit'] == -1
    assert paged_2['entries_found'] == 4
    assert paged_2['entries_total'] == 5
    assert paged_2['entries_limit'] == -1
    assert paged_1['entries'][0]['tx_hash'] != paged_2['entries'][0]['tx_hash']

    filtered = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'internaltxconflictsresource'),
            json={'async_query': False, 'tx_hash': str(tx_hash_pending)},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    assert filtered['entries_found'] == 1
    assert filtered['entries_total'] == 5
    assert filtered['entries'][0]['tx_hash'] == str(tx_hash_pending)

    fixed_rows = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'internaltxconflictsresource'),
            json={'async_query': False, 'fixed': True},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    assert fixed_rows['entries_found'] == 1
    assert fixed_rows['entries_total'] == 5
    assert fixed_rows['entries'][0]['tx_hash'] == str(tx_hash_done)

    failed_rows = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'internaltxconflictsresource'),
            json={'async_query': False, 'failed': True},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    assert failed_rows['entries_found'] == 2
    assert failed_rows['entries_total'] == 5
    assert {entry['tx_hash'] for entry in failed_rows['entries']} == {
        str(tx_hash_pending),
        str(tx_hash_failed),
    }


def test_get_pending_internal_tx_conflicts_chain_and_timestamp_filters(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    tx_hash_eth_early = make_evm_tx_hash()
    tx_hash_optimism = make_evm_tx_hash()
    tx_hash_eth_late = make_evm_tx_hash()

    ts_early = Timestamp(1700000000)
    ts_mid = Timestamp(1700001000)
    ts_late = Timestamp(1700002000)

    with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO evm_transactions(tx_hash, chain_id, timestamp, block_number, from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',  # noqa: E501
            [
                (tx_hash_eth_early, ChainID.ETHEREUM.serialize_for_db(), ts_early, 1, '0xabc', None, '0', '21000', '1', '21000', b'', 0),  # noqa: E501
                (tx_hash_optimism, ChainID.OPTIMISM.serialize_for_db(), ts_mid, 2, '0xabc', None, '0', '21000', '1', '21000', b'', 1),  # noqa: E501
                (tx_hash_eth_late, ChainID.ETHEREUM.serialize_for_db(), ts_late, 3, '0xabc', None, '0', '21000', '1', '21000', b'', 2),  # noqa: E501
            ],
        )
        write_cursor.executemany(
            'INSERT INTO evm_internal_tx_conflicts(transaction_hash, chain, action, repull_reason, redecode_reason, fixed, last_retry_ts, last_error) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',  # noqa: E501
            [
                (tx_hash_eth_early, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL, INTERNAL_TX_CONFLICT_REPULL_REASON_ALL_ZERO_GAS, None, 0, None, None),  # noqa: E501
                (tx_hash_optimism, ChainID.OPTIMISM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL, INTERNAL_TX_CONFLICT_REPULL_REASON_ALL_ZERO_GAS, None, 0, None, None),  # noqa: E501
                (tx_hash_eth_late, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL, INTERNAL_TX_CONFLICT_REPULL_REASON_ALL_ZERO_GAS, None, 0, None, None),  # noqa: E501
            ],
        )

    # filter by chain
    by_chain = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'internaltxconflictsresource'),
            json={'async_query': False, 'chain': 'ethereum'},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    assert by_chain['entries_found'] == 2
    assert by_chain['entries_total'] == 3
    assert {entry['tx_hash'] for entry in by_chain['entries']} == {
        str(tx_hash_eth_early),
        str(tx_hash_eth_late),
    }
    assert all(entry['chain'] == 'ethereum' for entry in by_chain['entries'])

    # filter by from_timestamp
    by_from_ts = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'internaltxconflictsresource'),
            json={'async_query': False, 'from_timestamp': ts_mid},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    assert by_from_ts['entries_found'] == 2
    assert {entry['tx_hash'] for entry in by_from_ts['entries']} == {
        str(tx_hash_optimism),
        str(tx_hash_eth_late),
    }

    # filter by to_timestamp
    by_to_ts = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'internaltxconflictsresource'),
            json={'async_query': False, 'to_timestamp': ts_mid},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    assert by_to_ts['entries_found'] == 2
    assert {entry['tx_hash'] for entry in by_to_ts['entries']} == {
        str(tx_hash_eth_early),
        str(tx_hash_optimism),
    }

    # filter by timestamp range (only middle entry)
    by_range = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'internaltxconflictsresource'),
            json={'async_query': False, 'from_timestamp': ts_mid, 'to_timestamp': ts_mid},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    assert by_range['entries_found'] == 1
    assert by_range['entries'][0]['tx_hash'] == str(tx_hash_optimism)
    assert by_range['entries'][0]['timestamp'] == ts_mid
    assert by_range['entries'][0]['chain'] == 'optimism'

    # combine chain and timestamp filters
    chain_and_ts = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'internaltxconflictsresource'),
            json={'async_query': False, 'chain': 'ethereum', 'from_timestamp': ts_late},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    assert chain_and_ts['entries_found'] == 1
    assert chain_and_ts['entries'][0]['tx_hash'] == str(tx_hash_eth_late)
    assert chain_and_ts['entries'][0]['timestamp'] == ts_late
