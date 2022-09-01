import pytest

from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.chain.bitcoin.xpub import XpubData, XpubDerivedAddressData
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.utils import insert_tag_mappings
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import BlockchainAccountData, SupportedBlockchain
from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='setup_db_for_xpub_tests')
def fixture_setup_db_for_xpub_tests(data_dir, username, sql_vm_instructions_cb):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True)

    with data.db.user_write() as cursor:
        data.db.add_tag(cursor, 'public', 'foooo', 'ffffff', '000000')
        data.db.add_tag(cursor, 'desktop', 'boooo', 'ffffff', '000000')

        xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
        derivation_path = 'm/0/0/0'
        xpub_data1 = XpubData(
            xpub=HDKey.from_xpub(xpub=xpub, path='m'),
            blockchain=SupportedBlockchain.BITCOIN_CASH,
            derivation_path=derivation_path,
            label='xpub1',
            tags=['public', 'desktop'],
        )
        data.db.ensure_tags_exist(cursor, [xpub_data1], action='adding', data_type='bitcoin cash xpub')  # noqa: E501
        insert_tag_mappings(    # if we got tags add them to the xpub
            write_cursor=cursor,
            data=[xpub_data1],
            object_reference_keys=['xpub.xpub', 'derivation_path'],
        )

        data.db.add_bitcoin_xpub(cursor, xpub_data1)
        addr1 = '1LZypJUwJJRdfdndwvDmtAjrVYaHko136r'
        addr2 = '1MKSdDCtBSXiE49vik8xUG2pTgTGGh5pqe'
        addr3 = '12wxFzpjdymPk3xnHmdDLCTXUT9keY3XRd'
        addr4 = '16zNpyv8KxChtjXnE5nYcPqcXcrSQXX2JW'
        addr5 = '16zNpyv8KxChtjXnE5oYcPqcXcrSQXX2JJ'
        all_addresses = [addr1, addr2, addr3, addr4, addr5]
        account_data = [BlockchainAccountData(x) for x in [addr1, addr2, addr3, addr4, addr5]]
        data.db.add_blockchain_accounts(
            cursor,
            account_data=account_data,
            blockchain=xpub_data1.blockchain,
        )
        insert_tag_mappings(    # if we got tags add them to the existing addresses too
            write_cursor=cursor,
            data=account_data,
            object_reference_keys=['address'],
        )
        data.db.ensure_xpub_mappings_exist(
            cursor,
            xpub_data=xpub_data1,
            derived_addresses_data=[
                XpubDerivedAddressData(0, 0, addr1, ZERO),
                XpubDerivedAddressData(0, 1, addr2, ZERO),
                XpubDerivedAddressData(0, 5, addr5, ZERO),
            ],
        )

        xpub = 'zpub6quTRdxqWmerHdiWVKZdLMp9FY641F1F171gfT2RS4D1FyHnutwFSMiab58Nbsdu4fXBaFwpy5xyGnKZ8d6xn2j4r4yNmQ3Yp3yDDxQUo3q'  # noqa: E501
        derivation_path = 'm/0'
        xpub_data2 = XpubData(
            xpub=HDKey.from_xpub(xpub=xpub, path='m'),
            blockchain=SupportedBlockchain.BITCOIN,
            derivation_path=derivation_path,
        )
        data.db.add_bitcoin_xpub(cursor, xpub_data2)
        addr1 = 'bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5'
        addr2 = 'bc1qnus7355ecckmeyrmvv56mlm42lxvwa4wuq5aev'
        addr3 = 'bc1qup7f8g5k3h5uqzfjed03ztgn8hhe542w69wc0g'
        addr4 = 'bc1qr4r8vryfzexvhjrx5fh5uj0s2ead8awpqspqra'
        addr5 = 'bc1qr5r8vryfzexvhjrx5fh5uj0s2ead8awpqspalz'
        all_addresses.extend([addr1, addr2, addr3, addr4, addr5])
        data.db.add_blockchain_accounts(
            cursor,
            account_data=[BlockchainAccountData(x) for x in [addr1, addr2, addr3, addr4, addr5]],
            blockchain=xpub_data2.blockchain,
        )
        data.db.ensure_xpub_mappings_exist(
            cursor,
            xpub_data=xpub_data2,
            derived_addresses_data=[
                XpubDerivedAddressData(1, 0, addr1, ZERO),
                XpubDerivedAddressData(1, 1, addr2, ZERO),
                XpubDerivedAddressData(1, 2, addr3, ZERO),
                XpubDerivedAddressData(1, 3, addr4, ZERO),
                XpubDerivedAddressData(1, 7, addr5, ZERO),
            ],
        )

        # Finally also add the same xpub as xpub1 with no derivation path
        xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
        derivation_path = None
        xpub_data3 = XpubData(
            xpub=HDKey.from_xpub(xpub=xpub, path='m'),
            blockchain=SupportedBlockchain.BITCOIN,
            derivation_path=derivation_path,
        )
        data.db.add_bitcoin_xpub(cursor, xpub_data3)

    return data.db, xpub_data1, xpub_data2, xpub_data3, all_addresses


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


def test_edit_bitcoin_xpub(setup_db_for_xpub_tests):
    """Test that editing bitcoin xpub label and tags"""
    db, xpub, _, _, _ = setup_db_for_xpub_tests

    with db.user_write() as cursor:
        db.add_tag(cursor, 'test', description="test", background_color='000000', foreground_color='111111')  # noqa: E501
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

    assert result[0].xpub == xpub.xpub
    assert result[0].label == '123'
    assert result[0].derivation_path == xpub.derivation_path
    assert set(result[0].tags) == {'test'}


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
