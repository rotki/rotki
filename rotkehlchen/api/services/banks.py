from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

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
        try:
            result, msg = self.rotkehlchen.bank_manager.setup_bank(
                name=name,
                connector=connector,
                credentials=BankCredentialInput(values=credentials),
                database=self.rotkehlchen.data.db,
            )
        except BankMFARequired as e:
            return e.challenge.serialize(), '', HTTPStatus.ACCEPTED
        except InputError as e:
            return None, str(e), HTTPStatus.BAD_REQUEST
        if not result:
            return None, msg, HTTPStatus.CONFLICT
        if (
            bank := self.rotkehlchen.bank_manager.get_bank(name=name, connector=connector)
        ) is None:
            raise AssertionError('successful bank setup did not register the connection')
        return self._setup_success(bank), msg, HTTPStatus.OK

    def answer_authentication(
            self,
            name: str,
            connector: BankConnectorType,
            response: str | None,
    ) -> tuple[bool | dict[str, Any] | None, str, HTTPStatus]:
        manager = self.rotkehlchen.bank_manager
        completes_setup = manager.get_bank(name=name, connector=connector) is None
        try:
            result, message = manager.answer_bank_authentication(
                name=name,
                connector=connector,
                response=response,
            )
        except BankMFARequired as e:
            return e.challenge.serialize(), '', HTTPStatus.ACCEPTED
        except BankAuthExpired as e:  # dropped by the bank: only a new sync or setup helps
            return None, str(e), HTTPStatus.GONE
        except RemoteError as e:
            return None, str(e), HTTPStatus.CONFLICT
        if result is False:
            return None, message, HTTPStatus.CONFLICT
        if completes_setup:
            if (bank := manager.get_bank(name=name, connector=connector)) is None:
                raise AssertionError('successful bank setup authentication did not register it')
            return self._setup_success(bank), '', HTTPStatus.OK
        return True, '', HTTPStatus.OK

    def edit_bank(
            self,
            name: str,
            connector: BankConnectorType,
            new_name: str | None,
            credentials: dict[str, str],
    ) -> tuple[bool | None, str, HTTPStatus]:
        try:
            result, msg = self.rotkehlchen.bank_manager.edit_bank(
                name=name,
                connector=connector,
                new_name=new_name,
                credentials=BankCredentialInput(values=credentials),
            )
        except InputError as e:
            return None, str(e), HTTPStatus.BAD_REQUEST
        if not result:
            return None, msg, HTTPStatus.CONFLICT
        return True, msg, HTTPStatus.OK

    def remove_bank(
            self,
            name: str,
            connector: BankConnectorType,
    ) -> tuple[bool | None, str, HTTPStatus]:
        result, msg = self.rotkehlchen.bank_manager.delete_bank(name=name, connector=connector)
        if not result:
            return None, msg, HTTPStatus.CONFLICT
        return True, msg, HTTPStatus.OK

    def cancel_authentication(
            self,
            name: str,
            connector: BankConnectorType,
    ) -> tuple[bool | None, str, HTTPStatus]:
        if not self.rotkehlchen.bank_manager.cancel_bank_authentication(name=name, connector=connector):  # noqa: E501
            return (
                None,
                f'{connector!s} bank connection {name} does not exist',
                HTTPStatus.CONFLICT,
            )
        return True, '', HTTPStatus.OK

    def sync_banks(
            self,
            connector: BankConnectorType | None,
            name: str | None,
    ) -> dict[str, Any]:
        try:
            self.rotkehlchen.bank_manager.query_bank_history_events(connector=connector, name=name)
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
            name: str | None,
            ignore_cache: bool,
            value_threshold: FVal | None = None,
    ) -> dict[str, Any]:
        """Return aggregate balances and the balances of each individual bank connection.

        Limited to one connector's connections, or to one connection when its name is given.
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
        if connector is None:
            banks = list(manager.iterate_banks())
        elif name is None:
            banks = manager.connected_banks[connector]
        elif (bank := manager.get_bank(name=name, connector=connector)) is not None:
            banks = [bank]
        else:
            return {
                'result': None,
                'message': f'No {connector!s} bank connection named {name} exists',
                'status_code': HTTPStatus.CONFLICT,
            }
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
            aggregate = combine_dicts(aggregate, balances)
            connections.append({
                'connector': bank.connector,
                'name': bank.name,
                'balances': balances,
            })

        if len(connections) == 0 and error_msg != '':
            return {'result': None, 'message': error_msg, 'status_code': HTTPStatus.CONFLICT}
        return {
            'result': {'aggregate': aggregate, 'connections': connections},
            'message': error_msg,
            'status_code': HTTPStatus.OK,
        }
