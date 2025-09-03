from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests
from eth_utils import to_checksum_address

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.substrate.types import SubstrateAddress
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.ens import DBEns
from rotkehlchen.db.filtering import AddressbookFilterQuery
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.factories import (
    ADDRESS_ETH,
    ADDRESS_MULTICHAIN,
    ADDRESS_OP,
    make_addressbook_entries,
)
from rotkehlchen.types import (
    ADDRESSBOOK_BLOCKCHAIN_GROUP_PREFIX,
    AddressbookEntry,
    AddressbookType,
    BTCAddress,
    ChainType,
    OptionalChainAddress,
    SupportedBlockchain,
    Timestamp,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


KELSOS_ADDR = string_to_evm_address('0x7277F7849966426d345D8F6B9AFD1d3d89183083')
KELSOS_BOOK_ENTRY = AddressbookEntry(
    name='new kelsos',
    address=KELSOS_ADDR,
    blockchain=None,
)


@pytest.mark.parametrize('empty_global_addressbook', [True])
@pytest.mark.parametrize('book_type', [AddressbookType.GLOBAL, AddressbookType.PRIVATE])
def test_get_addressbook(
        rotkehlchen_api_server: 'APIServer',
        book_type: AddressbookType,
) -> None:
    generated_entries = make_addressbook_entries()
    entries_set = generated_entries + [KELSOS_BOOK_ENTRY]
    db_addressbook = DBAddressbook(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    with db_addressbook.write_ctx(book_type=book_type) as write_cursor:
        db_addressbook.add_or_update_addressbook_entries(
            write_cursor=write_cursor,
            entries=entries_set,
        )
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert deserialized_entries == entries_set
    assert deserialized_entries != sorted(deserialized_entries, key=lambda x: x.name)  # not sorted
    assert result['entries_found'] == len(entries_set)
    assert result['entries_total'] == len(entries_set)

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'addresses': [
                {'address': generated_entries[0].address},
                {'address': generated_entries[1].address},
            ],
        },
    )
    result = assert_proper_sync_response_with_result(response=response)
    assert result['entries_found'] == 3
    assert result['entries_total'] == len(entries_set)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert set(deserialized_entries) == set(generated_entries[0:3])

    # filter by chain also
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'addresses': [
                {
                    'address': generated_entries[1].address,
                    'blockchain': SupportedBlockchain.OPTIMISM.serialize(),
                },
            ],
        },
    )
    result = assert_proper_sync_response_with_result(response=response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert set(deserialized_entries) == {generated_entries[1]}
    assert result['entries_found'] == 1
    assert result['entries_total'] == len(entries_set)

    # filter by name and blockchain
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'name_substring': 'neighbour',
            'blockchain': SupportedBlockchain.ETHEREUM.serialize(),
        },
    )
    result = assert_proper_sync_response_with_result(response=response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert set(deserialized_entries) == {generated_entries[2]}
    assert result['entries_found'] == 1
    assert result['entries_total'] == len(entries_set)

    # test api pagination
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'offset': 0,
            'limit': 1,
            'blockchain': SupportedBlockchain.ETHEREUM.serialize(),
        },
    )
    result = assert_proper_sync_response_with_result(response=response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert set(deserialized_entries) == {generated_entries[0]}
    assert result['entries_found'] == 2
    assert result['entries_total'] == len(entries_set)

    # pagination offset works
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'offset': 1,
            'limit': 1,
            'blockchain': SupportedBlockchain.ETHEREUM.serialize(),
        },
    )
    result = assert_proper_sync_response_with_result(response=response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert set(deserialized_entries) == {generated_entries[2]}
    assert result['entries_found'] == 2
    assert result['entries_total'] == len(entries_set)

    # filter by multiple addresses
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={'addresses': [{'address': KELSOS_ADDR}]},
    )
    result = assert_proper_sync_response_with_result(response=response)
    assert AddressbookEntry.deserialize(data=result['entries'][0]) == KELSOS_BOOK_ENTRY
    assert result['entries_found'] == 1
    assert result['entries_total'] == len(entries_set)

    # filter by multiple addresses
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'addresses': [
                {'address': generated_entries[0].address},
                {'address': generated_entries[1].address},
            ],
        },
    )
    result = assert_proper_sync_response_with_result(response=response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert set(deserialized_entries) == set(generated_entries[0:3])
    assert result['entries_found'] == 3
    assert result['entries_total'] == len(entries_set)

    # order by name/address in ascending order
    for attribute in ('name', 'address'):
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'addressbookresource',
                book_type=book_type,
            ),
            json={
                'order_by_attributes': [attribute],
                'ascending': [True],
            },
        )
        result = assert_proper_sync_response_with_result(response=response)
        entries = [raw_entry[attribute] for raw_entry in result['entries']]
        assert entries == sorted(entries)


