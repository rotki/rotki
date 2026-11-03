from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.banks.errors import BankAuthChallenge
from rotkehlchen.banks.manager import BankCredentialInput
from rotkehlchen.banks.manifest import AuthPrimitive, BankConnectorType
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import InputError
from rotkehlchen.exchanges.exchange import RecoveringExchangeSession
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.locations.constants import (
    LOCATION_BANKS,
)
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


def _add_qonto(server: APIServer, name: str = 'Qonto 1') -> None:
    response = requests.put(api_url_for(server, 'banksresource'), json={
        'connector': 'qonto',
        'name': name,
        'credentials': {'api_key': 'login', 'api_secret': 'secret'},
    })
    assert assert_proper_sync_response_with_result(response) == {
        'success': True,
        'history_start_ts': None,
    }


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_supported_banks_and_locations(rotkehlchen_api_server: APIServer) -> None:
    result = assert_proper_sync_response_with_result(
        requests.get(api_url_for(rotkehlchen_api_server, 'supportedbanksresource')),
    )
    assert [m['connector'] for m in result] == ['qonto', 'fints']
    manifest = result[0]
    assert manifest['access_tier'] == 'official api'
    assert manifest['auth_flow'] == [{'primitive': 'static secret'}]
    assert [s['slot'] for s in manifest['secrets']] == ['api_key', 'api_secret']
    assert len(manifest['setup_notes']) > 0
    assert manifest['image'] == 'qonto.svg'
    fints = result[1]
    assert fints['access_tier'] == 'fints'
    assert fints['image'] is None
    assert [field['slot'] for field in fints['secrets']] == [
        'bank_code', 'endpoint', 'username', 'pin',
    ]

    locations = assert_proper_sync_response_with_result(
        requests.get(api_url_for(rotkehlchen_api_server, 'locationresource')),
    )['locations']
    assert locations['banks']['is_bank'] is True
    assert 'exchange_details' not in locations['banks']
    assert 'qonto' not in locations
    assert 'fints' not in locations


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

        _add_qonto(rotkehlchen_api_server)
        banks = assert_proper_sync_response_with_result(
            requests.get(api_url_for(rotkehlchen_api_server, 'banksresource')),
        )
        assert banks == [{
            'name': 'Qonto 1',
            'connector': 'qonto',
            'location': 'banks',
            'display_name': 'Qonto',
            'bank_code': None,
            'sync_status': {
                'running': False,
                'last_sync_ts': None,
                'last_error': None,
                'auth_challenge': None,
                'auth_expired': False,
            },
        }]
        connector = rotki.bank_manager.get_bank(name='Qonto 1', connector=BankConnectorType.QONTO)
        assert connector is not None
        assert connector.session.headers['Authorization'] == 'login:secret'
        with rotki.data.db.conn.read_ctx() as cursor:
            assert cursor.execute(
                'SELECT api_key, api_secret FROM user_credentials WHERE location=?',
                (LOCATION_BANKS,),
            ).fetchall() == [('login', 'secret')]
        # and the exchange manager knows nothing about it
        assert rotki.exchange_manager.connected_exchanges == {}

        # sync pulls the history, twice without duplicates
        for _ in range(2):
            response = requests.post(api_url_for(rotkehlchen_api_server, 'banksyncresource'), json={'connector': 'qonto', 'name': 'Qonto 1'})  # noqa: E501
            assert assert_proper_sync_response_with_result(response) is True
            with rotki.data.db.conn.read_ctx() as cursor:
                events = DBHistoryEvents(rotki.data.db).get_history_events(
                    cursor=cursor,
                    filter_query=HistoryEventFilterQuery.make(location=LOCATION_BANKS),
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

        # balances, for one connector and for all banks
        result = assert_proper_sync_response_with_result(requests.get(
            api_url_for(rotkehlchen_api_server, 'named_bank_balances_resource', connector='qonto'),
        ))
        assert FVal(result['aggregate'][A_EUR.identifier]['amount']) == FVal(transport.organization['organization']['bank_accounts'][0]['balance_cents']) / 100  # noqa: E501
        assert result['connections'][0]['name'] == 'Qonto 1'
        assert [(x['iban'], x['asset'], x['amount']) for x in result['connections'][0]['accounts']] == [  # noqa: E501
            ('DE86601995651153419937', A_EUR.identifier, result['aggregate'][A_EUR.identifier]['amount']),  # noqa: E501
        ]
        assert assert_proper_sync_response_with_result(requests.get(
            api_url_for(rotkehlchen_api_server, 'bankbalancesresource'),
            json={'connector': 'qonto', 'name': 'Qonto 1'},
        ))['connections'] == result['connections']
        result = assert_proper_sync_response_with_result(requests.get(
            api_url_for(rotkehlchen_api_server, 'bankbalancesresource'),
        ))
        assert list(result) == ['aggregate', 'connections']
        # and the aggregate balances include the bank
        result = assert_proper_sync_response_with_result(requests.get(
            api_url_for(rotkehlchen_api_server, 'allbalancesresource'),
        ))
        assert 'banks' in result['location']

        # edit: rename and replace the secret, validated against the bank
        response = requests.patch(api_url_for(rotkehlchen_api_server, 'banksresource'), json={
            'connector': 'qonto',
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
                (LOCATION_BANKS,),
            ).fetchall() == [('Qonto main', 'newsecret')]
            assert cursor.execute(
                "SELECT COUNT(*) FROM used_query_ranges WHERE name='banks_history_events_Qonto main'",  # noqa: E501
            ).fetchone()[0] == 1
            assert cursor.execute(
                'SELECT COUNT(*) FROM history_events WHERE location=? AND location_label=?',
                (LOCATION_BANKS, 'Qonto main'),
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
        response = requests.delete(api_url_for(rotkehlchen_api_server, 'banksresource'), json={'connector': 'qonto', 'name': 'Qonto main'})  # noqa: E501
        assert_simple_ok_response(response)
        assert assert_proper_sync_response_with_result(
            requests.get(api_url_for(rotkehlchen_api_server, 'banksresource')),
        ) == []
        with rotki.data.db.conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM user_credentials').fetchone()[0] == 0
            assert cursor.execute("SELECT COUNT(*) FROM key_value_cache WHERE name LIKE 'banks_%'").fetchone()[0] == 0  # noqa: E501
            assert cursor.execute("SELECT COUNT(*) FROM used_query_ranges WHERE name LIKE 'banks_%'").fetchone()[0] == 0  # noqa: E501
            assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 28


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_bank_connections_survive_relogin(rotkehlchen_api_server: APIServer) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with _patch_bank_http(QontoFixtureTransport()):
        _add_qonto(rotkehlchen_api_server)
    rotki.bank_manager.delete_all_banks()
    assert rotki.bank_manager.connected_banks_num() == 0
    with rotki.data.db.conn.read_ctx() as cursor:
        bank_credentials = rotki.data.db.get_bank_credentials(cursor)
        exchange_credentials = rotki.data.db.get_exchange_credentials(cursor)
    rotki.bank_manager.initialize_banks(credentials=bank_credentials, database=rotki.data.db)
    rotki.exchange_manager.initialize_exchanges(exchange_credentials=exchange_credentials, database=rotki.data.db)  # noqa: E501
    assert rotki.bank_manager.connected_banks_num() == 1
    assert rotki.exchange_manager.connected_exchanges == {}, 'banks are not exchanges'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_renaming_bank_keeps_similarly_prefixed_connection_caches(
        rotkehlchen_api_server: APIServer,
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with _patch_bank_http(QontoFixtureTransport()):
        _add_qonto(rotkehlchen_api_server, name='Business')
        _add_qonto(rotkehlchen_api_server, name='Business_US')
        business = rotki.bank_manager.get_bank(name='Business', connector=BankConnectorType.QONTO)
        business_us = rotki.bank_manager.get_bank(
            name='Business_US', connector=BankConnectorType.QONTO,
        )
        assert business is not None and business_us is not None
        rotki.bank_manager.sync_status[business.location_id()].last_sync_ts = Timestamp(3)
        with rotki.data.db.user_write() as write_cursor:
            business.set_cursor(write_cursor, 'account', Timestamp(1))
            business_us.set_cursor(write_cursor, 'account', Timestamp(2))

        response = requests.patch(api_url_for(rotkehlchen_api_server, 'banksresource'), json={
            'connector': 'qonto',
            'name': 'Business',
            'new_name': 'Renamed',
            'credentials': {},
        })
        assert_simple_ok_response(response)
        with rotki.data.db.conn.read_ctx() as cursor:
            assert business.get_cursor(cursor, 'account') == Timestamp(1)
            assert business_us.get_cursor(cursor, 'account') == Timestamp(2)
        assert rotki.bank_manager.sync_status[business.location_id()].last_sync_ts == Timestamp(3)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_deleting_bank_keeps_similarly_prefixed_connection_caches(
        rotkehlchen_api_server: APIServer,
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with _patch_bank_http(QontoFixtureTransport()):
        _add_qonto(rotkehlchen_api_server, name='Business')
        _add_qonto(rotkehlchen_api_server, name='Business_US')
        business_us = rotki.bank_manager.get_bank(
            name='Business_US', connector=BankConnectorType.QONTO,
        )
        assert business_us is not None
        with rotki.data.db.user_write() as write_cursor:
            business_us.set_cursor(write_cursor, 'account', Timestamp(2))
            business_us.save_session(write_cursor, 'session')

        assert_simple_ok_response(requests.delete(
            api_url_for(rotkehlchen_api_server, 'banksresource'),
            json={'connector': 'qonto', 'name': 'Business'},
        ))
        with rotki.data.db.conn.read_ctx() as cursor:
            assert business_us.get_cursor(cursor, 'account') == Timestamp(2)
        assert business_us.load_session() == 'session'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_query_one_bank_connection_balances(rotkehlchen_api_server: APIServer) -> None:
    """A connection name limits the balance query to that connection alone"""
    url = api_url_for(rotkehlchen_api_server, 'bankbalancesresource')
    with _patch_bank_http(QontoFixtureTransport()):
        _add_qonto(rotkehlchen_api_server, name='Business')
        _add_qonto(rotkehlchen_api_server, name='Personal')
        assert [x['name'] for x in assert_proper_sync_response_with_result(
            requests.get(url, json={'connector': 'qonto'}),
        )['connections']] == ['Business', 'Personal']
        result = assert_proper_sync_response_with_result(
            requests.get(url, json={'connector': 'qonto', 'name': 'Personal'}),
        )
        assert [x['name'] for x in result['connections']] == ['Personal']
        assert result['aggregate'] == result['connections'][0]['balances']
        assert_error_response(
            requests.get(url, json={'connector': 'qonto', 'name': 'nope'}),
            'No qonto bank connection named nope',
            HTTPStatus.CONFLICT,
        )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_failed_bank_deletion_keeps_connection(rotkehlchen_api_server: APIServer) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with _patch_bank_http(QontoFixtureTransport()):
        _add_qonto(rotkehlchen_api_server, name='Business')
    with (
        patch.object(rotki.data.db, 'remove_exchange', side_effect=InputError('write failed')),
        pytest.raises(InputError, match='write failed'),
    ):
        rotki.bank_manager.delete_bank(name='Business', connector=BankConnectorType.QONTO)
    assert rotki.bank_manager.get_bank(
        name='Business', connector=BankConnectorType.QONTO,
    ) is not None


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_failed_bank_edit_restores_credentials(rotkehlchen_api_server: APIServer) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with _patch_bank_http(QontoFixtureTransport()):
        _add_qonto(rotkehlchen_api_server, name='Business')
        bank = rotki.bank_manager.get_bank(name='Business', connector=BankConnectorType.QONTO)
        assert bank is not None
        with (
            patch.object(
                rotki.data.db, 'edit_bank_credentials', side_effect=InputError('write failed'),
            ),
            pytest.raises(InputError, match='write failed'),
        ):
            rotki.bank_manager.edit_bank(
                name='Business',
                connector=BankConnectorType.QONTO,
                new_name=None,
                credentials=BankCredentialInput(values={'api_secret': 'newsecret'}),
            )
    assert bank.session.headers['Authorization'] == 'login:secret'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_balance_success_keeps_a_challenge_the_connector_still_waits_on(
        rotkehlchen_api_server: APIServer,
) -> None:
    """A balance query answered from cache succeeds while a TAN is pending"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    url = api_url_for(rotkehlchen_api_server, 'bankbalancesresource')
    with _patch_bank_http(QontoFixtureTransport()):
        _add_qonto(rotkehlchen_api_server)
        bank = rotki.bank_manager.get_bank(name='Qonto 1', connector=BankConnectorType.QONTO)
        assert bank is not None
        status = rotki.bank_manager.sync_status[bank.location_id()]
        status.set_challenge(challenge := BankAuthChallenge(
            primitive=AuthPrimitive.OTP_INPUT,
            prompt='Enter the TAN',
        ))
        with patch.object(type(bank), 'has_pending_authentication', return_value=True):
            assert_proper_sync_response_with_result(requests.get(url))
        assert status.auth_challenge == challenge

        assert_proper_sync_response_with_result(requests.get(url))
        assert status.serialize()['auth_challenge'] is None

        # an expired TAN outlives a balance success, since transactions may still need one
        status.expire_challenge()
        assert_proper_sync_response_with_result(requests.get(url, json={'ignore_cache': True}))
        assert status.serialize()['auth_expired'] is True


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_starting_over_an_authentication_clears_the_pending_challenge(
        rotkehlchen_api_server: APIServer,
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    url = api_url_for(rotkehlchen_api_server, 'bankauthenticationresource')
    with _patch_bank_http(QontoFixtureTransport()):
        _add_qonto(rotkehlchen_api_server)
    bank = rotki.bank_manager.get_bank(name='Qonto 1', connector=BankConnectorType.QONTO)
    assert bank is not None
    rotki.bank_manager.sync_status[bank.location_id()].set_challenge(BankAuthChallenge(
        primitive=AuthPrimitive.OTP_INPUT,
        prompt='Enter the TAN',
    ))

    assert_simple_ok_response(requests.delete(url, json={'connector': 'qonto', 'name': 'Qonto 1'}))
    banks = assert_proper_sync_response_with_result(
        requests.get(api_url_for(rotkehlchen_api_server, 'banksresource')),
    )
    assert banks[0]['sync_status']['auth_challenge'] is None

    response = requests.delete(url, json={'connector': 'qonto', 'name': 'nope'})
    assert_error_response(response, 'does not exist', HTTPStatus.CONFLICT)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_bank_errors(rotkehlchen_api_server: APIServer) -> None:
    url = api_url_for(rotkehlchen_api_server, 'banksresource')
    response = requests.put(url, json={'connector': 'kraken', 'name': 'x', 'credentials': {'api_key': 'a', 'api_secret': 'b'}})  # noqa: E501
    assert_error_response(response, 'kraken', HTTPStatus.BAD_REQUEST)
    response = requests.put(url, json={'connector': 'qonto', 'name': 'x', 'credentials': {'api_key': '', 'api_secret': 'b'}})  # noqa: E501
    assert_error_response(response, 'must not be empty', HTTPStatus.BAD_REQUEST)
    response = requests.delete(url, json={'connector': 'qonto', 'name': 'nope'})
    assert_error_response(response, 'does not exist', HTTPStatus.CONFLICT)
    response = requests.patch(url, json={'connector': 'qonto', 'name': 'nope', 'credentials': {}})
    assert_error_response(response, 'Could not find', HTTPStatus.CONFLICT)
    response = requests.post(api_url_for(rotkehlchen_api_server, 'banksyncresource'), json={'name': 'x'})  # noqa: E501
    assert_error_response(response, 'needs its connector', HTTPStatus.BAD_REQUEST)
    response = requests.get(api_url_for(rotkehlchen_api_server, 'named_bank_balances_resource', connector='qonto'))  # noqa: E501
    assert_error_response(response, 'No qonto bank connection', HTTPStatus.CONFLICT)
    response = requests.get(api_url_for(rotkehlchen_api_server, 'bankbalancesresource'), json={'name': 'x'})  # noqa: E501
    assert_error_response(response, 'needs its connector', HTTPStatus.BAD_REQUEST)
