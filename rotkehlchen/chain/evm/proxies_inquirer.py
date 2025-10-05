
import logging
from collections import defaultdict
from collections.abc import Sequence
from enum import StrEnum
from typing import TYPE_CHECKING, overload

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.summer_fi.constants import CPT_SUMMER_FI
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
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
    SUMMER_FI = 'summer_fi'


class EvmProxiesInquirer:
    """Class to retrieve information about proxies for defi addresses."""

    def __init__(
            self,
            node_inquirer: 'EvmNodeInquirer',
            dsproxy_registry: 'EvmContract',
    ) -> None:
        self.node_inquirer = node_inquirer
        self.dsproxy_registry = dsproxy_registry
        self.address_to_proxies: dict[ProxyType, dict[ChecksumEvmAddress, set[ChecksumEvmAddress]]] = {  # noqa: E501
            ProxyType.DS: {},
            ProxyType.LIQUITY: {},
            ProxyType.SUMMER_FI: {},
        }
        self.proxy_to_address: dict[ProxyType, dict[ChecksumEvmAddress, ChecksumEvmAddress]] = {
            ProxyType.DS: {},
            ProxyType.LIQUITY: {},
            ProxyType.SUMMER_FI: {},
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

    def get_or_query_ds_proxy(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, set[ChecksumEvmAddress]]:
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
                    mapping[address] = {proxy_address}
            except DeserializationError as e:
                msg = f'Failed to deserialize {result} DSproxy for address {address}. {e!s}'
                log.error(msg)
        return mapping

    def get_or_query_liquity_proxy(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, set[ChecksumEvmAddress]]:
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
                    mapping[address] = {proxy_address}
            except DeserializationError as e:
                msg = f'Failed to deserialize {result} liquity proxy for address {address}. {e!s}'
                log.error(msg)
        return mapping

    def get_or_query_summer_fi_proxy(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, set[ChecksumEvmAddress]]:
        """Return summer.fi proxies if they exist for the list of addresses.
        Finds proxy addresses by inspecting the decoded history events.
        """
        with self.node_inquirer.database.conn.read_ctx() as cursor:
            events = DBHistoryEvents(self.node_inquirer.database).get_history_events_internal(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(
                    event_types=[HistoryEventType.INFORMATIONAL],
                    event_subtypes=[HistoryEventSubType.CREATE],
                    counterparties=[CPT_SUMMER_FI],
                    location_labels=list(addresses),
                ),
            )

        mapping: defaultdict[ChecksumEvmAddress, set[ChecksumEvmAddress]] = defaultdict(set)
        for event in events:
            if (
                event.extra_data is None or
                (proxy_address := event.extra_data.get('proxy_address')) is None
            ):
                continue

            mapping[event.location_label].add(proxy_address)  # type: ignore  # location_label and proxy_address should be valid addresses here

        return mapping

    def query_address_for_proxies(self, address: ChecksumEvmAddress) -> None:
        """
        Checks the given address for all proxies and if found having one adds them to the mappings
        Ignores the cache.
        """
        for proxy_type in ProxyType:
            if len(mapping := getattr(self, f'get_or_query_{proxy_type}_proxy')([address])) != 0:
                self.address_to_proxies[proxy_type][address] = (proxy_addresses := mapping[address])  # noqa: E501
                for proxy_address in proxy_addresses:
                    self.proxy_to_address[proxy_type][proxy_address] = address

    @overload
    def get_accounts_having_proxy(self, proxy_type: None = None) -> dict[ProxyType, dict[ChecksumEvmAddress, set[ChecksumEvmAddress]]]:  # noqa: E501
        ...

    @overload
    def get_accounts_having_proxy(self, proxy_type: ProxyType) -> dict[ChecksumEvmAddress, set[ChecksumEvmAddress]]:  # noqa: E501
        ...

    def get_accounts_having_proxy(self, proxy_type: ProxyType | None = None) -> dict[ChecksumEvmAddress, set[ChecksumEvmAddress]] | dict[ProxyType, dict[ChecksumEvmAddress, set[ChecksumEvmAddress]]]:  # noqa: E501
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
            return self.address_to_proxies if proxy_type is None else self.address_to_proxies[proxy_type]  # noqa: E501

        with self.node_inquirer.database.conn.read_ctx() as cursor:
            accounts = self.node_inquirer.database.get_blockchain_accounts(cursor)

        for _type in ProxyType:
            if proxy_type is None or proxy_type == _type:
                mapping = getattr(self, f'get_or_query_{_type}_proxy')(
                    addresses=accounts.get(self.node_inquirer.blockchain),
                )
                self.address_to_proxies[_type] = mapping
                self.proxy_to_address[_type] = {proxy: addr for addr, proxies in mapping.items() for proxy in proxies}  # noqa: E501

        self.last_proxy_mapping_query_ts = ts_now()
        if proxy_type is not None:  # return a copy to avoid "dictionary modified during iteration errors"  # noqa: E501
            return self.address_to_proxies[proxy_type].copy()
        # else again copy but the whole thing
        return self.address_to_proxies.copy()
