from typing import List, Dict

import pytest

from rotkehlchen.chain.ethereum.names import NamePrioritizer
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.types import ChecksumEvmAddress, AddressNameSource, DEFAULT_ADDRESS_NAME_PRIORITY


class TestNameFetcher:
    address_names: Dict[ChecksumEvmAddress, str]

    def __init__(self, address_names: Dict[ChecksumEvmAddress, str]):
        self.address_names = address_names

    def get_addresses_names(self, addresses: List[ChecksumEvmAddress]) -> Dict[ChecksumEvmAddress, str]:
        return self.address_names


@pytest.fixture
def evm_address() -> ChecksumEvmAddress:
    return string_to_evm_address("0xasdf")


@pytest.fixture
def name_source_ids() -> List[AddressNameSource]:
    return DEFAULT_ADDRESS_NAME_PRIORITY


@pytest.fixture
def fetchers(name_source_ids, evm_address) -> Dict[AddressNameSource, TestNameFetcher]:
    fetchers: Dict[AddressNameSource, TestNameFetcher] = {}
    for source_id in name_source_ids:
        fetchers[source_id] = TestNameFetcher({evm_address: f"{source_id} address name"})
    return fetchers


@pytest.fixture
def name_sources_with_lowest_prio_has_name(name_source_ids, fetchers) -> Dict[AddressNameSource, TestNameFetcher]:
    for i, name_source_id in enumerate(name_source_ids):
        if i == len(name_source_ids) - 1:  # do nothing with lowest prio name source
            break

        all_addr_names = fetchers[name_source_id].address_names
        for addr in all_addr_names:
            fetchers[name_source_id].address_names[
                addr] = ""  # reset names of all "higher than lowest prio" name sources
    return fetchers


def test_get_prioritized_name(name_source_ids, fetchers, evm_address):
    prioritizer = NamePrioritizer()
    prioritizer.add_fetchers(fetchers)  # noqa

    first_fetcher = fetchers[name_source_ids[0]]

    assert prioritizer.get_prioritized_names(name_source_ids, [evm_address]) == \
           first_fetcher.get_addresses_names([evm_address])


def test_get_name_of_lowest_prio_name_source(name_source_ids, name_sources_with_lowest_prio_has_name, evm_address):
    prioritizer = NamePrioritizer()
    prioritizer.add_fetchers(name_sources_with_lowest_prio_has_name)  # noqa

    last_name_source = name_sources_with_lowest_prio_has_name[name_source_ids[-1]]

    assert prioritizer.get_prioritized_names(name_source_ids, [evm_address]) == \
           last_name_source.get_addresses_names([evm_address])
