from dataclasses import replace
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, Mock, patch

import pytest
from freezegun import freeze_time

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.concurrency import TaskCancelledError
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    TX_DECODED,
    TX_SPAM,
    HistoryMappingState,
)
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.remediation.base import RemediationOutcome
from rotkehlchen.history.data_issues.types import DataIssueFilters
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import (
    LOCATION_ETHEREUM,
)
from rotkehlchen.tasks.data_issues import (
    DISCOVERY_BATCH_SIZE,
    TRACKED_ADDRESS_TRANSFER_CANDIDATES_QUERY,
    _tracked_address_transfer_candidates_bindings,
    _write_tracked_address_transfer_issues,
    run_data_issue_remediation,
)
from rotkehlchen.tasks.historical_balances import process_historical_balances
from rotkehlchen.tests.fixtures.messages import MockedWsMessage, MockRotkiNotifier
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.messages import consume_errors
from rotkehlchen.types import (
    ChainID,
    ChecksumAddress,
    EvmTransaction,
    EVMTxHash,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.concurrency import Task
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.tasks.manager import TaskManager

pytestmark = [
    pytest.mark.accounting_update,
    pytest.mark.parametrize('use_clean_caching_directory', [True]),
]


def _make_event(
        tx_hash: EVMTxHash,
        amount: str,
        timestamp: int = 1_000,
        event_type: HistoryEventType = HistoryEventType.SPEND,
        location_label: str = TEST_ADDR1,
        address: ChecksumAddress | None = None,
        sequence_index: int = 0,
) -> EvmEvent:
    return EvmEvent(
        tx_ref=tx_hash,
        sequence_index=sequence_index,
        timestamp=TimestampMS(timestamp),
        location=LOCATION_ETHEREUM,
        event_type=event_type,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal(amount),
        location_label=location_label,
        address=address,
        notes='saved customized event',
    )


def _make_transaction(tx_hash: EVMTxHash, timestamp: int = 1) -> EvmTransaction:
    return EvmTransaction(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(timestamp),
        block_number=1,
        from_address=TEST_ADDR1,
        to_address=TEST_ADDR2,
        value=0,
        gas=21_000,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )


def _add_negative_balance_issue(
        database: DBHandler,
        customized: bool,
) -> tuple[int, EVMTxHash]:
    tx_hash = make_evm_tx_hash()
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[_make_transaction(tx_hash)],
            relevant_address=TEST_ADDR1,
        )
        event_id = DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=_make_event(tx_hash=tx_hash, amount='2'),
            mapping_values=(
                {HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED}
                if customized else None
            ),
        )
    assert event_id is not None
    issue_id = DataIssuesManager(database).write_issue(
        kind=IssueKind.NEGATIVE_BALANCE,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
        protocol=None,
        asset=A_ETH.identifier,
        payload={
            'event_identifier': event_id,
            'in_memory_negative_amount': '-1',
            'derived_balance_before_event': '1',
        },
        ts_start=1_000,
        ts_end=1_000,
    )
    return issue_id, tx_hash


def _get_saved_event_rows(database: DBHandler) -> tuple[list[tuple], list[tuple], list[tuple]]:
    with database.conn.read_ctx() as cursor:
        return (
            cursor.execute('SELECT * FROM history_events ORDER BY identifier').fetchall(),
            cursor.execute('SELECT * FROM chain_events_info ORDER BY identifier').fetchall(),
            cursor.execute(
                'SELECT * FROM history_events_mappings ORDER BY parent_identifier, name',
            ).fetchall(),
        )


def _add_plain_tracked_address_transfer(
        database: DBHandler,
        customized: bool,
) -> tuple[int, EVMTxHash]:
    tx_hash = make_evm_tx_hash()
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[_make_transaction(tx_hash)],
            relevant_address=TEST_ADDR1,
        )
        event_id = DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=_make_event(tx_hash=tx_hash, amount='1', address=TEST_ADDR2),
            mapping_values=(
                {HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED}
                if customized else None
            ),
        )
    assert event_id is not None
    return event_id, tx_hash


def _wait_for_background_task(tasks: list[Task] | None) -> None:
    assert tasks is not None
    assert len(tasks) == 1
    task = tasks[0]
    task.join(timeout=10)
    assert task.dead, f'{task.task_name} did not finish'
    task.get()


def _replace_transaction_events(
        database: DBHandler,
        tx_hash: EVMTxHash,
        events: list[EvmEvent],
) -> None:
    """Emulate a forced redecode: drop the transaction events and add the decoded ones.

    A throwaway event is inserted first so the replacements get identifiers distinct from
    the deleted rows, the way a redecode of a busy history does.
    """
    with database.user_write() as write_cursor:
        dbevents = DBHistoryEvents(database)
        throwaway_id = dbevents.add_history_event(
            write_cursor=write_cursor,
            event=_make_event(
                tx_hash=make_evm_tx_hash(),
                amount='1',
                location_label=make_evm_address(),
            ),
        )
        dbevents.delete_events_by_tx_ref(
            write_cursor=write_cursor,
            tx_refs=[tx_hash],
            location=LOCATION_ETHEREUM,
            customized_handling='preserve_transactions',
        )
        for event in events:
            dbevents.add_history_event(write_cursor=write_cursor, event=event)
        if throwaway_id is not None:
            dbevents.delete_events_and_track(
                write_cursor=write_cursor,
                where_clause='WHERE identifier = ?',
                where_bindings=(throwaway_id,),
            )


def _add_transaction_with_events(
        database: DBHandler,
        events: list[EvmEvent],
        timestamp: int = 1,
) -> EVMTxHash:
    tx_hash = events[0].tx_ref
    assert (relevant_address := events[0].location_label) is not None
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[_make_transaction(tx_hash, timestamp=timestamp)],
            relevant_address=string_to_evm_address(relevant_address),
        )
        for event in events:
            DBHistoryEvents(database).add_history_event(
                write_cursor=write_cursor,
                event=event,
            )

    return tx_hash


def _mock_decoder(database: DBHandler, decoded_events: list[EvmEvent]) -> MagicMock:
    """A decoder mock whose forced redecode replaces the transaction events."""
    decoder = MagicMock()

    def _decode_transaction_hashes(
            ignore_cache: bool,
            tx_hashes: list[EVMTxHash],
    ) -> None:
        assert ignore_cache is True
        assert len(tx_hashes) == 1
        _replace_transaction_events(
            database=database,
            tx_hash=tx_hashes[0],
            events=decoded_events,
        )

    decoder.decode_transaction_hashes.side_effect = _decode_transaction_hashes
    return decoder


def _mock_chains_aggregator(decoder: MagicMock) -> MagicMock:
    chains_aggregator = MagicMock()
    chains_aggregator.get_evm_manager.return_value.transactions_decoder = decoder
    return chains_aggregator


