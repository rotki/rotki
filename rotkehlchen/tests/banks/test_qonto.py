"""Qonto-specific behaviour on top of the contract suite"""
import json

import pytest

from rotkehlchen.banks.errors import BankSchemaDrift
from rotkehlchen.banks.normalization import BankTransactionKind
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.tests.utils.banks import (
    BANK_FIXTURES_DIR,
    QontoFixtureTransport,
    patch_bank_transport,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ApiKey, ApiSecret, ExchangeAuthCredentials, Location, Timestamp
from rotkehlchen.utils.misc import ts_now


def test_declined_transactions_are_not_ingested(qonto):
    transport = QontoFixtureTransport()
    assert len([t for t in transport.transactions if t['status'] == 'declined']) == 1
    with patch_bank_transport(qonto, transport):
        events, _ = qonto.query_online_history_events(Timestamp(0), ts_now())
    assert len(events) == len(transport.transactions) - 1
    assert all(
        params.get('status[]') == 'completed'
        for path, params in transport.requests if path.endswith('/transactions')
    ), 'only final transactions are ever requested'


def test_event_mapping_per_operation_type(qonto):
    transport = QontoFixtureTransport()
    with patch_bank_transport(qonto, transport):
        events, _ = qonto.query_online_history_events(Timestamp(0), ts_now())
    raw_by_group_id = {
        create_group_identifier_from_unique_id(Location.QONTO, t['id']): t
        for t in transport.transactions
    }
    assert len(events) == 28
    for event in events:
        raw = raw_by_group_id[event.group_identifier]
        assert event.asset == A_EUR
        assert event.amount == FVal(raw['amount_cents']) / 100
        assert event.extra_data['bank_account_id'] == raw['bank_account_id']
        if raw['side'] == 'credit':
            assert event.event_type == HistoryEventType.RECEIVE
            assert event.event_subtype == HistoryEventSubType.NONE
            assert event.notes.startswith(f'Receive {event.amount} EUR from {raw["label"]}')
            assert event.extra_data['kind'] == BankTransactionKind.TRANSFER.serialize()
        elif raw['operation_type'] == 'qonto_fee':
            assert event.event_type == HistoryEventType.SPEND
            assert event.event_subtype == HistoryEventSubType.FEE
            assert event.notes.startswith(f'Pay {event.amount} EUR as qonto fee')
            assert event.extra_data['kind'] == BankTransactionKind.FEE.serialize()
        else:
            assert event.event_type == HistoryEventType.SPEND
            assert event.event_subtype == HistoryEventSubType.NONE
            assert event.notes.startswith(f'Send {event.amount} EUR to {raw["label"]}')
            assert event.extra_data['counterparty_account'] == raw['transfer']['counterparty_account_number']  # noqa: E501
        if raw['reference']:
            assert event.extra_data['reference'] == raw['reference']
            assert f'with reference: {raw["reference"]}' in event.notes


def test_events_reconcile_with_account_balance(qonto):
    """Signed completed amounts add up to the account's settled balance"""
    transport = QontoFixtureTransport()
    with patch_bank_transport(qonto, transport):
        events, _ = qonto.query_online_history_events(Timestamp(0), ts_now())
        accounts = qonto.query_accounts()
    total = sum(
        (e.amount if e.event_type == HistoryEventType.RECEIVE else -e.amount for e in events),
        start=FVal(0),
    )
    assert total == accounts[0].balance


def test_unknown_status_is_reported_once_and_skipped(qonto, function_scope_messages_aggregator):
    transport = QontoFixtureTransport()
    with patch_bank_transport(qonto, transport):
        account = qonto.query_accounts()[0]
    for tx in transport.transactions[:2]:
        assert qonto._deserialize_transaction({**tx, 'status': 'teleported'}, account) is None
    warnings = function_scope_messages_aggregator.consume_warnings()
    assert len(warnings) == 1, 'reported once, not per transaction'
    assert 'teleported' in warnings[0]


def test_unknown_operation_type_is_ingested_as_other(qonto, function_scope_messages_aggregator):
    transport = QontoFixtureTransport()
    with patch_bank_transport(qonto, transport):
        account = qonto.query_accounts()[0]
    tx = next(t for t in transport.transactions if t['status'] == 'completed')
    transaction = qonto._deserialize_transaction({**tx, 'operation_type': 'holo_pay'}, account)
    assert transaction is not None
    assert transaction.kind == BankTransactionKind.OTHER
    assert 'holo_pay' in function_scope_messages_aggregator.consume_warnings()[0]


def test_missing_key_is_schema_drift_without_values(qonto):
    transport = QontoFixtureTransport()
    with patch_bank_transport(qonto, transport):
        account = qonto.query_accounts()[0]
    entry = dict(transport.transactions[0])
    del entry['settled_at']
    with pytest.raises(BankSchemaDrift) as drift:
        qonto._deserialize_transaction(entry, account)
    assert drift.value.context['endpoint'] == 'transactions'
    assert 'settled_at' not in drift.value.context['keys']
    assert entry['label'] not in str(drift.value)
    assert entry['id'] not in str(drift.value)


def test_unknown_currency_account_is_skipped(qonto, function_scope_messages_aggregator):
    transport = QontoFixtureTransport()
    transport.organization = json.loads(
        (BANK_FIXTURES_DIR / 'qonto' / 'organization.json').read_text(encoding='utf8'),
    )
    transport.organization['organization']['bank_accounts'][0]['currency'] = 'XXX'
    with patch_bank_transport(qonto, transport):
        assert qonto.query_accounts() == []


def test_auth_header_follows_credential_edits(qonto):
    assert qonto.session.headers['Authorization'] == 'test-login:test-secret'
    qonto.edit_exchange_credentials(ExchangeAuthCredentials(
        api_key=ApiKey('new-login'),
        api_secret=ApiSecret(b'new-secret'),
        passphrase=None,
    ))
    assert qonto.session.headers['Authorization'] == 'new-login:new-secret'


def test_rate_limit_backoff_then_success(qonto):
    transport = QontoFixtureTransport()
    calls = {'n': 0}
    original = transport.route

    def flaky(path, params):
        calls['n'] += 1
        if calls['n'] == 1:
            return MockResponse(429, '{}', headers={'Retry-After': '0'})
        return original(path, params)

    transport.route = flaky
    with patch_bank_transport(qonto, transport):
        accounts = qonto.query_accounts()
    assert len(accounts) == 1
    assert calls['n'] == 2
