import copy
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDC
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import DataIssuesFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.diagnostics import (
    explain_data_issue,
    get_accounting_health,
    list_data_issues,
    trace_bucket,
)
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.remediation import (
    PlanState,
    RemediationError,
    apply_plan,
    get_plan,
    preview_bridge_link,
    preview_redecode,
    reject_plan,
)
from rotkehlchen.history.data_issues.transaction_diagnostics import (
    explain_bridge_match,
    inspect_transaction,
)
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM, LOCATION_KRAKEN, LOCATION_OPTIMISM
from rotkehlchen.tasks.historical_balances import (
    Bucket,
    BucketEffectRule,
    process_historical_balances,
)
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import ChainID, EvmTransaction, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.locations.types import LocationIdentifier
    from rotkehlchen.types import EVMTxHash

pytestmark = pytest.mark.accounting_update

WALLET: Bucket = Bucket(
    location=LOCATION_ETHEREUM,
    location_label=TEST_ADDR1,
    protocol=None,
    asset=A_ETH.identifier,
)


def _event(
        timestamp: int,
        event_type: HistoryEventType,
        amount: str,
        location: LocationIdentifier = LOCATION_ETHEREUM,
        event_subtype: HistoryEventSubType = HistoryEventSubType.NONE,
        sequence_index: int = 0,
        tx_hash: EVMTxHash | None = None,
        **kwargs: object,
) -> EvmEvent:
    return EvmEvent(
        tx_ref=make_evm_tx_hash() if tx_hash is None else tx_hash,
        sequence_index=sequence_index,
        timestamp=TimestampMS(timestamp),
        location=location,
        event_type=event_type,
        event_subtype=event_subtype,
        asset=A_ETH,
        amount=FVal(amount),
        location_label=TEST_ADDR1,
        **kwargs,  # type: ignore[arg-type]
    )


def _add(database: DBHandler, events: list[EvmEvent], customized: bool = False) -> list[int]:
    with database.user_write() as write_cursor:
        return [DBHistoryEvents(database).add_history_event(  # type: ignore[misc]
            write_cursor=write_cursor,
            event=event,
            mapping_values=(
                {HISTORY_MAPPING_KEY_STATE: HistoryMappingState.CUSTOMIZED}
                if customized else None
            ),
        ) for event in events]


def _issues(database: DBHandler, kind: IssueKind) -> list[int]:
    return [issue.id for issue in DataIssuesManager(database).list_issues(
        DataIssuesFilterQuery.make(kinds=[kind]),
    )]


def test_trace_and_explain_decimal_residue_stop(database: DBHandler) -> None:
    """A one-wei shortfall stops the bucket. The trace keeps it exact and the explanation
    calls it decimal residue as a hypothesis, while the stop itself is a fact."""
    receive_id, _, spend_id, later_id = _add(database, [
        _event(1_000, HistoryEventType.RECEIVE, '1'),
        _event(2_000, HistoryEventType.SPEND, '0.4'),
        _event(3_000, HistoryEventType.SPEND, '0.600000000000000001'),
        _event(4_000, HistoryEventType.RECEIVE, '5'),
    ])
    assert get_accounting_health(database)['status'] == 'unprocessed'
    process_historical_balances(database=database, msg_aggregator=database.msg_aggregator)

    trace = trace_bucket(database=database, bucket=WALLET, offset=0)
    assert [
        (row['status'], row['rule'], row['signed_amount'], row['balance_after'], row['stored_balance'])  # noqa: E501
        for row in trace['rows']
    ] == [
        ('applied', 'wallet', '1', '1', '1'),
        ('applied', 'wallet', '-0.4', '0.6', '0.6'),
        ('stop', 'wallet', '-0.600000000000000001', '-0.000000000000000001', None),
        ('skipped_after_stop', 'wallet', '5', '-0.000000000000000001', None),
    ]
    assert trace['summary']['stop_row_index'] == 2
    assert trace['summary']['stored_balance_mismatches'] == 0
    assert trace['stop']['event_identifier'] == spend_id
    assert trace['rows'][0]['event_identifier'] == receive_id

    health = get_accounting_health(database)
    assert health['status'] == 'blocked'
    assert health['stops']['count'] == 1
    assert health['stops']['entries'][0]['negative_amount'] == '-0.000000000000000001'

    issue_id, = _issues(database, IssueKind.NEGATIVE_BALANCE)
    explanation = explain_data_issue(database=database, issue_id=issue_id)
    assert explanation['facts']['shortfall'] == '0.000000000000000001'
    assert explanation['facts']['derived_balance_before_event'] == '0.6'
    assert explanation['facts']['bucket_stopped_at_this_event'] is True
    assert explanation['trigger_event']['rule'] == BucketEffectRule.WALLET
    assert explanation['affected_later_history']['events_not_applied'] == 1
    assert [x['code'] for x in explanation['hypotheses']] == ['decimal_residue']
    assert explanation['confirmed_conflicts'] == []
    assert later_id not in {x['event_identifier'] for x in explanation['same_transaction_effects_on_bucket']}  # noqa: E501

    DataIssuesManager(database).dismiss(issue_id)  # dismissing must not look like a repair
    assert [x['code'] for x in explain_data_issue(
        database=database,
        issue_id=issue_id,
    )['confirmed_conflicts']] == ['closed_issue_but_bucket_still_stopped']
    assert get_accounting_health(database)['status'] == 'blocked'