def _tracked_transfer_issues(database: DBHandler) -> list:
    return DataIssuesManager(database).list_issues(DataIssueFilters(
        kind=IssueKind.TRACKED_ADDRESS_TRANSFER,
    ))


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_remediation_sends_phase_websocket_updates(database: DBHandler) -> None:
    run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

    notifier = cast('MockRotkiNotifier', database.msg_aggregator.rotki_notifier)
    assert notifier.pop_message() == MockedWsMessage(
        message_type=WSMessageType.PROGRESS_UPDATES,
        data={
            'subtype': str(ProgressUpdateSubType.DATA_ISSUE_REMEDIATION),
            'phase': 'running',
        },
    )
    assert notifier.pop_message() == MockedWsMessage(
        message_type=WSMessageType.PROGRESS_UPDATES,
        data={
            'subtype': str(ProgressUpdateSubType.DATA_ISSUE_REMEDIATION),
            'phase': 'completed',
        },
    )


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_remediation_sends_completed_websocket_update_on_failure(database: DBHandler) -> None:
    with (
        patch.object(
            DataIssuesManager,
            'reconcile_dangling_tracked_address_transfer_issues',
            side_effect=RuntimeError('boom'),
        ),
        pytest.raises(RuntimeError),
    ):
        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

    notifier = cast('MockRotkiNotifier', database.msg_aggregator.rotki_notifier)
    assert notifier.pop_message() == MockedWsMessage(
        message_type=WSMessageType.PROGRESS_UPDATES,
        data={
            'subtype': str(ProgressUpdateSubType.DATA_ISSUE_REMEDIATION),
            'phase': 'running',
        },
    )
    assert notifier.pop_message() == MockedWsMessage(
        message_type=WSMessageType.PROGRESS_UPDATES,
        data={
            'subtype': str(ProgressUpdateSubType.DATA_ISSUE_REMEDIATION),
            'phase': 'completed',
        },
    )


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_one_redecode_verifies_all_sibling_issues(database: DBHandler) -> None:
    """Two events of one transaction are verified against a single forced redecode."""
    tx_hash = make_evm_tx_hash()
    _add_transaction_with_events(database, [
        _make_event(
            tx_hash=tx_hash,
            amount='1',
            address=TEST_ADDR2,
            sequence_index=1,
        ),
        _make_event(
            tx_hash=tx_hash,
            amount='2',
            address=TEST_ADDR2,
            sequence_index=2,
        ),
    ])
    decoder = _mock_decoder(database, [
        _make_event(
            tx_hash=tx_hash,
            amount='1',
            address=TEST_ADDR2,
            event_type=HistoryEventType.TRANSFER,
            sequence_index=1,
        ),
        _make_event(
            tx_hash=tx_hash,
            amount='2',
            address=TEST_ADDR2,
            event_type=HistoryEventType.TRANSFER,
            sequence_index=2,
        ),
    ])

    run_data_issue_remediation(
        database=database,
        chains_aggregator=_mock_chains_aggregator(decoder),
    )

    assert decoder.decode_transaction_hashes.call_count == 1
    issues = _tracked_transfer_issues(database)
    assert len(issues) == 2
    assert all(issue.state == IssueState.RESOLVED for issue in issues)


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_redecode_verifies_the_candidate_at_its_sequence_index(database: DBHandler) -> None:
    """A duplicate identical transfer elsewhere in the transaction must not resolve an issue."""
    tx_hash = make_evm_tx_hash()
    _add_transaction_with_events(database, [
        _make_event(tx_hash=tx_hash, amount='1', address=TEST_ADDR2, sequence_index=1),
        _make_event(tx_hash=tx_hash, amount='1', address=TEST_ADDR2, sequence_index=2),
    ])
    decoder = _mock_decoder(database, [
        _make_event(
            tx_hash=tx_hash,
            amount='1',
            address=TEST_ADDR2,
            event_type=HistoryEventType.TRANSFER,
            sequence_index=1,
        ),
        _make_event(tx_hash=tx_hash, amount='1', address=TEST_ADDR2, sequence_index=2),
    ])

    run_data_issue_remediation(
        database=database,
        chains_aggregator=_mock_chains_aggregator(decoder),
    )

    assert decoder.decode_transaction_hashes.call_count == 1
    issues = _tracked_transfer_issues(database)
    by_sequence = {
        issue.payload['sequence_index']: issue.state for issue in issues
    }
    assert by_sequence == {
        1: IssueState.RESOLVED,
        2: IssueState.UNRESOLVED,
    }


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_unsuccessful_redecode_migrates_issue_to_the_replacement_event(
        database: DBHandler,
) -> None:
    """The issue follows its replacement event, so a later scan does not duplicate it."""
    _event_id, tx_hash = _add_plain_tracked_address_transfer(database, customized=False)
    decoder = _mock_decoder(database, [
        _make_event(tx_hash=tx_hash, amount='1', address=TEST_ADDR2),
    ])

    run_data_issue_remediation(
        database=database,
        chains_aggregator=_mock_chains_aggregator(decoder),
    )

    issues = _tracked_transfer_issues(database)
    assert len(issues) == 1
    issue = issues[0]
    assert issue.state == IssueState.UNRESOLVED
    with database.conn.read_ctx() as cursor:
        replacement_id = cursor.execute(
            'SELECT H.identifier FROM history_events H '
            'JOIN chain_events_info C ON C.identifier = H.identifier WHERE C.tx_ref = ?',
            (tx_hash,),
        ).fetchone()[0]
    assert issue.payload['event_identifier'] == replacement_id


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_unsuccessful_redecode_does_not_create_a_duplicate_issue(database: DBHandler) -> None:
    _event_id, tx_hash = _add_plain_tracked_address_transfer(database, customized=False)
    decoder = _mock_decoder(database, [
        _make_event(tx_hash=tx_hash, amount='1', address=TEST_ADDR2),
    ])
    chains_aggregator = _mock_chains_aggregator(decoder)

    run_data_issue_remediation(database=database, chains_aggregator=chains_aggregator)
    issues = _tracked_transfer_issues(database)
    assert len(issues) == 1
    issue = issues[0]

    run_data_issue_remediation(database=database, chains_aggregator=chains_aggregator)

    issues = _tracked_transfer_issues(database)
    assert len(issues) == 1
    assert issues[0].id == issue.id


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_resolved_issue_related_event_link_survives_redecode(database: DBHandler) -> None:
    _event_id, tx_hash = _add_plain_tracked_address_transfer(database, customized=False)
    decoder = _mock_decoder(database, [
        _make_event(
            tx_hash=tx_hash,
            amount='1',
            address=TEST_ADDR2,
            event_type=HistoryEventType.TRANSFER,
        ),
    ])

    run_data_issue_remediation(
        database=database,
        chains_aggregator=_mock_chains_aggregator(decoder),
    )

    issue = _tracked_transfer_issues(database)[0]
    assert issue.state == IssueState.RESOLVED
    with database.conn.read_ctx() as cursor:
        replacement_id, group_identifier = cursor.execute(
            'SELECT H.identifier, H.group_identifier FROM history_events H '
            'JOIN chain_events_info C ON C.identifier = H.identifier WHERE C.tx_ref = ?',
            (tx_hash,),
        ).fetchone()
    assert issue.payload['event_identifier'] == replacement_id
    assert issue.group_identifier == group_identifier


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
@pytest.mark.parametrize(('replacement_type', 'expected_state'), [
    (HistoryEventType.TRANSFER, IssueState.RESOLVED),
    (HistoryEventType.SPEND, IssueState.OPEN),
])
def test_discovery_reconciles_event_redecoded_elsewhere(
        database: DBHandler,
        replacement_type: HistoryEventType,
        expected_state: IssueState,
) -> None:
    """An issue whose event was replaced outside remediation is re-pointed or resolved."""
    event_id, tx_hash = _add_plain_tracked_address_transfer(database, customized=False)
    manager = DataIssuesManager(database)
    _write_tracked_address_transfer_issues(database=database, issues_manager=manager)
    original_issues = _tracked_transfer_issues(database)
    assert len(original_issues) == 1
    original_issue_id = original_issues[0].id

    _replace_transaction_events(database, tx_hash, [_make_event(
        tx_hash=tx_hash,
        amount='1',
        address=TEST_ADDR2,
        event_type=replacement_type,
    )])
    _write_tracked_address_transfer_issues(database=database, issues_manager=manager)

    issues = _tracked_transfer_issues(database)
    assert len(issues) == 1  # the original row is reconciled, not duplicated
    issue = issues[0]
    assert issue.id == original_issue_id
    assert issue.state == expected_state
    with database.conn.read_ctx() as cursor:
        replacement_id = cursor.execute(
            'SELECT H.identifier FROM history_events H '
            'JOIN chain_events_info C ON C.identifier = H.identifier WHERE C.tx_ref = ?',
            (tx_hash,),
        ).fetchone()[0]
    assert event_id != replacement_id
    assert issue.payload['event_identifier'] == replacement_id
    assert manager.get_issue(issue.id).group_identifier is not None


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_discovery_resolves_issue_when_transaction_is_gone(database: DBHandler) -> None:
    _event_id, tx_hash = _add_plain_tracked_address_transfer(database, customized=False)
    manager = DataIssuesManager(database)
    _write_tracked_address_transfer_issues(database=database, issues_manager=manager)

    with database.user_write() as write_cursor:
        write_cursor.execute('DELETE FROM evm_transactions WHERE tx_hash = ?', (tx_hash,))
        write_cursor.execute(
            'DELETE FROM history_events WHERE identifier IN ('
            'SELECT identifier FROM chain_events_info WHERE tx_ref = ?)',
            (tx_hash,),
        )
    _write_tracked_address_transfer_issues(database=database, issues_manager=manager)

    issue = _tracked_transfer_issues(database)[0]
    assert issue.state == IssueState.RESOLVED


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_customized_transaction_is_never_redecoded(database: DBHandler) -> None:
    """A customized transaction keeps its events byte-identical and stays for the user."""
    event_id, tx_hash = _add_plain_tracked_address_transfer(database, customized=False)
    manager = DataIssuesManager(database)
    issue_id = manager.write_issue(
        kind=IssueKind.TRACKED_ADDRESS_TRANSFER,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
        protocol=None,
        asset=A_ETH.identifier,
        payload={
            'event_identifier': event_id,
            'chain_id': ChainID.ETHEREUM.serialize_for_db(),
            'tx_hash': str(tx_hash),
            'sequence_index': 0,
        },
        ts_start=1_000,
        ts_end=1_000,
    )
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO history_events_mappings(parent_identifier, name, value) '
            'VALUES (?, ?, ?)',
            (event_id, HISTORY_MAPPING_KEY_STATE, HistoryMappingState.CUSTOMIZED.serialize_for_db()),  # noqa: E501
        )
    saved_rows = _get_saved_event_rows(database)
    decoder = _mock_decoder(database, [])

    run_data_issue_remediation(
        database=database,
        chains_aggregator=_mock_chains_aggregator(decoder),
    )

    decoder.decode_transaction_hashes.assert_not_called()
    assert _get_saved_event_rows(database) == saved_rows
    issue = manager.get_issue(issue_id)
    assert issue.state == IssueState.OPEN
    assert issue.auto_remediation_attempts == []


