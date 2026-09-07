from dataclasses import replace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock, patch

import pytest
from freezegun import freeze_time

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.data_issues import run_data_issue_remediation
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import ChainID, EvmTransaction, Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.concurrency import Task
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.tasks.manager import TaskManager
    from rotkehlchen.types import EVMTxHash

pytestmark = pytest.mark.accounting_update


def _make_event(
        tx_hash: EVMTxHash,
        amount: str,
        timestamp: int = 1_000,
        event_type: HistoryEventType = HistoryEventType.SPEND,
        location_label: str = TEST_ADDR1,
) -> EvmEvent:
    return EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(timestamp),
        location=Location.ETHEREUM,
        event_type=event_type,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal(amount),
        location_label=location_label,
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
        location=Location.ETHEREUM.serialize_for_db(),
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


def _wait_for_background_task(tasks: list[Task] | None) -> None:
    assert tasks is not None
    assert len(tasks) == 1
    task = tasks[0]
    task.join(timeout=10)
    assert task.dead, f'{task.task_name} did not finish'
    task.get()


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
        request: pytest.FixtureRequest,
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
            location=Location.ETHEREUM,
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
    assert {key: value for key, value in attempt.items() if key != 'reason'} == {
        'attribution': 'system',
        'strategy': 'redecode_customized_transactions',
        'timestamp': ts_now(),
        'result': 'redecoding_failed' if missing_receipt else expected_result,
        'customized_transaction_count': 1,
        'changed_transaction_count': int(not missing_receipt and decoded_spend != 11),
    }
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
            request.applymarker(pytest.mark.xfail(
                strict=True,
                reason='Step 5: unresolved failed comparisons are not retried yet',
            ))
            assert len(issue.auto_remediation_attempts) == 2
            assert issue.auto_remediation_attempts[0] == attempt
            assert issue.auto_remediation_attempts[1] == {
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
    assert issue.auto_remediation_attempts == [{
        'attribution': 'system',
        'strategy': 'redecode_customized_transactions',
        'timestamp': issue.auto_remediation_attempts[0]['timestamp'],
        'result': expected_result,
        'customized_transaction_count': 1,
        'changed_transaction_count': expected_changed,
    }]
    assert _get_saved_event_rows(database) == saved_rows


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
        location=Location.ETHEREUM.serialize_for_db(),
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


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1]])
@pytest.mark.parametrize('rule_stage', [
    'address', 'input', 'event', 'post_decoding', 'enrichment',
])
@pytest.mark.parametrize('error_type', [RemoteError, ValueError])
def test_decoder_rule_failure_is_reported_as_failed_comparison(
        database: DBHandler,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        rule_stage: str,
        error_type: type[Exception],
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
    failing_rule = Mock(__name__='failing_rule', side_effect=error_type('rule unavailable'))
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
        assert any('failed' in message for message in decoder.msg_aggregator.consume_errors())
