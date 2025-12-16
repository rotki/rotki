import datetime
import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.calendar import CalendarEntry
from rotkehlchen.errors.api import AuthenticationError
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.google_calendar import GoogleCalendarAPI
from rotkehlchen.types import SupportedBlockchain, Timestamp


@pytest.fixture(name='google_calendar_api')
def fixture_google_calendar_api(database):
    """Create a GoogleCalendarAPI instance for testing."""
    return GoogleCalendarAPI(database)


def _store_credentials(
        database,
        token='mock_token',  # noqa: S107
        refresh_token='mock_refresh_token',  # noqa: S107
        user_email=None,
):
    """Helper to store credentials in database."""
    creds_data = {
        'token': token,
        'refresh_token': refresh_token,
    }
    if user_email:
        creds_data['user_email'] = user_email

    with database.conn.write_ctx() as cursor:
        cursor.execute(
            'INSERT INTO key_value_cache (name, value) VALUES (?, ?)',
            ('google_calendar_credentials', json.dumps(creds_data)),
        )


def _create_mock_credentials(
        valid=True,
        expired=False,
        token='mock_token',  # noqa: S107
        refresh_token='mock_refresh_token',  # noqa: S107
        scopes=None,
):
    """Helper to create mock credentials."""
    mock_creds = Mock()
    mock_creds.valid = valid
    mock_creds.expired = expired
    mock_creds.token = token
    mock_creds.refresh_token = refresh_token
    mock_creds.scopes = scopes or ['https://www.googleapis.com/auth/calendar.app.created']
    return mock_creds


def _create_mock_service(calendar_list_items=None, existing_events=None):
    """Helper to create mock Google Calendar service."""
    mock_service = MagicMock()
    if calendar_list_items is not None:
        mock_service.calendarList().list().execute.return_value = {
            'items': calendar_list_items,
        }

    if existing_events is not None:
        mock_service.events().list().execute.return_value = {
            'items': existing_events,
        }

    mock_service.events().update().execute.return_value = {}
    mock_service.events().insert().execute.return_value = {}
    mock_service.calendars().insert().execute.return_value = {'id': 'new_rotki_cal'}

    return mock_service


def _create_mock_response(status_code=200, json_data=None, text=''):
    """Helper to create mock HTTP response."""
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.text = text
    if json_data:
        mock_response.json.return_value = json_data
    return mock_response


def test_init(google_calendar_api, database):
    """Test initialization of GoogleCalendarAPI."""
    assert google_calendar_api.db == database
    assert google_calendar_api._credentials is None
    assert google_calendar_api._service is None


def test_is_authenticated_no_credentials(google_calendar_api):
    """Test is_authenticated when no credentials are stored."""
    assert google_calendar_api.is_authenticated() is False


def test_is_authenticated_with_valid_credentials(google_calendar_api, database):
    """Test is_authenticated with valid stored credentials."""
    _store_credentials(database)
    mock_creds = _create_mock_credentials()

    with patch('rotkehlchen.externalapis.google_calendar.Credentials', return_value=mock_creds):
        assert google_calendar_api.is_authenticated() is True


def test_is_authenticated_wrong_scope(google_calendar_api, database):
    """Test is_authenticated when credentials have wrong scope."""
    _store_credentials(database)
    mock_creds = _create_mock_credentials(scopes=['https://www.googleapis.com/auth/gmail.readonly'])

    with patch('rotkehlchen.externalapis.google_calendar.Credentials', return_value=mock_creds):
        assert google_calendar_api.is_authenticated() is False


def test_get_credentials_refresh_error(google_calendar_api, database):
    """Test _get_credentials when refresh fails."""
    _store_credentials(database, token='old_token', refresh_token='bad_refresh_token')

    mock_creds = _create_mock_credentials(valid=False, expired=True)
    mock_creds.refresh.side_effect = RefreshError('Token refresh failed')

    with patch('rotkehlchen.externalapis.google_calendar.Credentials', return_value=mock_creds):
        result = google_calendar_api._get_credentials()
        assert result is None


