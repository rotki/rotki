from typing import Mapping, Optional
from unittest.mock import Mock

import pytest

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.evm.names import FetcherFunc, NamePrioritizer, search_for_addresses_names
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import (
    AddressbookEntry,
    AddressNameSource,
    ChainAddress,
    ChecksumEvmAddress,
    OptionalChainAddress,
    SupportedBlockchain,
)


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

    prioritizer_names = prioritizer.get_prioritized_names(list(fetchers.keys()), [OptionalChainAddress(evm_address, SupportedBlockchain.ETHEREUM)])  # noqa: E501
    assert prioritizer_names == [AddressbookEntry(
        name='blockchain account label',
        address=evm_address,
        blockchain=SupportedBlockchain.ETHEREUM,
    )]


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

    prioritizer_names = prioritizer.get_prioritized_names(list(fetchers.keys()), [OptionalChainAddress(evm_address, SupportedBlockchain.ETHEREUM)])  # noqa: E501
    assert prioritizer_names == [AddressbookEntry(
        name='global addressbook label',
        address=evm_address,
        blockchain=SupportedBlockchain.ETHEREUM,
    )]


def get_fetchers_with_names(
        fetchers_to_name: Mapping[AddressNameSource, Optional[str]],
) -> dict[AddressNameSource, FetcherFunc]:
    fetchers: dict[AddressNameSource, FetcherFunc] = {}
    for source_id, returned_name in fetchers_to_name.items():
        def make_fetcher(label: Optional[str]) -> FetcherFunc:
            return lambda db, chain_address: label

        fetchers[source_id] = make_fetcher(returned_name)

    return fetchers


def test_uses_sources_only_when_needed(evm_address, database: 'DBHandler'):
    """
    Tests that names sources are not used when they are not supposed to be used. For example
    blockchain labels shouldn't be used when blockchain is not specified.
    """
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=evm_address,
                label='Account label',
            )],
        )
    names = search_for_addresses_names(
        database=database,
        chain_addresses=[ChainAddress(
            address=evm_address,
            blockchain=None,
        )],
    )
    assert names == [], 'No names should have been returned since the blockchain was None'