def test_effects_report_the_deciding_rule() -> None:
    assert Bucket.effects_with_rule(_event(
        1,
        HistoryEventType.TRANSFER,
        '1',
        event_subtype=HistoryEventSubType.NONE,
        address=TEST_ADDR2,
    ))[0] == BucketEffectRule.OWNED_ADDRESS_TRANSFER
    assert Bucket.effects_with_rule(HistoryEvent(
        group_identifier='x',
        sequence_index=0,
        timestamp=TimestampMS(1),
        location=LOCATION_KRAKEN,
        event_type=HistoryEventType.TRANSFER,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal(1),
    )) == (BucketEffectRule.IGNORED_EXCHANGE_TRANSFER, [])
    assert Bucket.effects_with_rule(_event(
        1,
        HistoryEventType.INFORMATIONAL,
        '1',
    )) == (BucketEffectRule.NO_BALANCE_DIRECTION, [])


def test_list_data_issues_groups_issues_of_one_transaction(database: DBHandler) -> None:
    tx_hash = make_evm_tx_hash()
    first_id, second_id = _add(database, [
        _event(1_000, HistoryEventType.SPEND, '1', tx_hash=tx_hash),
        _event(1_000, HistoryEventType.SPEND, '1', tx_hash=tx_hash, sequence_index=1),
    ])
    manager = DataIssuesManager(database)
    for event_id, label in ((first_id, TEST_ADDR1), (second_id, TEST_ADDR2)):
        manager.write_issue(
            IssueKind.NEGATIVE_BALANCE,
            location=LOCATION_ETHEREUM,
            location_label=label,
            protocol=None,
            asset=A_ETH.identifier,
            payload={
                'event_identifier': event_id,
                'in_memory_negative_amount': '-1',
                'derived_balance_before_event': '0',
            },
            ts_start=1_000,
            ts_end=1_000,
        )

    result = list_data_issues(database, DataIssuesFilterQuery.make())
    assert result['entries_found'] == 2
    group, = result['groups']
    assert group['shared_cause'] == 'hypothesis'
    assert len(group['issue_ids']) == 2


def _add_bridge_scenario(database: DBHandler) -> tuple[int, int, dict[str, int]]:
    """A funded bridge deposit and candidates that each fail one check, plus one eligible."""
    _, bridge_id, eligible_id, same_chain_id, wrong_amount_id, late_id = _add(database, [
        _event(1_000, HistoryEventType.RECEIVE, '2'),
        _event(1_000_000, HistoryEventType.DEPOSIT, '1', event_subtype=HistoryEventSubType.BRIDGE),
        _event(1_060_000, HistoryEventType.RECEIVE, '0.995', location=LOCATION_OPTIMISM),
        _event(1_060_000, HistoryEventType.RECEIVE, '1'),
        _event(1_070_000, HistoryEventType.RECEIVE, '0.5', location=LOCATION_OPTIMISM),
        _event(1_000_000 + 5 * 3600 * 1000, HistoryEventType.RECEIVE, '1', location=LOCATION_OPTIMISM),  # noqa: E501
    ])
    return bridge_id, eligible_id, {
        'same_location': same_chain_id,
        'amount_mismatch': wrong_amount_id,
        'outside_time_window': late_id,
    }