@pytest.mark.parametrize('state', [IssueState.RESOLVED, IssueState.DISMISSED])
def test_remediation_skips_final_issues(database: DBHandler, state: IssueState) -> None:
    manager = DataIssuesManager(database)
    issue_id, _ = _add_negative_balance_issue(database=database, customized=True)
    if state == IssueState.RESOLVED:
        manager.update_state(issue_id, IssueState.AUTO_REMEDIATING)
        manager.update_state(issue_id, IssueState.RESOLVED)
    else:
        manager.dismiss(issue_id)

    run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

    issue = manager.get_issue(issue_id)
    assert issue.state == state
    assert issue.auto_remediation_attempts == []


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_remediation_keeps_unchanged_transfer_unresolved(
        database: DBHandler,
) -> None:
    """A decoder that leaves the transfer unchanged must not resolve its issue."""
    _event_id, tx_hash = _add_plain_tracked_address_transfer(database, customized=False)
    chains_aggregator = MagicMock()

    run_data_issue_remediation(database=database, chains_aggregator=chains_aggregator)

    decoder = chains_aggregator.get_evm_manager.return_value.transactions_decoder
    decoder.decode_transaction_hashes.assert_called_once_with(
        ignore_cache=True,
        tx_hashes=[tx_hash],
    )
    issues = DataIssuesManager(database).list_issues()
    assert len(issues) == 1
    assert issues[0].state == IssueState.UNRESOLVED
    assert issues[0].auto_remediation_attempts[0]['success'] is False
    assert issues[0].auto_remediation_attempts[0]['strategy'] == (
        'redecode_tracked_address_transfer'
    )


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
@pytest.mark.parametrize('event_type', [HistoryEventType.SPEND, HistoryEventType.RECEIVE])
@pytest.mark.parametrize('decoded_amount', [0, 1, 2])
def test_remediation_verifies_saved_internal_transfer(
        database: DBHandler,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        event_type: HistoryEventType,
        decoded_amount: int,
) -> None:
    """Resolve spend/receive issues only when the decoder saves a matching internal transfer."""
    event_id, tx_hash = _add_plain_tracked_address_transfer(database, customized=False)
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'UPDATE evm_transactions SET value = ? WHERE tx_hash = ?',
            (str(decoded_amount * 10**18), tx_hash),
        )
        # a decode of this transaction keeps the transfer at sequence index 1, after gas
        write_cursor.execute(
            'UPDATE history_events SET sequence_index = 1 WHERE identifier = ?',
            (event_id,),
        )
        if event_type == HistoryEventType.RECEIVE:
            write_cursor.execute(
                'UPDATE history_events SET type = ?, location_label = ? WHERE identifier = ?',
                (event_type.serialize(), TEST_ADDR2, event_id),
            )
            write_cursor.execute(
                'UPDATE chain_events_info SET address = ? WHERE identifier = ?',
                (TEST_ADDR1, event_id),
            )
        DBEvmTx(database).add_or_ignore_receipt_data(write_cursor, ChainID.ETHEREUM, {
            'transactionHash': str(tx_hash),
            'type': '0x0',
            'status': 1,
            'contractAddress': None,
            'logs': [],
        })
    chains_aggregator = MagicMock()
    chains_aggregator.get_evm_manager.return_value.transactions_decoder = (
        ethereum_transaction_decoder
    )

    run_data_issue_remediation(database=database, chains_aggregator=chains_aggregator)

    issues = _tracked_transfer_issues(database)
    assert len(issues) == 1
    assert issues[0].state == (
        IssueState.RESOLVED if decoded_amount == 1 else IssueState.UNRESOLVED
    )
    assert issues[0].auto_remediation_attempts[0]['success'] is (decoded_amount == 1)


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
@pytest.mark.parametrize('failure_stage', ['decode', 'write'])
def test_cancelled_redecode_preserves_events_and_flags(
        database: DBHandler,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        failure_stage: str,
) -> None:
    """Cancellation before replacement or during insertion preserves the committed history."""
    _event_id, tx_hash = _add_plain_tracked_address_transfer(database, customized=False)
    with database.user_write() as cursor:
        cursor.execute(
            'UPDATE evm_transactions SET value = ? WHERE tx_hash = ?',
            (str(10**18), tx_hash),
        )
        tx_id = cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash = ?', (tx_hash,),
        ).fetchone()[0]
        cursor.executemany(
            'INSERT INTO evm_tx_mappings(tx_id, value) VALUES (?, ?)',
            [(tx_id, TX_DECODED), (tx_id, TX_SPAM)],
        )
        DBEvmTx(database).add_or_ignore_receipt_data(cursor, ChainID.ETHEREUM, {
            'transactionHash': str(tx_hash), 'type': '0x0', 'status': 1,
            'contractAddress': None, 'logs': [],
        })
    saved_rows = _get_saved_event_rows(database)
    decoder = ethereum_transaction_decoder
    with (
        patch.object(
            decoder,
            '_decode_transaction' if failure_stage == 'decode' else '_write_tx_events',
            side_effect=TaskCancelledError('cancelled during redecoding'),
        ),
        pytest.raises(TaskCancelledError),
    ):
        decoder.decode_transaction_hashes(ignore_cache=True, tx_hashes=[tx_hash])

    assert _get_saved_event_rows(database) == saved_rows
    with database.conn.read_ctx() as cursor:
        assert set(cursor.execute(
            'SELECT value FROM evm_tx_mappings WHERE tx_id = ?', (tx_id,),
        )) == {(TX_DECODED,), (TX_SPAM,)}

    decoder.decode_transaction_hashes(ignore_cache=True, tx_hashes=[tx_hash])
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT type, amount FROM history_events WHERE subtype = ?',
            (HistoryEventSubType.NONE.serialize(),),
        ).fetchall() == [(HistoryEventType.TRANSFER.serialize(), '1')]
        assert set(cursor.execute(
            'SELECT value FROM evm_tx_mappings WHERE tx_id = ?', (tx_id,),
        )) == {(TX_DECODED,)}


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
@pytest.mark.parametrize('polygon_pos_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_remediation_redecodes_transfer_on_its_event_chain_only(database: DBHandler) -> None:
    _event_id, tx_hash = _add_plain_tracked_address_transfer(database, customized=False)
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[replace(_make_transaction(tx_hash), chain_id=ChainID.POLYGON_POS)],
            relevant_address=TEST_ADDR1,
        )
    chains_aggregator = MagicMock()

    run_data_issue_remediation(database=database, chains_aggregator=chains_aggregator)

    chains_aggregator.get_evm_manager.assert_called_once_with(ChainID.ETHEREUM)


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_remediation_skips_customized_tracked_address_transfer(database: DBHandler) -> None:
    """A customized transaction is not discovered, and is never redecoded."""
    _event_id, _tx_hash = _add_plain_tracked_address_transfer(database, customized=True)
    chains_aggregator = MagicMock()

    run_data_issue_remediation(database=database, chains_aggregator=chains_aggregator)

    chains_aggregator.get_evm_manager.assert_not_called()
    assert _tracked_transfer_issues(database) == []


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_scan_keeps_manual_resolution_of_unchanged_transfer(database: DBHandler) -> None:
    """Rediscovering an unchanged transfer candidate must not reopen its resolved issue."""
    _event_id, _tx_hash = _add_plain_tracked_address_transfer(database, customized=False)
    manager = DataIssuesManager(database)
    run_data_issue_remediation(database=database, chains_aggregator=MagicMock())
    issue_id = manager.list_issues()[0].id
    manager.resolve_manually(issue_id, note='expected')

    run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

    issue = manager.get_issue(issue_id)
    assert issue.state == IssueState.RESOLVED
    assert issue.payload['resolution'] == {'manual': True, 'note': 'expected'}


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1]])
@pytest.mark.usefixtures('ethereum_transaction_decoder')
@pytest.mark.parametrize(('decoded_spend', 'missing_receipt', 'expected_result'), [
    (5, False, 'redecoding_would_change_balance'),
    (11, False, 'redecoding_would_not_change_balance'),
    (5, True, 'redecoding_would_change_balance'),
])
@freeze_time('2026-09-07 12:00:00')
def test_negative_balance_customized_spend_is_compared_with_real_decoder(
        database: DBHandler,
        task_manager: TaskManager,
        decoded_spend: int,
        missing_receipt: bool,
        expected_result: str,
) -> None:
    """Schedule balance processing and real previews, preserving events across attempts."""
    receive_tx_hash, spend_tx_hash = make_evm_tx_hash(), make_evm_tx_hash()
    spend_transaction = EvmTransaction(
        tx_hash=spend_tx_hash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(2),
        block_number=1,
        from_address=TEST_ADDR1,
        to_address=TEST_ADDR2,
        value=decoded_spend * 10**18,
        gas=21_000,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt_data = {
        'transactionHash': str(spend_tx_hash),
        'type': '0x0',
        'status': 1,
        'contractAddress': None,
        'logs': [],
    }
    dbevents, dbtx = DBHistoryEvents(database), DBEvmTx(database)
    with database.user_write() as write_cursor:
        dbtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[spend_transaction],
            relevant_address=TEST_ADDR1,
        )
        if missing_receipt is False:
            dbtx.add_or_ignore_receipt_data(write_cursor, ChainID.ETHEREUM, receipt_data)
        dbevents.add_history_event(
            write_cursor=write_cursor,
            event=_make_event(
                tx_hash=receive_tx_hash,
                amount='10',
                event_type=HistoryEventType.RECEIVE,
            ),
        )
        dbevents.add_history_event(write_cursor, EvmEvent(
            tx_ref=spend_tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(2_000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0),
            location_label=TEST_ADDR1,
            counterparty=CPT_GAS,
            notes='Burn 0 ETH for gas',
        ))
        saved_spend = _make_event(tx_hash=spend_tx_hash, amount='11', timestamp=2_000)
        saved_spend.sequence_index = 1
        spend_event_id = dbevents.add_history_event(
            write_cursor=write_cursor,
            event=saved_spend,
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED},
        )
    assert spend_event_id is not None

    assert task_manager._maybe_run_data_issue_remediation() is None
    _wait_for_background_task(task_manager._maybe_process_historical_balances())
    issues_manager = DataIssuesManager(database)
    issues = issues_manager.list_issues()
    assert len(issues) == 1
    assert issues[0].kind == IssueKind.NEGATIVE_BALANCE
    assert issues[0].state == IssueState.OPEN
    assert issues[0].payload == {
        'event_identifier': spend_event_id,
        'in_memory_negative_amount': '-1',
        'derived_balance_before_event': '10',
    }
    saved_rows = _get_saved_event_rows(database)
    with database.conn.read_ctx() as cursor:
        saved_tx_mappings = cursor.execute('SELECT * FROM evm_tx_mappings').fetchall()
        assert database.get_static_cache(
            cursor, DBCacheStatic.LAST_HISTORICAL_BALANCE_PROCESSING_TS,
        ) == ts_now()
    _wait_for_background_task(task_manager._maybe_run_data_issue_remediation())

    issue = issues_manager.get_issue(issues[0].id)
    assert issue.state == IssueState.UNRESOLVED
    assert len(issue.auto_remediation_attempts) == 1
    attempt = issue.auto_remediation_attempts[0]
    assert {
        key: value for key, value in attempt.items() if key not in {'reason', 'transactions'}
    } == {
        'attribution': 'system',
        'strategy': 'redecode_customized_transactions',
        'timestamp': ts_now(),
        'result': 'redecoding_failed' if missing_receipt else expected_result,
        'customized_transaction_count': 1,
        'changed_transaction_count': int(not missing_receipt and decoded_spend != 11),
    }
    if not missing_receipt and decoded_spend != 11:
        comparison = attempt['transactions'][0]
        assert comparison['tx_hash'] == str(spend_tx_hash)
        assert [event['amount'] for event in comparison['saved_events']] == ['0', '11']
        assert [event['customized'] for event in comparison['saved_events']] == [False, True]
        assert [event['amount'] for event in comparison['decoded_events']] == [
            '0', str(decoded_spend),
        ]
    else:
        assert 'transactions' not in attempt
    assert _get_saved_event_rows(database) == saved_rows
    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT * FROM evm_tx_mappings').fetchall() == saved_tx_mappings
        assert database.get_static_cache(
            cursor, DBCacheStatic.LAST_DATA_ISSUE_REMEDIATION_TS,
        ) == ts_now()
    assert task_manager._maybe_run_data_issue_remediation() is None

    if missing_receipt:
        assert 'Missing transaction data' in attempt['reason']
        with database.user_write() as cursor:
            dbtx.add_or_ignore_receipt_data(cursor, ChainID.ETHEREUM, receipt_data)

    with freeze_time('2026-09-08 12:00:01'):
        _wait_for_background_task(task_manager._maybe_run_data_issue_remediation())
        issue = issues_manager.get_issue(issue.id)
        assert issue.state == IssueState.UNRESOLVED
        assert _get_saved_event_rows(database) == saved_rows
        with database.conn.read_ctx() as cursor:
            assert cursor.execute('SELECT * FROM evm_tx_mappings').fetchall() == saved_tx_mappings
            assert database.get_static_cache(
                cursor, DBCacheStatic.LAST_DATA_ISSUE_REMEDIATION_TS,
            ) == ts_now()

        if missing_receipt:
            assert len(issue.auto_remediation_attempts) == 2
            assert issue.auto_remediation_attempts[0] == attempt
            retry_attempt = issue.auto_remediation_attempts[1]
            assert retry_attempt['transactions'][0]['tx_hash'] == str(spend_tx_hash)
            assert {
                key: value for key, value in retry_attempt.items() if key != 'transactions'
            } == {
                'attribution': 'system',
                'strategy': 'redecode_customized_transactions',
                'timestamp': ts_now(),
                'result': expected_result,
                'customized_transaction_count': 1,
                'changed_transaction_count': 1,
            }
        else:
            assert issue.auto_remediation_attempts == [attempt]