@pytest.mark.parametrize('empty_global_addressbook', [True])
@pytest.mark.parametrize('book_type', [AddressbookType.GLOBAL, AddressbookType.PRIVATE])
def test_insert_into_addressbook(
        rotkehlchen_api_server: 'APIServer',
        book_type: AddressbookType,
) -> None:
    generated_entries = make_addressbook_entries()
    db_addressbook = DBAddressbook(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    with db_addressbook.write_ctx(book_type=book_type) as write_cursor:
        db_addressbook.add_or_update_addressbook_entries(
            write_cursor=write_cursor,
            entries=generated_entries,
        )
    new_entries = [
        AddressbookEntry(
            address=generated_entries[0].address,
            name='name 1',
            blockchain=SupportedBlockchain.OPTIMISM,
        ),
        AddressbookEntry(
            address=to_checksum_address('0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD'),
            name='name 2',
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
        AddressbookEntry(
            address=BTCAddress('qzcnx0z2l9ncs7el5fcwgufv4mrng605ngc8p5csqn'),
            name='name 3',
            blockchain=SupportedBlockchain.BITCOIN_CASH,
        ),
    ]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'entries': [entry.serialize() for entry in new_entries],
        },
    )
    assert_proper_response(response=response)

    with db_addressbook.read_ctx(book_type) as cursor:
        assert db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0] == generated_entries + new_entries  # noqa: E501

        existing_entries = [
            AddressbookEntry(
                address=generated_entries[0].address,
                name='name 4',
                blockchain=SupportedBlockchain.ETHEREUM,
            ), AddressbookEntry(
                address=to_checksum_address('0xa500A944c0dff775Ad89Ec28C82b20d4BF60A0b4'),
                name='name 5',
                blockchain=SupportedBlockchain.ETHEREUM,
            ),
        ]
        # Check for error without the update_existing flag
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'addressbookresource', book_type=book_type),
            json={'entries': [entry.serialize() for entry in existing_entries]},
        )
        assert_error_response(
            response=response,
            contained_in_msg=f'Entry with address {generated_entries[0].address} and blockchain ethereum already exists in the address book.',  # noqa: E501
            status_code=HTTPStatus.CONFLICT,
        )
        # Check that existing entries are updated with the update_existing flag
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'addressbookresource', book_type=book_type),
            json={
                'entries': [entry.serialize() for entry in existing_entries],
                'update_existing': True,
            },
        )
        assert_proper_response(response=response)
        addressbook_entries = db_addressbook.get_addressbook_entries(
            cursor=cursor,
            filter_query=AddressbookFilterQuery.make(),
        )[0]
        assert all(entry in addressbook_entries for entry in existing_entries)

    # test to insert a name for an address that is recorded with two names in two different
    # evm chains a new name but this time valid for all addresses
    new_entry = AddressbookEntry(address=ADDRESS_MULTICHAIN, name='multichain', blockchain=None)

    # first check that we have two names if chain is not set
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'addresses': [{'address': ADDRESS_MULTICHAIN}],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 2

    # insert the new entry replacing all the previous values stored
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'entries': [new_entry.serialize()],
        },
    )

    # querying by address should return the only one with blockchain None
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={'addresses': [{'address': ADDRESS_MULTICHAIN}]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries'] == [new_entry.serialize()]

    # try inserting a non checksummed address
    yabir_address_not_checksummed = '0xc37b40abdb939635068d3c5f13e7faf686f03b65'
    new_entry = AddressbookEntry(
        address=yabir_address_not_checksummed,  # type: ignore  # we are forcing the error on types here
        name='yab yab',
        blockchain=SupportedBlockchain.GNOSIS,
    )
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={'entries': [new_entry.serialize()]},
    )
    result = assert_proper_sync_response_with_result(response)

    # check that in the database it was inserted checksummed
    with db_addressbook.read_ctx(book_type=book_type) as cursor:
        gnosis_entries = db_addressbook.get_addressbook_entries(
            cursor=cursor,
            filter_query=AddressbookFilterQuery.make(blockchain=new_entry.blockchain),
        )
        assert gnosis_entries[0] == [
            AddressbookEntry(
                address=to_checksum_address(new_entry.address),
                name=new_entry.name,
                blockchain=new_entry.blockchain,
            ),
        ]

    # try inserting an evm address that is not checksummed valid for all the chains
    non_checksummed_entry = AddressbookEntry(
        name='Non checksummed',
        address=(non_checksummed_addr := string_to_evm_address('0x4675c7e5baafbffbca748158becba61ef3b0a263')),  # noqa: E501
        blockchain=None,
    )
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'addressbookresource', book_type=book_type),
        json={'entries': [non_checksummed_entry.serialize()]},
    )
    # check that we can query correctly by the non checksummed version of an address
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'allnamesresource', book_type=book_type),
        json={'addresses': [{'address': non_checksummed_addr}]},
    )
    result = assert_proper_sync_response_with_result(response=response)
    assert result[0]['address'] == to_checksum_address(non_checksummed_addr)