def test_get_credentials_json_error(google_calendar_api, database):
    """Test _get_credentials with invalid JSON in database."""
    with database.conn.write_ctx() as cursor:
        cursor.execute(
            'INSERT INTO key_value_cache (name, value) VALUES (?, ?)',
            ('google_calendar_credentials', 'invalid json'),
        )

    result = google_calendar_api._get_credentials()
    assert result is None


def test_get_connected_user_email_success(google_calendar_api, database):
    """Test get_connected_user_email successful retrieval from stored data."""
    _store_credentials(database, user_email='test@example.com')

    email = google_calendar_api.get_connected_user_email()
    assert email == 'test@example.com'


def test_get_connected_user_email_from_api(google_calendar_api, database):
    """Test get_connected_user_email when email not in stored credentials."""
    _store_credentials(database)
    mock_creds = _create_mock_credentials()
    mock_response = _create_mock_response(json_data={'email': 'api@example.com'})

    with (
        patch('rotkehlchen.externalapis.google_calendar.Credentials', return_value=mock_creds),
        patch('requests.get', return_value=mock_response),
    ):
        email = google_calendar_api.get_connected_user_email()
        assert email == 'api@example.com'


def test_get_connected_user_email_api_error(google_calendar_api, database):
    """Test get_connected_user_email when API call fails."""
    _store_credentials(database)
    mock_creds = _create_mock_credentials()
    mock_response = _create_mock_response(status_code=401)

    with (
        patch('rotkehlchen.externalapis.google_calendar.Credentials', return_value=mock_creds),
        patch('requests.get', return_value=mock_response),
    ):
        email = google_calendar_api.get_connected_user_email()
        assert email is None


def test_disconnect(google_calendar_api, database):
    """Test disconnect removes stored credentials."""
    # Store some data first
    _store_credentials(database)

    result = google_calendar_api.disconnect()
    assert result == {'success': True}

    # Verify data was deleted
    with database.conn.read_ctx() as cursor:
        count = cursor.execute(
            'SELECT COUNT(*) FROM key_value_cache WHERE name IN (?, ?)',
            ('google_calendar_credentials', 'google_calendar_client_config'),
        ).fetchone()[0]
        assert count == 0


def test_get_service_not_authenticated(google_calendar_api):
    """Test _get_service raises AuthenticationError when not authenticated."""
    with pytest.raises(AuthenticationError, match='Google Calendar not authenticated'):
        google_calendar_api._get_service()


def test_get_service_success(google_calendar_api, database):
    """Test _get_service creates service successfully."""
    _store_credentials(database)
    mock_creds = _create_mock_credentials()
    mock_service = Mock()

    with (
        patch('rotkehlchen.externalapis.google_calendar.Credentials', return_value=mock_creds),
        patch('rotkehlchen.externalapis.google_calendar.build', return_value=mock_service),
    ):
        service = google_calendar_api._get_service()
        assert service == mock_service
        # Test caching
        service2 = google_calendar_api._get_service()
        assert service2 == mock_service


def test_get_or_create_calendar_existing(google_calendar_api, database):
    """Test _get_or_create_calendar returns existing calendar_id from stored credentials."""
    # Store credentials with calendar_id already set
    creds_data = {
        'token': 'mock_token',
        'refresh_token': 'mock_refresh_token',
        'user_email': 'test@example.com',
        'calendar_id': 'existing_rotki_cal',
    }

    with database.conn.write_ctx() as cursor:
        cursor.execute(
            'INSERT INTO key_value_cache (name, value) VALUES (?, ?)',
            ('google_calendar_credentials', json.dumps(creds_data)),
        )

    mock_creds = _create_mock_credentials()
    mock_service = _create_mock_service()

    with (
        patch('rotkehlchen.externalapis.google_calendar.Credentials', return_value=mock_creds),
        patch('rotkehlchen.externalapis.google_calendar.build', return_value=mock_service),
    ):
        calendar_id = google_calendar_api._get_or_create_calendar()
        assert calendar_id == 'existing_rotki_cal'


