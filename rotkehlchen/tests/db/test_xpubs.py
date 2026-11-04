import pytest

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.bitcoin.hdkey import HDKey, XpubType
from rotkehlchen.chain.bitcoin.xpub import XpubData, XpubDerivedAddressData
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import SupportedBlockchain


def test_get_last_consecutive_xpub_derived_indices(setup_db_for_xpub_tests):
    db, xpub1, xpub2, xpub3, _ = setup_db_for_xpub_tests
    with db.conn.read_ctx() as cursor:
        receiving_idx, change_idx = db.get_last_consecutive_xpub_derived_indices(cursor, xpub1)
        assert receiving_idx == 1
        assert change_idx == 0
        receiving_idx, change_idx = db.get_last_consecutive_xpub_derived_indices(cursor, xpub2)
        assert receiving_idx == 0
        assert change_idx == 3
        receiving_idx, change_idx = db.get_last_consecutive_xpub_derived_indices(cursor, xpub3)
        assert receiving_idx == 0
        assert change_idx == 0
    db.logout()


def test_get_addresses_to_xpub_mapping(setup_db_for_xpub_tests):
    db, xpub1, xpub2, _, all_addresses = setup_db_for_xpub_tests
    # Also add a non-existing address in there for fun
    all_addresses.append('18ddjB7HWTVxzvTbLp1nWvaBxU3U2oTZF2')
    with db.conn.read_ctx() as cursor:
        result_bch = db.get_addresses_to_xpub_mapping(
            cursor=cursor,
            blockchain=SupportedBlockchain.BITCOIN_CASH,
            addresses=all_addresses,
        )
        result_btc = db.get_addresses_to_xpub_mapping(
            cursor=cursor,
            blockchain=SupportedBlockchain.BITCOIN,
            addresses=all_addresses,
        )
    assert len(result_bch) == 3
    assert len(result_btc) == 5
    for x in all_addresses[:2]:
        assert result_bch[x].xpub.xpub == xpub1.xpub.xpub
        assert result_bch[x].derivation_path == xpub1.derivation_path

    x = all_addresses[4]
    assert result_bch[x].xpub.xpub == xpub1.xpub.xpub
    assert result_bch[x].derivation_path == xpub1.derivation_path

    for x in all_addresses[5:10]:
        assert result_btc[x].xpub.xpub == xpub2.xpub.xpub
        assert result_btc[x].derivation_path == xpub2.derivation_path
    db.logout()


def test_delete_bitcoin_xpub(setup_db_for_xpub_tests):
    """Test that bitcoin xpub deletion works fine and that also tag mappings are gone"""
    db, xpub1, xpub2, _, all_addresses = setup_db_for_xpub_tests
    # Also add a non-existing address in there for fun
    all_addresses.append('18ddjB7HWTVxzvTbLp1nWvaBxU3U2oTZF2')
    with db.user_write() as cursor:
        db.delete_bitcoin_xpub(cursor, xpub1)  # xpub1 is a bch xpub
        result_bch = db.get_addresses_to_xpub_mapping(
            cursor=cursor,
            blockchain=SupportedBlockchain.BITCOIN_CASH,
            addresses=all_addresses,
        )
        result_btc = db.get_addresses_to_xpub_mapping(
            cursor=cursor,
            blockchain=SupportedBlockchain.BITCOIN,
            addresses=all_addresses,
        )
        assert len(result_bch) == 0
        assert len(result_btc) == 5

        for x in all_addresses[5:10]:
            assert result_btc[x].xpub.xpub == xpub2.xpub.xpub
            assert result_btc[x].derivation_path == xpub2.derivation_path

        cursor.execute('SELECT * from tag_mappings;')
        assert len(cursor.fetchall()) == 0
    db.logout()


def test_get_bitcoin_xpub_data(setup_db_for_xpub_tests):
    """Test that retrieving bitcoin xpub data also returns all properly mapped tags"""
    db, xpub1, xpub2, xpub3, _ = setup_db_for_xpub_tests
    with db.conn.read_ctx() as cursor:
        result1 = db.get_bitcoin_xpub_data(cursor, SupportedBlockchain.BITCOIN_CASH)
        result2 = db.get_bitcoin_xpub_data(cursor, SupportedBlockchain.BITCOIN)
    assert len(result1) == 1
    assert len(result2) == 2

    assert result2[0] == xpub3
    assert result2[1] == xpub2

    # Equality won't work due to undefined order of tags list. Check each attribute
    assert result1[0].xpub == xpub1.xpub
    assert result1[0].label == xpub1.label
    assert result1[0].derivation_path == xpub1.derivation_path
    assert set(result1[0].tags) == set(xpub1.tags)
    db.logout()