@pytest.mark.parametrize('empty_global_addressbook', [True])
@pytest.mark.parametrize('book_type', [AddressbookType.GLOBAL, AddressbookType.PRIVATE])
def test_update_addressbook(
        rotkehlchen_api_server: 'APIServer',
        book_type: AddressbookType,
) -> None:
    generated_entries = make_addressbook_entries()
    db_addressbook = DBAddressbook(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    with db_addressbook.write_ctx(book_type=book_type) as write_cursor:
        db_addressbook.add_or_update_addressbook_entries(
            write_cursor=write_cursor,
            entries=generated_entries,
        )
    entries_to_update = [
        AddressbookEntry(
            address=ADDRESS_ETH,
            name='NEW NAME WOW!',
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
        AddressbookEntry(
            address=ADDRESS_MULTICHAIN,
            name='LoL kek',
            blockchain=SupportedBlockchain.OPTIMISM,
        ),
        AddressbookEntry(
            address=SubstrateAddress('13EcxFSXEFmJfxGXSQYLfgEXXGZBSF1P753MyHauw5NV4tAV'),
            name='Polkadot staker',
            blockchain=SupportedBlockchain.POLKADOT,
        ),
    ]
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'entries': [entry.serialize() for entry in entries_to_update],
        },
    )
    assert_proper_response(response=response)
    expected_entries = entries_to_update + generated_entries[2:-1]
    with db_addressbook.read_ctx(book_type) as cursor:
        assert set(db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0]) == set(expected_entries)  # noqa: E501

    # test that editing nonexistent entries adds them to the database
    new_entries = [
        AddressbookEntry(
            address=ADDRESS_ETH,
            name='Hola amigos!',
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
        AddressbookEntry(
            address=string_to_evm_address('0x79B598976bD83a47CD8B428C824C8474311267b8'),
            name='Have a good day, friend!',
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
    ]

    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={'entries': [entry.serialize() for entry in new_entries]},
    )
    assert_proper_sync_response_with_result(response)
    with db_addressbook.read_ctx(book_type) as cursor:
        entries_after_update = db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0]  # noqa: E501
    assert all(entry in entries_after_update for entry in new_entries)

    # test that updating an entry with a blank label deletes the entry
    entry_to_delete = new_entries[0]
    blank_name_entry = AddressbookEntry(
        address=entry_to_delete.address,
        name='',
        blockchain=entry_to_delete.blockchain,
    )
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={'entries': [blank_name_entry.serialize()]},
    )
    assert_proper_sync_response_with_result(response)
    with db_addressbook.read_ctx(book_type) as cursor:
        assert entry_to_delete not in db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0]  # noqa: E501

    # add a new entry with no blockchain assigned
    new_entry = AddressbookEntry(
        address=ADDRESS_ETH,
        name='super name',
        blockchain=None,
    )
    with db_addressbook.write_ctx(book_type=book_type) as write_cursor:
        db_addressbook.add_or_update_addressbook_entries(
            write_cursor=write_cursor,
            entries=[new_entry],
        )

    # edit it without the blockchain argument
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'entries': [{'address': ADDRESS_ETH, 'name': 'super name ray'}],
        },
    )
    assert_proper_response(response)
    with db_addressbook.read_ctx(book_type) as cursor:
        optional_chain_addresses = [OptionalChainAddress(ADDRESS_ETH, None)]
        names, _ = db_addressbook.get_addressbook_entries(
            cursor=cursor,
            filter_query=AddressbookFilterQuery.make(optional_chain_addresses=optional_chain_addresses),
        )
        assert names[0].name == 'super name ray'


