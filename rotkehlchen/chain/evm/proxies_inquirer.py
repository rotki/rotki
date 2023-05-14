
import logging
from typing import TYPE_CHECKING, Optional

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

DS_REQUERY_PERIOD = DAY_IN_SECONDS  # Refresh proxies every 24 hours

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EvmProxiesInquirer():
    """Class to retrieve information about DSProxy for defi addresses."""

    def __init__(self, node_inquirer: 'EvmNodeInquirer', dsproxy_registry: 'EvmContract') -> None:
        self.node_inquirer = node_inquirer
        self.dsproxy_registry = dsproxy_registry
        self.address_to_proxy: dict[ChecksumEvmAddress, ChecksumEvmAddress] = {}
        self.proxy_to_address: dict[ChecksumEvmAddress, ChecksumEvmAddress] = {}
        self.reset_last_query_ts()

    def add_mapping(self, address: ChecksumEvmAddress, proxy: ChecksumEvmAddress) -> None:
        self.address_to_proxy[address] = proxy
        self.proxy_to_address[proxy] = address

    def reset_last_query_ts(self) -> None:
        """Reset the last query timestamps, effectively cleaning the caches"""
        self.last_proxy_mapping_query_ts = 0

    def get_account_proxy(self, address: ChecksumEvmAddress) -> Optional[ChecksumEvmAddress]:
        """Checks if a DS proxy exists for the given address and returns it if it does.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result. Also this error can be raised
        if there is a problem deserializing the result address.
        - BlockchainQueryError if an evm node is used and the contract call
        queries fail for some reason
        """
        result = self.dsproxy_registry.call(self.node_inquirer, 'proxies', arguments=[address])
        try:
            result = deserialize_evm_address(result)
        except DeserializationError as e:
            msg = f'Failed to deserialize {result} DS proxy for address {address}'
            log.error(msg)
            raise RemoteError(msg) from e
        return None if result == ZERO_ADDRESS else result

    def get_accounts_proxy(
            self,
            addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, ChecksumEvmAddress]:
        """
        Returns DSProxy if it exists for a list of addresses using only one call
        to the chain.

        May raise:
        - RemoteError if query to the node failed
        """
        output = self.node_inquirer.multicall(
            calls=[(
                self.dsproxy_registry.address,
                self.dsproxy_registry.encode(method_name='proxies', arguments=[address]),
            ) for address in addresses],
        )
        mapping = {}
        for idx, result_encoded in enumerate(output):
            address = addresses[idx]
            result = self.dsproxy_registry.decode(
                result_encoded,
                'proxies',
                arguments=[address],
            )[0]
            try:
                proxy_address = deserialize_evm_address(result)
                if proxy_address != ZERO_ADDRESS:
                    mapping[address] = proxy_address
            except DeserializationError as e:
                msg = f'Failed to deserialize {result} DSproxy for address {address}. {e!s}'
                log.error(msg)
        return mapping

    def get_accounts_having_proxy(self) -> dict[ChecksumEvmAddress, ChecksumEvmAddress]:
        """Returns a mapping of accounts that have DS proxies to their proxies.

        If the proxy mappings have been queried in the past REQUERY_PERIOD
        seconds then the old result is used.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        now = ts_now()
        if now - self.last_proxy_mapping_query_ts < DS_REQUERY_PERIOD:
            return self.address_to_proxy

        with self.node_inquirer.database.conn.read_ctx() as cursor:
            accounts = self.node_inquirer.database.get_blockchain_accounts(cursor)
        eth_accounts = accounts.eth
        mapping = self.get_accounts_proxy(eth_accounts)

        self.last_proxy_mapping_query_ts = ts_now()
        self.address_to_proxy = mapping
        self.proxy_to_address = {v: k for k, v in mapping.items()}
        return mapping