def test_get_or_create_calendar_create_new(google_calendar_api, database):
    """Test _get_or_create_calendar creates new calendar when not found."""
    _store_credentials(database)
    mock_creds = _create_mock_credentials()
    mock_service = _create_mock_service(calendar_list_items=[])

    with (
        patch('rotkehlchen.externalapis.google_calendar.Credentials', return_value=mock_creds),
        patch('rotkehlchen.externalapis.google_calendar.build', return_value=mock_service),
    ):
        calendar_id = google_calendar_api._get_or_create_calendar()
        assert calendar_id == 'new_rotki_cal'


def test_get_or_create_calendar_insufficient_permissions(google_calendar_api, database):
    """Test _get_or_create_calendar handles insufficient permissions."""
    _store_credentials(database)
    mock_creds = _create_mock_credentials()

    mock_service = MagicMock()
    mock_response = Mock()
    mock_response.status = 403
    mock_error = HttpError(mock_response, b'insufficient authentication scopes')
    mock_service.calendars().insert().execute.side_effect = mock_error

    with (
        patch('rotkehlchen.externalapis.google_calendar.Credentials', return_value=mock_creds),
        patch('rotkehlchen.externalapis.google_calendar.build', return_value=mock_service),
        pytest.raises(RemoteError, match='Insufficient permissions'),
    ):
        google_calendar_api._get_or_create_calendar()


def test_sync_events_empty_list(google_calendar_api):
    """Test sync_events with empty event list."""
    result = google_calendar_api.sync_events([])
    assert result == {
        'success': True,
        'calendar_id': '',
        'events_processed': 0,
        'events_created': 0,
        'events_updated': 0,
        'message': 'No calendar events found to sync',
    }


def test_sync_events_success(google_calendar_api, database):
    """Test sync_events creates and updates events successfully."""
    # Store credentials with calendar_id already set
    creds_data = {
        'token': 'mock_token',
        'refresh_token': 'mock_refresh_token',
        'user_email': 'test@example.com',
        'calendar_id': 'rotki_cal',
    }

    with database.conn.write_ctx() as cursor:
        cursor.execute(
            'INSERT INTO key_value_cache (name, value) VALUES (?, ?)',
            ('google_calendar_credentials', json.dumps(creds_data)),
        )

    mock_creds = _create_mock_credentials()

    # Create test events
    ens_timestamp = Timestamp(int(
        datetime.datetime.now(tz=datetime.UTC).timestamp() + DAY_IN_SECONDS,
    ))
    crv_timestamp = Timestamp(int(
        datetime.datetime.now(tz=datetime.UTC).timestamp() + 2 * DAY_IN_SECONDS,
    ))
    events = [
        CalendarEntry(
            identifier=1,
            name='ENS Renewal',
            description='Renew ENS domain',
            timestamp=ens_timestamp,
            counterparty='ENS',
            address=string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65'),
            blockchain=SupportedBlockchain.ETHEREUM,
            color='FF0000',
            auto_delete=False,
        ),
        CalendarEntry(
            identifier=2,
            name='CRV Unlock',
            description='CRV tokens unlock',
            timestamp=crv_timestamp,
            counterparty='Curve',
            address=None,
            blockchain=None,
            color='00FF00',
            auto_delete=True,
        ),
    ]

    # Mock service with one existing event
    mock_service = _create_mock_service(
        existing_events=[{
            'id': 'existing_event',
            'summary': 'ENS Renewal',
            'start': {'dateTime': datetime.datetime.fromtimestamp(ens_timestamp, tz=datetime.UTC).isoformat()},  # noqa: E501
        }],
    )

    with (
        patch('rotkehlchen.externalapis.google_calendar.Credentials', return_value=mock_creds),
        patch('rotkehlchen.externalapis.google_calendar.build', return_value=mock_service),
    ):
        result = google_calendar_api.sync_events(events)

    assert result['events_processed'] == 2
    assert result['events_created'] == 1  # CRV Unlock
    assert result['events_updated'] == 1  # ENS Renewal
    assert result['calendar_id'] == 'rotki_cal'
    assert 'errors' not in result


