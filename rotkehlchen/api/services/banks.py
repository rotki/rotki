from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from rotkehlchen.banks.errors import BankMFARequired
from rotkehlchen.banks.manager import BankCredentialInput
from rotkehlchen.banks.manifests import BANK_MANIFESTS
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.utils.misc import combine_dicts, ts_now

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.balance import Balance
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.banks.connector import BankConnector
    from rotkehlchen.fval import FVal
    from rotkehlchen.locations.types import LocationIdentifier
    from rotkehlchen.rotkehlchen import Rotkehlchen


class BanksService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen

    @staticmethod
    def get_supported_banks() -> list[dict[str, Any]]:
        return [manifest.serialize() for manifest in BANK_MANIFESTS.values()]

    def get_banks(self) -> list[dict[str, Any]]:
        return self.rotkehlchen.bank_manager.get_connected_banks_info()

    @staticmethod
    def _setup_success(bank: BankConnector) -> dict[str, Any]:
        retention_days = bank.history_retention_days()
        return {
            'success': True,
            'history_start_ts': (
                ts_now() - retention_days * DAY_IN_SECONDS
                if retention_days is not None else None
            ),
        }

    def setup_bank(
            self,
            name: str,
            location: LocationIdentifier,
            credentials: dict[str, str],
    ) -> tuple[bool | dict[str, Any] | None, str, HTTPStatus]:
        try:
            result, msg = self.rotkehlchen.bank_manager.setup_bank(
                name=name,
                location=location,
                credentials=BankCredentialInput(values=credentials),
                database=self.rotkehlchen.data.db,
            )
        except BankMFARequired as e:
            return e.challenge.serialize(), '', HTTPStatus.ACCEPTED
        except InputError as e:
            return None, str(e), HTTPStatus.BAD_REQUEST
        if not result:
            return None, msg, HTTPStatus.CONFLICT
        if (bank := self.rotkehlchen.bank_manager.get_bank(name=name, location=location)) is None:
            raise AssertionError('successful bank setup did not register the connection')
        return self._setup_success(bank), msg, HTTPStatus.OK

    def answer_authentication(
            self,
            name: str,
            location: LocationIdentifier,
            response: str | None,
    ) -> tuple[bool | dict[str, Any] | None, str, HTTPStatus]:
        manager = self.rotkehlchen.bank_manager
        completes_setup = manager.get_bank(name=name, location=location) is None
        try:
            result, message = manager.answer_bank_authentication(
                name=name,
                location=location,
                response=response,
            )
        except BankMFARequired as e:
            return e.challenge.serialize(), '', HTTPStatus.ACCEPTED
        except RemoteError as e:
            return None, str(e), HTTPStatus.CONFLICT
        if result is False:
            return None, message, HTTPStatus.CONFLICT
        if completes_setup:
            if (bank := manager.get_bank(name=name, location=location)) is None:
                raise AssertionError('successful bank setup authentication did not register it')
            return self._setup_success(bank), '', HTTPStatus.OK
        return True, '', HTTPStatus.OK

    def edit_bank(
            self,
            name: str,
            location: LocationIdentifier,
            new_name: str | None,
            credentials: dict[str, str],
    ) -> tuple[bool | None, str, HTTPStatus]:
        try:
            result, msg = self.rotkehlchen.bank_manager.edit_bank(
                name=name,
                location=location,
                new_name=new_name,
                credentials=BankCredentialInput(values=credentials),
            )
        except InputError as e:
            return None, str(e), HTTPStatus.BAD_REQUEST
        if not result:
            return None, msg, HTTPStatus.CONFLICT
        return True, msg, HTTPStatus.OK

    def remove_bank(self, name: str, location: LocationIdentifier) -> tuple[bool | None, str, HTTPStatus]:  # noqa: E501
        result, msg = self.rotkehlchen.bank_manager.delete_bank(name=name, location=location)
        if not result:
            return None, msg, HTTPStatus.CONFLICT
        return True, msg, HTTPStatus.OK

    def sync_banks(self, location: LocationIdentifier | None, name: str | None) -> dict[str, Any]:
        try:
            self.rotkehlchen.bank_manager.query_bank_history_events(location=location, name=name)
        except BankMFARequired:
            return {'result': None, 'message': '', 'status_code': HTTPStatus.ACCEPTED}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        return {'result': True, 'message': ''}

    def query_bank_balances(
            self,
            location: LocationIdentifier | None,
            ignore_cache: bool,
            value_threshold: FVal | None = None,
    ) -> dict[str, Any]:
        """Balances per bank location, in the shape of the exchange balances endpoint"""
        manager = self.rotkehlchen.bank_manager
        if location is not None and location not in manager.connected_banks:
            return {
                'result': None,
                'message': f'No {location!s} bank connection exists',
                'status_code': HTTPStatus.CONFLICT,
            }

        final: dict[str, dict[AssetWithOracles, Balance]] = {}
        error_msg = ''
        banks = manager.connected_banks.get(location, []) if location is not None else list(manager.iterate_banks())  # noqa: E501
        for bank in banks:
            try:
                balances, msg = bank.query_balances(ignore_cache=ignore_cache)
            except BankMFARequired as e:
                manager.sync_status[bank.location_id()].auth_challenge = e.challenge
                error_msg += f'{bank.manifest.display_name} {bank.name} requires authentication. '
                continue
            if balances is None:
                error_msg += msg
                continue
            manager.sync_status[bank.location_id()].auth_challenge = None
            if value_threshold is not None:
                balances = {a: b for a, b in balances.items() if b.value > value_threshold}
            key = str(bank.location)
            final[key] = combine_dicts(final[key], balances) if key in final else balances

        if len(final) == 0 and error_msg != '':
            return {'result': None, 'message': error_msg, 'status_code': HTTPStatus.CONFLICT}
        result: Any = final[str(location)] if location is not None else final
        return {'result': result, 'message': error_msg, 'status_code': HTTPStatus.OK}