@pytest.mark.parametrize(('preview_amount', 'expected_result', 'expected_changed'), [
    ('1', 'redecoding_would_change_balance', 1),
    ('2', 'redecoding_would_not_change_balance', 0),
])
def test_customized_transaction_redecode_comparison_preserves_saved_events(
        database: DBHandler,
        preview_amount: str,
        expected_result: str,
        expected_changed: int,
) -> None:
    issue_id, tx_hash = _add_negative_balance_issue(database=database, customized=True)
    saved_rows = _get_saved_event_rows(database)

    with patch(
        'rotkehlchen.tasks.data_issues._preview_transaction',
        return_value=[_make_event(tx_hash=tx_hash, amount=preview_amount)],
    ) as preview:
        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

    preview.assert_called_once()
    issue = DataIssuesManager(database).get_issue(issue_id)
    assert issue.state == IssueState.UNRESOLVED
    comparisons = issue.auto_remediation_attempts[0].get('transactions', [])
    if expected_changed:
        assert len(comparisons) == 1
        comparison = comparisons[0]
        assert comparison['tx_hash'] == str(tx_hash)
        assert comparison['saved_events'][0]['amount'] == '2'
        assert comparison['saved_events'][0]['customized'] is True
        assert comparison['saved_events'][0]['balance_effect'] == '-2'
        assert comparison['decoded_events'][0]['amount'] == preview_amount
        assert comparison['decoded_events'][0]['customized'] is False
        assert comparison['decoded_events'][0]['balance_effect'] == f'-{preview_amount}'
        assert comparison['group_identifier'] == comparison['saved_events'][0]['group_identifier']
    else:
        assert comparisons == []
    assert issue.auto_remediation_attempts == [{
        'attribution': 'system',
        'strategy': 'redecode_customized_transactions',
        'timestamp': issue.auto_remediation_attempts[0]['timestamp'],
        'result': expected_result,
        'customized_transaction_count': 1,
        'changed_transaction_count': expected_changed,
        **({'transactions': comparisons} if expected_changed else {}),
    }]
    assert _get_saved_event_rows(database) == saved_rows


