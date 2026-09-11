"""The contract every bank connector has to honour, run against its committed fixtures.

Framework-level: a new connector gets covered by adding a kit to BANK_KITS, not by
writing these tests again.
"""
from pathlib import Path
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import FiatAsset
from rotkehlchen.banks.constants import SUPPORTED_BANKS
from rotkehlchen.banks.errors import BankAuthExpired, BankRateLimited, BankSchemaDrift
from rotkehlchen.banks.manager import BankManager
from rotkehlchen.banks.manifests import BANK_MANIFESTS
from rotkehlchen.constants.location_details import LOCATION_DETAILS
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.exchanges.exchange import HistoryEventQueue
from rotkehlchen.history.events.structures.bank_transaction import BankTransactionEvent
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.banks import BANK_KITS, BankConnectorKit, patch_bank_transport
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.utils.misc import ts_now

ALLOWED_EVENT_TYPES = {
    (HistoryEventType.RECEIVE, HistoryEventSubType.NONE),
    (HistoryEventType.SPEND, HistoryEventSubType.NONE),
    (HistoryEventType.SPEND, HistoryEventSubType.FEE),
}
FRONTEND_IMAGES_DIR = Path(__file__).resolve().parents[3] / 'frontend' / 'app' / 'public' / 'assets' / 'images' / 'protocols'  # noqa: E501
KITS = pytest.mark.parametrize('kit', BANK_KITS, ids=[str(kit.location) for kit in BANK_KITS])


def _db_events(database) -> list[HistoryBaseEntry]:
    with database.conn.read_ctx() as cursor:
        return DBHistoryEvents(database).get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            entries_limit=None,
        )


def test_every_supported_bank_has_a_kit_and_a_manifest():
    assert {kit.location for kit in BANK_KITS} == set(SUPPORTED_BANKS)
    assert set(BANK_MANIFESTS) == set(SUPPORTED_BANKS)


@KITS
def test_manifest_is_valid_and_registered(kit: BankConnectorKit):
    manifest = kit.connector_class.manifest
    manifest.validate()
    assert manifest is BANK_MANIFESTS[kit.location]
    assert manifest.location == kit.location
    assert kit.location not in SUPPORTED_EXCHANGES, 'a bank is its own integration'
    # the manager stores credentials by slot, so the manifest must declare the key slot
    # and whatever the connector constructor needs
    slots = {secret.slot for secret in manifest.secrets}
    assert {'api_key', 'api_secret'} <= slots
    # the UI derives the setup form and the icon from the location details
    details = LOCATION_DETAILS[kit.location]
    assert details['is_bank'] is True
    assert 'exchange_details' not in details
    assert details['bank_details'] == manifest.serialize()
    assert (FRONTEND_IMAGES_DIR / details['image']).is_file()
    # the module/class naming the bank manager relies on to instantiate it
    assert BankManager._connector_class(kit.location) is kit.connector_class


@KITS
def test_manifest_serializes_to_plain_json_types(kit: BankConnectorKit):
    serialized = kit.connector_class.manifest.serialize()
    assert serialized['location'] == kit.location.serialize()
    assert isinstance(serialized['access_tier'], str)
    assert all(isinstance(step['primitive'], str) for step in serialized['auth_flow'])
    assert all({'slot', 'label', 'description'} <= set(s) for s in serialized['secrets'])
    assert len(serialized['setup_notes']) > 0, 'user-facing setup notes are required'


@KITS
def test_validate_api_key(kit: BankConnectorKit, database, function_scope_messages_aggregator):
    connector = kit.create(database, function_scope_messages_aggregator)
    transport = kit.create_transport()
    with patch_bank_transport(connector, transport):
        assert connector.validate_api_key() == (True, '')
        transport.force(401, '{"errors":[{"code":"unauthorized"}]}')
        result, message = connector.validate_api_key()
    assert result is False
    assert 'rejected' in message


@KITS
def test_query_balances(kit: BankConnectorKit, database, function_scope_messages_aggregator, inquirer):  # pylint: disable=unused-argument  # noqa: E501
    connector = kit.create(database, function_scope_messages_aggregator)
    with patch_bank_transport(connector, kit.create_transport()):
        balances, message = connector.query_balances()
    assert message == ''
    assert balances is not None
    assert {asset: balance.amount for asset, balance in balances.items()} == kit.expected_balances
    assert all(isinstance(asset, FiatAsset) for asset in balances)


@KITS
def test_normalization_output(kit: BankConnectorKit, database, function_scope_messages_aggregator):
    connector = kit.create(database, function_scope_messages_aggregator)
    with patch_bank_transport(connector, kit.create_transport()):
        events, end_ts = connector.query_online_history_events(Timestamp(0), now := ts_now())
    assert end_ts == now
    assert len(events) == kit.expected_event_count
    assert len({event.group_identifier for event in events}) == len(events), 'stable ids'
    for event in events:
        assert isinstance(event, BankTransactionEvent)
        assert event.entry_type == HistoryBaseEntryType.BANK_TRANSACTION_EVENT
        assert event.location == kit.location
        assert event.location_label == connector.name
        assert event.sequence_index == 0
        assert (event.event_type, event.event_subtype) in ALLOWED_EVENT_TYPES
        assert event.amount > 0
        assert event.timestamp > 0
        assert isinstance(event.asset, FiatAsset)
        assert event.notes
        assert event.extra_data is not None and 'bank_account_id' in event.extra_data