@pytest.mark.parametrize('empty_global_addressbook', [True])
def test_blockchain_type_query_filters(rotkehlchen_api_server: 'APIServer') -> None:
    """Add the same address to BTC and BCH, then ensure queries return a multichain entry.

    - Add label valid both for BTC and BCH
    - Query filtering by BTC, BCH and None should return the multichain entry
    - Query filtering by unrelated chain (e.g. Polkadot) should return nothing
    """
    db_addressbook = DBAddressbook(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    book_type = AddressbookType.PRIVATE

    # Use a valid Bitcoin Cash CashAddr which also classifies under the BITCOIN ecosystem key
    btc_like_address = BTCAddress('bitcoincash:pp8skudq3x5hzw8ew7vzsw8tn4k8wxsqsv0lt0mf3g')

    # Insert same label for both BTC and BCH for the same address
    with db_addressbook.write_ctx(book_type=book_type) as write_cursor:
        db_addressbook.add_or_update_addressbook_entries(
            write_cursor=write_cursor,
            entries=(expected_output := [
                AddressbookEntry(address=btc_like_address, name='Satoshi', blockchain=None),
            ]),
        )

    def query(blockchain: SupportedBlockchain | None, strict_blockchain: bool = False) -> list[dict]:  # noqa: E501
        payload: dict[str, object] = {
            'addresses': [{'address': btc_like_address}],
        }
        if blockchain is not None:
            payload['blockchain'] = blockchain.serialize()
            payload['strict_blockchain'] = strict_blockchain

        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'addressbookresource', book_type=book_type),
            json=payload,
        )
        result = assert_proper_sync_response_with_result(response)
        return result['entries']

    # Filtering by BTC should return the multichain entry when not strict
    result_entries = query(SupportedBlockchain.BITCOIN, strict_blockchain=False)
    assert [AddressbookEntry.deserialize(x) for x in result_entries] == expected_output

    # Filtering by BCH should also return the multichain entry when not strict
    result_entries = query(SupportedBlockchain.BITCOIN_CASH, strict_blockchain=False)
    assert [AddressbookEntry.deserialize(x) for x in result_entries] == expected_output

    # Filtering with blockchain=None should return the multichain entry
    result_entries = query(None)
    assert [AddressbookEntry.deserialize(x) for x in result_entries] == expected_output

    # Filtering by an unrelated chain type should not return the entry
    result_entries = query(SupportedBlockchain.POLKADOT, strict_blockchain=False)
    assert result_entries == []


