import tempfile
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, patch

import pytest
from freezegun import freeze_time

import rotkehlchen.chain.evm.names
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.modules.gwei_names.constants import GWEI_NAMES_ADDRESS
from rotkehlchen.chain.ethereum.modules.gwei_names.naming import gns_resolve, gns_reverse_lookup
from rotkehlchen.chain.ethereum.utils import try_download_ens_avatar
from rotkehlchen.chain.evm.names import (
    FetcherFunc,
    NamePrioritizer,
    NamingSystem,
    find_ens_mappings,
    search_for_addresses_names,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.ens import DBEns
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import (
    AddressbookEntryWithSource,
    AddressNameSource,
    ChainAddress,
    ChecksumEvmAddress,
    OptionalChainAddress,
    SupportedBlockchain,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Mapping

    from rotkehlchen.db.dbhandler import DBHandler


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
    assert prioritizer_names == [AddressbookEntryWithSource(
        name='blockchain account label',
        address=evm_address,
        blockchain=SupportedBlockchain.ETHEREUM,
        source='blockchain_account',
    )]


def test_get_name_of_lowest_prio_name_source(
        evm_address: ChecksumEvmAddress,
) -> None:
    """Given some name fetchers where only the one with the lowest priority
    (the last one) returns a name, the NamePrioritizer must return
    the name with the last priority
    """
    prioritizer = NamePrioritizer(Mock())
    fetchers: Mapping[AddressNameSource, str | None] = {
        'blockchain_account': None,
        'ens_names': None,
        'global_addressbook': 'global addressbook label',
    }
    prioritizer.add_fetchers(
        get_fetchers_with_names(fetchers),
    )

    prioritizer_names = prioritizer.get_prioritized_names(list(fetchers.keys()), [OptionalChainAddress(evm_address, SupportedBlockchain.ETHEREUM)])  # noqa: E501
    assert prioritizer_names == [AddressbookEntryWithSource(
        name='global addressbook label',
        address=evm_address,
        blockchain=SupportedBlockchain.ETHEREUM,
        source='global_addressbook',
    )]


def get_fetchers_with_names(
        fetchers_to_name: Mapping[AddressNameSource, str | None],
) -> dict[AddressNameSource, FetcherFunc]:
    fetchers: dict[AddressNameSource, FetcherFunc] = {}
    for source_id, returned_name in fetchers_to_name.items():
        def make_fetcher(label: str | None) -> FetcherFunc:
            return lambda db, chain_address: label

        fetchers[source_id] = make_fetcher(returned_name)

    return fetchers


def test_uses_sources_only_when_needed(evm_address: Any, database: DBHandler) -> None:
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
        prioritizer=NamePrioritizer(database),
        chain_addresses=[ChainAddress(address=evm_address, blockchain=None)],
    )
    assert names == [], 'No names should have been returned since the blockchain was None'


def test_naming_system_names_priority(evm_address: Any, database: DBHandler) -> None:
    """Test that an address can have a cached name per naming system and that
    the priority between them is applied at read time by the prioritizer"""
    dbens = DBEns(database)
    with database.user_write() as write_cursor:
        dbens.add_ens_mapping(write_cursor, address=evm_address, name='someone.eth', now=ts_now())
        dbens.add_ens_mapping(write_cursor, address=evm_address, name='someone.gwei', now=ts_now(), source='gns')  # noqa: E501

    cases: tuple[tuple[list[AddressNameSource], str], ...] = (
        (['ens_names', 'gns_names'], 'someone.eth'),
        (['gns_names', 'ens_names'], 'someone.gwei'),
    )
    for priority, expected_name in cases:
        assert NamePrioritizer(database).get_prioritized_names(
            prioritized_name_source=priority,
            chain_addresses=[OptionalChainAddress(evm_address, SupportedBlockchain.ETHEREUM)],
        ) == [AddressbookEntryWithSource(
            name=expected_name,
            address=evm_address,
            blockchain=SupportedBlockchain.ETHEREUM,
            source=priority[0],
        )]


def test_find_ens_mappings_naming_systems(evm_address: Any, database: DBHandler, monkeypatch: Any) -> None:  # noqa: E501
    """Test that additional naming systems are only queried when they are in the
    address_name_priority setting and that the highest priority name wins the merge"""
    queried_systems = []

    def make_reverse_lookup(identifier: str, suffix: str) -> Any:
        def reverse_lookup(inquirer: Any, addresses: Any) -> Any:
            queried_systems.append(identifier)
            return dict.fromkeys(addresses, f'someone{suffix}')
        return reverse_lookup

    monkeypatch.setattr(rotkehlchen.chain.evm.names, 'ETHEREUM_NAMING_SYSTEMS', (
        NamingSystem(
            identifier='ens',
            source='ens_names',
            suffix='',
            reverse_lookup=make_reverse_lookup('ens', '.eth'),
            resolve=lambda inquirer, name: None,
        ), NamingSystem(
            identifier='gns',
            source='gns_names',
            suffix='.gwei',
            reverse_lookup=make_reverse_lookup('gns', '.gwei'),
            resolve=lambda inquirer, name: None,
        ),
    ))
    ethereum_inquirer = Mock(database=database)

    # The default priority has ENS before GNS, so both are queried and the ENS name wins.
    assert find_ens_mappings(
        ethereum_inquirer=ethereum_inquirer,
        addresses=[evm_address],
        ignore_cache=True,
    ) == {evm_address: 'someone.eth'}
    assert sorted(queried_systems) == ['ens', 'gns']

    cases: tuple[tuple[list[AddressNameSource], str], ...] = (
        (['gns_names', 'ens_names'], 'someone.gwei'),
        (['ens_names', 'gns_names'], 'someone.eth'),
    )
    for priority, expected_name in cases:
        with database.user_write() as write_cursor:
            database.set_settings(
                write_cursor=write_cursor,
                settings=ModifiableDBSettings(address_name_priority=priority),
            )
        queried_systems.clear()
        assert find_ens_mappings(
            ethereum_inquirer=ethereum_inquirer,
            addresses=[evm_address],
            ignore_cache=True,
        ) == {evm_address: expected_name}
        assert sorted(queried_systems) == ['ens', 'gns']


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_gns_reverse_lookup(ethereum_inquirer: Any) -> None:
    """Test that reverse resolution of gwei names works properly"""
    assert gns_reverse_lookup(ethereum_inquirer, [
        (donnoh := string_to_evm_address('0xC04689227Fa24785609B1174698DBe481437f1A3')),  # has donnoh.gwei set as primary name  # noqa: E501
        (yabir := string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306')),  # has no gwei primary name  # noqa: E501
    ]) == {donnoh: 'donnoh.gwei', yabir: None}


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_gns_resolve(ethereum_inquirer: Any) -> None:
    """Test that forward resolution of gwei names works properly."""
    assert gns_resolve(ethereum_inquirer, 'yabir.gwei') == ethereum_inquirer.ens_lookup('yabir.eth') == string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')  # noqa: E501
    assert gns_resolve(ethereum_inquirer, 'surely-not-registered-a1b2c3.gwei') is None


@pytest.mark.vcr
@freeze_time('2023-05-12')  # freezing time just to make sure comparisons of timestamps won't fail
def test_download_ens_avatar(ethereum_inquirer: Any, opensea: Any) -> None:
    """
    Tests that detection and downloading of ens avatars works properly for all resolvers
    """
    dbens = DBEns(ethereum_inquirer.database)
    with dbens.db.user_write() as write_cursor:
        dbens.add_ens_mapping(
            write_cursor=write_cursor,
            address=make_evm_address(),
            name='random.ens.name.eth',
            now=ts_now(),
        )
        dbens.add_ens_mapping(
            write_cursor=write_cursor,
            address=make_evm_address(),
            name='yabir.eth',  # resolver v2
            now=ts_now(),
        )
        dbens.add_ens_mapping(
            write_cursor=write_cursor,
            address=make_evm_address(),
            name='tewshi.eth',  # resolver v3
            now=ts_now(),
        )
        dbens.add_ens_mapping(
            write_cursor=write_cursor,
            address=make_evm_address(),
            name='arpit59.eth',  # got an NFT image
            now=ts_now(),
        )

    with tempfile.TemporaryDirectory() as tempdir_str:
        tempdir = Path(tempdir_str)
        try_download_ens_avatar(
            eth_inquirer=ethereum_inquirer,
            opensea=opensea,
            avatars_dir=tempdir,
            ens_name='random.ens.name.eth',  # a random ens name, and thus there is no avatar
        )
        assert dbens.get_last_avatar_update('random.ens.name.eth') <= ts_now(), 'Last update timestamp should have been set'  # noqa: E501
        assert list(tempdir.iterdir()) == []
        try_download_ens_avatar(
            eth_inquirer=ethereum_inquirer,
            opensea=opensea,
            avatars_dir=tempdir,
            ens_name='yabir.eth',  # resolver v2
        )
        assert dbens.get_last_avatar_update('yabir.eth') <= ts_now(), 'Last update timestamp should have been set'  # noqa: E501
        try_download_ens_avatar(
            eth_inquirer=ethereum_inquirer,
            opensea=opensea,
            avatars_dir=tempdir,
            ens_name='tewshi.eth',  # an avatar should be downloaded. Resolver v3
        )
        assert dbens.get_last_avatar_update('tewshi.eth') <= ts_now(), 'Last update timestamp should have been set'  # noqa: E501
        assert set(tempdir.iterdir()) == {tempdir / 'tewshi.eth.png', tempdir / 'yabir.eth.png'}
        try_download_ens_avatar(
            eth_inquirer=ethereum_inquirer,
            opensea=opensea,
            avatars_dir=tempdir,
            ens_name='arpit59.eth',  # avatar should be downloaded. NFT image using ensapp metadata
        )
        assert dbens.get_last_avatar_update('arpit59.eth') <= ts_now(), 'Last update timestamp should have been set'  # noqa: E501

        assert set(tempdir.iterdir()) == {
            tempdir / 'arpit59.eth.png',
            tempdir / 'tewshi.eth.png',
            tempdir / 'yabir.eth.png',
        }


def test_download_gwei_name_avatar(ethereum_inquirer: Any) -> None:
    """Test that avatars of gwei names are queried from the GNS contract, which acts as
    an ENS-compatible resolver for all .gwei names, and downloaded properly"""
    dbens = DBEns(ethereum_inquirer.database)
    with dbens.db.user_write() as write_cursor:
        dbens.add_ens_mapping(
            write_cursor=write_cursor,
            address=make_evm_address(),
            name='skas.gwei',
            now=ts_now(),
            source='gns',
        )

    def mock_call_contract(contract_address: Any, abi: Any, method_name: Any, arguments: Any) -> Any:  # noqa: E501
        assert contract_address == GWEI_NAMES_ADDRESS
        assert method_name == 'text'
        assert arguments[1] == 'avatar'
        return 'https://example.com/avatar.png'

    with (
        patch.object(ethereum_inquirer, 'call_contract', side_effect=mock_call_contract),
        patch(
            target='rotkehlchen.chain.ethereum.utils.requests.get',
            return_value=Mock(
                status_code=HTTPStatus.OK,
                headers={'Content-Type': 'image/png'},
                content=(image_bytes := b'\x89PNG fake avatar image'),
            ),
        ),
        tempfile.TemporaryDirectory() as tempdir_str,
    ):
        try_download_ens_avatar(
            eth_inquirer=ethereum_inquirer,
            opensea=None,
            avatars_dir=(tempdir := Path(tempdir_str)),
            ens_name='skas.gwei',
        )
        assert (tempdir / 'skas.gwei.png').read_bytes() == image_bytes

    assert dbens.get_last_avatar_update('skas.gwei') <= ts_now(), 'Last update timestamp should have been set'  # noqa: E501
