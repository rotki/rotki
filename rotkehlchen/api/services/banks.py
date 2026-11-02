from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from rotkehlchen.api.result import ApiResult, FailResult, OkResult
from rotkehlchen.banks.errors import BankAuthExpired, BankMFARequired
from rotkehlchen.banks.manager import BankCredentialInput
from rotkehlchen.banks.manifests import BANK_MANIFESTS
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.utils.misc import combine_dicts, ts_now

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.balance import Balance
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.banks.connector import BankConnector
    from rotkehlchen.fval import FVal
    from rotkehlchen.rotkehlchen import Rotkehlchen
    from rotkehlchen.types import Location


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
            location: Location,
            credentials: dict[str, str],
    ) -> ApiResult:
        try:
            result, msg = self.rotkehlchen.bank_manager.setup_bank(
                name=name,
                location=location,
                credentials=BankCredentialInput(values=credentials),
                database=self.rotkehlchen.data.db,
            )
        except BankMFARequired as e:
            return OkResult(e.challenge.serialize(), status=HTTPStatus.ACCEPTED)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)
        if not result:
            return FailResult(msg, HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        if (bank := self.rotkehlchen.bank_manager.get_bank(name=name, location=location)) is None:
            raise AssertionError('successful bank setup did not register the connection')
        return OkResult(self._setup_success(bank), message=msg)

    def answer_authentication(
            self,
            name: str,
            location: Location,
            response: str | None,
    ) -> ApiResult:
        manager = self.rotkehlchen.bank_manager
        completes_setup = manager.get_bank(name=name, location=location) is None
        try:
            result, message = manager.answer_bank_authentication(
                name=name,
                location=location,
                response=response,
            )
        except BankMFARequired as e:
            return OkResult(e.challenge.serialize(), status=HTTPStatus.ACCEPTED)
        except BankAuthExpired as e:  # dropped by the bank: only a new sync or setup helps
            return FailResult(str(e), HTTPStatus.GONE, FailureCause.AUTH)
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, e.cause)
        if result is False:
            return FailResult(message, HTTPStatus.CONFLICT, FailureCause.REMOTE_REJECTED)
        if completes_setup:
            if (bank := manager.get_bank(name=name, location=location)) is None:
                raise AssertionError('successful bank setup authentication did not register it')
            return OkResult(self._setup_success(bank))
        return OkResult(True)

    def edit_bank(
            self,
            name: str,
            location: Location,
            new_name: str | None,
            credentials: dict[str, str],
    ) -> ApiResult:
        try:
            result, msg = self.rotkehlchen.bank_manager.edit_bank(
                name=name,
                location=location,
                new_name=new_name,
                credentials=BankCredentialInput(values=credentials),
            )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)
        if not result:
            return FailResult(msg, HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        return OkResult(True, message=msg)

    def remove_bank(self, name: str, location: Location) -> ApiResult:
        result, msg = self.rotkehlchen.bank_manager.delete_bank(name=name, location=location)
        if not result:
            return FailResult(msg, HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        return OkResult(True, message=msg)

    def cancel_authentication(
            self,
            name: str,
            location: Location,
    ) -> ApiResult:
        if not self.rotkehlchen.bank_manager.cancel_bank_authentication(name=name, location=location):  # noqa: E501
            return FailResult(
                f'{location!s} bank connection {name} does not exist',
                HTTPStatus.CONFLICT,
                FailureCause.NOT_FOUND,
            )
        return OkResult(True)

    def sync_banks(self, location: Location | None, name: str | None) -> ApiResult:
        try:
            self.rotkehlchen.bank_manager.query_bank_history_events(location=location, name=name)
        except BankMFARequired:
            return OkResult(None, status=HTTPStatus.ACCEPTED)
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.BAD_GATEWAY, e.cause)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        return OkResult(True)

    def query_bank_balances(
            self,
            location: Location | None,
            ignore_cache: bool,
            value_threshold: FVal | None = None,
    ) -> ApiResult:
        """Balances per bank location, in the shape of the exchange balances endpoint"""
        manager = self.rotkehlchen.bank_manager
        if location is not None and location not in manager.connected_banks:
            return FailResult(
                f'No {location!s} bank connection exists',
                HTTPStatus.CONFLICT,
                FailureCause.NOT_FOUND,
            )

        final: dict[str, dict[AssetWithOracles, Balance]] = {}
        error_msg = ''
        banks = manager.connected_banks.get(location, []) if location is not None else list(manager.iterate_banks())  # noqa: E501
        for bank in banks:
            status = manager.sync_status[bank.location_id()]
            try:
                balances, msg = bank.query_balances(ignore_cache=ignore_cache)
            except BankMFARequired as e:
                status.set_challenge(e.challenge)
                error_msg += f'{bank.manifest.display_name} {bank.name} requires authentication. '
                continue
            if balances is None:
                error_msg += msg
                continue
            # a cached success must not drop a challenge the connector still waits on
            status.drop_challenge(still_pending=bank.has_pending_authentication)
            if value_threshold is not None:
                balances = {a: b for a, b in balances.items() if b.value > value_threshold}
            key = str(bank.location)
            final[key] = combine_dicts(final[key], balances) if key in final else balances

        if len(final) == 0 and error_msg != '':
            return FailResult(error_msg, HTTPStatus.CONFLICT, FailureCause.NETWORK)
        result: Any = final[str(location)] if location is not None else final
        return OkResult(result, message=error_msg)