@pytest.mark.parametrize('empty_global_addressbook', [True])
@pytest.mark.parametrize('book_type', [AddressbookType.GLOBAL, AddressbookType.PRIVATE])
def test_delete_addressbook(
        rotkehlchen_api_server: 'APIServer',
        book_type: AddressbookType,
) -> None:
    generated_entries = make_addressbook_entries()
    db_addressbook = DBAddressbook(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    with db_addressbook.write_ctx(book_type=book_type) as write_cursor:
        db_addressbook.add_or_update_addressbook_entries(
            write_cursor=write_cursor,
            entries=generated_entries,
        )

    btc_address = BTCAddress('bc1qamhqfr5z2ypehv0sqq784hzgd6ws2rjf6v46w8')
    addresses_to_delete = [ADDRESS_ETH, ADDRESS_OP]
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'addresses': [{'address': address} for address in addresses_to_delete],
        },
    )
    assert_proper_response(response)

    with db_addressbook.read_ctx(book_type) as cursor:
        assert set(
            db_addressbook.get_addressbook_entries(
                cursor=cursor,
                filter_query=AddressbookFilterQuery.make(),
            )[0],
        ) == set(generated_entries[1:3] + generated_entries[4:])
        nonexistent_addresses = [ADDRESS_ETH, ADDRESS_OP]

        data_before_bad_request = db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0]  # noqa: E501
        response = requests.delete(
            api_url_for(
                rotkehlchen_api_server,
                'addressbookresource',
                book_type=book_type,
            ),
            json={
                'addresses': [{'address': address} for address in nonexistent_addresses],
            },
        )
        assert_error_response(
            response=response,
            contained_in_msg='are not present in the database',
            status_code=HTTPStatus.CONFLICT,
        )
        assert db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0] == data_before_bad_request  # noqa: E501

    # try to delete by invalid combination of address and chain
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'addresses': [{'address': generated_entries[1].address, 'blockchain': 'btc'}],
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Given value {generated_entries[1].address} is not a bitcoin address',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # try to delete by chain
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'addresses': [{'address': generated_entries[1].address, 'blockchain': 'base'}],
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='One or more of the addresses with blockchains provided do not exist in the database',  # noqa: E501
        status_code=HTTPStatus.CONFLICT,
    )

    # try to delete by chain that is not evm
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'addresses': [{'address': btc_address, 'blockchain': 'btc'}],
        },
    )
    assert_proper_response(response)

    # try to delete it using the correct chain
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'addresses': [{'address': generated_entries[1].address, 'blockchain': 'optimism'}],
        },
    )
    assert_proper_response(response)
    with db_addressbook.read_ctx(book_type) as cursor:
        assert len(db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0]) == 3  # noqa: E501

    # add entry with no blockchain to check that it can be deleted
    with db_addressbook.write_ctx(book_type=book_type) as write_cursor:
        db_addressbook.add_or_update_addressbook_entries(
            write_cursor=write_cursor,
            entries=[KELSOS_BOOK_ENTRY],
        )
    with db_addressbook.read_ctx(book_type) as cursor:
        optional_chain_addresses = [OptionalChainAddress(address=KELSOS_ADDR, blockchain=None)]
        assert db_addressbook.get_addressbook_entries(
            cursor=cursor,
            filter_query=AddressbookFilterQuery.make(optional_chain_addresses=optional_chain_addresses),
        )[0] == [KELSOS_BOOK_ENTRY]

    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'addresses': [{'address': KELSOS_ADDR}],
        },
    )
    assert_proper_response(response)
    with db_addressbook.read_ctx(book_type) as cursor:
        optional_chain_addresses = [OptionalChainAddress(address=KELSOS_ADDR, blockchain=None)]
        assert len(db_addressbook.get_addressbook_entries(
            cursor=cursor,
            filter_query=AddressbookFilterQuery.make(optional_chain_addresses=optional_chain_addresses))[0],
        ) == 0


