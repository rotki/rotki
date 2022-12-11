from typing import Mapping, Optional
from unittest.mock import Mock

import pytest

from rotkehlchen.chain.ethereum.names import FetcherFunc, NamePrioritizer
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import AddressNameSource, ChecksumEvmAddress


@pytest.fixture(name='evm_address')
def fixture_evm_address() -> ChecksumEvmAddress:
    return make_evm_address()


def test_get_prioritized_name(evm_address: ChecksumEvmAddress) -> None:
    """Given some name fetchers which return names, the NamePrioritizer must return
    the first found name, which has also the highest priority
    """
    prioritizer = NamePrioritizer(Mock())
    fetchers: Mapping[AddressNameSource, str] = {
        'blockchain_account': 'blockchain account label',
        'ens_names': 'ens name',
        'global_addressbook': 'global addressbook label',
    }
    prioritizer.add_fetchers(
        get_fetchers_with_names(fetchers),
    )

    prioritizer_names = prioritizer.get_prioritized_names(list(fetchers.keys()), [evm_address])
    assert prioritizer_names == {evm_address: 'blockchain account label'}


def test_get_name_of_lowest_prio_name_source(
        evm_address: ChecksumEvmAddress,
):
    """Given some name fetchers where only the one with the lowest priority
    (the last one) returns a name, the NamePrioritizer must return
    the name with the last priority
    """
    prioritizer = NamePrioritizer(Mock())
    fetchers: Mapping[AddressNameSource, Optional[str]] = {
        'blockchain_account': None,
        'ens_names': None,
        'global_addressbook': 'global addressbook label',
    }
    prioritizer.add_fetchers(
        get_fetchers_with_names(fetchers),
    )

    prioritizer_names = prioritizer.get_prioritized_names(list(fetchers.keys()), [evm_address])

    assert prioritizer_names == {evm_address: 'global addressbook label'}


def get_fetchers_with_names(
        fetchers_to_name: Mapping[AddressNameSource, Optional[str]],
) -> dict[AddressNameSource, FetcherFunc]:
    fetchers: dict[AddressNameSource, FetcherFunc] = {}
    for source_id, returned_name in fetchers_to_name.items():
        def make_fetcher(label: Optional[str]) -> FetcherFunc:
            return lambda db, addr: label

        fetchers[source_id] = make_fetcher(returned_name)

    return fetchers