def test_explain_bridge_match_reports_rejections(database: DBHandler) -> None:
    bridge_id, eligible_id, rejected = _add_bridge_scenario(database)
    result = explain_bridge_match(database, bridge_id)
    assert result is not None
    assert result['conclusion'] == 'unique_eligible_candidate'
    assert result['eligible_count'] == 1
    by_id = {x['event_identifier']: x for x in result['candidates']}
    assert by_id[eligible_id]['tier'] == 'other'
    assert by_id[eligible_id]['amount_difference'] == '-0.005'
    assert {reason: by_id[event_id]['rejection'] for reason, event_id in rejected.items()} == {
        reason: reason for reason in rejected
    }
    assert 'transfer_id' in result['missing_metadata']
    assert explain_bridge_match(database, eligible_id) is None  # not a bridge leg


def test_bridge_link_plan_lifecycle(database: DBHandler) -> None:
    """Preview, refuse without approval, apply once, verify and refuse a second apply."""
    bridge_id, eligible_id, rejected = _add_bridge_scenario(database)
    process_historical_balances(database=database, msg_aggregator=database.msg_aggregator)
    unmatched_issue, = _issues(database, IssueKind.UNMATCHED_BRIDGE)

    with pytest.raises(RemediationError, match='rejects this candidate') as error:
        preview_bridge_link(database, bridge_id, rejected['amount_mismatch'])
    assert error.value.code == 'candidate_rejected'

    plan = preview_bridge_link(database, bridge_id, eligible_id)
    assert plan['state'] == PlanState.PENDING
    assert plan['plan']['baseline']['open_issue_ids'] == [unmatched_issue]
    assert [x['action'] for x in plan['audit']] == ['created']

    with pytest.raises(RemediationError) as error:
        apply_plan(database, MagicMock(), plan['plan_id'], 'agent_says_yes', ts_now())
    assert error.value.code == 'approval_required'

    result = apply_plan(database, MagicMock(), plan['plan_id'], 'mcp_elicitation', ts_now())
    assert result['state'] == PlanState.APPLIED
    assert result['result']['items'][0]['outcome'] == 'applied'
    assert result['result']['reprocessing'] == 'completed'
    assert result['verification']['reevaluated'] is True
    assert result['verification']['baseline_issues'] == [
        {'issue_id': unmatched_issue, 'state': IssueState.RESOLVED},
    ]
    assert [x['action'] for x in result['audit']] == ['created', 'approved', 'applied', 'verified']
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT left_event_id, right_event_id FROM history_event_links',
        ).fetchall() == [(bridge_id, eligible_id)]

    with pytest.raises(RemediationError) as error:
        apply_plan(database, MagicMock(), plan['plan_id'], 'mcp_elicitation', ts_now())
    assert error.value.code == 'plan_not_pending'


def test_plan_refused_when_stale_expired_or_rejected(database: DBHandler) -> None:
    bridge_id, eligible_id, _ = _add_bridge_scenario(database)
    stale_plan = preview_bridge_link(database, bridge_id, eligible_id)
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'UPDATE history_events SET amount = ? WHERE identifier = ?',
            ('0.996', eligible_id),
        )
    with pytest.raises(RemediationError) as error:
        apply_plan(database, MagicMock(), stale_plan['plan_id'], 'mcp_elicitation', ts_now())
    assert error.value.code == 'plan_stale'
    assert get_plan(database, stale_plan['plan_id'])['state'] == PlanState.STALE

    expired_plan = preview_bridge_link(database, bridge_id, eligible_id)
    with patch('rotkehlchen.history.data_issues.remediation.ts_now', return_value=ts_now() + 3600):
        assert get_plan(database, expired_plan['plan_id'])['state'] == PlanState.EXPIRED
        with pytest.raises(RemediationError) as error:
            apply_plan(database, MagicMock(), expired_plan['plan_id'], 'mcp_elicitation', ts_now())
    assert error.value.code == 'plan_expired'

    rejected_plan = preview_bridge_link(database, bridge_id, eligible_id)
    assert reject_plan(database, rejected_plan['plan_id'], 'user_decline')['state'] == PlanState.REJECTED  # noqa: E501
    with pytest.raises(RemediationError) as error:
        apply_plan(database, MagicMock(), rejected_plan['plan_id'], 'mcp_elicitation', ts_now())
    assert error.value.code == 'plan_not_pending'
    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM history_event_links').fetchone()[0] == 0


