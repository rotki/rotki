"""Google Calendar integration for syncing rotki calendar events using OAuth 2.0 desktop flow."""

from __future__ import annotations

import datetime
import json
import logging
import os
import threading
from typing import TYPE_CHECKING, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
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
        self._flow: InstalledAppFlow | None = None
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

                # Check if this is from external OAuth (our custom format)
                if creds_data.get('external_oauth'):
                    log.info('Loading external OAuth credentials')
                    self._credentials = Credentials(  # type: ignore[no-untyped-call]
                        token=creds_data['token'],
                        scopes=creds_data['scopes'],
                    )
                else:
                    # Use the original method for standard OAuth credentials
                    self._credentials = Credentials.from_authorized_user_info(  # type: ignore
                        creds_data,
                        GOOGLE_CALENDAR_SCOPES,
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
                                'token_uri': self._credentials.token_uri,
                                'client_id': self._credentials.client_id,
                                'client_secret': self._credentials.client_secret,
                                'scopes': self._credentials.scopes,
                            })),
                        )

            except Exception as e:
                log.error(f'Failed to load credentials: {e}')
                return None
            else:
                return self._credentials

    def start_oauth_flow(self) -> dict[str, Any]:
        """Start OAuth2 Authorization Code Flow for desktop apps.

        Returns information needed to complete the authorization in the frontend.
        The actual authorization will happen via run_authorization_flow().
        """
        # Default rotki OAuth credentials (for desktop app)
        # These are not secret - Google acknowledges that desktop app secrets
        # cannot be kept confidential. Users can optionally override these.
        client_id = os.environ.get(
            'ROTKI_GOOGLE_CLIENT_ID',
            # This would be rotki's actual client ID
            'XXX',
        )
        client_secret = os.environ.get(
            'ROTKI_GOOGLE_CLIENT_SECRET',
            # This would be rotki's actual client secret
            'XXX',
        )

        if client_id in (None, '', 'YOUR-ACTUAL-CLIENT-ID.apps.googleusercontent.com'):
            # Fall back to user-provided credentials if rotki's aren't configured
            # This allows both approaches: built-in or user-provided
            raise RemoteError(
                'Google Calendar integration requires OAuth credentials. '
                'Either use the built-in credentials or provide your own.',
            )

        # Create OAuth flow configuration
        client_config = {
            'installed': {
                'client_id': client_id,
                'client_secret': client_secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
                'redirect_uris': ['http://localhost', 'urn:ietf:wg:oauth:2.0:oob'],
            },
        }

        # Create the flow instance with PKCE enabled
        # For installed (desktop) apps, google-auth-oauthlib automatically uses PKCE
        self._flow = InstalledAppFlow.from_client_config(
            client_config,
            scopes=GOOGLE_CALENDAR_SCOPES,
        )

        # The Flow class automatically generates code_verifier and code_challenge for PKCE
        # when using the 'installed' application type. This is handled internally by
        # run_local_server() method which implements the full PKCE flow.

        # Store client credentials for later use
        with self.db.conn.write_ctx() as write_cursor:
            write_cursor.execute(
                'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                ('google_calendar_client_config', json.dumps(client_config)),
            )

        return {
            'status': 'ready',
            'message': 'Ready to connect to Google Calendar.',
        }

    def run_authorization_flow(self) -> dict[str, Any]:
        """Run the authorization flow by opening browser and starting local server.

        This should be called after start_oauth_flow() to actually perform the authorization.
        """
        if self._flow is None:
            # Try to restore flow from stored config
            with self.db.conn.read_ctx() as cursor:
                result = cursor.execute(
                    'SELECT value FROM key_value_cache WHERE name=?',
                    ('google_calendar_client_config',),
                ).fetchone()

                if result is None:
                    raise RemoteError('OAuth flow not initialized. Call start_oauth_flow first.')

                client_config = json.loads(result[0])
                self._flow = InstalledAppFlow.from_client_config(
                    client_config,
                    scopes=GOOGLE_CALENDAR_SCOPES,
                )

        try:
            # Run local server and get credentials using OAuth 2.0 with PKCE
            # port=0 means "use any available port"
            # This implements the full PKCE flow as described in the document:
            # 1. Generates code_verifier and code_challenge (handled by Flow internally)
            # 2. Starts a local web server on random port
            # 3. Opens browser to Google's auth page with code_challenge
            # 4. Waits for the callback with auth code
            # 5. Exchanges the code + code_verifier for tokens
            self._credentials = self._flow.run_local_server(  # pylint: disable=no-member
                port=0,
                authorization_prompt_message='',
                success_message=(
                    'Authorization complete! You can close this window and return to rotki.'
                ),
                open_browser=True,
            )

            # Save credentials to database
            if self._credentials:
                with self.db.conn.write_ctx() as write_cursor:
                    write_cursor.execute(
                        'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                        ('google_calendar_credentials', json.dumps({
                            'token': self._credentials.token,
                            'refresh_token': self._credentials.refresh_token,
                            'token_uri': self._credentials.token_uri,
                            'client_id': self._credentials.client_id,
                            'client_secret': self._credentials.client_secret,
                            'scopes': self._credentials.scopes,
                        })),
                    )
                    # Clean up the client config as it's no longer needed
                    write_cursor.execute(
                        'DELETE FROM key_value_cache WHERE name=?',
                        ('google_calendar_client_config',),
                    )

                log.info('Google Calendar OAuth2 authorization completed successfully')
                return {'success': True, 'message': 'Authorization successful'}
            else:
                raise RemoteError('Authorization failed: no credentials received')

        except Exception as e:
            log.error(f'OAuth authorization failed: {e}')
            raise RemoteError(f'Authorization failed: {e!s}') from e

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

    def complete_oauth_with_token(self, access_token: str) -> dict[str, Any]:
        """Complete OAuth flow using an access token from external OAuth flow.

        Args:
            access_token: The access token received from the external OAuth flow

        Returns:
            dict with success status and message
        """
        try:
            # Use the access token to get user info and validate the token
            import requests

            # Validate the access token by making a request to Google's userinfo endpoint
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers=headers,
                timeout=30,
            )

            if response.status_code != 200:
                msg = f'Invalid access token: {response.status_code} {response.text}'
                raise RemoteError(msg)

            user_info = response.json()
            log.info(f'Access token validated for user: {user_info.get("email", "unknown")}')

            # Check what scopes the token actually has
            token_info_response = requests.get(
                f'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}',
                timeout=30,
            )
            if token_info_response.status_code == 200:
                token_info = token_info_response.json()
                actual_scopes = token_info.get('scope', '').split(' ')
                log.info(f'Token has scopes: {actual_scopes}')

                required_scope = 'https://www.googleapis.com/auth/calendar'
                if required_scope not in actual_scopes:
                    msg = (
                        f'Access token is missing required scope: {required_scope}. '
                        f'Token has scopes: {actual_scopes}'
                    )
                    raise RemoteError(msg)
            else:
                log.warning(f'Could not verify token scopes: {token_info_response.status_code}')

            # Create a simple credentials object for immediate use
            # Note: This won't have refresh capabilities, but will work for current session
            credentials = Credentials(  # type: ignore[no-untyped-call]
                token=access_token,
                scopes=GOOGLE_CALENDAR_SCOPES,
            )

            # Test the credentials with a Calendar API call
            service = build('calendar', 'v3', credentials=credentials)

            # Add more detailed logging for debugging
            log.debug(f'Testing calendar API access with token: {access_token[:20]}...')
            log.debug(f'Credentials scopes: {credentials.scopes}')
            log.debug(f'Credentials valid: {credentials.valid}')

            calendar_list = service.calendarList().list().execute()  # pylint: disable=no-member
            calendar_count = len(calendar_list.get('items', []))
            log.debug(f'Calendar API test successful, found {calendar_count} calendars')

            # Store the access token and user info for this session
            # Note: This is a simplified storage for external OAuth tokens
            credentials_data = {
                'token': access_token,
                'scopes': GOOGLE_CALENDAR_SCOPES,
                'user_email': user_info.get('email'),
                'external_oauth': True,  # Flag to indicate this came from external OAuth
            }

            # Store credentials in database using the same method as existing code
            with self.db.conn.write_ctx() as write_cursor:
                write_cursor.execute(
                    'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
                    ('google_calendar_credentials', json.dumps(credentials_data)),
                )

            self._credentials = credentials
            self._service = service

            log.info('Google Calendar OAuth completed successfully with external access token')

            return {
                'success': True,
                'message': 'Successfully authenticated with Google Calendar',
                'user_email': user_info.get('email', 'Unknown'),
            }

        except Exception as e:
            error_msg = f'Failed to complete OAuth with access token: {e}'
            log.error(error_msg)
            return {
                'success': False,
                'message': error_msg,
            }
