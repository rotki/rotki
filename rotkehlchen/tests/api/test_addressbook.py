from http import HTTPStatus

import pytest
import requests
from eth_utils import to_checksum_address

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.ens import DBEns
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.factories import make_addressbook_entries
from rotkehlchen.types import AddressbookEntry, AddressbookType, SupportedBlockchain, Timestamp


@pytest.mark.parametrize('book_type', [AddressbookType.GLOBAL, AddressbookType.PRIVATE])
def test_get_addressbook(rotkehlchen_api_server, book_type: AddressbookType) -> None:
    generated_entries = make_addressbook_entries()
    db_addressbook = DBAddressbook(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    db_addressbook.add_addressbook_entries(book_type=book_type, entries=generated_entries)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'addressbookresource',
            book_type=book_type,
        ),
    )
    result = assert_proper_response_with_result(response)
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result]
    assert deserialized_entries == generated_entries

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
    expected_entries = [generated_entries[0], generated_entries[1]]
    deserialized_entries = [AddressbookEntry.deserialize(data=raw_entry) for raw_entry in result]
    assert set(deserialized_entries) == set(expected_entries)


@pytest.mark.parametrize('book_type', [AddressbookType.GLOBAL, AddressbookType.PRIVATE])
def test_insert_into_addressbook(rotkehlchen_api_server, book_type: AddressbookType) -> None:
    generated_entries = make_addressbook_entries()
    db_addressbook = DBAddressbook(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    db_addressbook.add_addressbook_entries(book_type=book_type, entries=generated_entries)
    new_entries = [
        AddressbookEntry(
            address=to_checksum_address('0x9531c059098e3d194ff87febb587ab07b30b1306'),
            name='name 1',
            blockchain=SupportedBlockchain.ETHEREUM,
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
        assert db_addressbook.get_addressbook_entries(cursor) == generated_entries + new_entries  # noqa: E501

        existing_entries = [
            AddressbookEntry(
                address=to_checksum_address('0x9531c059098e3d194ff87febb587ab07b30b1306'),
                name='name 3',
                blockchain=SupportedBlockchain.ETHEREUM,
            ), AddressbookEntry(
                address=to_checksum_address('0xa500A944c0dff775Ad89Ec28C82b20d4BF60A0b4'),
                name='name 4',
                blockchain=SupportedBlockchain.ETHEREUM,
            ),
        ]
        entries_in_db_before_bad_put = db_addressbook.get_addressbook_entries(cursor)
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
            contained_in_msg='entry with address "0x9531C059098e3d194fF87FebB587aB07B30B1306"',
            status_code=HTTPStatus.CONFLICT,
        )
        assert db_addressbook.get_addressbook_entries(cursor) == entries_in_db_before_bad_put  # noqa: E501


@pytest.mark.parametrize('book_type', [AddressbookType.GLOBAL, AddressbookType.PRIVATE])
def test_update_addressbook(rotkehlchen_api_server, book_type: AddressbookType) -> None:
    generated_entries = make_addressbook_entries()
    db_addressbook = DBAddressbook(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    db_addressbook.add_addressbook_entries(book_type=book_type, entries=generated_entries)
    entries_to_update = [
        AddressbookEntry(
            address=to_checksum_address('0x9d904063e7e120302a13c6820561940538a2ad57'),
            name='NEW NAME WOW!',
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
        AddressbookEntry(
            address=to_checksum_address('0x368B9ad9B6AAaeFCE33b8c21781cfF375e09be67'),
            name='LoL kek',
            blockchain=SupportedBlockchain.ETHEREUM,
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
    expected_entries = entries_to_update + [generated_entries[2]]

    with db_addressbook.read_ctx(book_type) as cursor:
        assert db_addressbook.get_addressbook_entries(cursor) == expected_entries

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

        entries_in_db_before_bad_patch = db_addressbook.get_addressbook_entries(cursor)
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
            contained_in_msg='entry with address "0x79B598976bD83a47CD8B428C824C8474311267b8"',
            status_code=HTTPStatus.CONFLICT)
        assert db_addressbook.get_addressbook_entries(cursor) == entries_in_db_before_bad_patch  # noqa: E501


@pytest.mark.parametrize('book_type', [AddressbookType.GLOBAL, AddressbookType.PRIVATE])
def test_delete_addressbook(rotkehlchen_api_server, book_type: AddressbookType):
    generated_entries = make_addressbook_entries()
    db_addressbook = DBAddressbook(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    db_addressbook.add_addressbook_entries(book_type=book_type, entries=generated_entries)
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
        assert db_addressbook.get_addressbook_entries(cursor) == [generated_entries[1]]

        nonexistent_addresses = [
            to_checksum_address('0x368B9ad9B6AAaeFCE33b8c21781cfF375e09be67'),
            to_checksum_address('0x9d904063e7e120302a13c6820561940538a2ad57'),
        ]

        data_before_bad_request = db_addressbook.get_addressbook_entries(cursor)
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
            contained_in_msg='Addressbook entry with address "0x9D904063e7e120302a13C6820561940538a2Ad57" doesnt exist ',  # noqa: E501
            status_code=HTTPStatus.CONFLICT,
        )
        assert db_addressbook.get_addressbook_entries(cursor) == data_before_bad_request


def test_names_compilation(rotkehlchen_api_server):
    def names_request(addresses: list[str]):
        return requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'allnamesresource',
            ),
            json={
                'addresses': [{'address': address} for address in addresses],
            },
        )
    address_rotki = to_checksum_address('0x9531c059098e3d194ff87febb587ab07b30b1306')
    address_cody = to_checksum_address('0x368B9ad9B6AAaeFCE33b8c21781cfF375e09be67')
    address_rose = to_checksum_address('0xE07Af3FBEAf8584dc885f5bAA7c72419BDDf002D')
    address_tylor = to_checksum_address('0xC88eA7a5df3A7BA59C72393C5b2dc2CE260ff04D')
    address_nonlabel = to_checksum_address('0x9d904063e7e120302a13c6820561940538a2ad57')
    address_1world = to_checksum_address('0xfDBc1aDc26F0F8f8606a5d63b7D3a3CD21c22B23')
    address_firstblood = to_checksum_address('0xAf30D2a7E90d7DC361c8C4585e9BB7D2F6f15bc7')
    address_kraken10 = to_checksum_address('0xAe2D4617c862309A3d75A0fFB358c7a5009c673F')

    db_handler = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    db_ens = DBEns(db_handler=db_handler)
    db_addressbook = DBAddressbook(db_handler=db_handler)

    with db_handler.user_write() as cursor:
        db_ens.add_ens_mapping(
            write_cursor=cursor,
            address=address_rotki,
            name='rotki.eth',
            now=Timestamp(1),
        )
    publicly_known_addresses = [
        address_rotki,
        address_1world,
        address_kraken10,
        address_firstblood,
        # Below is an address that we don't know anything about
        to_checksum_address('0x42F47A289B1E17BCbbBc1630f112c036ed901f5d'),
    ]
    publicly_known_expected = {
        (address_kraken10, 'eth', 'Kraken 10'),
        (address_1world, 'eth', '1World'),
        (address_rotki, 'eth', 'rotki.eth'),
        (address_firstblood, 'eth', 'FirstBlood'),
    }
    response = names_request(publicly_known_addresses)
    result = assert_proper_response_with_result(response)
    assert {(*x,) for x in result} == publicly_known_expected

    db_addressbook.add_addressbook_entries(
        book_type=AddressbookType.GLOBAL,
        entries=[
            AddressbookEntry(
                name='Cody',
                address=address_cody,
                blockchain=SupportedBlockchain.ETHEREUM,
            ), AddressbookEntry(
                name='Rotki global db',
                address=address_rotki,
                blockchain=SupportedBlockchain.ETHEREUM,
            ),
        ],
    )
    global_addressbook_addresses = [
        address_cody,
        address_rotki,  # rotki.eth
    ]
    global_addressbook_expected = {
        (address_cody, 'eth', 'Cody'),
        (address_rotki, 'eth', 'Rotki global db'),
    }
    response = names_request(global_addressbook_addresses)
    result = assert_proper_response_with_result(response)
    assert {(*x,) for x in result} == global_addressbook_expected

    with db_handler.user_write() as cursor:
        db_handler.add_blockchain_accounts(
            cursor,
            account_data=[
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=address_tylor, label='Tylor'),  # noqa: E501
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=address_rotki, label='Rotki label'),  # noqa: E501
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=address_nonlabel),  # noqa: E501
            ],
        )
    labels_addresses = [
        address_tylor,
        address_nonlabel,  # address with None label
        address_rose,  # private addressbook
        address_cody,  # global addressbook
        address_rotki,  # rotki.eth
    ]
    labels_expected = {
        (address_tylor, 'eth', 'Tylor'),
        (address_cody, 'eth', 'Cody'),
        (address_rotki, 'eth', 'Rotki label'),
    }
    response = names_request(labels_addresses)
    result = assert_proper_response_with_result(response)
    assert {(*x,) for x in result} == labels_expected

    db_addressbook.add_addressbook_entries(
        book_type=AddressbookType.PRIVATE,
        entries=[
            AddressbookEntry(
                name='Rose',
                address=address_rose,
                blockchain=SupportedBlockchain.ETHEREUM,
            ), AddressbookEntry(
                name='Rotki private db',
                address=address_rotki,
                blockchain=SupportedBlockchain.ETHEREUM,
            ),
        ],
    )
    private_addressbook_addresses = [
        address_tylor,
        address_rose,
        address_cody,  # global addressbook
        address_rotki,  # rotki.eth
    ]
    private_addressbook_expected = {
        (address_tylor, 'eth', 'Tylor'),
        (address_rose, 'eth', 'Rose'),
        (address_cody, 'eth', 'Cody'),
        (address_rotki, 'eth', 'Rotki private db'),
    }
    response = names_request(private_addressbook_addresses)
    result = assert_proper_response_with_result(response)
    assert {(*x,) for x in result} == private_addressbook_expected
