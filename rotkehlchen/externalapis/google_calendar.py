"""Google Calendar integration for syncing rotki calendar events."""

from __future__ import annotations

import datetime
import json
import logging
from typing import TYPE_CHECKING, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
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

    def start_oauth_flow(self, client_id: str, client_secret: str) -> str:
        """Start OAuth2 flow and return authorization URL for user to visit."""
        client_config = {
            'installed': {
                'client_id': client_id,
                'client_secret': client_secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': ['http://localhost:8080'],
            },
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=GOOGLE_CALENDAR_SCOPES,
            redirect_uri='http://localhost:8080',
        )

        # Store flow state for later use
        self._flow_state = flow.state
        self._flow = flow

        auth_url, _ = flow.authorization_url(
            prompt='consent',
            access_type='offline',
            include_granted_scopes='true',
        )
        return auth_url

    def complete_oauth_flow(self, auth_response_url: str) -> bool:
        """Complete OAuth2 flow with the redirect URL from browser."""
        try:
            if not hasattr(self, '_flow') or self._flow is None:
                log.error('OAuth flow not started. Call start_oauth_flow() first.')
                return False

            # Extract authorization code from the response URL
            self._flow.fetch_token(authorization_response=auth_response_url)
            self._credentials = self._flow.credentials

            # Store credentials in database
            with self.db.conn.write_ctx() as write_cursor:
                write_cursor.execute(
                    'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                    ('google_calendar_credentials', self._credentials.to_json()),
                )

            # Clean up flow state
            self._flow = None
            self._flow_state = None

        except Exception as e:
            log.error(f'Failed to complete Google Calendar authentication: {e}')
            return False
        else:
            return True

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
