
import logging
from collections.abc import Sequence
from enum import StrEnum
from typing import TYPE_CHECKING, overload

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress, SupportedBlockchain
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ProxyType(StrEnum):
    DS = 'ds'
    LIQUITY = 'liquity'


class EvmProxiesInquirer:
    """Class to retrieve information about proxies for defi addresses."""

    def __init__(
            self,
            node_inquirer: 'EvmNodeInquirer',
            dsproxy_registry: 'EvmContract',
    ) -> None:
        self.node_inquirer = node_inquirer
        self.dsproxy_registry = dsproxy_registry
        self.address_to_proxy: dict[ProxyType, dict[ChecksumEvmAddress, ChecksumEvmAddress]] = {
            ProxyType.DS: {},
            ProxyType.LIQUITY: {},
        }
        self.proxy_to_address: dict[ProxyType, dict[ChecksumEvmAddress, ChecksumEvmAddress]] = {
            ProxyType.DS: {},
            ProxyType.LIQUITY: {},
        }
        self.reset_last_query_ts()
        self.lqtyv2_router = EvmContract(
            address=string_to_evm_address('0x807DEf5E7d057DF05C796F4bc75C3Fe82Bd6EeE1'),
            abi=[{'inputs': [{'name': '_user', 'type': 'address'}], 'name': 'deriveUserProxyAddress', 'outputs': [{'name': '', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'}],  # noqa: E501
        ) if self.node_inquirer.blockchain == SupportedBlockchain.ETHEREUM else None

    def reset_last_query_ts(self) -> None:
        """Reset the last query timestamps, effectively cleaning the caches"""
        self.last_proxy_mapping_query_ts = 0

    def maybe_get_proxy_owner(self, address: ChecksumEvmAddress) -> ChecksumEvmAddress | None:
        """
        Checks whether given address is a proxy owned by any of the tracked accounts.
        If it is a proxy, it returns the owner of the proxy, otherwise `None`.
        """
        self.get_accounts_having_proxy()  # calling to make sure that proxies are queried  # noqa: E501
        owner = None
        for proxy_type in ProxyType:
            if (owner := self.proxy_to_address[proxy_type].get(address)):
                break

        return owner

    def get_account_ds_proxy(self, address: ChecksumEvmAddress) -> ChecksumEvmAddress | None:
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

        if result != ZERO_ADDRESS:
            self.address_to_proxy[ProxyType.DS][address] = result
            self.proxy_to_address[ProxyType.DS][result] = address
            return result

        return None

    def get_or_query_ds_proxy(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, ChecksumEvmAddress]:
        """
        Returns DSProxy (Now called Sky proxies) if it exists for a list
        of addresses using only one call
        to the chain.

        May raise:
        - RemoteError if query to the node failed
        """
        calls = [(
            self.dsproxy_registry.address,
            self.dsproxy_registry.encode(method_name='proxies', arguments=[address]),
        ) for address in addresses]
        output = self.node_inquirer.multicall(calls=calls)
        mapping = {}
        for idx, result_encoded in enumerate(output):
            address = addresses[idx]
            result = self.dsproxy_registry.decode(
                result_encoded,
                'proxies',
                arguments=[address],
            )[0]
            try:
                if (proxy_address := deserialize_evm_address(result)) != ZERO_ADDRESS:
                    mapping[address] = proxy_address
            except DeserializationError as e:
                msg = f'Failed to deserialize {result} DSproxy for address {address}. {e!s}'
                log.error(msg)
        return mapping

    def get_or_query_liquity_proxy(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, ChecksumEvmAddress]:
        """Return liquity v2 proxies if they exist for the list of addresses
        This should only be called if the chain is ethereum and lqtyv2_router is set.
        """
        assert self.lqtyv2_router, 'get_liquity_proxy should only be called for ethereum'
        calls = [(
            self.lqtyv2_router.address,
            self.lqtyv2_router.encode(method_name='deriveUserProxyAddress', arguments=[address]),
        ) for address in addresses]
        output = self.node_inquirer.multicall(calls=calls)
        mapping = {}
        for idx, result_encoded in enumerate(output):
            address = addresses[idx]
            result = self.lqtyv2_router.decode(
                result_encoded,
                'deriveUserProxyAddress',
                arguments=[address],
            )[0]
            try:
                if (proxy_address := deserialize_evm_address(result)) != ZERO_ADDRESS:
                    mapping[address] = proxy_address
            except DeserializationError as e:
                msg = f'Failed to deserialize {result} liquity proxy for address {address}. {e!s}'
                log.error(msg)
        return mapping

    def query_address_for_proxies(self, address: ChecksumEvmAddress) -> None:
        """
        Checks the given address for all proxies and if found having one adds them to the mappings
        Ignores the cache.
        """
        for proxy_type in ProxyType:
            if len(mapping := getattr(self, f'get_or_query_{proxy_type}_proxy')([address])) != 0:
                self.address_to_proxy[proxy_type][address] = (proxy_address := mapping[address])
                self.proxy_to_address[proxy_type][proxy_address] = address

    @overload
    def get_accounts_having_proxy(self, proxy_type: None = None) -> dict[ProxyType, dict[ChecksumEvmAddress, ChecksumEvmAddress]]:  # noqa: E501
        ...

    @overload
    def get_accounts_having_proxy(self, proxy_type: ProxyType) -> dict[ChecksumEvmAddress, ChecksumEvmAddress]:  # noqa: E501
        ...

    def get_accounts_having_proxy(self, proxy_type: ProxyType | None = None) -> dict[ChecksumEvmAddress, ChecksumEvmAddress] | dict[ProxyType, dict[ChecksumEvmAddress, ChecksumEvmAddress]]:  # noqa: E501
        """Returns a mapping of accounts that have proxies to their proxies. Either all proxies or
        specific ones if the proxy types argument is given.

        If the proxy mappings have been recently queried then the old result is used.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        now = ts_now()
        if now - self.last_proxy_mapping_query_ts < DAY_IN_SECONDS:  # refresh daily
            return self.address_to_proxy if proxy_type is None else self.address_to_proxy[proxy_type]  # noqa: E501

        with self.node_inquirer.database.conn.read_ctx() as cursor:
            accounts = self.node_inquirer.database.get_blockchain_accounts(cursor)

        ds_mapping, liquity_mapping = {}, {}
        if proxy_type is None or proxy_type == ProxyType.DS:
            ds_mapping = self.get_or_query_ds_proxy(accounts.get(self.node_inquirer.blockchain))
            self.address_to_proxy[ProxyType.DS] = ds_mapping
            self.proxy_to_address[ProxyType.DS] = {v: k for k, v in ds_mapping.items()}

        if proxy_type is None or proxy_type == ProxyType.LIQUITY:
            liquity_mapping = self.get_or_query_liquity_proxy(
                accounts.get(self.node_inquirer.blockchain),
            )
            self.address_to_proxy[ProxyType.LIQUITY] = liquity_mapping
            self.proxy_to_address[ProxyType.LIQUITY] = {v: k for k, v in liquity_mapping.items()}

        self.last_proxy_mapping_query_ts = ts_now()
        if proxy_type is not None:  # return a copy to avoid "dictionary modified during iteration errors"  # noqa: E501
            return self.address_to_proxy[proxy_type].copy()
        # else again copy but the whole thing
        return self.address_to_proxy.copy()