def test_redecode_comparison_ignores_sequence_index_changes(database: DBHandler) -> None:
    issue_id, tx_hash = _add_negative_balance_issue(database=database, customized=True)
    preview_event = _make_event(tx_hash=tx_hash, amount='2')
    preview_event.sequence_index = 7

    with patch(
        'rotkehlchen.tasks.data_issues._preview_transaction',
        return_value=[preview_event],
    ):
        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

    attempt = DataIssuesManager(database).get_issue(issue_id).auto_remediation_attempts[0]
    assert attempt['result'] == 'redecoding_would_not_change_balance'
    assert attempt['changed_transaction_count'] == 0


def test_normal_transaction_is_not_redecoded_for_negative_balance(database: DBHandler) -> None:
    issue_id, _tx_hash = _add_negative_balance_issue(database=database, customized=False)
    with patch('rotkehlchen.tasks.data_issues._preview_transaction') as preview:
        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

    preview.assert_not_called()
    issue = DataIssuesManager(database).get_issue(issue_id)
    assert issue.state == IssueState.OPEN
    assert issue.auto_remediation_attempts == []


def test_earlier_customized_transaction_in_negative_bucket_is_compared(
        database: DBHandler,
) -> None:
    customized_tx_hash, failing_tx_hash = make_evm_tx_hash(), make_evm_tx_hash()
    dbevents, dbtx = DBHistoryEvents(database), DBEvmTx(database)
    with database.user_write() as write_cursor:
        dbtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[_make_transaction(customized_tx_hash)],
            relevant_address=TEST_ADDR1,
        )
        dbevents.add_history_event(
            write_cursor=write_cursor,
            event=_make_event(
                tx_hash=customized_tx_hash,
                amount='1',
                event_type=HistoryEventType.RECEIVE,
            ),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED},
        )
        failing_event_id = dbevents.add_history_event(
            write_cursor=write_cursor,
            event=_make_event(tx_hash=failing_tx_hash, amount='2', timestamp=2_000),
        )
    assert failing_event_id is not None
    issue_id = DataIssuesManager(database).write_issue(
        kind=IssueKind.NEGATIVE_BALANCE,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
        protocol=None,
        asset=A_ETH.identifier,
        payload={
            'event_identifier': failing_event_id,
            'in_memory_negative_amount': '-1',
            'derived_balance_before_event': '1',
        },
        ts_start=2_000,
        ts_end=2_000,
    )

    with patch(
        'rotkehlchen.tasks.data_issues._preview_transaction',
        return_value=[_make_event(
            tx_hash=customized_tx_hash,
            amount='2',
            event_type=HistoryEventType.RECEIVE,
        )],
    ) as preview:
        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

    preview.assert_called_once()
    issue = DataIssuesManager(database).get_issue(issue_id)
    assert issue.state == IssueState.UNRESOLVED
    assert issue.auto_remediation_attempts[0]['result'] == 'redecoding_would_change_balance'