def test_sync_events_same_summary_different_times(google_calendar_api, database):
    """Events sharing the same name but different timestamps should both sync."""
    # Store credentials with calendar_id already set
    creds_data = {
        'token': 'mock_token',
        'refresh_token': 'mock_refresh_token',
        'user_email': 'test@example.com',
        'calendar_id': 'rotki_cal',
    }

    with database.conn.write_ctx() as cursor:
        cursor.execute(
            'INSERT INTO key_value_cache (name, value) VALUES (?, ?)',
            ('google_calendar_credentials', json.dumps(creds_data)),
        )

    mock_creds = _create_mock_credentials()

    base_ts = int(datetime.datetime.now(tz=datetime.UTC).timestamp())
    first_timestamp = Timestamp(base_ts + DAY_IN_SECONDS)
    second_timestamp = Timestamp(base_ts + 2 * DAY_IN_SECONDS)
    events = [
        CalendarEntry(
            identifier=1,
            name='Recurring Reminder',
            description='First reminder',
            timestamp=first_timestamp,
            counterparty=None,
            address=None,
            blockchain=None,
            color=None,
            auto_delete=False,
        ),
        CalendarEntry(
            identifier=2,
            name='Recurring Reminder',
            description='Second reminder',
            timestamp=second_timestamp,
            counterparty=None,
            address=None,
            blockchain=None,
            color=None,
            auto_delete=False,
        ),
    ]

    mock_service = _create_mock_service(
        existing_events=[
            {
                'id': 'existing_event_1',
                'summary': 'Recurring Reminder',
                'start': {'dateTime': datetime.datetime.fromtimestamp(first_timestamp, tz=datetime.UTC).isoformat()},  # noqa: E501
            },
            {
                'id': 'existing_event_2',
                'summary': 'Recurring Reminder',
                'start': {'dateTime': datetime.datetime.fromtimestamp(second_timestamp, tz=datetime.UTC).isoformat()},  # noqa: E501
            },
        ],
    )

    with (
        patch('rotkehlchen.externalapis.google_calendar.Credentials', return_value=mock_creds),
        patch('rotkehlchen.externalapis.google_calendar.build', return_value=mock_service),
    ):
        result = google_calendar_api.sync_events(events)

    assert result['events_processed'] == 2
    assert result['events_created'] == 0
    assert result['events_updated'] == 2


def test_sync_events_with_errors(google_calendar_api, database):
    """Test sync_events handles individual event errors gracefully."""
    _store_credentials(database)
    mock_creds = _create_mock_credentials()

    # Create test event with invalid timestamp
    events = [
        CalendarEntry(
            identifier=1,
            name='Invalid Event',
            description='This has invalid timestamp',
            timestamp=Timestamp(999999999999999),  # Invalid timestamp
            counterparty='Test',
            address=None,
            blockchain=None,
            color='0000FF',
            auto_delete=False,
        ),
    ]

    mock_service = _create_mock_service(
        calendar_list_items=[{'id': 'rotki_cal', 'summary': 'Rotki Events'}],
        existing_events=[],
    )

    with (
        patch('rotkehlchen.externalapis.google_calendar.Credentials', return_value=mock_creds),
        patch('rotkehlchen.externalapis.google_calendar.build', return_value=mock_service),
    ):
        result = google_calendar_api.sync_events(events)

    assert result['events_processed'] == 1
    assert result['events_created'] == 0
    assert result['events_updated'] == 0
    assert 'errors' in result
    assert len(result['errors']) == 1


