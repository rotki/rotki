from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from rotkehlchen.banks.connector import sum_account_balances
from rotkehlchen.banks.errors import BankAuthExpired, BankMFARequired
from rotkehlchen.banks.manager import BankCredentialInput
from rotkehlchen.banks.manifests import BANK_MANIFESTS
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.misc import InputError, RemoteError
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
    ) -> tuple[bool | dict[str, Any] | None, str, HTTPStatus]:
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
            return self._challenge(e), '', HTTPStatus.ACCEPTED
        except InputError as e:
            return None, str(e), HTTPStatus.BAD_REQUEST
        if identifier is None:
            return None, msg, HTTPStatus.CONFLICT
        if (bank := self.rotkehlchen.bank_manager.get_bank(identifier)) is None:
            raise AssertionError('successful bank setup did not register the connection')
        return self._setup_success(bank), msg, HTTPStatus.OK

    @staticmethod
    def _challenge(error: BankMFARequired) -> dict[str, Any]:
        return error.challenge.serialize() | {'identifier': error.connection_identifier}

    def answer_authentication(
            self,
            identifier: ConnectionIdentifier,
            response: str | None,
    ) -> tuple[bool | dict[str, Any] | None, str, HTTPStatus]:
        manager = self.rotkehlchen.bank_manager
        completes_setup = manager.get_bank(identifier) is None
        try:
            result, message = manager.answer_bank_authentication(
                identifier=identifier,
                response=response,
            )
        except BankMFARequired as e:
            return self._challenge(e), '', HTTPStatus.ACCEPTED
        except BankAuthExpired as e:  # dropped by the bank: only a new sync or setup helps
            return None, str(e), HTTPStatus.GONE
        except RemoteError as e:
            return None, str(e), HTTPStatus.CONFLICT
        if result is False:
            return None, message, HTTPStatus.CONFLICT
        if completes_setup:
            if (bank := manager.get_bank(identifier)) is None:
                raise AssertionError('successful bank setup authentication did not register it')
            return self._setup_success(bank), '', HTTPStatus.OK
        return True, '', HTTPStatus.OK

    def edit_bank(
            self,
            identifier: ConnectionIdentifier,
            new_name: str | None,
            credentials: dict[str, str],
    ) -> tuple[bool | None, str, HTTPStatus]:
        try:
            result, msg = self.rotkehlchen.bank_manager.edit_bank(
                identifier=identifier,
                new_name=new_name,
                credentials=BankCredentialInput(values=credentials),
            )
        except InputError as e:
            return None, str(e), HTTPStatus.BAD_REQUEST
        if not result:
            return None, msg, HTTPStatus.CONFLICT
        return True, msg, HTTPStatus.OK

    def remove_bank(self, identifier: ConnectionIdentifier) -> tuple[bool | None, str, HTTPStatus]:
        result, msg = self.rotkehlchen.bank_manager.delete_bank(identifier)
        if not result:
            return None, msg, HTTPStatus.CONFLICT
        return True, msg, HTTPStatus.OK

    def cancel_authentication(
            self,
            identifier: ConnectionIdentifier,
    ) -> tuple[bool | None, str, HTTPStatus]:
        if not self.rotkehlchen.bank_manager.cancel_bank_authentication(identifier):
            return None, f'Bank connection {identifier} does not exist', HTTPStatus.CONFLICT
        return True, '', HTTPStatus.OK

    def sync_banks(
            self,
            connector: BankConnectorType | None,
            identifier: str | None,
    ) -> dict[str, Any]:
        try:
            self.rotkehlchen.bank_manager.query_bank_history_events(
                connector=connector,
                identifier=identifier,
            )
        except BankMFARequired:
            return {'result': None, 'message': '', 'status_code': HTTPStatus.ACCEPTED}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        return {'result': True, 'message': ''}

    def query_bank_balances(
            self,
            connector: BankConnectorType | None,
            identifier: str | None,
            ignore_cache: bool,
            value_threshold: FVal | None = None,
    ) -> dict[str, Any]:
        """Return aggregate balances and the balances of each individual bank connection.

        Limited to one connector's connections, or to one connection by its identifier.
        """
        manager = self.rotkehlchen.bank_manager
        if connector is not None and connector not in manager.connected_banks:
            return {
                'result': None,
                'message': f'No {connector!s} bank connection exists',
                'status_code': HTTPStatus.CONFLICT,
            }

        aggregate: dict[AssetWithOracles, Balance] = {}
        connections: list[dict[str, Any]] = []
        error_msg = ''
        if identifier is not None:
            if (
                (bank := manager.get_bank(identifier)) is None or
                (connector is not None and bank.manifest.connector != connector)
            ):
                return {
                    'result': None,
                    'message': f'No matching bank connection with identifier {identifier} exists',
                    'status_code': HTTPStatus.CONFLICT,
                }
            banks = [bank]
        elif connector is None:
            banks = list(manager.iterate_banks())
        else:
            banks = manager.connected_banks[connector]
        for bank in banks:
            status = manager.sync_status[bank.connection_identifier]
            try:
                accounts, msg = bank.query_account_balances(ignore_cache=ignore_cache)
            except BankMFARequired as e:
                status.set_challenge(e.challenge)
                error_msg += f'{bank.manifest.display_name} {bank.name} requires authentication. '
                continue
            if accounts is None:
                error_msg += msg
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
            return {'result': None, 'message': error_msg, 'status_code': HTTPStatus.CONFLICT}
        return {
            'result': {'aggregate': aggregate, 'connections': connections},
            'message': error_msg,
            'status_code': HTTPStatus.OK,
        }