@pytest.mark.parametrize('empty_global_addressbook', [True])
def test_names_compilation(rotkehlchen_api_server: 'APIServer') -> None:
    def names_request(chain_addresses: list[OptionalChainAddress]) -> requests.Response:
        return requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'allnamesresource',
            ),
            json={
                'addresses': [
                    {'address': chain_address.address, 'blockchain': chain_address.blockchain.serialize() if chain_address.blockchain is not None else None} for chain_address in chain_addresses],  # noqa: E501
            },
        )

    address_rotki = string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    address_cody = ADDRESS_MULTICHAIN
    address_rose = string_to_evm_address('0xE07Af3FBEAf8584dc885f5bAA7c72419BDDf002D')
    address_tylor = string_to_evm_address('0xC88eA7a5df3A7BA59C72393C5b2dc2CE260ff04D')
    address_nonlabel = ADDRESS_ETH
    address_firstblood = string_to_evm_address('0xAf30D2a7E90d7DC361c8C4585e9BB7D2F6f15bc7')
    address_kraken = string_to_evm_address('0xAe2D4617c862309A3d75A0fFB358c7a5009c673F')
    address_titan = string_to_evm_address('0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97')
    db_handler = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    db_ens = DBEns(db_handler=db_handler)
    db_addressbook = DBAddressbook(db_handler=db_handler)
    with db_handler.user_write() as cursor:
        db_ens.add_ens_mapping(  # write ens rotki.eth
            write_cursor=cursor,
            address=address_rotki,
            name='rotki.eth',
            now=Timestamp(1),
        )
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        db_addressbook.add_or_update_addressbook_entries(  # add an entry for all chains
            write_cursor=write_cursor,
            entries=[AddressbookEntry(address=address_titan, name='Titan Builder', blockchain=None)],  # noqa: E501
        )
    publicly_known_addresses = [
        OptionalChainAddress(address_rotki, None),
        OptionalChainAddress(address_titan, None),
        OptionalChainAddress(address_kraken, SupportedBlockchain.ETHEREUM),
        OptionalChainAddress(address_firstblood, SupportedBlockchain.ETHEREUM),
        # Below is an address that we don't know anything about
        OptionalChainAddress(to_checksum_address('0x42F47A289B1E17BCbbBc1630f112c036ed901f5d'), SupportedBlockchain.ETHEREUM),  # noqa: E501
    ]
    publicly_known_expected = [
        AddressbookEntry(address=address_rotki, blockchain=None, name='rotki.eth'),
        AddressbookEntry(address=address_titan, blockchain=None, name='Titan Builder'),
        AddressbookEntry(address=address_kraken, blockchain=SupportedBlockchain.ETHEREUM, name='Kraken'),  # noqa: E501
        AddressbookEntry(address=address_firstblood, blockchain=SupportedBlockchain.ETHEREUM, name='FirstBlood'),  # noqa: E501
    ]

    response = names_request(publicly_known_addresses)
    result = assert_proper_sync_response_with_result(response)
    assert {AddressbookEntry.deserialize(x) for x in result} == set(publicly_known_expected)

    # now query names that are saved for all chains, but for a specific chain and see they appear
    response = names_request([
        OptionalChainAddress(address_rotki, SupportedBlockchain.ETHEREUM),
        OptionalChainAddress(address_titan, SupportedBlockchain.ETHEREUM),
    ])
    result = assert_proper_sync_response_with_result(response)
    assert {AddressbookEntry.deserialize(x) for x in result} == {
        AddressbookEntry(address=address_rotki, blockchain=SupportedBlockchain.ETHEREUM, name='rotki.eth'),  # noqa: E501
        AddressbookEntry(address=address_titan, blockchain=SupportedBlockchain.ETHEREUM, name='Titan Builder'),  # noqa: E501
    }

    with db_addressbook.write_ctx(book_type=AddressbookType.GLOBAL) as write_cursor:
        db_addressbook.add_or_update_addressbook_entries(
            write_cursor=write_cursor,
            entries=[
                AddressbookEntry(
                    name='Cody',
                    address=address_cody,
                    blockchain=SupportedBlockchain.ETHEREUM,
                ),  # address_rotki is already added
            ],
        )
    global_addressbook_addresses = [
        OptionalChainAddress(address_cody, SupportedBlockchain.ETHEREUM),
        OptionalChainAddress(address_rotki, SupportedBlockchain.ETHEREUM),
    ]
    global_addressbook_expected = {
        AddressbookEntry(address=address_rotki, blockchain=SupportedBlockchain.ETHEREUM, name='rotki.eth'),  # noqa: E501
        AddressbookEntry(address=address_cody, blockchain=SupportedBlockchain.ETHEREUM, name='Cody'),  # noqa: E501
    }
    response = names_request(global_addressbook_addresses)
    result = assert_proper_sync_response_with_result(response)
    assert {AddressbookEntry.deserialize(x) for x in result} == global_addressbook_expected

    with db_handler.user_write() as cursor:
        db_handler.add_blockchain_accounts(
            cursor,
            account_data=[
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=address_tylor, label='Tylor'),  # noqa: E501
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=address_rotki, label='rotki label'),  # noqa: E501
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=address_nonlabel),  # noqa: E501
            ],
        )
    labels_addresses = [
        OptionalChainAddress(address_tylor, SupportedBlockchain.ETHEREUM),
        OptionalChainAddress(address_nonlabel, SupportedBlockchain.ETHEREUM),  # address with None label  # noqa: E501
        OptionalChainAddress(address_rose, SupportedBlockchain.ETHEREUM),  # private addressbook
        OptionalChainAddress(address_cody, SupportedBlockchain.ETHEREUM),  # global addressbook
        OptionalChainAddress(address_rotki, SupportedBlockchain.ETHEREUM),  # rotki.eth
    ]
    labels_expected = {
        AddressbookEntry(address=address_rotki, blockchain=SupportedBlockchain.ETHEREUM, name='rotki label'),  # noqa: E501
        AddressbookEntry(address=address_tylor, blockchain=SupportedBlockchain.ETHEREUM, name='Tylor'),  # noqa: E501
        AddressbookEntry(address=address_cody, blockchain=SupportedBlockchain.ETHEREUM, name='Cody'),  # noqa: E501
    }
    response = names_request(labels_addresses)
    result = assert_proper_sync_response_with_result(response)
    assert {AddressbookEntry.deserialize(x) for x in result} == labels_expected

    with db_addressbook.write_ctx(book_type=AddressbookType.PRIVATE) as write_cursor:
        db_addressbook.add_or_update_addressbook_entries(
            write_cursor=write_cursor,
            entries=[
                AddressbookEntry(
                    name='Rose',
                    address=address_rose,
                    blockchain=SupportedBlockchain.ETHEREUM,
                ),  # address_rotki is already added
            ],
        )
    private_addressbook_addresses = [
        OptionalChainAddress(address_tylor, SupportedBlockchain.ETHEREUM),
        OptionalChainAddress(address_rose, SupportedBlockchain.ETHEREUM),
        OptionalChainAddress(address_cody, SupportedBlockchain.ETHEREUM),  # global addressbook
        OptionalChainAddress(address_rotki, SupportedBlockchain.ETHEREUM),  # rotki.eth
    ]
    private_addressbook_expected = {
        AddressbookEntry(address=address_rotki, blockchain=SupportedBlockchain.ETHEREUM, name='rotki label'),  # noqa: E501
        AddressbookEntry(address=address_tylor, blockchain=SupportedBlockchain.ETHEREUM, name='Tylor'),  # noqa: E501
        AddressbookEntry(address=address_cody, blockchain=SupportedBlockchain.ETHEREUM, name='Cody'),  # noqa: E501
        AddressbookEntry(address=address_rose, blockchain=SupportedBlockchain.ETHEREUM, name='Rose'),  # noqa: E501
    }
    response = names_request(private_addressbook_addresses)
    result = assert_proper_sync_response_with_result(response)
    assert {AddressbookEntry.deserialize(x) for x in result} == private_addressbook_expected


