from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.exchanges.exchange import RecoveringExchangeSession
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.banks import QontoFixtureTransport
from rotkehlchen.types import Location, Timestamp
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


def _add_qonto(server: APIServer, name: str = 'Qonto 1') -> None:
    response = requests.put(api_url_for(server, 'banksresource'), json={
        'location': 'qonto',
        'name': name,
        'credentials': {'api_key': 'login', 'api_secret': 'secret'},
    })
    assert_simple_ok_response(response)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_supported_banks_and_locations(rotkehlchen_api_server: APIServer) -> None:
    result = assert_proper_sync_response_with_result(
        requests.get(api_url_for(rotkehlchen_api_server, 'supportedbanksresource')),
    )
    assert [m['location'] for m in result] == ['qonto']
    manifest = result[0]
    assert manifest['access_tier'] == 'official api'
    assert manifest['auth_flow'] == [{'primitive': 'static secret'}]
    assert [s['slot'] for s in manifest['secrets']] == ['api_key', 'api_secret']
    assert len(manifest['setup_notes']) > 0

    locations = assert_proper_sync_response_with_result(
        requests.get(api_url_for(rotkehlchen_api_server, 'locationresource')),
    )['locations']
    assert locations['qonto']['is_bank'] is True
    assert 'exchange_details' not in locations['qonto']
    assert locations['qonto']['bank_details'] == manifest


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_bank_lifecycle(rotkehlchen_api_server: APIServer) -> None:
    """Add, list, sync, query balances, edit and remove a bank connection"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    transport = QontoFixtureTransport()
    with _patch_bank_http(transport):
        # bad credentials are rejected by the bank at setup
        transport.force(401, '{"errors":[{"code":"unauthorized"}]}')
        response = requests.put(api_url_for(rotkehlchen_api_server, 'banksresource'), json={
            'location': 'qonto',
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
            'location': 'qonto',
            'name': 'Qonto 1',
            'credentials': {'api_key': 'login', 'passphrase': 'x'},
        })
        assert_error_response(response, 'does not use credential fields', HTTPStatus.BAD_REQUEST)

        _add_qonto(rotkehlchen_api_server)
        banks = assert_proper_sync_response_with_result(
            requests.get(api_url_for(rotkehlchen_api_server, 'banksresource')),
        )
        assert banks == [{
            'name': 'Qonto 1',
            'location': 'qonto',
            'display_name': 'Qonto',
            'sync_status': {'running': False, 'last_sync_ts': None, 'last_error': None},
        }]
        connector = rotki.bank_manager.get_bank(name='Qonto 1', location=Location.QONTO)
        assert connector is not None
        assert connector.session.headers['Authorization'] == 'login:secret'
        with rotki.data.db.conn.read_ctx() as cursor:
            assert cursor.execute(
                'SELECT api_key, api_secret FROM user_credentials WHERE location=?',
                (Location.QONTO.serialize_for_db(),),
            ).fetchall() == [('login', 'secret')]
        # and the exchange manager knows nothing about it
        assert rotki.exchange_manager.connected_exchanges == {}

        # sync pulls the history, twice without duplicates
        for _ in range(2):
            response = requests.post(api_url_for(rotkehlchen_api_server, 'banksyncresource'), json={'location': 'qonto', 'name': 'Qonto 1'})  # noqa: E501
            assert assert_proper_sync_response_with_result(response) is True
            with rotki.data.db.conn.read_ctx() as cursor:
                events = DBHistoryEvents(rotki.data.db).get_history_events(
                    cursor=cursor,
                    filter_query=HistoryEventFilterQuery.make(location=Location.QONTO),
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
            'location': 'qonto',
            'name': 'Qonto 1',
            'new_name': 'Qonto main',
            'credentials': {'api_secret': 'newsecret'},
        })
        assert_simple_ok_response(response)
        assert connector.name == 'Qonto main'
        assert connector.session.headers['Authorization'] == 'login:newsecret'
        with rotki.data.db.conn.read_ctx() as cursor:
            assert cursor.execute(
                'SELECT name, api_secret FROM user_credentials WHERE location=?',
                (Location.QONTO.serialize_for_db(),),
            ).fetchall() == [('Qonto main', 'newsecret')]
            assert cursor.execute(
                "SELECT COUNT(*) FROM used_query_ranges WHERE name='qonto_history_events_Qonto main'",  # noqa: E501
            ).fetchone()[0] == 1

        # a failed sync is reported in the status. The range bookkeeping only queries new
        # time, so move the clock forward or nothing would be asked of the bank at all
        transport.force(500, 'boom')
        with patch('rotkehlchen.exchanges.exchange.ts_now', return_value=Timestamp(ts_now() + 3600)):  # noqa: E501
            response = requests.post(api_url_for(rotkehlchen_api_server, 'banksyncresource'), json={'location': 'qonto'})  # noqa: E501
        assert_error_response(response, 'boom', HTTPStatus.BAD_GATEWAY)
        banks = assert_proper_sync_response_with_result(
            requests.get(api_url_for(rotkehlchen_api_server, 'banksresource')),
        )
        assert 'boom' in banks[0]['sync_status']['last_error']
        transport.forced_response = None

        # remove: credentials, cursors and ranges go, events stay
        response = requests.delete(api_url_for(rotkehlchen_api_server, 'banksresource'), json={'location': 'qonto', 'name': 'Qonto main'})  # noqa: E501
        assert_simple_ok_response(response)
        assert assert_proper_sync_response_with_result(
            requests.get(api_url_for(rotkehlchen_api_server, 'banksresource')),
        ) == []
        with rotki.data.db.conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM user_credentials').fetchone()[0] == 0
            assert cursor.execute("SELECT COUNT(*) FROM key_value_cache WHERE name LIKE 'qonto_%'").fetchone()[0] == 0  # noqa: E501
            assert cursor.execute("SELECT COUNT(*) FROM used_query_ranges WHERE name LIKE 'qonto_%'").fetchone()[0] == 0  # noqa: E501
            assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 28


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_bank_connections_survive_relogin(rotkehlchen_api_server: APIServer) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with _patch_bank_http(QontoFixtureTransport()):
        _add_qonto(rotkehlchen_api_server)
    rotki.bank_manager.delete_all_banks()
    assert rotki.bank_manager.connected_banks_num() == 0
    with rotki.data.db.conn.read_ctx() as cursor:
        credentials = rotki.data.db.get_exchange_credentials(cursor)
    rotki.bank_manager.initialize_banks(credentials=credentials, database=rotki.data.db)
    rotki.exchange_manager.initialize_exchanges(exchange_credentials=credentials, database=rotki.data.db)  # noqa: E501
    assert rotki.bank_manager.connected_banks_num() == 1
    assert rotki.exchange_manager.connected_exchanges == {}, 'banks are not exchanges'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_bank_errors(rotkehlchen_api_server: APIServer) -> None:
    url = api_url_for(rotkehlchen_api_server, 'banksresource')
    response = requests.put(url, json={'location': 'kraken', 'name': 'x', 'credentials': {'api_key': 'a', 'api_secret': 'b'}})  # noqa: E501
    assert_error_response(response, 'kraken', HTTPStatus.BAD_REQUEST)
    response = requests.put(url, json={'location': 'qonto', 'name': 'x', 'credentials': {'api_key': '', 'api_secret': 'b'}})  # noqa: E501
    assert_error_response(response, 'must not be empty', HTTPStatus.BAD_REQUEST)
    response = requests.delete(url, json={'location': 'qonto', 'name': 'nope'})
    assert_error_response(response, 'does not exist', HTTPStatus.CONFLICT)
    response = requests.patch(url, json={'location': 'qonto', 'name': 'nope', 'credentials': {}})
    assert_error_response(response, 'Could not find', HTTPStatus.CONFLICT)
    response = requests.post(api_url_for(rotkehlchen_api_server, 'banksyncresource'), json={'name': 'x'})  # noqa: E501
    assert_error_response(response, 'needs its location', HTTPStatus.BAD_REQUEST)
    response = requests.get(api_url_for(rotkehlchen_api_server, 'named_bank_balances_resource', location='qonto'))  # noqa: E501
    assert_error_response(response, 'No qonto bank connection', HTTPStatus.CONFLICT)
