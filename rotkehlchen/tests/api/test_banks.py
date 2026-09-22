from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.banks.fints import Fints
from rotkehlchen.banks.manager import BankCredentialInput
from rotkehlchen.connections.types import connection_range_name
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.db.connections import DBConnections
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.locations import DBLocations
from rotkehlchen.errors.misc import InputError
from rotkehlchen.exchanges.exchange import RecoveringExchangeSession
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.locations.constants import LOCATION_BANKS, LOCATION_QONTO
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.banks import QontoFixtureTransport
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def _patch_bank_http(transport: QontoFixtureTransport):
    """Every connector session created by the server answers from the fixtures"""
    return patch.object(
        RecoveringExchangeSession,
        'get',
        autospec=True,
        side_effect=lambda self, url, **kwargs: transport(url, **kwargs),
    )


def _add_qonto(server: APIServer, name: str = 'Qonto 1') -> str:
    """Set up a Qonto connection and return its identifier"""
    response = requests.put(api_url_for(server, 'banksresource'), json={
        'connector': 'qonto',
        'name': name,
        'credentials': {'api_key': 'login', 'api_secret': 'secret'},
    })
    result = assert_proper_sync_response_with_result(response)
    assert result == {'success': True, 'identifier': result['identifier'], 'history_start_ts': None}  # noqa: E501
    return result['identifier']


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_supported_banks_and_locations(rotkehlchen_api_server: APIServer) -> None:
    result = assert_proper_sync_response_with_result(
        requests.get(api_url_for(rotkehlchen_api_server, 'supportedbanksresource')),
    )
    assert [(m['connector_identifier'], m['fixed_location']) for m in result] == [('qonto', 'qonto'), ('fints', None)]  # noqa: E501
    manifest = result[0]
    assert manifest['access_tier'] == 'official api'
    assert manifest['auth_flow'] == [{'primitive': 'static secret'}]
    assert [s['slot'] for s in manifest['secrets']] == ['api_key', 'api_secret']
    assert len(manifest['setup_notes']) > 0
    fints = result[1]
    assert fints['access_tier'] == 'fints'
    assert [field['slot'] for field in fints['secrets']] == [
        'bank_code', 'endpoint', 'username', 'pin',
    ]

    # connectors are not locations: FinTS has none, and Qonto's carries no connector data
    locations = assert_proper_sync_response_with_result(
        requests.get(api_url_for(rotkehlchen_api_server, 'locationresource')),
    )['locations']
    assert 'fints' not in locations
    assert locations['qonto'] == {'label': 'Qonto', 'image': locations['qonto']['image']}


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_bank_lifecycle(rotkehlchen_api_server: APIServer) -> None:
    """Add, list, sync, query balances, edit and remove a bank connection"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    transport = QontoFixtureTransport()
    with _patch_bank_http(transport):
        # bad credentials are rejected by the bank at setup
        transport.force(401, '{"errors":[{"code":"unauthorized"}]}')
        response = requests.put(api_url_for(rotkehlchen_api_server, 'banksresource'), json={
            'connector': 'qonto',
            'name': 'Qonto 1',
            'credentials': {'api_key': 'login', 'api_secret': 'wrong'},
        })
        assert_error_response(response, 'rejected the credentials', HTTPStatus.CONFLICT)
        assert assert_proper_sync_response_with_result(
            requests.get(api_url_for(rotkehlchen_api_server, 'banksresource')),
        ) == []
        transport.forced_response = None

        # credentials that do not fit the manifest never reach the bank
        response = requests.put(api_url_for(rotkehlchen_api_server, 'banksresource'), json={
            'connector': 'qonto',
            'name': 'Qonto 1',
            'credentials': {'api_key': 'login', 'passphrase': 'x'},
        })
        assert_error_response(response, 'does not use credential fields', HTTPStatus.BAD_REQUEST)

        identifier = _add_qonto(rotkehlchen_api_server)
        banks = assert_proper_sync_response_with_result(
            requests.get(api_url_for(rotkehlchen_api_server, 'banksresource')),
        )
        assert banks == [{
            'identifier': identifier,
            'name': 'Qonto 1',
            'connector': 'qonto',
            'location': 'qonto',
            'display_name': 'Qonto',
            'sync_status': {
                'running': False,
                'last_sync_ts': None,
                'last_error': None,
                'auth_challenge': None,
            },
        }]
        connector = rotki.bank_manager.get_bank(identifier)
        assert connector is not None
        assert connector.session.headers['Authorization'] == 'login:secret'
        with rotki.data.db.conn.read_ctx() as cursor:
            assert cursor.execute(
                'SELECT connector_identifier, location_identifier, api_key, api_secret FROM integration_connections',  # noqa: E501
            ).fetchall() == [('qonto', 'qonto', 'login', 'secret')]
        # and the exchange manager knows nothing about it
        assert rotki.exchange_manager.connected_exchanges == {}

        # sync pulls the history, twice without duplicates
        for _ in range(2):
            response = requests.post(api_url_for(rotkehlchen_api_server, 'banksyncresource'), json={'identifier': identifier})  # noqa: E501
            assert assert_proper_sync_response_with_result(response) is True
            with rotki.data.db.conn.read_ctx() as cursor:
                events = DBHistoryEvents(rotki.data.db).get_history_events(
                    cursor=cursor,
                    filter_query=HistoryEventFilterQuery.make(location=LOCATION_QONTO),
                    entries_limit=None,
                )
            assert len(events) == 28
            assert all(event.entry_type == HistoryBaseEntryType.BANK_TRANSACTION_EVENT for event in events)  # noqa: E501
        # the entry type is what lets the history view show banks alone
        response = requests.post(api_url_for(rotkehlchen_api_server, 'historyeventresource'), json={'entry_types': {'values': ['bank transaction event']}})  # noqa: E501
        assert assert_proper_sync_response_with_result(response)['entries_found'] == 28
        banks = assert_proper_sync_response_with_result(
            requests.get(api_url_for(rotkehlchen_api_server, 'banksresource')),
        )
        assert banks[0]['sync_status']['last_sync_ts'] is not None
        assert banks[0]['sync_status']['last_error'] is None

        # balances, per location and for all banks
        result = assert_proper_sync_response_with_result(requests.get(
            api_url_for(rotkehlchen_api_server, 'named_bank_balances_resource', location='qonto'),
        ))
        assert FVal(result[A_EUR.identifier]['amount']) == FVal(transport.organization['organization']['bank_accounts'][0]['balance_cents']) / 100  # noqa: E501
        result = assert_proper_sync_response_with_result(requests.get(
            api_url_for(rotkehlchen_api_server, 'bankbalancesresource'),
        ))
        assert list(result) == ['qonto']
        # and the aggregate balances include the bank
        result = assert_proper_sync_response_with_result(requests.get(
            api_url_for(rotkehlchen_api_server, 'allbalancesresource'),
        ))
        assert 'qonto' in result['location']

        # edit: rename and replace the secret, validated against the bank
        response = requests.patch(api_url_for(rotkehlchen_api_server, 'banksresource'), json={
            'identifier': identifier,
            'new_name': 'Qonto main',
            'credentials': {'api_secret': 'newsecret'},
        })
        assert_simple_ok_response(response)
        assert connector.name == 'Qonto main'
        assert connector.session.headers['Authorization'] == 'login:newsecret'
        with rotki.data.db.conn.read_ctx() as cursor:
            assert cursor.execute(
                'SELECT name, api_secret FROM integration_connections WHERE identifier=?',
                (identifier,),
            ).fetchall() == [('Qonto main', 'newsecret')]
            assert cursor.execute(  # the rename keeps what the connection queried
                'SELECT COUNT(*) FROM used_query_ranges WHERE name=?',
                (connection_range_name(identifier, 'history_events'),),
            ).fetchone()[0] == 1
            assert cursor.execute(
                'SELECT COUNT(*) FROM history_events WHERE location=? AND location_label=?',
                (LOCATION_QONTO, 'Qonto main'),
            ).fetchone()[0] == 28

        # a failed sync is reported in the status. The range bookkeeping only queries new
        # time, so move the clock forward or nothing would be asked of the bank at all
        transport.force(500, 'boom')
        with patch('rotkehlchen.exchanges.exchange.ts_now', return_value=Timestamp(ts_now() + 3600)):  # noqa: E501
            response = requests.post(api_url_for(rotkehlchen_api_server, 'banksyncresource'), json={'connector': 'qonto'})  # noqa: E501
        assert_error_response(response, 'boom', HTTPStatus.BAD_GATEWAY)
        banks = assert_proper_sync_response_with_result(
            requests.get(api_url_for(rotkehlchen_api_server, 'banksresource')),
        )
        assert 'boom' in banks[0]['sync_status']['last_error']
        transport.forced_response = None

        # remove: credentials, cursors and ranges go, events stay
        response = requests.delete(api_url_for(rotkehlchen_api_server, 'banksresource'), json={'identifier': identifier})  # noqa: E501
        assert_simple_ok_response(response)
        assert assert_proper_sync_response_with_result(
            requests.get(api_url_for(rotkehlchen_api_server, 'banksresource')),
        ) == []
        with rotki.data.db.conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM integration_connections').fetchone()[0] == 0  # noqa: E501
            assert cursor.execute('SELECT COUNT(*) FROM key_value_cache WHERE name LIKE ?', (f'{identifier}%',)).fetchone()[0] == 0  # noqa: E501
            assert cursor.execute('SELECT COUNT(*) FROM used_query_ranges WHERE name LIKE ?', (f'{identifier}%',)).fetchone()[0] == 0  # noqa: E501
            assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 28


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_bank_connections_survive_relogin(rotkehlchen_api_server: APIServer) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with _patch_bank_http(QontoFixtureTransport()):
        _add_qonto(rotkehlchen_api_server)
    rotki.bank_manager.delete_all_banks()
    assert rotki.bank_manager.connected_banks_num() == 0
    with rotki.data.db.conn.read_ctx() as cursor:
        connections = rotki.data.db.get_exchange_credentials(cursor)
    rotki.bank_manager.initialize_banks(connections=connections, database=rotki.data.db)
    rotki.exchange_manager.initialize_exchanges(connections=connections, database=rotki.data.db)
    assert rotki.bank_manager.connected_banks_num() == 1
    assert rotki.exchange_manager.connected_exchanges == {}, 'banks are not exchanges'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_bank_progress_follows_the_connection(rotkehlchen_api_server: APIServer) -> None:
    """Cursors, sessions and the sync status belong to the connection identifier. Renaming
    a connection keeps them and deleting one leaves every other connection's alone, even
    when its name starts with the deleted one's."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with _patch_bank_http(QontoFixtureTransport()):
        business_id = _add_qonto(rotkehlchen_api_server, name='Business')
        business_us_id = _add_qonto(rotkehlchen_api_server, name='Business_US')
        business = rotki.bank_manager.get_bank(business_id)
        business_us = rotki.bank_manager.get_bank(business_us_id)
        assert business is not None and business_us is not None
        rotki.bank_manager.sync_status[business_id].last_sync_ts = Timestamp(3)
        with rotki.data.db.user_write() as write_cursor:
            business.set_cursor(write_cursor, 'account', Timestamp(1))
            business_us.set_cursor(write_cursor, 'account', Timestamp(2))
            business_us.save_session(write_cursor, 'session')

        assert_simple_ok_response(requests.patch(api_url_for(rotkehlchen_api_server, 'banksresource'), json={  # noqa: E501
            'identifier': business_id,
            'new_name': 'Renamed',
            'credentials': {},
        }))
        with rotki.data.db.conn.read_ctx() as cursor:
            assert business.get_cursor(cursor, 'account') == Timestamp(1)
        assert rotki.bank_manager.sync_status[business_id].last_sync_ts == Timestamp(3)

        assert_simple_ok_response(requests.delete(
            api_url_for(rotkehlchen_api_server, 'banksresource'),
            json={'identifier': business_id},
        ))
        with rotki.data.db.conn.read_ctx() as cursor:
            assert business.get_cursor(cursor, 'account') is None
            assert business_us.get_cursor(cursor, 'account') == Timestamp(2)
        assert business_us.load_session() == 'session'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_fints_connections_point_at_their_bank(rotkehlchen_api_server: APIServer) -> None:
    """A FinTS connection needs a location in the Banks subtree, puts its data there and
    two connections at the same bank add up. FinTS itself is never a location."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.user_write() as write_cursor:
        ing = DBLocations().add_custom(write_cursor, name='ING', parent_identifier=LOCATION_BANKS)
    url = api_url_for(rotkehlchen_api_server, 'banksresource')
    credentials = {'bank_code': '50010517', 'endpoint': 'https://fints.ing.de/fints', 'username': 'user', 'pin': '1234'}  # noqa: E501
    for location, message in (
        (None, 'need the location of their bank'),
        ('kraken', 'is not a bank'),
        ('total', 'cannot be assigned directly'),
    ):
        response = requests.put(url, json={'connector': 'fints', 'name': 'x', 'location': location, 'credentials': credentials})  # noqa: E501
        assert_error_response(response, message, HTTPStatus.BAD_REQUEST)
    response = requests.put(url, json={'connector': 'qonto', 'name': 'x', 'location': 'banks', 'credentials': {'api_key': 'a', 'api_secret': 'b'}})  # noqa: E501
    assert_error_response(response, 'always use the qonto location', HTTPStatus.BAD_REQUEST)

    with patch.object(Fints, 'validate_api_key', return_value=(True, '')):
        identifiers = [assert_proper_sync_response_with_result(requests.put(url, json={
            'connector': 'fints',
            'name': name,
            'location': ing.identifier,
            'credentials': credentials,
        }))['identifier'] for name in ('ING checking', 'ING joint')]

    assert [(x['connector'], x['location']) for x in assert_proper_sync_response_with_result(requests.get(url))] == [('fints', ing.identifier)] * 2  # noqa: E501
    with rotki.data.db.conn.read_ctx() as cursor:
        assert DBLocations().usage(cursor, ing.identifier) == {'integration_connections': 2}

    balances = {identifier: {A_EUR: Balance(amount=FVal(amount), value=FVal(amount))} for identifier, amount in zip(identifiers, (10, 5), strict=True)}  # noqa: E501
    with patch.object(Fints, 'query_balances', autospec=True, side_effect=lambda self, **kwargs: (balances[self.connection_identifier], '')):  # noqa: E501
        result = assert_proper_sync_response_with_result(requests.get(
            api_url_for(rotkehlchen_api_server, 'bankbalancesresource'),
        ))
    assert list(result) == [ing.identifier]
    assert FVal(result[ing.identifier][A_EUR.identifier]['amount']) == 15


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_failed_bank_deletion_keeps_connection(rotkehlchen_api_server: APIServer) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with _patch_bank_http(QontoFixtureTransport()):
        identifier = _add_qonto(rotkehlchen_api_server, name='Business')
    with (
        patch.object(rotki.data.db, 'remove_exchange', side_effect=InputError('write failed')),
        pytest.raises(InputError, match='write failed'),
    ):
        rotki.bank_manager.delete_bank(identifier)
    assert rotki.bank_manager.get_bank(identifier) is not None


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_failed_bank_edit_restores_credentials(rotkehlchen_api_server: APIServer) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with _patch_bank_http(QontoFixtureTransport()):
        identifier = _add_qonto(rotkehlchen_api_server, name='Business')
        bank = rotki.bank_manager.get_bank(identifier)
        assert bank is not None
        with (
            patch.object(DBConnections, 'edit', side_effect=InputError('write failed')),
            pytest.raises(InputError, match='write failed'),
        ):
            rotki.bank_manager.edit_bank(
                identifier=identifier,
                new_name=None,
                credentials=BankCredentialInput(values={'api_secret': 'newsecret'}),
            )
    assert bank.session.headers['Authorization'] == 'login:secret'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_bank_errors(rotkehlchen_api_server: APIServer) -> None:
    url = api_url_for(rotkehlchen_api_server, 'banksresource')
    response = requests.put(url, json={'connector': 'kraken', 'name': 'x', 'credentials': {'api_key': 'a', 'api_secret': 'b'}})  # noqa: E501
    assert_error_response(response, 'kraken is not a supported bank', HTTPStatus.BAD_REQUEST)
    response = requests.put(url, json={'connector': 'qonto', 'name': 'x', 'credentials': {'api_key': '', 'api_secret': 'b'}})  # noqa: E501
    assert_error_response(response, 'must not be empty', HTTPStatus.BAD_REQUEST)
    response = requests.delete(url, json={'identifier': 'nope'})
    assert_error_response(response, 'does not exist', HTTPStatus.CONFLICT)
    response = requests.patch(url, json={'identifier': 'nope', 'credentials': {}})
    assert_error_response(response, 'Could not find', HTTPStatus.CONFLICT)
    response = requests.post(api_url_for(rotkehlchen_api_server, 'banksyncresource'), json={'identifier': 'x'})  # noqa: E501
    assert_error_response(response, 'does not exist', HTTPStatus.CONFLICT)
    response = requests.get(api_url_for(rotkehlchen_api_server, 'named_bank_balances_resource', location='qonto'))  # noqa: E501
    assert_error_response(response, 'No bank connection at qonto', HTTPStatus.CONFLICT)
