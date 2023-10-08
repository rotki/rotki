from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests
from eth_utils import to_checksum_address

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.ens import DBEns
from rotkehlchen.db.filtering import AddressbookFilterQuery
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.factories import make_addressbook_entries
from rotkehlchen.types import (
    AddressbookEntry,
    AddressbookType,
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
        db_addressbook.add_addressbook_entries(write_cursor=write_cursor, entries=generated_entries + [KELSOS_BOOK_ENTRY])  # noqa: E501
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
    )
    result = assert_proper_response_with_result(response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert deserialized_entries == entries_set
    assert result['entries_found'] == 5
    assert result['entries_total'] == 5

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
    result = assert_proper_response_with_result(response=response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert set(deserialized_entries) == set(generated_entries[0:3])
    assert result['entries_found'] == 3
    assert result['entries_total'] == 5

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
    result = assert_proper_response_with_result(response=response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert set(deserialized_entries) == {generated_entries[1]}
    assert result['entries_found'] == 1
    assert result['entries_total'] == 5

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
    result = assert_proper_response_with_result(response=response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert set(deserialized_entries) == {generated_entries[2]}
    assert result['entries_found'] == 1
    assert result['entries_total'] == 5

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
    result = assert_proper_response_with_result(response=response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert set(deserialized_entries) == {generated_entries[0]}
    assert result['entries_found'] == 2
    assert result['entries_total'] == 5

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
    result = assert_proper_response_with_result(response=response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert set(deserialized_entries) == {generated_entries[2]}
    assert result['entries_found'] == 2
    assert result['entries_total'] == 5

    # filter by multiple addresses
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={'addresses': [{'address': KELSOS_ADDR}]},
    )
    result = assert_proper_response_with_result(response=response)
    assert AddressbookEntry.deserialize(data=result['entries'][0]) == KELSOS_BOOK_ENTRY
    assert result['entries_found'] == 1
    assert result['entries_total'] == 5

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
    result = assert_proper_response_with_result(response=response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result['entries']]  # noqa: E501
    assert set(deserialized_entries) == set(generated_entries[0:3])
    assert result['entries_found'] == 3
    assert result['entries_total'] == 5


@pytest.mark.parametrize('empty_global_addressbook', [True])
@pytest.mark.parametrize('book_type', [AddressbookType.GLOBAL, AddressbookType.PRIVATE])
def test_insert_into_addressbook(
        rotkehlchen_api_server: 'APIServer',
        book_type: AddressbookType,
) -> None:
    generated_entries = make_addressbook_entries()
    db_addressbook = DBAddressbook(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    with db_addressbook.write_ctx(book_type=book_type) as write_cursor:
        db_addressbook.add_addressbook_entries(write_cursor=write_cursor, entries=generated_entries)  # noqa: E501
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
                name='name 3',
                blockchain=SupportedBlockchain.ETHEREUM,
            ), AddressbookEntry(
                address=to_checksum_address('0xa500A944c0dff775Ad89Ec28C82b20d4BF60A0b4'),
                name='name 4',
                blockchain=SupportedBlockchain.ETHEREUM,
            ),
        ]
        entries_in_db_before_bad_put = db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0]  # noqa: E501
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'addressbookresource',
                book_type=book_type,
            ),
            json={
                'entries': [entry.serialize() for entry in existing_entries],
            },
        )
        assert_error_response(
            response=response,
            contained_in_msg=f'address "0x9D904063e7e120302a13C6820561940538a2Ad57" and blockchain {SupportedBlockchain.ETHEREUM!s} already exists in the address book.',  # noqa: E501
            status_code=HTTPStatus.CONFLICT,
        )
        assert db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0] == entries_in_db_before_bad_put  # noqa: E501

    # test to insert a name for an address that is recorded with two names in two different
    # evm chains a new name but this time valid for all addresses
    multichain_addr = to_checksum_address('0x368B9ad9B6AAaeFCE33b8c21781cfF375e09be67')
    new_entry = AddressbookEntry(
        address=multichain_addr,
        name='multichain',
        blockchain=None,
    )

    # first check that we have two names if chain is not set
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'addresses': [
                {'address': multichain_addr},
            ],
        },
    )
    result = assert_proper_response_with_result(response)
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

    # quering by address should return the only one with blockchain None
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'addresses': [
                {'address': multichain_addr},
            ],
        },
    )
    result = assert_proper_response_with_result(response)
    assert result['entries'] == [new_entry.serialize()]