@pytest.mark.parametrize(('saved_timestamp', 'saved_location_label'), [
    (1_000, TEST_ADDR2),
    (2_000, TEST_ADDR1),
])
def test_customized_transaction_with_changed_bucket_scope_is_compared(
        database: DBHandler,
        saved_timestamp: int,
        saved_location_label: str,
) -> None:
    customized_tx_hash = make_evm_tx_hash()
    issue_id, _failing_tx_hash = _add_negative_balance_issue(
        database=database,
        customized=False,
    )
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[_make_transaction(customized_tx_hash)],
            relevant_address=TEST_ADDR1,
        )
        DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=_make_event(
                tx_hash=customized_tx_hash,
                amount='1',
                timestamp=saved_timestamp,
                event_type=HistoryEventType.RECEIVE,
                location_label=saved_location_label,
            ),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED},
        )

    with patch(
        'rotkehlchen.tasks.data_issues._preview_transaction',
        return_value=[_make_event(
            tx_hash=customized_tx_hash,
            amount='1',
            event_type=HistoryEventType.RECEIVE,
        )],
    ) as preview:
        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

    preview.assert_called_once()
    issue = DataIssuesManager(database).get_issue(issue_id)
    assert issue.state == IssueState.UNRESOLVED
    assert issue.auto_remediation_attempts[0]['result'] == 'redecoding_would_change_balance'
    assert issue.auto_remediation_attempts[0]['changed_transaction_count'] == 1


def test_customized_transaction_for_unrelated_account_is_not_compared(
        database: DBHandler,
) -> None:
    customized_tx_hash = make_evm_tx_hash()
    issue_id, _failing_tx_hash = _add_negative_balance_issue(
        database=database,
        customized=False,
    )
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[_make_transaction(customized_tx_hash)],
            relevant_address=TEST_ADDR2,
        )
        DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=_make_event(
                tx_hash=customized_tx_hash,
                amount='1',
                event_type=HistoryEventType.RECEIVE,
            ),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED},
        )

    with patch('rotkehlchen.tasks.data_issues._preview_transaction') as preview:
        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

    preview.assert_not_called()
    issue = DataIssuesManager(database).get_issue(issue_id)
    assert issue.state == IssueState.OPEN
    assert issue.auto_remediation_attempts == []


def test_failed_redecode_comparison_preserves_saved_events(database: DBHandler) -> None:
    issue_id, _tx_hash = _add_negative_balance_issue(database=database, customized=True)
    saved_rows = _get_saved_event_rows(database)
    with patch(
        'rotkehlchen.tasks.data_issues._preview_transaction',
        side_effect=RuntimeError('receipt unavailable'),
    ):
        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

    issue = DataIssuesManager(database).get_issue(issue_id)
    assert issue.state == IssueState.UNRESOLVED
    assert issue.auto_remediation_attempts[0] | {'timestamp': 0} == {
        'attribution': 'system',
        'strategy': 'redecode_customized_transactions',
        'timestamp': 0,
        'result': 'redecoding_failed',
        'customized_transaction_count': 1,
        'changed_transaction_count': 0,
        'reason': 'receipt unavailable',
    }
    assert _get_saved_event_rows(database) == saved_rows


def test_repeated_failed_comparison_records_every_attempt(database: DBHandler) -> None:
    issue_id, _tx_hash = _add_negative_balance_issue(database=database, customized=True)
    with patch(
        'rotkehlchen.tasks.data_issues._preview_transaction',
        side_effect=RuntimeError('receipt unavailable'),
    ) as preview:
        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())
        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

    assert preview.call_count == 2
    issue = DataIssuesManager(database).get_issue(issue_id)
    assert issue.state == IssueState.UNRESOLVED
    assert len(issue.auto_remediation_attempts) == 2
    assert all(
        attempt['result'] == 'redecoding_failed' for attempt in issue.auto_remediation_attempts
    )


