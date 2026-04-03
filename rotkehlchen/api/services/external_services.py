from http import HTTPStatus
from typing import Any

from rotkehlchen.premium.premium import has_premium_check
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.types import ExternalService, ExternalServiceApiCredentials


class ExternalServicesService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen

    def _build_payload(self) -> dict[str, Any]:
        credentials_list = self.rotkehlchen.data.db.get_all_external_service_credentials()
        response_dict: dict[str, Any] = {}
        for credential in credentials_list:
            name, key_info = credential.serialize_for_api()
            response_dict[name] = key_info
        return response_dict

    def get_services(self) -> dict[str, Any]:
        return self._build_payload()

    def add_services(
            self,
            services: list[ExternalServiceApiCredentials],
    ) -> tuple[bool, str, dict[str, Any] | None, HTTPStatus]:
        should_renable_etherscan = False
        for service in services:
            if service.service.premium_only() and not has_premium_check(self.rotkehlchen.premium):
                return (
                    False,
                    f'You can only use {service.service} with rotki premium',
                    None,
                    HTTPStatus.FORBIDDEN,
                )
            if service.service == ExternalService.GNOSIS_PAY:
                return (
                    False,
                    'GnosisPay credentials are set using /services/gnosispay/token',
                    None,
                    HTTPStatus.FORBIDDEN,
                )
            if service.service == ExternalService.ETHERSCAN:
                should_renable_etherscan = True

        with self.rotkehlchen.data.db.user_write() as write_cursor:
            self.rotkehlchen.data.db.add_external_service_credentials(
                write_cursor=write_cursor,
                credentials=services,
            )

        if should_renable_etherscan:
            self.rotkehlchen.chains_aggregator.renable_etherscan_indixer()

        return True, '', self._build_payload(), HTTPStatus.OK

    def delete_services(
            self,
            services: list[ExternalService],
    ) -> dict[str, Any]:
        self.rotkehlchen.data.db.delete_external_service_credentials(services)
        return self._build_payload()
