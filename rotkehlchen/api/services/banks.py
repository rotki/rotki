from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from rotkehlchen.api.result import ApiResult, FailResult, OkResult
from rotkehlchen.banks.connector import sum_account_balances
from rotkehlchen.banks.errors import BankAuthExpired, BankMFARequired
from rotkehlchen.banks.manager import BankCredentialInput
from rotkehlchen.banks.manifests import BANK_MANIFESTS
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import InputError, RemoteError, combined_cause
from rotkehlchen.utils.misc import combine_dicts, ts_now

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.balance import Balance
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.banks.connector import BankConnector
    from rotkehlchen.banks.manifest import BankConnectorType
    from rotkehlchen.connections.types import ConnectionIdentifier
    from rotkehlchen.fval import FVal
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
            'identifier': bank.connection_identifier,
            'history_start_ts': (
                ts_now() - retention_days * DAY_IN_SECONDS
                if retention_days is not None else None
            ),
        }

    def setup_bank(
            self,
            name: str,
            connector: BankConnectorType,
            credentials: dict[str, str],
    ) -> ApiResult:
        """Returns the new connection's identifier, or when the bank asks for an
        authentication its challenge together with the identifier to answer it under"""
        try:
            identifier, msg = self.rotkehlchen.bank_manager.setup_bank(
                name=name,
                connector=connector,
                credentials=BankCredentialInput(values=credentials),
                database=self.rotkehlchen.data.db,
            )
        except BankMFARequired as e:
            return OkResult(self._challenge(e), status=HTTPStatus.ACCEPTED)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, e.cause)
        if identifier is None:
            return FailResult(msg, HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        if (bank := self.rotkehlchen.bank_manager.get_bank(identifier)) is None:
            raise AssertionError('successful bank setup did not register the connection')
        return OkResult(self._setup_success(bank), message=msg)

    @staticmethod
    def _challenge(error: BankMFARequired) -> dict[str, Any]:
        return error.challenge.serialize() | {'identifier': error.connection_identifier}

    def answer_authentication(
            self,
            identifier: ConnectionIdentifier,
            response: str | None,
    ) -> ApiResult:
        manager = self.rotkehlchen.bank_manager
        completes_setup = manager.get_bank(identifier) is None
        try:
            result, message = manager.answer_bank_authentication(
                identifier=identifier,
                response=response,
            )
        except BankMFARequired as e:
            return OkResult(self._challenge(e), status=HTTPStatus.ACCEPTED)
        except BankAuthExpired as e:  # dropped by the bank: only a new sync or setup helps
            return FailResult(str(e), HTTPStatus.GONE, e.cause)
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, e.cause)
        if result is False:
            return FailResult(message, HTTPStatus.CONFLICT, FailureCause.REMOTE_REJECTED)
        if completes_setup:
            if (bank := manager.get_bank(identifier)) is None:
                raise AssertionError('successful bank setup authentication did not register it')
            return OkResult(self._setup_success(bank))
        return OkResult(True)

    def edit_bank(
            self,
            identifier: ConnectionIdentifier,
            new_name: str | None,
            credentials: dict[str, str],
    ) -> ApiResult:
        try:
            result, msg = self.rotkehlchen.bank_manager.edit_bank(
                identifier=identifier,
                new_name=new_name,
                credentials=BankCredentialInput(values=credentials),
            )
        except InputError as e:
            return FailResult(str(e), HTTPStatus.BAD_REQUEST, FailureCause.INVALID_INPUT)
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, e.cause)
        if not result:
            return FailResult(msg, HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        return OkResult(True, message=msg)

    def remove_bank(self, identifier: ConnectionIdentifier) -> ApiResult:
        result, msg = self.rotkehlchen.bank_manager.delete_bank(identifier)
        if not result:
            return FailResult(msg, HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        return OkResult(True, message=msg)

    def cancel_authentication(
            self,
            identifier: ConnectionIdentifier,
    ) -> ApiResult:
        if not self.rotkehlchen.bank_manager.cancel_bank_authentication(identifier):
            return FailResult(
                f'Bank connection {identifier} does not exist',
                HTTPStatus.CONFLICT,
                FailureCause.NOT_FOUND,
            )
        return OkResult(True)

    def sync_banks(
            self,
            connector: BankConnectorType | None,
            identifier: str | None,
    ) -> ApiResult:
        try:
            self.rotkehlchen.bank_manager.query_bank_history_events(
                connector=connector,
                identifier=identifier,
            )
        except BankMFARequired:
            return OkResult(None, status=HTTPStatus.ACCEPTED)
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.BAD_GATEWAY, e.cause)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        return OkResult(True)

    def query_bank_balances(
            self,
            connector: BankConnectorType | None,
            identifier: str | None,
            ignore_cache: bool,
            value_threshold: FVal | None = None,
    ) -> ApiResult:
        """Return aggregate balances and the balances of each individual bank connection.

        Limited to one connector's connections, or to one connection by its identifier.
        """
        manager = self.rotkehlchen.bank_manager
        if connector is not None and connector not in manager.connected_banks:
            return FailResult(
                f'No {connector!s} bank connection exists',
                HTTPStatus.CONFLICT,
                FailureCause.NOT_FOUND,
            )

        aggregate: dict[AssetWithOracles, Balance] = {}
        connections: list[dict[str, Any]] = []
        failure_causes: set[FailureCause] = set()
        error_msg = ''
        if identifier is not None:
            if (
                (bank := manager.get_bank(identifier)) is None or
                (connector is not None and bank.manifest.connector != connector)
            ):
                return FailResult(
                    f'No matching bank connection with identifier {identifier} exists',
                    HTTPStatus.CONFLICT,
                    FailureCause.NOT_FOUND,
                )
            banks = [bank]
        elif connector is None:
            banks = list(manager.iterate_banks())
        else:
            banks = manager.connected_banks[connector]
        for bank in banks:
            status = manager.sync_status[bank.connection_identifier]
            try:
                accounts = bank.query_account_balances(ignore_cache=ignore_cache)
            except BankMFARequired as e:
                status.set_challenge(e.challenge)
                error_msg += f'{bank.manifest.display_name} {bank.name} requires authentication. '
                failure_causes.add(FailureCause.AUTH)
                continue
            if isinstance(accounts, RemoteError):
                error_msg += str(accounts)
                failure_causes.add(accounts.cause)
                continue
            # a cached success must not drop a challenge the connector still waits on
            status.drop_challenge(still_pending=bank.has_pending_authentication)
            balances = sum_account_balances(accounts)
            if value_threshold is not None:
                balances = {a: b for a, b in balances.items() if b.value > value_threshold}
                accounts = [x for x in accounts if x.account.asset in balances]
            aggregate = combine_dicts(aggregate, balances)
            connections.append({
                'identifier': bank.connection_identifier,
                'connector': bank.connector,
                'name': bank.name,
                'balances': balances,
                'accounts': [x.serialize() for x in accounts],
            })

        if len(connections) == 0 and error_msg != '':
            return FailResult(error_msg, HTTPStatus.CONFLICT, combined_cause(failure_causes))
        return OkResult({'aggregate': aggregate, 'connections': connections}, message=error_msg)
