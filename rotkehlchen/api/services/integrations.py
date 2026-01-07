import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import gevent

from rotkehlchen.chain.evm.types import ChainID
from rotkehlchen.db.calendar import CalendarEntry, CalendarFilterQuery, DBCalendar, ReminderEntry
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.gnosispay import (
    fetch_gnosis_pay_siwe_nonce,
    verify_gnosis_pay_siwe_signature as external_verify_gnosis_pay_siwe_signature,
)
from rotkehlchen.externalapis.google_calendar import GoogleCalendarAPI
from rotkehlchen.externalapis.monerium import Monerium
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.types import ApiKey, ExternalService, ExternalServiceApiCredentials

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class IntegrationsService:
    def __init__(self, rotkehlchen: 'Rotkehlchen') -> None:
        self.rotkehlchen = rotkehlchen

    def create_calendar_entry(self, calendar: CalendarEntry) -> dict[str, Any]:
        try:
            calendar_event_id = DBCalendar(self.rotkehlchen.data.db).create_calendar_entry(
                calendar=calendar,
            )
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}

        return {
            'result': {'entry_id': calendar_event_id},
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def delete_calendar_entry(self, identifier: int) -> dict[str, Any]:
        try:
            DBCalendar(self.rotkehlchen.data.db).delete_entry(
                identifier=identifier,
                entry_type='calendar',
            )
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def query_calendar(self, filter_query: CalendarFilterQuery) -> dict[str, Any]:
        result = DBCalendar(self.rotkehlchen.data.db).query_calendar_entry(
            filter_query=filter_query,
        )
        return {
            'result': process_result(result),
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def update_calendar_entry(self, calendar: CalendarEntry) -> dict[str, Any]:
        try:
            calendar_event_id = DBCalendar(self.rotkehlchen.data.db).update_calendar_entry(
                calendar=calendar,
            )
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}

        return {
            'result': {'entry_id': calendar_event_id},
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def create_calendar_reminder(self, reminders: list[ReminderEntry]) -> dict[str, Any]:
        success, failed = DBCalendar(self.rotkehlchen.data.db).create_reminder_entries(
            reminders=reminders,
        )
        result: dict[str, Any] = {'success': success}
        if len(failed):
            result['failed'] = failed

        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def delete_reminder_entry(self, identifier: int) -> dict[str, Any]:
        try:
            DBCalendar(self.rotkehlchen.data.db).delete_entry(
                identifier=identifier,
                entry_type='calendar_reminders',
            )
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def update_reminder_entry(self, reminder: ReminderEntry) -> dict[str, Any]:
        try:
            calendar_event_id = DBCalendar(self.rotkehlchen.data.db).update_reminder_entry(
                reminder=reminder,
            )
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}

        return {
            'result': {'entry_id': calendar_event_id},
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def query_reminders(self, event_id: int) -> dict[str, Any]:
        result = DBCalendar(self.rotkehlchen.data.db).query_reminder_entry(event_id=event_id)
        return {
            'result': process_result(result),
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def get_google_calendar_status(self) -> dict[str, Any]:
        try:
            google_calendar = GoogleCalendarAPI(self.rotkehlchen.data.db)
            is_authenticated = google_calendar.is_authenticated()

            user_email = None
            if is_authenticated:
                user_email = google_calendar.get_connected_user_email()

        except Exception as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}
        return {
            'result': {
                'authenticated': is_authenticated,
                'user_email': user_email,
            },
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def sync_google_calendar(self) -> dict[str, Any]:
        try:
            google_calendar = GoogleCalendarAPI(self.rotkehlchen.data.db)
            db_calendar = DBCalendar(self.rotkehlchen.data.db)
            calendar_result = db_calendar.query_calendar_entry(
                CalendarFilterQuery.make(),
            )
            calendar_entries = calendar_result['entries']
            result = google_calendar.sync_events(calendar_entries)
        except Exception as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def disconnect_google_calendar(self) -> dict[str, Any]:
        try:
            google_calendar = GoogleCalendarAPI(self.rotkehlchen.data.db)
            success = google_calendar.disconnect()
            if success.get('success') is not True:
                return {
                    'result': None,
                    'message': 'Failed to disconnect Google Calendar',
                    'status_code': HTTPStatus.BAD_REQUEST,
                }
        except Exception as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}
        return {'result': {'success': True}, 'message': '', 'status_code': HTTPStatus.OK}

    def complete_google_calendar_oauth(
            self,
            access_token: str,
            refresh_token: str,
    ) -> dict[str, Any]:
        try:
            google_calendar = GoogleCalendarAPI(self.rotkehlchen.data.db)
            result = google_calendar.complete_oauth_with_token(access_token, refresh_token)
        except Exception as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def get_monerium_status(self) -> dict[str, Any]:
        monerium = Monerium(self.rotkehlchen.data.db)
        return {
            'result': monerium.oauth_client.get_status(),
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def complete_monerium_oauth(
            self,
            access_token: str,
            refresh_token: str,
            expires_in: int,
    ) -> dict[str, Any]:
        try:
            result = Monerium(self.rotkehlchen.data.db).oauth_client.complete_oauth(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
            )
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}

        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def disconnect_monerium(self) -> dict[str, Any]:
        Monerium(self.rotkehlchen.data.db).oauth_client.clear_credentials()
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def get_gnosis_pay_safe_admin_addresses(self) -> dict[str, Any]:
        if not (tracked_addresses := self.rotkehlchen.chains_aggregator.accounts.gnosis):
            return {'result': {}, 'message': '', 'status_code': HTTPStatus.OK}

        gnosis_manager = self.rotkehlchen.chains_aggregator.get_evm_manager(ChainID.GNOSIS)
        try:
            addresses_with_admins = gnosis_manager.node_inquirer.get_safe_admins_for_addresses(tracked_addresses)  # type: ignore  # mypy doesn't identify the inquirer as GnosisInquirer  # noqa: E501
        except (RemoteError, DeserializationError) as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        return {'result': addresses_with_admins, 'message': '', 'status_code': HTTPStatus.OK}

    def fetch_gnosis_pay_nonce(self) -> dict[str, Any]:
        try:
            nonce = fetch_gnosis_pay_siwe_nonce()
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        return {'result': nonce, 'message': '', 'status_code': HTTPStatus.OK}

    def verify_gnosis_pay_siwe_signature(
            self,
            message: str,
            signature: str,
    ) -> dict[str, Any]:
        try:
            token = external_verify_gnosis_pay_siwe_signature(
                message=message,
                signature=signature,
            )
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        log.debug('Got a valid token from gnosis pay. Saving it in credentials')
        with self.rotkehlchen.data.db.user_write() as write_cursor:
            self.rotkehlchen.data.db.add_external_service_credentials(
                write_cursor=write_cursor,
                credentials=[ExternalServiceApiCredentials(
                    service=ExternalService.GNOSIS_PAY,
                    api_key=ApiKey(token),
                )],
            )

        chain_manager = self.rotkehlchen.chains_aggregator.get_evm_manager(ChainID.GNOSIS)
        gnosispay_decoder = chain_manager.transactions_decoder.decoders.get('GnosisPay')
        if gnosispay_decoder is not None:
            gnosispay_decoder.reload_data()  # type: ignore
            if gnosispay_decoder.gnosispay_api is not None:  # type: ignore
                gevent.spawn(
                    gnosispay_decoder.gnosispay_api.backfill_missing_events,  # type: ignore
                )

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}