@pytest.mark.parametrize('empty_global_addressbook', [True])
@pytest.mark.parametrize('book_type', [AddressbookType.GLOBAL, AddressbookType.PRIVATE])
def test_insert_into_addressbook_no_blockchain(
        rotkehlchen_api_server: 'APIServer',
        book_type: AddressbookType,
) -> None:
    """
    Check that adding a name with no blockchain works as expected and it replaces any other
    entry if it exists.
    """
    test_address = to_checksum_address('0x9531c059098e3d194ff87febb587ab07b30b1306')
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    # add a name for blockchain ethereum
    custom_name = AddressbookEntry(
        address=test_address,
        name='my address',
        blockchain=SupportedBlockchain.ETHEREUM,
    )
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'entries': [custom_name.serialize()],
        },
    )
    assert_proper_sync_response_with_result(response)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'addresses': [
                {'address': test_address},
            ],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries'] == [custom_name.serialize()]

    # now add the same name for all blockchains and see the value replaced
    custom_name = AddressbookEntry(
        address=test_address,
        name='my address',
        blockchain=None,
    )
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'entries': [custom_name.serialize()],
        },
    )
    assert_proper_sync_response_with_result(response)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={'addresses': [{'address': test_address}]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries'] == [custom_name.serialize()]
    if book_type == AddressbookType.PRIVATE:
        with database.conn.read_ctx() as cursor:
            cursor.execute('SELECT * FROM address_book')
            result = cursor.fetchall()
    else:
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute('SELECT * FROM address_book')
            result = cursor.fetchall()

    assert result == [(test_address, f'{ADDRESSBOOK_BLOCKCHAIN_GROUP_PREFIX}EVMLIKE', 'my address')]  # noqa: E501


def test_edit_multichain_address_label(rotkehlchen_api_server: 'APIServer') -> None:
    """Check that editing the label of a multichain evm address works correctly"""
    test_address = to_checksum_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')
    db_addressbook = DBAddressbook(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    with db_addressbook.write_ctx(book_type=AddressbookType.PRIVATE) as write_cursor:
        db_addressbook.add_or_update_addressbook_entries(
            write_cursor=write_cursor,
            entries=[AddressbookEntry(
                address=test_address,
                name='original name',
                blockchain=None,
            )],
        )

    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'chaintypeaccountresource',
            chain_type=ChainType.EVM.serialize(),
        ),
        json={
            'accounts': [{
                'address': test_address,
                'label': 'new name',
            }],
        },
    )
    assert_proper_sync_response_with_result(response)

    with db_addressbook.read_ctx(book_type=AddressbookType.PRIVATE) as cursor:
        entries = db_addressbook.get_addressbook_entries(cursor, AddressbookFilterQuery.make())[0]
        assert entries == [AddressbookEntry(
            address=test_address,
            name='new name',
            blockchain=None,
        )]