def test_complete_oauth_with_token_success(google_calendar_api, database):
    """Test complete_oauth_with_token succeeds with valid tokens."""
    access_token = 'valid_access_token'
    refresh_token = 'valid_refresh_token'

    # Mock responses
    user_response = _create_mock_response(json_data={'email': 'user@example.com'})
    token_response = _create_mock_response(
        json_data={'scope': 'https://www.googleapis.com/auth/calendar.app.created openid email'},
    )

    mock_service = _create_mock_service(calendar_list_items=[])

    with (
        patch('requests.get', side_effect=[user_response, token_response]),
        patch('rotkehlchen.externalapis.google_calendar.build', return_value=mock_service),
    ):
        result = google_calendar_api.complete_oauth_with_token(access_token, refresh_token)

    assert result['success'] is True
    assert result['user_email'] == 'user@example.com'
    assert 'Successfully authenticated' in result['message']

    # Verify credentials were stored
    with database.conn.read_ctx() as cursor:
        stored = cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?',
            ('google_calendar_credentials',),
        ).fetchone()
        assert stored is not None
        creds = json.loads(stored[0])
        assert creds['token'] == access_token
        assert creds['refresh_token'] == refresh_token
        assert creds['user_email'] == 'user@example.com'


def test_complete_oauth_with_token_invalid_token(google_calendar_api):
    """Test complete_oauth_with_token fails with invalid token."""
    mock_response = _create_mock_response(status_code=401, text='Invalid token')

    with patch('requests.get', return_value=mock_response):
        result = google_calendar_api.complete_oauth_with_token('invalid_token', 'refresh_token')

    assert result['success'] is False
    assert 'Failed to validate tokens' in result['message']


def test_complete_oauth_with_token_missing_scope(google_calendar_api):
    """Test complete_oauth_with_token fails with missing scope."""
    # Mock responses
    user_response = _create_mock_response(json_data={'email': 'user@example.com'})
    # Missing calendar scope
    token_response = _create_mock_response(json_data={'scope': 'openid email'})

    with patch('requests.get', side_effect=[user_response, token_response]):
        result = google_calendar_api.complete_oauth_with_token(
            'token_without_scope',
            'refresh_token',
        )

    assert result['success'] is False
    assert 'missing required scope' in result['message']


def test_validate_access_token_success(google_calendar_api):
    """Test _validate_access_token with valid token."""
    mock_response = _create_mock_response(
        json_data={'email': 'test@example.com', 'verified_email': True},
    )

    with patch('requests.get', return_value=mock_response):
        user_info = google_calendar_api._validate_access_token('valid_token')

    assert user_info['email'] == 'test@example.com'


def test_validate_access_token_invalid(google_calendar_api):
    """Test _validate_access_token with invalid token."""
    mock_response = _create_mock_response(status_code=401, text='Invalid token')

    with (
        patch('requests.get', return_value=mock_response),
        pytest.raises(RemoteError, match='Invalid access token'),
    ):
        google_calendar_api._validate_access_token('invalid_token')


def test_verify_token_scopes_success(google_calendar_api):
    """Test _verify_token_scopes with correct scope."""
    mock_response = _create_mock_response(
        json_data={'scope': 'https://www.googleapis.com/auth/calendar.app.created openid email'},
    )

    with patch('requests.get', return_value=mock_response):
        # Should not raise
        google_calendar_api._verify_token_scopes('valid_token')


def test_verify_token_scopes_missing_scope(google_calendar_api):
    """Test _verify_token_scopes with missing scope."""
    # Missing calendar scope
    mock_response = _create_mock_response(json_data={'scope': 'openid email'})

    with (
        patch('requests.get', return_value=mock_response),
        pytest.raises(RemoteError, match='missing required scope'),
    ):
        google_calendar_api._verify_token_scopes('token_without_scope')