def test_cancelled_comparison_is_retried(database: DBHandler) -> None:
    issue_id, tx_hash = _add_negative_balance_issue(database=database, customized=True)
    with patch(
        'rotkehlchen.tasks.data_issues._preview_transaction',
        side_effect=(
            TaskCancelledError(),
            [_make_event(tx_hash=tx_hash, amount='2')],
        ),
    ) as preview:
        with pytest.raises(TaskCancelledError):
            run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

        issue = DataIssuesManager(database).get_issue(issue_id)
        assert issue.state == IssueState.UNRESOLVED
        assert len(issue.auto_remediation_attempts) == 1
        assert issue.auto_remediation_attempts[0]['result'] == 'redecoding_failed'
        assert issue.auto_remediation_attempts[0]['reason'] == (
            'Remediation was cancelled before the comparison finished'
        )

        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())

    assert preview.call_count == 2
    issue = DataIssuesManager(database).get_issue(issue_id)
    assert issue.state == IssueState.UNRESOLVED
    assert len(issue.auto_remediation_attempts) == 2
    assert issue.auto_remediation_attempts[1]['result'] == (
        'redecoding_would_not_change_balance'
    )


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1]])
@pytest.mark.parametrize('rule_stage', [
    'address', 'input', 'event', 'post_decoding', 'enrichment',
])
@pytest.mark.parametrize('rule_error', [
    RemoteError('rule unavailable', cause=FailureCause.NETWORK),
    ValueError('rule unavailable'),
], ids=lambda error: type(error).__name__)
def test_decoder_rule_failure_is_reported_as_failed_comparison(
        database: DBHandler,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        rule_stage: str,
        rule_error: Exception,
) -> None:
    """A rule failure invalidates previews without changing normal decoding's error tolerance."""
    issue_id, tx_hash = _add_negative_balance_issue(database, customized=True)
    dbtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbtx.add_or_ignore_receipt_data(cursor, ChainID.ETHEREUM, {
            'transactionHash': str(tx_hash),
            'type': '0x0',
            'status': 1,
            'contractAddress': None,
            'logs': [{
                'logIndex': 0,
                'data': '0x' + (1000000).to_bytes(32, 'big').hex(),
                'address': (
                    '0xdAC17F958D2ee523a2206206994597C13D831ec7'
                    if rule_stage == 'enrichment' else TEST_ADDR2
                ),
                'topics': [
                    '0x' + ERC20_OR_ERC721_TRANSFER.hex(),
                    '0x' + '00' * 12 + TEST_ADDR1[2:],
                    '0x' + '00' * 12 + TEST_ADDR2[2:],
                ] if rule_stage == 'enrichment' else ['0x' + '01' * 32],
            }],
        })
    with database.conn.read_ctx() as cursor:
        receipt = dbtx.get_receipt(cursor, tx_hash, ChainID.ETHEREUM)
    assert receipt is not None
    saved_rows = _get_saved_event_rows(database)
    decoder = ethereum_transaction_decoder
    failing_rule = Mock(__name__='failing_rule', side_effect=rule_error)
    chains_aggregator = MagicMock()
    chains_aggregator.get_evm_manager.return_value.transactions_decoder = decoder

    with (
        patch.object(
            decoder,
            'rules',
            replace(
                decoder.rules,
                address_mappings=(
                    {TEST_ADDR2: (failing_rule,)} if rule_stage == 'address' else {}
                ),
                input_data_rules=(
                    {b'': {bytes.fromhex('01' * 32): failing_rule}}
                    if rule_stage == 'input' else {}
                ),
                event_rules=(
                    [failing_rule] if rule_stage == 'event' else
                    [decoder._maybe_decode_erc20_721_transfer]
                ),
                token_enricher_rules=[failing_rule] if rule_stage == 'enrichment' else [],
            ),
        ),
        patch.object(
            decoder,
            '_chain_specific_post_decoding_rules',
            return_value=[(0, failing_rule)] if rule_stage == 'post_decoding' else [],
        ),
    ):
        run_data_issue_remediation(database, chains_aggregator)
        issue = DataIssuesManager(database).get_issue(issue_id)
        assert issue.state == IssueState.UNRESOLVED
        assert issue.auto_remediation_attempts[0]['result'] == 'redecoding_failed'
        assert issue.auto_remediation_attempts[0]['reason'] == 'rule unavailable'
        failing_rule.assert_called_once()
        assert _get_saved_event_rows(database) == saved_rows

        events, _, _ = decoder._decode_transaction(
            transaction=_make_transaction(tx_hash),
            tx_receipt=receipt,
            write_buffer=[],
        )
        assert failing_rule.call_count == 2
        assert len(events) != 0
        assert any('failed' in message for message in consume_errors(decoder.msg_aggregator))


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_remediation_continues_to_next_issue_after_decoder_failure(
        database: DBHandler,
) -> None:
    """Continue after a remote failure and retry only the failed issue on the next run."""
    _add_plain_tracked_address_transfer(database, customized=False)
    _add_plain_tracked_address_transfer(database, customized=False)
    chains_aggregator = MagicMock()
    decoder = chains_aggregator.get_evm_manager.return_value.transactions_decoder
    decode = decoder.decode_transaction_hashes
    decode.side_effect = [
        RemoteError('receipt unavailable', cause=FailureCause.NETWORK),
        None,
        None,
    ]

    run_data_issue_remediation(database=database, chains_aggregator=chains_aggregator)

    assert decode.call_count == 2
    issues = DataIssuesManager(database).list_issues()
    assert len(issues) == 2
    assert all(issue.state == IssueState.UNRESOLVED for issue in issues)
    assert all(len(issue.auto_remediation_attempts) == 1 for issue in issues)
    assert issues[0].auto_remediation_attempts[0]['reason'] == 'receipt unavailable'
    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor, DBCacheStatic.LAST_DATA_ISSUE_REMEDIATION_TS,
        ) is not None

    run_data_issue_remediation(database=database, chains_aggregator=chains_aggregator)

    assert decode.call_count == 3
    assert decode.call_args == decode.call_args_list[0]
    issues = DataIssuesManager(database).list_issues()
    assert [len(issue.auto_remediation_attempts) for issue in issues] == [2, 1]
    assert issues[0].auto_remediation_attempts[0]['attribution'] == 'strategy_failed'
    assert issues[0].auto_remediation_attempts[-1]['attribution'] == 'system'

    run_data_issue_remediation(database=database, chains_aggregator=chains_aggregator)
    assert decode.call_count == 3


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
@pytest.mark.parametrize('kind', [IssueKind.NEGATIVE_BALANCE, IssueKind.TRACKED_ADDRESS_TRANSFER])
def test_timed_out_remediation_is_retried(database: DBHandler, kind: IssueKind) -> None:
    """Retry either strategy after a timeout, but stop retrying after a completed attempt."""
    if kind == IssueKind.NEGATIVE_BALANCE:
        _add_negative_balance_issue(database=database, customized=True)
    else:
        _add_plain_tracked_address_transfer(database, customized=False)
    with patch(
        'rotkehlchen.history.data_issues.remediation.base.RemediationPipeline._attempt_with_budget',
        side_effect=[
            RemediationOutcome(False, 'timeout', 'Time budget exceeded'),
            RemediationOutcome(False, 'system', 'No change needed'),
        ],
    ) as attempt:
        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())
        issue = DataIssuesManager(database).list_issues()[0]
        assert issue.state == IssueState.UNRESOLVED
        assert issue.auto_remediation_attempts[-1]['attribution'] == 'timeout'

        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())
        assert attempt.call_count == 2
        run_data_issue_remediation(database=database, chains_aggregator=MagicMock())
        assert attempt.call_count == 2

    issue = DataIssuesManager(database).get_issue(issue.id)
    assert issue.state == IssueState.UNRESOLVED
    assert len(issue.auto_remediation_attempts) == 2
    assert issue.auto_remediation_attempts[-1]['attribution'] == 'system'


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_discovery_large_history_writes_nothing_on_second_run(database: DBHandler) -> None:
    """A second scan of an unchanged history performs zero writes to the issues table."""
    manager = DataIssuesManager(database)
    transactions: list[EvmTransaction] = []
    events: list[EvmEvent] = []
    for _ in range(700):
        tx_hash = make_evm_tx_hash()
        transactions.append(_make_transaction(tx_hash))
        events.extend(
            _make_event(
                tx_hash=tx_hash,
                amount='1',
                address=TEST_ADDR2,
                sequence_index=sequence_index,
            ) for sequence_index in range(3)
        )
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=transactions,
            relevant_address=TEST_ADDR1,
        )
        dbevents = DBHistoryEvents(database)
        for event in events:
            dbevents.add_history_event(write_cursor=write_cursor, event=event)

    _write_tracked_address_transfer_issues(database=database, issues_manager=manager)
    assert len(_tracked_transfer_issues(database)) == len(events)
    with database.conn.read_ctx() as cursor:
        stored_rows = cursor.execute('SELECT * FROM data_issues ORDER BY id').fetchall()

    total_changes = database.conn.total_changes
    _write_tracked_address_transfer_issues(database=database, issues_manager=manager)

    assert database.conn.total_changes == total_changes
    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT * FROM data_issues ORDER BY id').fetchall() == stored_rows