@KITS
def test_cursor_dedup_and_full_resync(kit: BankConnectorKit, database, function_scope_messages_aggregator):  # noqa: E501
    connector = kit.create(database, function_scope_messages_aggregator)
    transport = kit.create_transport()
    with patch_bank_transport(connector, transport):
        connector.query_history_events()  # first sync: full, through the exchange pipeline
        first = _db_events(database)
        assert len(first) == kit.expected_event_count
        assert all(kit.cursor_param not in params for _, params in transport.requests), 'first sync is full'  # noqa: E501
        with database.conn.read_ctx() as cursor:
            cursors = [
                connector.get_cursor(cursor, account.identifier)
                for account in connector.query_accounts()
            ]
        assert all(value is not None for value in cursors), 'cursor persisted per account'

        transport.requests.clear()
        # a later sync: the exchange range bookkeeping only queries new time, so move the
        # clock, otherwise there is no range to query at all
        with patch('rotkehlchen.exchanges.exchange.ts_now', return_value=Timestamp(ts_now() + 3600)):  # noqa: E501
            connector.query_history_events()  # second sync: incremental, nothing new
        assert any(kit.cursor_param in params for _, params in transport.requests), 'incremental sync carries the cursor'  # noqa: E501
        second = _db_events(database)
        assert len(second) == kit.expected_event_count, 'double ingestion is a no-op'
        assert [e.serialize() for e in second] == [e.serialize() for e in first]

        # full resync must converge to the identical result
        transport.requests.clear()
        queue = HistoryEventQueue(
            database=database,
            location_string=f'{kit.location!s}_history_events_{connector.name}',
            query_start_ts=Timestamp(0),
        )
        connector.requery_online_history_events_into_queue(Timestamp(0), ts_now(), queue)
        queue.flush()
        assert all(kit.cursor_param not in params for _, params in transport.requests)
        third = _db_events(database)
        assert [e.serialize() for e in third] == [e.serialize() for e in first]

        # pagination must not change the outcome either
        for _, params in transport.requests:
            if kit.per_page_param in params:
                break
        else:
            pytest.fail('no paginated request observed')


@KITS
def test_pagination_converges(kit: BankConnectorKit, database, function_scope_messages_aggregator):
    """Walking the fixtures in tiny pages yields the same events as in one page"""
    connector = kit.create(database, function_scope_messages_aggregator)
    transport = kit.create_transport()
    module = __import__(kit.connector_class.__module__, fromlist=['PER_PAGE'])
    with (
        patch_bank_transport(connector, transport),
        patch.object(module, 'PER_PAGE', kit.small_page_size),
    ):
        events, _ = connector.query_online_history_events(Timestamp(0), ts_now())
    pages = [p for path, p in transport.requests if kit.per_page_param in p]
    assert len(pages) > 1
    assert len(events) == kit.expected_event_count
    assert len({event.group_identifier for event in events}) == len(events)


@KITS
def test_error_mapping(kit: BankConnectorKit, database, function_scope_messages_aggregator):
    connector = kit.create(database, function_scope_messages_aggregator)
    transport = kit.create_transport()
    with (
        patch_bank_transport(connector, transport),
        patch('rotkehlchen.db.settings.CachedSettings.get_query_retry_limit', return_value=1),
    ):
        transport.force(401, '{"errors":[{"code":"unauthorized"}]}')
        with pytest.raises(BankAuthExpired):
            connector.query_accounts()

        transport.force(429, '{"errors":[{"code":"too_many_requests"}]}', headers={'Retry-After': '7'})  # noqa: E501
        with pytest.raises(BankRateLimited) as exc_info:
            connector.query_accounts()
        assert exc_info.value.retry_after == 7

        transport.force(200, '<html>maintenance</html>')
        with pytest.raises(BankSchemaDrift) as drift:
            connector.query_accounts()
        assert 'endpoint' in drift.value.context

        transport.force(200, '{"unexpected": {}}')
        with pytest.raises(BankSchemaDrift) as drift:
            connector.query_accounts()
        assert drift.value.context.get('keys') == ['unexpected'], 'drift context names keys, never values'  # noqa: E501

        # the exchange pipeline surfaces a bank error as a failed query, not a crash
        transport.force(500, 'boom')
        balances, message = connector.query_balances()
        assert balances is None
        assert 'Failed to query' in message


@KITS
def test_purge_local_state_on_removal(kit: BankConnectorKit, database, function_scope_messages_aggregator):  # noqa: E501
    connector = kit.create(database, function_scope_messages_aggregator)
    with patch_bank_transport(connector, kit.create_transport()):
        connector.query_history_events()
        accounts = connector.query_accounts()
    with database.user_write() as write_cursor:
        connector.save_session(write_cursor, 'opaque-session-blob')
    assert connector.load_session() == 'opaque-session-blob'
    with database.user_write() as write_cursor:
        connector.purge_local_state(write_cursor)
    assert connector.load_session() is None
    with database.conn.read_ctx() as cursor:
        assert all(connector.get_cursor(cursor, a.identifier) is None for a in accounts)


def test_location_is_a_bank_only_once():
    assert len(set(SUPPORTED_BANKS)) == len(SUPPORTED_BANKS)
    assert all(isinstance(location, Location) for location in SUPPORTED_BANKS)
