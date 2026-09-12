from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from rotkehlchen.banks.manager import BankCredentialInput
from rotkehlchen.banks.manifests import BANK_MANIFESTS
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.utils.misc import combine_dicts

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.balance import Balance
    from rotkehlchen.assets.asset import AssetWithOracles
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

    def setup_bank(
            self,
            name: str,
            location: Location,
            credentials: dict[str, str],
    ) -> tuple[bool | None, str, HTTPStatus]:
        try:
            result, msg = self.rotkehlchen.bank_manager.setup_bank(
                name=name,
                location=location,
                credentials=BankCredentialInput(values=credentials),
                database=self.rotkehlchen.data.db,
            )
        except InputError as e:
            return None, str(e), HTTPStatus.BAD_REQUEST
        if not result:
            return None, msg, HTTPStatus.CONFLICT
        return True, msg, HTTPStatus.OK

    def edit_bank(
            self,
            name: str,
            location: Location,
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

    def remove_bank(self, name: str, location: Location) -> tuple[bool | None, str, HTTPStatus]:
        result, msg = self.rotkehlchen.bank_manager.delete_bank(name=name, location=location)
        if not result:
            return None, msg, HTTPStatus.CONFLICT
        return True, msg, HTTPStatus.OK

    def sync_banks(self, location: Location | None, name: str | None) -> dict[str, Any]:
        try:
            self.rotkehlchen.bank_manager.query_bank_history_events(location=location, name=name)
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        return {'result': True, 'message': ''}

    def query_bank_balances(
            self,
            location: Location | None,
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
            balances, msg = bank.query_balances(ignore_cache=ignore_cache)
            if balances is None:
                error_msg += msg
                continue
            if value_threshold is not None:
                balances = {a: b for a, b in balances.items() if b.value > value_threshold}
            key = str(bank.location)
            final[key] = combine_dicts(final[key], balances) if key in final else balances

        if len(final) == 0 and error_msg != '':
            return {'result': None, 'message': error_msg, 'status_code': HTTPStatus.CONFLICT}
        result: Any = final[str(location)] if location is not None else final
        return {'result': result, 'message': error_msg, 'status_code': HTTPStatus.OK}