def test_discovery_query_uses_the_history_events_index(database: DBHandler) -> None:
    with database.conn.read_ctx() as cursor:
        plan = cursor.execute(
            f'EXPLAIN QUERY PLAN {TRACKED_ADDRESS_TRANSFER_CANDIDATES_QUERY}',
            _tracked_address_transfer_candidates_bindings(
                after_identifier=0,
                limit=DISCOVERY_BATCH_SIZE,
            ),
        ).fetchall()

    details = [row[3] for row in plan]
    assert not any(detail in {'SCAN H', 'SCAN history_events'} for detail in details)
    assert any('idx_history_events_location_label' in detail for detail in details)


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_negative_balance_from_misdecoded_transfer_is_resolved(database: DBHandler) -> None:
    """Reprocessing after the redecode settles a negative balance the misdecode caused."""
    receive_tx, transfer_tx, spend_tx = (
        make_evm_tx_hash(), make_evm_tx_hash(), make_evm_tx_hash(),
    )
    dbtx, dbevents = DBEvmTx(database), DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        dbtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[
                _make_transaction(receive_tx, timestamp=1),
                _make_transaction(transfer_tx, timestamp=2),
                _make_transaction(spend_tx, timestamp=3),
            ],
            relevant_address=TEST_ADDR1,
        )
        dbevents.add_history_event(write_cursor=write_cursor, event=_make_event(
            tx_hash=receive_tx,
            amount='5',
            timestamp=1_000,
            event_type=HistoryEventType.RECEIVE,
        ))
        dbevents.add_history_event(write_cursor=write_cursor, event=_make_event(
            tx_hash=transfer_tx,
            amount='5',
            timestamp=2_000,
            address=TEST_ADDR2,
        ))
        dbevents.add_history_event(write_cursor=write_cursor, event=_make_event(
            tx_hash=spend_tx,
            amount='3',
            timestamp=3_000,
            location_label=TEST_ADDR2,
            address=make_evm_address(),
        ))

    assert process_historical_balances(
        database=database,
        msg_aggregator=database.msg_aggregator,
        chains_aggregator=MagicMock(),
    ) is True
    manager = DataIssuesManager(database)
    negative_issues = manager.list_issues(DataIssueFilters(kind=IssueKind.NEGATIVE_BALANCE))
    assert len(negative_issues) == 1
    assert negative_issues[0].state == IssueState.OPEN

    with database.conn.read_ctx() as cursor:
        assert database.get_static_cache(
            cursor, DBCacheStatic.STALE_BALANCES_FROM_TS,
        ) is None
    decoder = _mock_decoder(database, [_make_event(
        tx_hash=transfer_tx,
        amount='5',
        timestamp=2_000,
        event_type=HistoryEventType.TRANSFER,
        address=TEST_ADDR2,
    )])
    run_data_issue_remediation(
        database=database,
        chains_aggregator=_mock_chains_aggregator(decoder),
    )

    assert manager.get_issue(negative_issues[0].id).state == IssueState.RESOLVED
    assert _tracked_transfer_issues(database)[0].state == IssueState.RESOLVED


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]])
def test_negative_balance_issue_behind_an_earlier_stop_is_not_resolved(
        database: DBHandler,
) -> None:
    """A bucket blocked before the pass never re-evaluates its later event's issue."""
    earlier_tx, later_tx = make_evm_tx_hash(), make_evm_tx_hash()
    dbtx, dbevents = DBEvmTx(database), DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        dbtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[
                _make_transaction(earlier_tx, timestamp=1),
                _make_transaction(later_tx, timestamp=2),
            ],
            relevant_address=TEST_ADDR2,
        )
        dbevents.add_history_event(write_cursor=write_cursor, event=_make_event(
            tx_hash=earlier_tx,
            amount='3',
            timestamp=1_000,
            location_label=TEST_ADDR2,
            address=make_evm_address(),
        ))
        later_event_id = dbevents.add_history_event(write_cursor=write_cursor, event=_make_event(
            tx_hash=later_tx,
            amount='1',
            timestamp=2_000,
            event_type=HistoryEventType.RECEIVE,
            location_label=TEST_ADDR2,
        ))
    assert later_event_id is not None
    assert process_historical_balances(
        database=database,
        msg_aggregator=database.msg_aggregator,
        chains_aggregator=MagicMock(),
    ) is True
    manager = DataIssuesManager(database)
    earlier_issue = manager.list_issues(DataIssueFilters(kind=IssueKind.NEGATIVE_BALANCE))[0]
    later_issue_id = manager.write_issue(
        kind=IssueKind.NEGATIVE_BALANCE,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR2,
        protocol=None,
        asset=A_ETH.identifier,
        payload={
            'event_identifier': later_event_id,
            'in_memory_negative_amount': '-2',
            'derived_balance_before_event': '-3',
        },
        ts_start=2_000,
        ts_end=2_000,
    )

    # rerun from the later event: the retained stop leaves the bucket blocked
    assert process_historical_balances(
        database=database,
        msg_aggregator=database.msg_aggregator,
        from_ts=TimestampMS(2_000),
        chains_aggregator=MagicMock(),
    ) is True

    assert manager.get_issue(earlier_issue.id).state == IssueState.OPEN
    assert manager.get_issue(later_issue_id).state == IssueState.OPEN


def test_dismissed_negative_balance_issue_is_untouched_by_reprocessing(
        database: DBHandler,
) -> None:
    manager = DataIssuesManager(database)
    issue_id = manager.write_issue(
        kind=IssueKind.NEGATIVE_BALANCE,
        location=LOCATION_ETHEREUM,
        location_label=TEST_ADDR1,
        protocol=None,
        asset=A_ETH.identifier,
        payload={
            'event_identifier': 999,
            'in_memory_negative_amount': '-1',
            'derived_balance_before_event': '0',
        },
        ts_start=1_000,
        ts_end=1_000,
    )
    manager.dismiss(issue_id)

    assert process_historical_balances(
        database=database,
        msg_aggregator=database.msg_aggregator,
        chains_aggregator=MagicMock(),
    ) is True

    issue = manager.get_issue(issue_id)
    assert issue.state == IssueState.DISMISSED
    assert issue.resolved_at is None