def test_edit_bitcoin_xpub(setup_db_for_xpub_tests):
    """Test that editing bitcoin xpub label and tags"""
    db, xpub, _, _, _ = setup_db_for_xpub_tests

    with db.user_write() as cursor:
        db.add_tag(cursor, 'test', description='test', background_color='000000', foreground_color='111111')  # noqa: E501
        db.edit_bitcoin_xpub(
            cursor,
            XpubData(
                xpub=xpub.xpub,
                blockchain=SupportedBlockchain.BITCOIN_CASH,
                derivation_path=xpub.derivation_path,
                label='123',
                tags=['test'],
            ))
        result = db.get_bitcoin_xpub_data(cursor, blockchain=SupportedBlockchain.BITCOIN_CASH)

        # Make sure that the tags of the derived addresses were updated
        cursor.execute(
            'SELECT B.tag_name FROM xpub_mappings as A LEFT JOIN tag_mappings as B '
            'ON B.object_reference=A.address WHERE xpub=? AND blockchain=?',
            (xpub.xpub.xpub, SupportedBlockchain.BITCOIN_CASH.value),
        )
        found_tags = [entry[0] for entry in cursor]
        assert len(found_tags) == 3
        assert found_tags == ['test', 'test', 'test']

    assert result[0].xpub == xpub.xpub
    assert result[0].label == '123'
    assert result[0].derivation_path == xpub.derivation_path
    assert set(result[0].tags) == {'test'}
    db.logout()


def test_edit_bitcoin_xpub_not_existing_tag(setup_db_for_xpub_tests):
    """Test that edits bitcoin xpub label and tries to add non existing tag"""
    db, xpub, _, _, _ = setup_db_for_xpub_tests

    with db.user_write() as cursor:
        with pytest.raises(InputError):
            db.edit_bitcoin_xpub(
                cursor,
                XpubData(
                    xpub=xpub.xpub,
                    blockchain=SupportedBlockchain.BITCOIN_CASH,
                    derivation_path=xpub.derivation_path,
                    label='123',
                    tags=['test'],
                ),
            )
        result = db.get_bitcoin_xpub_data(cursor, SupportedBlockchain.BITCOIN_CASH)

    assert result[0].xpub == xpub.xpub
    assert result[0].label == xpub.label
    assert result[0].derivation_path == xpub.derivation_path
    assert result[0].tags != {'test'}
    db.logout()


@pytest.mark.parametrize('xpub_type', [None, *XpubType])
def test_saved_xpub_keeps_its_type(setup_db_for_xpub_tests, xpub_type):
    """An xpub loaded from the DB derives the same addresses as when it was added. A taproot
    xpub has the same prefix as a legacy one, so only its saved type tells them apart."""
    db, _, _, _, _ = setup_db_for_xpub_tests
    # account xpub of the BIP-86 test vectors, at m/86'/0'/0'
    xpub_data = XpubData(
        xpub=HDKey.from_xpub(
            xpub='xpub6BgBgsespWvERF3LHQu6CnqdvfEvtMcQjYrcRzx53QJjSxarj2afYWcLteoGVky7D3UKDP9QyrLprQ3VCECoY49yfdDEHGCtMMj92pReUsQ',
            xpub_type=xpub_type,
            path='m',
        ),
        blockchain=SupportedBlockchain.BITCOIN,
    )
    expected_address = xpub_data.xpub.derive_child(1).derive_child(0).address()
    if xpub_type == XpubType.P2TR:
        assert expected_address == 'bc1p3qkhfews2uk44qtvauqyr2ttdsw7svhkl9nkm9s9c3x4ax5h60wqwruhk7'

    with db.user_write() as write_cursor:
        db.add_bitcoin_xpub(write_cursor, xpub_data)
        db.add_blockchain_accounts(write_cursor, [BlockchainAccountData(
            chain=SupportedBlockchain.BITCOIN,
            address=expected_address,
        )])
        db.ensure_xpub_mappings_exist(
            write_cursor=write_cursor,
            xpub_data=xpub_data,
            derived_addresses_data=[XpubDerivedAddressData(1, 0, expected_address, ZERO)],
        )

    with db.conn.read_ctx() as cursor:
        saved_xpubs = [
            x for x in db.get_bitcoin_xpub_data(cursor, SupportedBlockchain.BITCOIN)
            if x == xpub_data
        ]
        mapped_xpub = db.get_addresses_to_xpub_mapping(
            cursor=cursor,
            blockchain=SupportedBlockchain.BITCOIN,
            addresses=[expected_address],
        )[expected_address]

    assert len(saved_xpubs) == 1
    for loaded in (saved_xpubs[0].xpub, mapped_xpub.xpub):
        assert loaded.xpub_type == xpub_type
        assert loaded.derive_child(1).derive_child(0).address() == expected_address
    db.logout()