@pytest.mark.parametrize('customized', [False, True])
def test_redecode_plan_repairs_a_wrong_direction(database: DBHandler, customized: bool) -> None:
    """A receive saved as a spend stops the bucket. Redecoding it clears the stop, which the
    verification reads from the stops. A customized transaction is only replaced on request."""
    tx_hash = make_evm_tx_hash()
    saved_id, = _add(database, [
        _event(1_000, HistoryEventType.SPEND, '1', tx_hash=tx_hash),
    ], customized=customized)
    process_historical_balances(database=database, msg_aggregator=database.msg_aggregator)
    issue_id, = _issues(database, IssueKind.NEGATIVE_BALANCE)
    decoded = [_event(1_000, HistoryEventType.RECEIVE, '1', tx_hash=tx_hash)]

    def fake_redecode(ignore_cache: bool, tx_hashes: list, delete_customized: bool) -> None:
        assert (ignore_cache, tx_hashes, delete_customized) == (True, [tx_hash], customized)
        with database.user_write() as write_cursor:
            write_cursor.execute('DELETE FROM history_events WHERE identifier = ?', (saved_id,))
            DBHistoryEvents(database).add_history_events(write_cursor, copy.deepcopy(decoded))

    chains_aggregator = MagicMock()
    decoder = chains_aggregator.get_evm_manager.return_value.transactions_decoder
    decoder.possible_decoding_exceptions = ()
    decoder.decode_transaction_hashes.side_effect = fake_redecode
    group = decoded[0].group_identifier
    with patch(
        'rotkehlchen.history.data_issues.remediation.preview_transaction',
        return_value=copy.deepcopy(decoded),
    ):
        blocked = preview_redecode(database, chains_aggregator, [group], replace_customized=False)
        plan = preview_redecode(database, chains_aggregator, [group], replace_customized=True)

    item, = blocked['plan']['items']
    assert item['status'] == ('blocked_by_customization' if customized else 'ready')
    assert item['bucket_effect_diff'] == [{
        'bucket': {
            'location': LOCATION_ETHEREUM,
            'location_label': TEST_ADDR1,
            'protocol': None,
            'asset': A_ETH.identifier,
        },
        'current_net': '-1',
        'proposed_net': '1',
        'difference': '2',
    }]
    assert item['event_diff']['changed'][0]['changed_fields'] == ['event_type']
    assert blocked['plan']['baseline']['open_issue_ids'] == [issue_id]
    if customized:
        with pytest.raises(RemediationError) as error:
            apply_plan(database, chains_aggregator, blocked['plan_id'], 'mcp_elicitation', ts_now())  # noqa: E501
        assert error.value.code == 'nothing_to_apply'

    result = apply_plan(database, chains_aggregator, plan['plan_id'], 'mcp_elicitation', ts_now())
    assert result['result']['items'] == [{'group_identifier': group, 'outcome': 'applied'}]
    assert result['verification']['verdict'] == 'repaired'
    assert result['verification']['buckets'][0]['outcome'] == 'stop_cleared'
    assert get_accounting_health(database)['stops']['count'] == 0


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1]])
def test_inspect_transaction_compares_receipt_transfers(database: DBHandler) -> None:
    """The receipt moved 100 USDC to the account but the saved event records 90."""
    tx_hash = make_evm_tx_hash()
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[EvmTransaction(
                tx_hash=tx_hash,
                chain_id=ChainID.ETHEREUM,
                timestamp=Timestamp(1),
                block_number=1,
                from_address=TEST_ADDR2,
                to_address=(usdc_address := string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')),  # noqa: E501
                value=0,
                gas=21_000,
                gas_price=0,
                gas_used=0,
                input_data=b'',
                nonce=0,
            )],
            relevant_address=TEST_ADDR1,
        )
        DBEvmTx(database).add_or_ignore_receipt_data(write_cursor, ChainID.ETHEREUM, {
            'transactionHash': str(tx_hash),
            'type': '0x0',
            'status': 1,
            'contractAddress': None,
            'logs': [{
                'logIndex': 0,
                'data': '0x' + (100_000_000).to_bytes(32, 'big').hex(),
                'address': usdc_address,
                'topics': [
                    '0x' + ERC20_OR_ERC721_TRANSFER.hex(),
                    '0x' + '00' * 12 + TEST_ADDR2[2:],
                    '0x' + '00' * 12 + TEST_ADDR1[2:],
                ],
            }],
        })
    _add(database, [received := EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(1_000),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_USDC,
        amount=FVal(90),
        location_label=TEST_ADDR1,
    )], customized=True)

    result = inspect_transaction(database, received.group_identifier)
    assert result is not None
    assert result['customized'] is True
    assert result['events'][0]['rule'] == BucketEffectRule.WALLET
    assert result['receipt_comparison']['discrepancies'] == [{
        'account': TEST_ADDR1,
        'asset': A_USDC.identifier,
        'observed_net': '100',
        'decoded_net': '90',
        'difference': '10',
    }]
    assert inspect_transaction(database, 'missing') is None