@pytest.mark.parametrize('empty_global_addressbook', [True])
@pytest.mark.parametrize('book_type', [AddressbookType.GLOBAL, AddressbookType.PRIVATE])
def test_update_addressbook(
        rotkehlchen_api_server: 'APIServer',
        book_type: AddressbookType,
) -> None:
    generated_entries = make_addressbook_entries()
    db_addressbook = DBAddressbook(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    with db_addressbook.write_ctx(book_type=book_type) as write_cursor:
        db_addressbook.add_addressbook_entries(write_cursor=write_cursor, entries=generated_entries)  # noqa: E501
    entries_to_update = [
        AddressbookEntry(
            address=to_checksum_address('0x9d904063e7e120302a13c6820561940538a2ad57'),
            name='NEW NAME WOW!',
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
        AddressbookEntry(
            address=to_checksum_address('0x368B9ad9B6AAaeFCE33b8c21781cfF375e09be67'),
            name='LoL kek',
            blockchain=SupportedBlockchain.OPTIMISM,
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
    expected_entries = entries_to_update + generated_entries[2:]

    # test editing entries that don't exist in the database
    with db_addressbook.read_ctx(book_type) as cursor:
        assert db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0] == expected_entries  # noqa: E501

        nonexistent_entries = [
            AddressbookEntry(
                address=to_checksum_address('0x9d904063e7e120302a13c6820561940538a2ad57'),
                name='Hola amigos!',
                blockchain=SupportedBlockchain.ETHEREUM,
            ),
            AddressbookEntry(
                address=to_checksum_address('0x79B598976bD83a47CD8B428C824C8474311267b8'),
                name='Have a good day, friend!',
                blockchain=SupportedBlockchain.ETHEREUM,
            ),
        ]

        entries_in_db_before_bad_patch = db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0]  # noqa: E501
        response = requests.patch(
            api_url_for(
                rotkehlchen_api_server,
                'addressbookresource',
                book_type=book_type,
            ),
            json={
                'entries': [entry.serialize() for entry in nonexistent_entries],
            },
        )
        assert_error_response(
            response=response,
            contained_in_msg='address "0x79B598976bD83a47CD8B428C824C8474311267b8" and blockchain ethereum doesn\'t exist in the address book',  # noqa: E501
            status_code=HTTPStatus.CONFLICT)
        assert db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0] == entries_in_db_before_bad_patch  # noqa: E501

    # add a new entry with no blockchain assigned
    new_entry_addr = to_checksum_address('0x9d904063e7e120302a13c6820561940538a2ad57')
    new_entry = AddressbookEntry(
        address=new_entry_addr,
        name='super name',
        blockchain=None,
    )
    with db_addressbook.write_ctx(book_type=book_type) as write_cursor:
        db_addressbook.add_addressbook_entries(write_cursor=write_cursor, entries=[new_entry])

    # edit it without the blockchain argument
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
        json={
            'entries': [{'address': new_entry_addr, 'name': 'super name ray'}],
        },
    )
    assert_proper_response(response)
    with db_addressbook.read_ctx(book_type) as cursor:
        optional_chain_addresses = [OptionalChainAddress(new_entry_addr, None)]
        names, _ = db_addressbook.get_addressbook_entries(
            cursor=cursor,
            filter_query=AddressbookFilterQuery.make(optional_chain_addresses=optional_chain_addresses),
        )
        assert names[0].name == 'super name ray'


