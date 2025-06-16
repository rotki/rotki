"""Tests for Google Calendar integration."""

from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.api import AuthenticationError
from rotkehlchen.externalapis.google_calendar import GoogleCalendarAPI
from rotkehlchen.tests.utils.factories import make_google_calendar_entry


@pytest.fixture(name='google_api')
def _google_api(database: DBHandler) -> GoogleCalendarAPI:
    """Create a GoogleCalendarAPI instance for testing."""
    return GoogleCalendarAPI(database)


class TestGoogleCalendarAPI:
    """Tests for Google Calendar API integration."""

    def test_initialization(self, google_api: GoogleCalendarAPI):
        """Test GoogleCalendarAPI initialization."""
        assert google_api.db is not None
        assert google_api._credentials is None

    @patch('rotkehlchen.externalapis.google_calendar.requests.post')
    def test_start_oauth_flow(self, mock_post, google_api: GoogleCalendarAPI):
        """Test starting OAuth2 device flow."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'device_code': 'test_device_code',
            'user_code': 'TEST-CODE',
            'verification_url': 'https://www.google.com/device',
            'expires_in': 1800,
            'interval': 5,
        }
        mock_post.return_value = mock_response

        # Test
        result = google_api.start_oauth_flow('test_client_id', 'test_client_secret')

        # Assertions
        assert result['user_code'] == 'TEST-CODE'
        assert result['verification_url'] == 'https://www.google.com/device'
        assert result['expires_in'] == 1800
        assert hasattr(google_api, '_device_code')
        assert google_api._device_code == 'test_device_code'
        mock_post.assert_called_once()

    @patch('rotkehlchen.externalapis.google_calendar.requests.post')
    def test_poll_for_authorization_success(self, mock_post, google_api: GoogleCalendarAPI):
        """Test polling for authorization success."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
        }
        mock_post.return_value = mock_response

        # Set device code
        google_api._device_code = 'test_device_code'
        google_api._client_id = 'test_client_id'
        google_api._client_secret = 'test_client_secret'

        # Test
        result = google_api.poll_for_authorization()

        # Assertions
        assert result is True
        assert google_api._credentials is not None
        mock_post.assert_called_once()

    @patch('rotkehlchen.externalapis.google_calendar.requests.post')
    def test_poll_for_authorization_pending(self, mock_post, google_api: GoogleCalendarAPI):
        """Test polling when authorization is still pending."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'authorization_pending'}
        mock_post.return_value = mock_response

        # Set device code
        google_api._device_code = 'test_device_code'
        google_api._client_id = 'test_client_id'
        google_api._client_secret = 'test_client_secret'

        # Test
        result = google_api.poll_for_authorization()

        # Assertions
        assert result is False
        mock_post.assert_called_once()

    @patch('rotkehlchen.externalapis.google_calendar.requests.post')
    def test_poll_for_authorization_denied(self, mock_post, google_api: GoogleCalendarAPI):
        """Test polling when user denies access."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'access_denied'}
        mock_post.return_value = mock_response

        # Set device code
        google_api._device_code = 'test_device_code'
        google_api._client_id = 'test_client_id'
        google_api._client_secret = 'test_client_secret'

        # Test
        with pytest.raises(AuthenticationError, match='User denied access'):
            google_api.poll_for_authorization()

    def test_poll_for_authorization_without_start(self, google_api: GoogleCalendarAPI):
        """Test polling without starting device flow first."""
        result = google_api.poll_for_authorization()
        assert result is False

    @patch('rotkehlchen.externalapis.google_calendar.build')
    @patch('rotkehlchen.externalapis.google_calendar.Credentials')
    def test_sync_events(
            self,
            mock_credentials_class,
            mock_build,
            google_api: GoogleCalendarAPI,
    ):
        """Test syncing calendar events."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_credentials.valid = True
        mock_credentials_class.from_authorized_user_info.return_value = mock_credentials

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock calendar list
        mock_calendar_list = MagicMock()
        mock_calendar_list.execute.return_value = {
            'items': [{'id': 'existing_cal_id', 'summary': 'Rotki Events'}],
        }
        mock_service.calendarList.return_value.list.return_value = mock_calendar_list

        # Mock events list (empty for simplicity)
        mock_events_list = MagicMock()
        mock_events_list.execute.return_value = {'items': []}
        mock_service.events.return_value.list.return_value = mock_events_list

        # Mock event insert
        mock_event_insert = MagicMock()
        mock_event_insert.execute.return_value = {'id': 'new_event_id'}
        mock_service.events.return_value.insert.return_value = mock_event_insert

        # Store credentials
        with google_api.db.conn.write_ctx() as cursor:
            cursor.execute(
                'INSERT INTO key_value_cache (name, value) VALUES (?, ?)',
                ('google_calendar_credentials', '{"token": "test"}'),
            )

        # Create test events
        calendar_entries = [make_google_calendar_entry()]

        # Test
        result = google_api.sync_events(calendar_entries)

        # Assertions
        assert result['events_processed'] == 1
        assert result['events_created'] == 1
        assert result['events_updated'] == 0
        mock_service.events.return_value.insert.assert_called_once()

    @patch('rotkehlchen.externalapis.google_calendar.Credentials')
    def test_disconnect(self, mock_credentials_class, google_api: GoogleCalendarAPI):
        """Test disconnecting from Google Calendar."""
        # Store credentials
        with google_api.db.conn.write_ctx() as cursor:
            cursor.execute(
                'INSERT INTO key_value_cache (name, value) VALUES (?, ?)',
                ('google_calendar_credentials', '{"token": "test"}'),
            )

        # Test
        result = google_api.disconnect()

        # Assertions
        assert result is True
        assert google_api._credentials is None

        # Check credentials removed from DB
        with google_api.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT value FROM key_value_cache WHERE name = ?',
                ('google_calendar_credentials',),
            )
            assert cursor.fetchone() is None

    def test_sync_events_not_connected(self, google_api: GoogleCalendarAPI):
        """Test syncing events when not connected."""
        with pytest.raises(AuthenticationError, match='Google Calendar not authenticated'):
            google_api.sync_events([])
