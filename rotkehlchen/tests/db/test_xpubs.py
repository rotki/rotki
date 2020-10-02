import pytest

from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.chain.bitcoin.xpub import XpubData, XpubDerivedAddressData
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.utils import insert_tag_mappings
from rotkehlchen.typing import BlockchainAccountData, SupportedBlockchain
from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture
def setup_db_for_xpub_tests(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    data.db.add_tag('public', 'foooo', 'ffffff', '000000')
    data.db.add_tag('desktop', 'boooo', 'ffffff', '000000')

    xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
    derivation_path = 'm/0/0/0'
    xpub_data1 = XpubData(
        xpub=HDKey.from_xpub(xpub=xpub),
        derivation_path=derivation_path,
        label='xpub1',
        tags=['public', 'desktop'],
    )
    data.db.ensure_tags_exist([xpub_data1], action='adding', data_type='bitcoin_xpub')
    insert_tag_mappings(    # if we got tags add them to the xpub
        cursor=data.db.conn.cursor(),
        data=[xpub_data1],
        object_reference_keys=['xpub.xpub', 'derivation_path'],
    )

    data.db.add_bitcoin_xpub(xpub_data1)
    addr1 = '1LZypJUwJJRdfdndwvDmtAjrVYaHko136r'
    addr2 = '1MKSdDCtBSXiE49vik8xUG2pTgTGGh5pqe'
    addr3 = '12wxFzpjdymPk3xnHmdDLCTXUT9keY3XRd'
    addr4 = '16zNpyv8KxChtjXnE5nYcPqcXcrSQXX2JW'
    all_addresses = [addr1, addr2, addr3, addr4]
    account_data = [BlockchainAccountData(x) for x in [addr1, addr2, addr3, addr4]]
    data.db.add_blockchain_accounts(
        blockchain=SupportedBlockchain.BITCOIN,
        account_data=account_data,
    )
    insert_tag_mappings(    # if we got tags add them to the existing addresses too
        cursor=data.db.conn.cursor(),
        data=account_data,
        object_reference_keys=['address'],
    )
    data.db.ensure_xpub_mappings_exist(
        xpub=xpub,
        derivation_path=derivation_path,
        derived_addresses_data=[
            XpubDerivedAddressData(0, 0, addr1, ZERO),
            XpubDerivedAddressData(0, 1, addr2, ZERO),
        ],
    )

    xpub = 'zpub6quTRdxqWmerHdiWVKZdLMp9FY641F1F171gfT2RS4D1FyHnutwFSMiab58Nbsdu4fXBaFwpy5xyGnKZ8d6xn2j4r4yNmQ3Yp3yDDxQUo3q'  # noqa: E501
    derivation_path = 'm/0'
    xpub_data2 = XpubData(xpub=HDKey.from_xpub(xpub=xpub), derivation_path=derivation_path)
    data.db.add_bitcoin_xpub(xpub_data2)
    addr1 = 'bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5'
    addr2 = 'bc1qnus7355ecckmeyrmvv56mlm42lxvwa4wuq5aev'
    addr3 = 'bc1qup7f8g5k3h5uqzfjed03ztgn8hhe542w69wc0g'
    addr4 = 'bc1qr4r8vryfzexvhjrx5fh5uj0s2ead8awpqspqra'
    all_addresses.extend([addr1, addr2, addr3, addr4])
    data.db.add_blockchain_accounts(
        blockchain=SupportedBlockchain.BITCOIN,
        account_data=[BlockchainAccountData(x) for x in [addr1, addr2, addr3, addr4]],
    )
    data.db.ensure_xpub_mappings_exist(
        xpub=xpub,
        derivation_path=derivation_path,
        derived_addresses_data=[
            XpubDerivedAddressData(1, 0, addr1, ZERO),
            XpubDerivedAddressData(1, 1, addr2, ZERO),
            XpubDerivedAddressData(1, 2, addr3, ZERO),
            XpubDerivedAddressData(1, 3, addr4, ZERO),
        ],
    )

    # Finally also add the same xpub as xpub1 with no derivation path
    xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
    derivation_path = None
    xpub_data3 = XpubData(xpub=HDKey.from_xpub(xpub=xpub), derivation_path=derivation_path)
    data.db.add_bitcoin_xpub(xpub_data3)

    return data.db, xpub_data1, xpub_data2, xpub_data3, all_addresses


def test_get_last_xpub_derived_indices(setup_db_for_xpub_tests):
    db, xpub1, xpub2, xpub3, _ = setup_db_for_xpub_tests
    # Get index from xpubs existing in the DB that have derived addresses
    receiving_idx, change_idx = db.get_last_xpub_derived_indices(xpub1)
    assert receiving_idx == 1
    assert change_idx == 0
    receiving_idx, change_idx = db.get_last_xpub_derived_indices(xpub2)
    assert receiving_idx == 0
    assert change_idx == 3
    # Get index from xpubs existing in the DB that have no derived addresses
    receiving_idx, change_idx = db.get_last_xpub_derived_indices(xpub3)
    assert receiving_idx == change_idx == 0
    # Get index from unknown xpub (not in DB)
    xpub = 'xpub6D1ZRhLSRWWGowFT22WJYYJx3GH5wxidsHcEm6NYeXfMAGxKWiQ5dQ8hSz7gdJsE86Lrjf1MN7SCKowZU8VxZ45Z1KeNP5CZ514JbCamRdC'  # noqa: E501
    derivation_path = 'm/0/0/0'
    xpub_data = XpubData(xpub=HDKey.from_xpub(xpub=xpub), derivation_path=derivation_path)
    receiving_idx, change_idx = db.get_last_xpub_derived_indices(xpub_data)
    assert receiving_idx == change_idx == 0


def test_get_addresses_to_xpub_mapping(setup_db_for_xpub_tests):
    db, xpub1, xpub2, _, all_addresses = setup_db_for_xpub_tests
    # Also add a non-existing address in there for fun
    all_addresses.append('18ddjB7HWTVxzvTbLp1nWvaBxU3U2oTZF2')
    result = db.get_addresses_to_xpub_mapping(all_addresses)
    assert len(result) == 6
    for x in all_addresses[:2]:
        assert result[x].xpub.xpub == xpub1.xpub.xpub
        assert result[x].derivation_path == xpub1.derivation_path

    for x in all_addresses[4:8]:
        assert result[x].xpub.xpub == xpub2.xpub.xpub
        assert result[x].derivation_path == xpub2.derivation_path


def test_delete_bitcoin_xpub(setup_db_for_xpub_tests):
    """Test that bitcoin xpub deletion works fine and that also tag mappings are gone"""
    db, xpub1, xpub2, _, all_addresses = setup_db_for_xpub_tests
    # Also add a non-existing address in there for fun
    all_addresses.append('18ddjB7HWTVxzvTbLp1nWvaBxU3U2oTZF2')
    db.delete_bitcoin_xpub(xpub1)

    result = db.get_addresses_to_xpub_mapping(all_addresses)
    assert len(result) == 4
    for x in all_addresses[4:8]:
        assert result[x].xpub.xpub == xpub2.xpub.xpub
        assert result[x].derivation_path == xpub2.derivation_path

    cursor = db.conn.cursor()
    result = cursor.execute('SELECT * from tag_mappings;')
    assert len(result.fetchall()) == 0


def test_get_bitcoin_xpub_data(setup_db_for_xpub_tests):
    """Test that retrieving bitcoin xpub data also returns all properly mapped tags"""
    db, xpub1, xpub2, xpub3, all_addresses = setup_db_for_xpub_tests
    # Also add a non-existing address in there for fun
    all_addresses.append('18ddjB7HWTVxzvTbLp1nWvaBxU3U2oTZF2')
    result = db.get_bitcoin_xpub_data()
    assert len(result) == 3

    assert result[0] == xpub3
    assert result[2] == xpub2

    # Equality won't work due to undefined order of tags list. Check each attribute
    assert result[1].xpub == xpub1.xpub
    assert result[1].label == xpub1.label
    assert result[1].derivation_path == xpub1.derivation_path
    assert set(result[1].tags) == set(xpub1.tags)