@pytest.mark.parametrize('empty_global_addressbook', [True])
@pytest.mark.parametrize('book_type', [AddressbookType.GLOBAL, AddressbookType.PRIVATE])
def test_delete_addressbook(
        rotkehlchen_api_server: 'APIServer',
        book_type: AddressbookType,
) -> None:
    generated_entries = make_addressbook_entries()
    db_addressbook = DBAddressbook(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    with db_addressbook.write_ctx(book_type=book_type) as write_cursor:
        db_addressbook.add_addressbook_entries(write_cursor=write_cursor, entries=generated_entries)  # noqa: E501
    addresses_to_delete = [
        to_checksum_address('0x9d904063e7e120302a13c6820561940538a2ad57'),
        to_checksum_address('0x3D61AEBB1238062a21BE5CC79df308f030BF0c1B'),
    ]
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
        assert db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0] == generated_entries[1:3]  # noqa: E501
        nonexistent_addresses = [
            to_checksum_address('0x368B9ad9B6AAaeFCE33b8c21781cfF375e09be67'),
            to_checksum_address('0x9d904063e7e120302a13c6820561940538a2ad57'),
        ]

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

    # try to delete by chain
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
        contained_in_msg='One or more of the addresses with blockchains provided do not exist in the database',  # noqa: E501
        status_code=HTTPStatus.CONFLICT,
    )

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
        assert len(db_addressbook.get_addressbook_entries(cursor, filter_query=AddressbookFilterQuery.make())[0]) == 1  # noqa: E501

    # add entry with no blockchain to check that it can be deleted
    with db_addressbook.write_ctx(book_type=book_type) as write_cursor:
        db_addressbook.add_addressbook_entries(
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
    address_cody = string_to_evm_address('0x368B9ad9B6AAaeFCE33b8c21781cfF375e09be67')
    address_rose = string_to_evm_address('0xE07Af3FBEAf8584dc885f5bAA7c72419BDDf002D')
    address_tylor = string_to_evm_address('0xC88eA7a5df3A7BA59C72393C5b2dc2CE260ff04D')
    address_nonlabel = string_to_evm_address('0x9D904063e7e120302a13C6820561940538a2Ad57')
    address_firstblood = string_to_evm_address('0xAf30D2a7E90d7DC361c8C4585e9BB7D2F6f15bc7')
    address_kraken10 = string_to_evm_address('0xAe2D4617c862309A3d75A0fFB358c7a5009c673F')
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
        db_addressbook.add_addressbook_entries(  # add an entry for all chains
            write_cursor=write_cursor,
            entries=[AddressbookEntry(address=address_titan, name='Titan Builder', blockchain=None)],  # noqa: E501
        )
    publicly_known_addresses = [
        OptionalChainAddress(address_rotki, None),
        OptionalChainAddress(address_titan, None),
        OptionalChainAddress(address_kraken10, SupportedBlockchain.ETHEREUM),
        OptionalChainAddress(address_firstblood, SupportedBlockchain.ETHEREUM),
        # Below is an address that we don't know anything about
        OptionalChainAddress(to_checksum_address('0x42F47A289B1E17BCbbBc1630f112c036ed901f5d'), SupportedBlockchain.ETHEREUM),  # noqa: E501
    ]
    publicly_known_expected = [
        AddressbookEntry(address=address_rotki, blockchain=None, name='rotki.eth'),
        AddressbookEntry(address=address_titan, blockchain=None, name='Titan Builder'),
        AddressbookEntry(address=address_kraken10, blockchain=SupportedBlockchain.ETHEREUM, name='Kraken 10'),  # noqa: E501
        AddressbookEntry(address=address_firstblood, blockchain=SupportedBlockchain.ETHEREUM, name='FirstBlood'),  # noqa: E501
    ]

    response = names_request(publicly_known_addresses)
    result = assert_proper_response_with_result(response)
    assert {AddressbookEntry.deserialize(x) for x in result} == set(publicly_known_expected)

    # now query names that are saved for all chains, but for a specific chain and see they appear
    response = names_request([
        OptionalChainAddress(address_rotki, SupportedBlockchain.ETHEREUM),
        OptionalChainAddress(address_titan, SupportedBlockchain.ETHEREUM),
    ])
    result = assert_proper_response_with_result(response)
    assert {AddressbookEntry.deserialize(x) for x in result} == {
        AddressbookEntry(address=address_rotki, blockchain=SupportedBlockchain.ETHEREUM, name='rotki.eth'),  # noqa: E501
        AddressbookEntry(address=address_titan, blockchain=SupportedBlockchain.ETHEREUM, name='Titan Builder'),  # noqa: E501
    }

    with db_addressbook.write_ctx(book_type=AddressbookType.GLOBAL) as write_cursor:
        db_addressbook.add_addressbook_entries(
            write_cursor=write_cursor,
            entries=[
                AddressbookEntry(
                    name='Cody',
                    address=address_cody,
                    blockchain=SupportedBlockchain.ETHEREUM,
                ), AddressbookEntry(
                    name='rotki global db',
                    address=address_rotki,
                    blockchain=SupportedBlockchain.ETHEREUM,
                ),
            ],
        )
    global_addressbook_addresses = [
        OptionalChainAddress(address_cody, SupportedBlockchain.ETHEREUM),
        OptionalChainAddress(address_rotki, SupportedBlockchain.ETHEREUM),
    ]
    global_addressbook_expected = {
        AddressbookEntry(address=address_rotki, blockchain=SupportedBlockchain.ETHEREUM, name='rotki global db'),  # noqa: E501
        AddressbookEntry(address=address_cody, blockchain=SupportedBlockchain.ETHEREUM, name='Cody'),  # noqa: E501
    }
    response = names_request(global_addressbook_addresses)
    result = assert_proper_response_with_result(response)
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
    result = assert_proper_response_with_result(response)
    assert {AddressbookEntry.deserialize(x) for x in result} == labels_expected

    with db_addressbook.write_ctx(book_type=AddressbookType.PRIVATE) as write_cursor:
        db_addressbook.add_addressbook_entries(
            write_cursor=write_cursor,
            entries=[
                AddressbookEntry(
                    name='Rose',
                    address=address_rose,
                    blockchain=SupportedBlockchain.ETHEREUM,
                ), AddressbookEntry(
                    name='rotki private db',
                    address=address_rotki,
                    blockchain=SupportedBlockchain.ETHEREUM,
                ),
            ],
        )
    private_addressbook_addresses = [
        OptionalChainAddress(address_tylor, SupportedBlockchain.ETHEREUM),
        OptionalChainAddress(address_rose, SupportedBlockchain.ETHEREUM),
        OptionalChainAddress(address_cody, SupportedBlockchain.ETHEREUM),  # global addressbook
        OptionalChainAddress(address_rotki, SupportedBlockchain.ETHEREUM),  # rotki.eth
    ]
    private_addressbook_expected = {
        AddressbookEntry(address=address_rotki, blockchain=SupportedBlockchain.ETHEREUM, name='rotki private db'),  # noqa: E501
        AddressbookEntry(address=address_tylor, blockchain=SupportedBlockchain.ETHEREUM, name='Tylor'),  # noqa: E501
        AddressbookEntry(address=address_cody, blockchain=SupportedBlockchain.ETHEREUM, name='Cody'),  # noqa: E501
        AddressbookEntry(address=address_rose, blockchain=SupportedBlockchain.ETHEREUM, name='Rose'),  # noqa: E501
    }
    response = names_request(private_addressbook_addresses)
    result = assert_proper_response_with_result(response)
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
    assert_proper_response_with_result(response)
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
    result = assert_proper_response_with_result(response)
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
    assert_proper_response_with_result(response)
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
    result = assert_proper_response_with_result(response)
    assert result['entries'] == [custom_name.serialize()]
    if book_type == AddressbookType.PRIVATE:
        with database.conn.read_ctx() as cursor:
            cursor.execute('SELECT * FROM address_book')
            result = cursor.fetchall()
    else:
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute('SELECT * FROM address_book')
            result = cursor.fetchall()

    assert result == [(test_address, None, 'my address')]
