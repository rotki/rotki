"""Google Calendar integration for syncing rotki calendar events."""

from __future__ import annotations

import datetime
import json
import logging
from typing import TYPE_CHECKING, Any

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from rotkehlchen.errors.api import AuthenticationError
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.db.calendar import CalendarEntry
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Note: Device flow requires broader scopes than web flow
# calendar.events scope is not supported in device flow, so we use calendar scope
# This gives broader permissions (can manage calendars) but is required for device flow
GOOGLE_CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']
ROTKI_CALENDAR_NAME = 'Rotki Events'


class GoogleCalendarAPI:
    """Interface for Google Calendar API operations."""

    def __init__(self, database: DBHandler) -> None:
        self.db = database
        self._credentials: Credentials | None = None
        self._service: Any = None

    def _get_credentials(self) -> Credentials | None:
        """Get stored OAuth2 credentials."""
        if self._credentials and self._credentials.valid:
            return self._credentials

        # Try to get credentials from database
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT value FROM key_value_cache WHERE name=?',
                ('google_calendar_credentials',),
            )
            result = cursor.fetchone()
            credentials_data = result[0] if result else None
        if credentials_data:
            try:
                self._credentials = Credentials.from_authorized_user_info(  # type: ignore[no-untyped-call]
                    json.loads(credentials_data),
                )
                if self._credentials.expired and self._credentials.refresh_token:
                    self._credentials.refresh(Request())  # type: ignore[no-untyped-call]
                    # Save refreshed credentials
                    with self.db.conn.write_ctx() as write_cursor:
                        write_cursor.execute(
                            'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                            ('google_calendar_credentials', self._credentials.to_json()),
                        )
            except Exception as e:
                log.warning(f'Failed to load Google Calendar credentials: {e}')
                # Clear invalid credentials
                with self.db.conn.write_ctx() as write_cursor:
                    write_cursor.execute(
                        'DELETE FROM key_value_cache WHERE name=?',
                        ('google_calendar_credentials',),
                    )
            else:
                return self._credentials

        return None

    def start_oauth_flow(self, client_id: str, client_secret: str) -> dict[str, Any]:
        """Start OAuth2 device flow and return device code response."""
        # Basic validation for Client ID format
        if not client_id.endswith('.apps.googleusercontent.com'):
            raise RemoteError(
                'Invalid Client ID format. Make sure you are using a Client ID from a '
                '"TV and Limited Input devices" OAuth application type, not "Web application".',
            )

        self._client_id = client_id
        self._client_secret = client_secret

        device_code_url = 'https://oauth2.googleapis.com/device/code'

        data = {
            'client_id': client_id,
            'scope': ' '.join(GOOGLE_CALENDAR_SCOPES),
        }

        try:
            log.debug(
                f'Starting device flow with client_id: {client_id[:8]}..., '
                f'scope: {" ".join(GOOGLE_CALENDAR_SCOPES)}',
            )
            response = requests.post(device_code_url, data=data, timeout=30)

            if response.status_code != 200:
                log.error(
                    f'Device flow request failed with status {response.status_code}: '
                    f'{response.text}',
                )
                response.raise_for_status()

            device_response = response.json()

            # Store device code for polling (both in memory and database)
            self._device_code = device_response['device_code']
            self._poll_interval = device_response.get('interval', 5)

            # Store device code and client credentials in database for persistence
            with self.db.conn.write_ctx() as write_cursor:
                write_cursor.execute(
                    'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                    ('google_calendar_device_code', self._device_code),
                )
                write_cursor.execute(
                    'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                    ('google_calendar_client_id', self._client_id),
                )
                write_cursor.execute(
                    'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                    ('google_calendar_client_secret', self._client_secret),
                )

            return {
                'verification_url': device_response['verification_url'],
                'user_code': device_response['user_code'],
                'expires_in': device_response.get('expires_in', 1800),  # 30 minutes default
            }

        except requests.RequestException as e:
            error_msg = f'Failed to start OAuth device flow: {e}'
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    if 'error_description' in error_details:
                        error_msg += f' - {error_details["error_description"]}'
                    elif 'error' in error_details:
                        error_msg += f' - {error_details["error"]}'
                except Exception:
                    error_msg += f' - Response: {e.response.text}'
            log.error(error_msg)
            raise RemoteError(error_msg) from e

    def poll_for_authorization(self) -> bool:
        """Poll for authorization completion in device flow."""
        log.debug('poll_for_authorization: Starting poll request')

        # Try to get device code from memory first, then from database
        if not hasattr(self, '_device_code') or not self._device_code:
            log.debug('poll_for_authorization: Device code not in memory, loading from database')
            with self.db.conn.read_ctx() as cursor:
                result = cursor.execute(
                    'SELECT value FROM key_value_cache WHERE name=?',
                    ('google_calendar_device_code',),
                ).fetchone()

                if result is None:
                    log.error('Device flow not started. Call start_oauth_flow() first.')
                    return False

                self._device_code = result[0]
                log.debug('poll_for_authorization: Loaded device code from database')

        # Also load client credentials from database if not in memory
        if not hasattr(self, '_client_id') or not self._client_id:
            log.debug('poll_for_authorization: Loading client credentials from database')
            with self.db.conn.read_ctx() as cursor:
                client_id_result = cursor.execute(
                    'SELECT value FROM key_value_cache WHERE name=?',
                    ('google_calendar_client_id',),
                ).fetchone()
                client_secret_result = cursor.execute(
                    'SELECT value FROM key_value_cache WHERE name=?',
                    ('google_calendar_client_secret',),
                ).fetchone()

                if client_id_result is None or client_secret_result is None:
                    log.error(
                        'Client credentials not found. Device flow was not properly started.',
                    )
                    return False

                self._client_id = client_id_result[0]
                self._client_secret = client_secret_result[0]
                log.debug('poll_for_authorization: Loaded client credentials from database')

        log.debug(f'poll_for_authorization: Using device_code: {self._device_code[:10]}...')
        token_url = 'https://oauth2.googleapis.com/token'

        data = {
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'device_code': self._device_code,
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
        }

        try:
            log.debug('poll_for_authorization: Making request to Google token endpoint')
            log.debug(f'poll_for_authorization: Request data: client_id={self._client_id[:8]}..., grant_type={data["grant_type"]}')
            response = requests.post(token_url, data=data, timeout=30)
            log.debug(f'poll_for_authorization: Response status: {response.status_code}')
            log.debug(f'poll_for_authorization: Response text: {response.text}')

            if response.status_code == 200:
                log.debug('poll_for_authorization: Success! Got access token')
                token_response = response.json()

                # Create credentials object
                self._credentials = Credentials(  # type: ignore[no-untyped-call]
                    token=token_response['access_token'],
                    refresh_token=token_response.get('refresh_token'),
                    token_uri=token_url,
                    client_id=self._client_id,
                    client_secret=self._client_secret,
                    scopes=GOOGLE_CALENDAR_SCOPES,
                )

                # Store credentials in database and clean up device code
                with self.db.conn.write_ctx() as write_cursor:
                    write_cursor.execute(
                        'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                        ('google_calendar_credentials', self._credentials.to_json()),  # type: ignore[no-untyped-call]
                    )
                    # Clean up temporary OAuth flow data since we're done with it
                    write_cursor.execute(
                        'DELETE FROM key_value_cache WHERE name=?',
                        ('google_calendar_device_code',),
                    )
                    write_cursor.execute(
                        'DELETE FROM key_value_cache WHERE name=?',
                        ('google_calendar_client_id',),
                    )
                    write_cursor.execute(
                        'DELETE FROM key_value_cache WHERE name=?',
                        ('google_calendar_client_secret',),
                    )

                log.info('Google Calendar OAuth2 device flow completed successfully')
                return True

            # Handle error responses
            try:
                error_data = response.json()
                error = error_data.get('error')
                log.debug(f'poll_for_authorization: Error response: {error}')
            except Exception:
                log.error(
                    f'poll_for_authorization: Failed to parse error response: {response.text}',
                )
                return False

            if error == 'authorization_pending':
                # User hasn't authorized yet
                log.info('poll_for_authorization: Still waiting for user authorization - user needs to complete OAuth in browser')
                return False
            elif error == 'slow_down':
                # Increase polling interval
                log.debug('poll_for_authorization: Rate limited, slowing down')
                self._poll_interval += 5
                return False
            elif error == 'access_denied':
                log.error('User denied access to Google Calendar')
                raise AuthenticationError('User denied access to Google Calendar')
            elif error == 'expired_token':
                log.error('Device code expired')
                # Clean up expired OAuth flow data
                with self.db.conn.write_ctx() as write_cursor:
                    write_cursor.execute(
                        'DELETE FROM key_value_cache WHERE name=?',
                        ('google_calendar_device_code',),
                    )
                    write_cursor.execute(
                        'DELETE FROM key_value_cache WHERE name=?',
                        ('google_calendar_client_id',),
                    )
                    write_cursor.execute(
                        'DELETE FROM key_value_cache WHERE name=?',
                        ('google_calendar_client_secret',),
                    )
                raise AuthenticationError(
                    'Device code expired. Please start the authorization process again.',
                )
            else:
                log.error(f'Unknown OAuth error: {error}')
                raise RemoteError(f'OAuth error: {error}')

        except requests.RequestException as e:
            log.error(f'Failed to poll for authorization: {e}')
            raise RemoteError(f'Failed to poll for authorization: {e}') from e

    def _get_service(self) -> Any:
        """Get Google Calendar service instance."""
        if self._service is not None:
            return self._service

        credentials = self._get_credentials()
        if credentials is None:
            raise AuthenticationError('Google Calendar not authenticated')

        try:
            self._service = build('calendar', 'v3', credentials=credentials)
        except Exception as e:
            raise RemoteError(f'Failed to create Google Calendar service: {e}') from e
        else:
            return self._service

    def is_authenticated(self) -> bool:
        """Check if user has valid Google Calendar credentials."""
        credentials = self._get_credentials()
        return credentials is not None and credentials.valid

    def _get_or_create_rotki_calendar(self) -> str:
        """Get or create the Rotki calendar and return its ID."""
        service = self._get_service()

        try:
            # List existing calendars to find Rotki calendar
            calendars_result = service.calendarList().list().execute()  # pylint: disable=no-member
            calendars = calendars_result.get('items', [])

            for calendar in calendars:
                if calendar.get('summary') == ROTKI_CALENDAR_NAME:
                    return calendar['id']

            # Create new Rotki calendar if not found
            calendar = {
                'summary': ROTKI_CALENDAR_NAME,
                'description': 'Calendar events automatically synced from Rotki portfolio tracker',
                'timeZone': 'UTC',
            }

            created_calendar = service.calendars().insert(body=calendar).execute()  # pylint: disable=no-member
            return created_calendar['id']

        except HttpError as e:
            raise RemoteError(f'Failed to get or create Rotki calendar: {e}') from e

    def sync_events(self, calendar_entries: Sequence[CalendarEntry]) -> dict[str, Any]:
        """Sync rotki calendar events to Google Calendar."""
        if not self.is_authenticated():
            raise AuthenticationError('Google Calendar not authenticated')

        calendar_id = self._get_or_create_rotki_calendar()
        service = self._get_service()

        # Get current time to filter future events
        now = ts_now()
        future_entries = [entry for entry in calendar_entries if entry.timestamp >= now]

        try:
            # Get existing events from Google Calendar
            now_iso = datetime.datetime.fromtimestamp(now, tz=datetime.UTC).isoformat()
            events_result = service.events().list(  # pylint: disable=no-member
                calendarId=calendar_id,
                timeMin=now_iso,
                singleEvents=True,
                orderBy='startTime',
            ).execute()
            existing_events = events_result.get('items', [])

            # Create mapping of existing events by rotki event ID (stored in description)
            existing_by_rotki_id = {}
            for event in existing_events:
                description = event.get('description', '')
                if description.startswith('rotki_id:'):
                    try:
                        rotki_id = description.split('rotki_id:')[1].split('\n')[0].strip()
                        existing_by_rotki_id[rotki_id] = event
                    except IndexError:
                        continue  # Skip malformed descriptions

            created_count = 0
            updated_count = 0

            # Process each rotki calendar entry
            for entry in future_entries:
                entry_iso = datetime.datetime.fromtimestamp(
                    entry.timestamp, tz=datetime.UTC,
                ).isoformat()
                event_data = {
                    'summary': entry.name,
                    'description': f'rotki_id:{entry.identifier}\n\n{entry.description or ""}',
                    'start': {
                        'dateTime': entry_iso,
                        'timeZone': 'UTC',
                    },
                    'end': {
                        'dateTime': entry_iso,
                        'timeZone': 'UTC',
                    },
                    'reminders': {
                        'useDefault': False,
                        'overrides': [
                            {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                            {'method': 'popup', 'minutes': 60},       # 1 hour before
                        ],
                    },
                }

                if entry.color:
                    # Map rotki colors to Google Calendar color IDs (1-11)
                    color_mapping = {
                        '#5298FF': '9',  # Blue
                        '#5bf054': '11',  # Green
                        '#36cfc9': '7',  # Cyan
                        '#ffd966': '5',  # Yellow
                        '#fcceee': '4',  # Pink
                    }
                    if entry.color in color_mapping:
                        event_data['colorId'] = color_mapping[entry.color]

                existing_event = existing_by_rotki_id.get(entry.identifier)

                if existing_event:
                    # Update existing event if needed
                    if (existing_event.get('summary') != event_data['summary'] or
                        existing_event.get('description') != event_data['description'] or
                        existing_event.get('start', {}).get('dateTime') !=
                        event_data['start']['dateTime']):  # type: ignore[index]

                        service.events().update(  # pylint: disable=no-member
                            calendarId=calendar_id,
                            eventId=existing_event['id'],
                            body=event_data,
                        ).execute()
                        updated_count += 1
                else:
                    # Create new event
                    service.events().insert(  # pylint: disable=no-member
                        calendarId=calendar_id,
                        body=event_data,
                    ).execute()
                    created_count += 1

            return {
                'success': True,
                'calendar_id': calendar_id,
                'events_processed': len(future_entries),
                'events_created': created_count,
                'events_updated': updated_count,
            }

        except HttpError as e:
            raise RemoteError(f'Failed to sync events to Google Calendar: {e}') from e

    def disconnect(self) -> bool:
        """Disconnect Google Calendar integration by clearing stored credentials."""
        try:
            with self.db.conn.write_ctx() as write_cursor:
                write_cursor.execute(
                    'DELETE FROM key_value_cache WHERE name=?',
                    ('google_calendar_credentials',),
                )
            self._credentials = None
            self._service = None
        except Exception as e:
            log.error(f'Failed to disconnect Google Calendar: {e}')
            return False
        else:
            return True
