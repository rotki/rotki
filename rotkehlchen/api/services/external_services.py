from http import HTTPStatus
from typing import Any, Final

from rotkehlchen.constants.misc import ONE
from rotkehlchen.externalapis.helius import HELIUS_RPC_NODE_NAME, HELIUS_RPC_URL
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import has_premium_check
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.types import ExternalService, ExternalServiceApiCredentials, SupportedBlockchain

HELIUS_RPC_ENDPOINT_PREFIXES = (HELIUS_RPC_URL, HELIUS_RPC_URL.removesuffix('/'))
HELIUS_RPC_NODE_WEIGHT: Final = FVal('0.5')


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

    def _refresh_solana_helius_rpc_node(self) -> None:
        """Refresh the solana in-memory node state after syncing the Helius RPC DB entry."""
        node_inquirer = self.rotkehlchen.chains_aggregator.solana.node_inquirer
        for node_info in list(node_inquirer.rpc_mapping):
            if (
                node_info.name == HELIUS_RPC_NODE_NAME and
                node_info.endpoint.startswith(HELIUS_RPC_ENDPOINT_PREFIXES)
            ):
                node_inquirer.rpc_mapping.pop(node_info, None)
                node_inquirer.clear_runtime_state(node_info)

        node_inquirer.known_node_capabilities.pop(HELIUS_RPC_NODE_NAME, None)
        node_inquirer.invalidate_nodes_cache()
        node_inquirer.connect_to_multiple_nodes(self.rotkehlchen.data.db.get_rpc_nodes(
            blockchain=SupportedBlockchain.SOLANA,
            only_active=True,
        ))

    def _sync_helius_rpc_node(self, api_key: str | None) -> None:
        with self.rotkehlchen.data.db.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM rpc_nodes WHERE name=? AND blockchain=? AND endpoint LIKE ?',
                (HELIUS_RPC_NODE_NAME, SupportedBlockchain.SOLANA.value, f'{HELIUS_RPC_URL.removesuffix("/")}%api-key=%'),  # noqa: E501
            )
            exclude_identifier = None
            if api_key is not None:
                endpoint = f'{HELIUS_RPC_URL}?api-key={api_key}'
                write_cursor.execute(
                    'INSERT OR IGNORE INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) VALUES (?, ?, ?, ?, ?, ?)',  # noqa: E501
                    (
                        HELIUS_RPC_NODE_NAME,
                        endpoint,
                        False,
                        True,
                        str(HELIUS_RPC_NODE_WEIGHT),
                        SupportedBlockchain.SOLANA.value,
                    ),
                )
                exclude_identifier = write_cursor.execute(
                    'SELECT identifier FROM rpc_nodes WHERE endpoint=? AND blockchain=?',
                    (endpoint, SupportedBlockchain.SOLANA.value),
                ).fetchone()[0]

            self.rotkehlchen.data.db.rebalance_rpc_nodes_weights(
                write_cursor=write_cursor,
                proportion_to_share=ONE - HELIUS_RPC_NODE_WEIGHT if api_key is not None else ONE,
                exclude_identifier=exclude_identifier,
                blockchain=SupportedBlockchain.SOLANA,
            )

        self._refresh_solana_helius_rpc_node()

    def add_services(
            self,
            services: list[ExternalServiceApiCredentials],
    ) -> tuple[bool, str, dict[str, Any] | None, HTTPStatus]:
        should_renable_etherscan = False
        helius_api_key = None
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
            elif service.service == ExternalService.HELIUS:
                helius_api_key = service.api_key

        with self.rotkehlchen.data.db.user_write() as write_cursor:
            self.rotkehlchen.data.db.add_external_service_credentials(
                write_cursor=write_cursor,
                credentials=services,
            )

        if should_renable_etherscan:
            self.rotkehlchen.chains_aggregator.renable_etherscan_indixer()
        if helius_api_key is not None:
            self._sync_helius_rpc_node(api_key=helius_api_key)

        return True, '', self._build_payload(), HTTPStatus.OK

    def delete_services(
            self,
            services: list[ExternalService],
    ) -> dict[str, Any]:
        self.rotkehlchen.data.db.delete_external_service_credentials(services)
        if ExternalService.HELIUS in services:
            self._sync_helius_rpc_node(api_key=None)
        return self._build_payload()
