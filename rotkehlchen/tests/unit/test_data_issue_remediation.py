from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.data_issues import run_data_issue_remediation
from rotkehlchen.tasks.historical_balances import process_historical_balances
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import ChainID, EvmTransaction, Location, Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import EVMTxHash
    from rotkehlchen.user_messages import MessagesAggregator

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


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1]])
def test_negative_balance_customized_spend_is_compared_with_real_decoder(
        database: DBHandler,
        messages_aggregator: MessagesAggregator,
        ethereum_transaction_decoder: EthereumTransactionDecoder,
) -> None:
    receive_tx_hash, spend_tx_hash = make_evm_tx_hash(), make_evm_tx_hash()
    spend_transaction = EvmTransaction(
        tx_hash=spend_tx_hash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(2),
        block_number=1,
        from_address=TEST_ADDR1,
        to_address=TEST_ADDR2,
        value=5 * 10**18,
        gas=21_000,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    dbevents, dbtx = DBHistoryEvents(database), DBEvmTx(database)
    with database.user_write() as write_cursor:
        dbtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[spend_transaction],
            relevant_address=TEST_ADDR1,
        )
        dbtx.add_or_ignore_receipt_data(write_cursor, ChainID.ETHEREUM, {
            'transactionHash': spend_tx_hash.hex(),
            'type': '0x0',
            'status': 1,
            'contractAddress': None,
            'logs': [],
        })
        dbevents.add_history_event(
            write_cursor=write_cursor,
            event=_make_event(
                tx_hash=receive_tx_hash,
                amount='10',
                event_type=HistoryEventType.RECEIVE,
            ),
        )
        spend_event_id = dbevents.add_history_event(
            write_cursor=write_cursor,
            event=_make_event(tx_hash=spend_tx_hash, amount='11', timestamp=2_000),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED},
        )
    assert spend_event_id is not None

    process_historical_balances(database=database, msg_aggregator=messages_aggregator)
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

    chains_aggregator = MagicMock()
    chains_aggregator.get_evm_manager.return_value.transactions_decoder = (
        ethereum_transaction_decoder
    )
    run_data_issue_remediation(
        database=database,
        chains_aggregator=chains_aggregator,
    )

    issue = issues_manager.get_issue(issues[0].id)
    assert issue.state == IssueState.UNRESOLVED
    assert issue.auto_remediation_attempts == [{
        'attribution': 'system',
        'strategy': 'redecode_customized_transactions',
        'timestamp': issue.auto_remediation_attempts[0]['timestamp'],
        'result': 'redecoding_would_change_balance',
        'customized_transaction_count': 1,
        'changed_transaction_count': 1,
    }]
    assert _get_saved_event_rows(database) == saved_rows


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
