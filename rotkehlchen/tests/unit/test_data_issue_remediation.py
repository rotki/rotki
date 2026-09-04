from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.data_issues import run_data_issue_remediation
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import EVMTxHash

pytestmark = pytest.mark.accounting_update


def _make_event(
        tx_hash: EVMTxHash,
        amount: str,
        timestamp: int = 1_000,
        event_type: HistoryEventType = HistoryEventType.SPEND,
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
        location_label=TEST_ADDR1,
        notes='saved customized event',
    )


def _add_negative_balance_issue(
        database: DBHandler,
        customized: bool,
) -> tuple[int, EVMTxHash]:
    tx_hash = make_evm_tx_hash()
    with database.user_write() as write_cursor:
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
    dbevents = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
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
