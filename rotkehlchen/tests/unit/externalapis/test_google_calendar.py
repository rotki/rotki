"""Tests for Google Calendar integration."""

from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.google_calendar import GoogleCalendarAPI
from rotkehlchen.tests.utils.factories import make_google_calendar_entry


@pytest.fixture
def google_calendar_api(database: DBHandler) -> GoogleCalendarAPI:
    """Create a GoogleCalendarAPI instance for testing."""
    return GoogleCalendarAPI(database)


class TestGoogleCalendarAPI:
    """Tests for Google Calendar API integration."""

    def test_initialization(self, google_calendar_api: GoogleCalendarAPI):
        """Test GoogleCalendarAPI initialization."""
        assert google_calendar_api.db is not None
        assert google_calendar_api._credentials is None

    @patch('rotkehlchen.externalapis.google_calendar.Flow')
    def test_start_oauth_flow(self, mock_flow_class, google_calendar_api: GoogleCalendarAPI):
        """Test starting OAuth2 flow."""
        # Setup mock
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ('https://accounts.google.com/auth', 'state123')
        mock_flow_class.from_client_config.return_value = mock_flow

        # Test
        auth_url = google_calendar_api.start_oauth_flow('test_client_id', 'test_client_secret')

        # Assertions
        assert auth_url == 'https://accounts.google.com/auth'
        assert google_calendar_api._flow == mock_flow
        mock_flow_class.from_client_config.assert_called_once()
        mock_flow.authorization_url.assert_called_once_with(
            prompt='consent',
            access_type='offline',
            include_granted_scopes='true',
        )

    @patch('rotkehlchen.externalapis.google_calendar.Flow')
    def test_complete_oauth_flow_with_code(
        self,
        mock_flow_class,
        google_calendar_api: GoogleCalendarAPI,
    ):
        """Test completing OAuth2 flow with just authorization code."""
        # Setup mock flow
        mock_flow = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.to_json.return_value = '{"token": "test_token"}'
        mock_flow.credentials = mock_credentials

        # Set the flow
        google_calendar_api._flow = mock_flow

        # Test with just code
        result = google_calendar_api.complete_oauth_flow('test_auth_code')

        # Assertions
        assert result is True
        mock_flow.fetch_token.assert_called_once_with(
            authorization_response='http://localhost:8080?code=test_auth_code',
        )
        assert google_calendar_api._credentials == mock_credentials

    @patch('rotkehlchen.externalapis.google_calendar.Flow')
    def test_complete_oauth_flow_with_url(
        self,
        mock_flow_class,
        google_calendar_api: GoogleCalendarAPI,
    ):
        """Test completing OAuth2 flow with full URL."""
        # Setup mock flow
        mock_flow = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.to_json.return_value = '{"token": "test_token"}'
        mock_flow.credentials = mock_credentials

        # Set the flow
        google_calendar_api._flow = mock_flow

        # Test with full URL
        result = google_calendar_api.complete_oauth_flow('http://localhost:8080?code=test_auth_code')

        # Assertions
        assert result is True
        mock_flow.fetch_token.assert_called_once_with(
            authorization_response='http://localhost:8080?code=test_auth_code',
        )

    def test_complete_oauth_flow_without_start(self, google_calendar_api: GoogleCalendarAPI):
        """Test completing OAuth2 flow without starting it first."""
        result = google_calendar_api.complete_oauth_flow('test_auth_code')
        assert result is False

    @patch('rotkehlchen.externalapis.google_calendar.build')
    @patch('rotkehlchen.externalapis.google_calendar.Credentials')
    def test_sync_events(
        self,
        mock_credentials_class,
        mock_build,
        google_calendar_api: GoogleCalendarAPI,
    ):
        """Test syncing calendar events."""
        # Setup mocks
        mock_credentials = MagicMock()
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
        with google_calendar_api.db.conn.write_ctx() as cursor:
            cursor.execute(
                'INSERT INTO key_value_cache (name, value) VALUES (?, ?)',
                ('google_calendar_credentials', '{"token": "test"}'),
            )

        # Create test events
        calendar_entries = [make_google_calendar_entry()]

        # Test
        result = google_calendar_api.sync_events(calendar_entries)

        # Assertions
        assert result['total_events'] == 1
        assert result['events_created'] == 1
        assert result['events_updated'] == 0
        mock_service.events.return_value.insert.assert_called_once()

    @patch('rotkehlchen.externalapis.google_calendar.Credentials')
    def test_disconnect(self, mock_credentials_class, google_calendar_api: GoogleCalendarAPI):
        """Test disconnecting from Google Calendar."""
        # Store credentials
        with google_calendar_api.db.conn.write_ctx() as cursor:
            cursor.execute(
                'INSERT INTO key_value_cache (name, value) VALUES (?, ?)',
                ('google_calendar_credentials', '{"token": "test"}'),
            )

        # Test
        result = google_calendar_api.disconnect()

        # Assertions
        assert result is True
        assert google_calendar_api._credentials is None

        # Check credentials removed from DB
        with google_calendar_api.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT value FROM key_value_cache WHERE name = ?',
                ('google_calendar_credentials',),
            )
            assert cursor.fetchone() is None

    def test_sync_events_not_connected(self, google_calendar_api: GoogleCalendarAPI):
        """Test syncing events when not connected."""
        with pytest.raises(RemoteError, match='Google Calendar is not connected'):
            google_calendar_api.sync_events([])
