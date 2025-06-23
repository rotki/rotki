"""Google Calendar integration for syncing rotki calendar events using OAuth 2.0 desktop flow."""

from __future__ import annotations

import datetime
import json
import logging
import threading
from typing import TYPE_CHECKING, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from rotkehlchen.errors.api import AuthenticationError
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.db.calendar import CalendarEntry
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Google Calendar API scope - need full calendar access to read calendar list and create calendars
GOOGLE_CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']
ROTKI_CALENDAR_NAME = 'Rotki Events'


class GoogleCalendarAPI:
    """Interface for Google Calendar API operations using OAuth 2.0 desktop flow."""

    def __init__(self, database: DBHandler) -> None:
        self.db = database
        self._credentials: Credentials | None = None
        self._service: Any = None
        self._auth_code: str | None = None
        self._auth_error: str | None = None
        self._auth_complete = threading.Event()

    def _get_credentials(self) -> Credentials | None:
        """Get stored OAuth2 credentials."""
        if self._credentials and self._credentials.valid:
            return self._credentials

        # Try to get credentials from database
        with self.db.conn.read_ctx() as cursor:
            result = cursor.execute(
                'SELECT value FROM key_value_cache WHERE name=?',
                ('google_calendar_credentials',),
            ).fetchone()

            if result is None:
                return None

            try:
                creds_data = json.loads(result[0])

                log.info('Loading OAuth credentials')
                self._credentials = Credentials(  # type: ignore[no-untyped-call]
                    token=creds_data['token'],
                    refresh_token=creds_data['refresh_token'],
                    scopes=GOOGLE_CALENDAR_SCOPES,
                )

                # Refresh if expired
                if (
                    self._credentials and self._credentials.expired and
                    self._credentials.refresh_token
                ):
                    log.debug('Refreshing expired Google Calendar credentials')
                    self._credentials.refresh(Request())  # type: ignore

                    # Save refreshed credentials
                    with self.db.conn.write_ctx() as write_cursor:
                        write_cursor.execute(
                            'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                            ('google_calendar_credentials', json.dumps({
                                'token': self._credentials.token,
                                'refresh_token': self._credentials.refresh_token,
                                'user_email': creds_data.get('user_email'),
                            })),
                        )

            except Exception as e:
                log.error(f'Failed to load credentials: {e}')
                return None
            else:
                return self._credentials

    def is_authenticated(self) -> bool:
        """Check if user has valid Google Calendar credentials."""
        credentials = self._get_credentials()
        if credentials is None:
            return False

        # Check if credentials are valid and have the correct scope
        if not credentials.valid:
            return False

        # Verify we have the correct scope
        if not credentials.scopes or GOOGLE_CALENDAR_SCOPES[0] not in credentials.scopes:
            log.debug('Google Calendar credentials have wrong scope, need to re-authorize')
            return False

        return True

    def get_connected_user_email(self) -> str | None:
        """Get the email of the connected Google account."""
        try:
            # Try to get email from stored credentials first
            with self.db.conn.read_ctx() as cursor:
                result = cursor.execute(
                    'SELECT value FROM key_value_cache WHERE name=?',
                    ('google_calendar_credentials',),
                ).fetchone()

                if result:
                    creds_data = json.loads(result[0])
                    if 'user_email' in creds_data:
                        return creds_data['user_email']

            # If no email in stored credentials, try to get it from Google API
            credentials = self._get_credentials()
            if credentials and credentials.valid:
                import requests
                headers = {'Authorization': f'Bearer {credentials.token}'}
                response = requests.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers=headers,
                    timeout=30,
                )

                if response.status_code == 200:
                    user_info = response.json()
                    return user_info.get('email')
                else:
                    return None
            else:
                return None
        except Exception as e:
            log.error(f'Failed to get connected user email: {e}')
            return None

    def disconnect(self) -> dict[str, Any]:
        """Disconnect Google Calendar by removing stored credentials."""
        with self.db.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'DELETE FROM key_value_cache WHERE name IN (?, ?)',
                ('google_calendar_credentials', 'google_calendar_client_config'),
            )

        self._credentials = None
        self._service = None
        self._flow = None

        log.info('Google Calendar disconnected')
        return {'success': True}

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

    def _get_or_create_calendar(self) -> str:
        """Get or create the Rotki calendar and return its ID."""
        service = self._get_service()

        try:
            # First, try to find existing Rotki calendar
            calendars = service.calendarList().list().execute()  # pylint: disable=no-member
            for calendar in calendars.get('items', []):
                if calendar.get('summary') == ROTKI_CALENDAR_NAME:
                    log.debug(f'Found existing Rotki calendar with ID: {calendar["id"]}')
                    return calendar['id']

            # Calendar doesn't exist, create it
            calendar_body = {
                'summary': ROTKI_CALENDAR_NAME,
                'description': (
                    'Automated calendar for rotki events like ENS expirations, CRV locks, '
                    'and airdrops'
                ),
                'timeZone': 'UTC',
            }

            created_calendar = service.calendars().insert(body=calendar_body).execute()  # pylint: disable=no-member
            calendar_id = created_calendar['id']
            log.info(f'Created new Rotki calendar with ID: {calendar_id}')

        except HttpError as e:
            if e.resp.status == 403 and 'insufficient authentication scopes' in str(e).lower():
                raise RemoteError(
                    'Insufficient permissions for Google Calendar. Please disconnect and '
                    'reconnect to grant the necessary permissions.',
                ) from e
            raise RemoteError(f'Failed to get or create Rotki calendar: {e}') from e
        else:
            return calendar_id

    def sync_events(self, events: Sequence[CalendarEntry]) -> dict[str, Any]:
        """Sync rotki calendar events to Google Calendar."""
        log.debug(f'Syncing {len(events)} calendar entries to Google Calendar')

        if len(events) == 0:
            log.info('No calendar events found in rotki to sync')
            return {
                'success': True,
                'calendar_id': '',
                'events_processed': 0,
                'events_created': 0,
                'events_updated': 0,
                'message': 'No calendar events found to sync',
            }
        calendar_id = self._get_or_create_calendar()
        service = self._get_service()

        events_processed = 0
        events_created = 0
        events_updated = 0
        errors = []

        # Get existing events from Google Calendar
        try:
            existing_events = {}
            page_token = None

            while True:
                events_result = service.events().list(  # pylint: disable=no-member
                    calendarId=calendar_id,
                    pageToken=page_token,
                    maxResults=2500,  # Max allowed by Google
                    fields='items(id,summary,description,start,end),nextPageToken',
                ).execute()

                for event in events_result.get('items', []):
                    # Store by summary (title) for matching
                    existing_events[event.get('summary', '')] = event

                page_token = events_result.get('nextPageToken')
                if not page_token:
                    break

        except HttpError as e:
            raise RemoteError(f'Failed to list existing calendar events: {e}') from e

        # Sync each rotki event
        for entry in events:
            events_processed += 1

            log.debug(
                f'Processing event: {entry.name}, timestamp: {entry.timestamp}, '
                f'type: {type(entry.timestamp)}',
            )

            # Convert timestamp to datetime
            try:
                # Check if timestamp is in milliseconds (common issue)
                if isinstance(entry.timestamp, int | float) and entry.timestamp > 1e10:
                    # Timestamp is likely in milliseconds, convert to seconds
                    timestamp_seconds = entry.timestamp / 1000
                    log.debug(
                        f'Converting milliseconds timestamp {entry.timestamp} to seconds '
                        f'{timestamp_seconds}',
                    )
                else:
                    timestamp_seconds = entry.timestamp

                event_date = datetime.datetime.fromtimestamp(
                    timestamp_seconds,
                    tz=datetime.UTC,
                )
                log.debug(f'Event date: {event_date}')
            except (ValueError, OSError) as e:
                log.error(
                    f'Failed to convert timestamp {entry.timestamp} for event {entry.name}: {e}',
                )
                errors.append(f'Failed to convert timestamp for event "{entry.name}": {e}')
                continue

            # Create event data
            description = entry.description or ''

            # Add additional details to description
            details = []
            if entry.counterparty:
                details.append(f'Counterparty: {entry.counterparty}')
            if entry.blockchain:
                details.append(f'Blockchain: {entry.blockchain.value}')
            if hasattr(entry, 'address') and entry.address:
                details.append(f'Address: {entry.address}')

            # Combine description with details
            if details:
                if description:
                    description += '\n\n' + '\n'.join(details)
                else:
                    description = '\n'.join(details)
            event_data = {
                'summary': entry.name,
                'description': description.strip(),
                'start': {
                    'dateTime': event_date.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': (event_date + datetime.timedelta(hours=1)).isoformat(),
                    'timeZone': 'UTC',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 60},       # 1 hour before
                    ],
                },
            }

            try:
                # Check if event already exists
                existing_event = existing_events.get(entry.name)

                if existing_event:
                    # Update existing event
                    service.events().update(  # pylint: disable=no-member
                        calendarId=calendar_id,
                        eventId=existing_event['id'],
                        body=event_data,
                    ).execute()
                    events_updated += 1
                    log.debug(f'Updated event: {entry.name}')
                else:
                    # Create new event
                    service.events().insert(  # pylint: disable=no-member
                        calendarId=calendar_id,
                        body=event_data,
                    ).execute()
                    events_created += 1
                    log.debug(f'Created event: {entry.name}')

            except HttpError as e:
                error_msg = f'Failed to sync event "{entry.name}": {e}'
                log.error(error_msg)
                errors.append(error_msg)

        result = {
            'events_processed': events_processed,
            'events_created': events_created,
            'events_updated': events_updated,
            'calendar_id': calendar_id,
        }

        if errors:
            result['errors'] = errors

        log.info(
            f'Calendar sync completed: {events_created} created, '
            f'{events_updated} updated out of {events_processed} total events',
        )

        return result

    def complete_oauth_with_token(self, access_token: str, refresh_token: str) -> dict[str, Any]:
        """Complete OAuth flow using tokens from external OAuth flow.

        Args:
            access_token: The access token received from the external OAuth flow
            refresh_token: The refresh token received from the external OAuth flow

        Returns:
            dict with success status and message
        """
        try:

            # Validate token and get user info
            user_info = self._validate_access_token(access_token)
            self._verify_token_scopes(access_token)

            # Create and test credentials
            credentials = self._create_credentials(access_token, refresh_token)
            self._test_calendar_access(credentials)

            # Store credentials and update instance state
            email_address = user_info.get('email', 'Unknown')
            self._store_external_credentials(access_token, refresh_token, email_address)
            self._credentials = credentials
            self._service = build('calendar', 'v3', credentials=credentials)

        except Exception as e:
            error_msg = f'Failed to complete OAuth with tokens: {e}'
            log.error(error_msg)
            return {
                'success': False,
                'message': error_msg,
            }

        else:
            log.info('Google Calendar OAuth completed successfully with external tokens')
            return {
                'success': True,
                'message': 'Successfully authenticated with Google Calendar',
                'user_email': email_address,
            }

    def _validate_access_token(self, access_token: str) -> dict[str, Any]:
        """Validate access token and return user info."""
        import requests

        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers=headers,
            timeout=30,
        )

        if response.status_code != 200:
            raise RemoteError(f'Invalid access token: {response.status_code} {response.text}')

        user_info = response.json()
        log.info(f'Access token validated for user: {user_info.get("email", "unknown")}')
        return user_info

    def _verify_token_scopes(self, access_token: str) -> None:
        """Verify that the token has required scopes."""
        import requests

        response = requests.get(
            f'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}',
            timeout=30,
        )

        if response.status_code != 200:
            log.warning(f'Could not verify token scopes: {response.status_code}')
            return

        token_info = response.json()
        actual_scopes = token_info.get('scope', '').split(' ')
        log.debug(f'Token has scopes: {actual_scopes}')

        required_scope = 'https://www.googleapis.com/auth/calendar'
        if required_scope not in actual_scopes:
            raise RemoteError(
                f'Access token is missing required scope: {required_scope}. '
                f'Token has scopes: {actual_scopes}',
            )

    def _create_credentials(self, access_token: str, refresh_token: str) -> Credentials:
        """Create Google credentials object with refresh capability."""
        return Credentials(  # type: ignore[no-untyped-call]
            token=access_token,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            scopes=GOOGLE_CALENDAR_SCOPES,
        )

    def _test_calendar_access(self, credentials: Credentials) -> None:
        """Test credentials by making a Calendar API call."""
        service = build('calendar', 'v3', credentials=credentials)

        log.debug('Testing calendar API access...')
        calendar_list = service.calendarList().list().execute()  # pylint: disable=no-member
        calendar_count = len(calendar_list.get('items', []))
        log.debug(f'Calendar API test successful, found {calendar_count} calendars')

    def _store_external_credentials(
            self,
            access_token: str,
            refresh_token: str,
            user_email: str,
    ) -> None:
        """Store external OAuth credentials in database."""
        credentials_data = {
            'token': access_token,
            'refresh_token': refresh_token,
            'user_email': user_email,
        }

        with self.db.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                ('google_calendar_credentials', json.dumps(credentials_data)),
           )
