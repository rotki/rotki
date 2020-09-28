import pytest

from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.typing import BlockchainAccountData, SupportedBlockchain
from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture
def setup_db_for_xpub_tests(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
    derivation_path = 'm'
    xpub_data1 = XpubData(xpub=HDKey.from_xpub(xpub=xpub), derivation_path=derivation_path)
    data.db.add_bitcoin_xpub(xpub_data1)
    addr1 = '1LZypJUwJJRdfdndwvDmtAjrVYaHko136r'
    addr2 = '1MKSdDCtBSXiE49vik8xUG2pTgTGGh5pqe'
    addr3 = '12wxFzpjdymPk3xnHmdDLCTXUT9keY3XRd'
    addr4 = '16zNpyv8KxChtjXnE5nYcPqcXcrSQXX2JW'
    all_addresses = [addr1, addr2, addr3, addr4]
    data.db.add_blockchain_accounts(
        blockchain=SupportedBlockchain.BITCOIN,
        account_data=[BlockchainAccountData(x) for x in [addr1, addr2, addr3, addr4]],
    )
    data.db.ensure_xpub_mappings_exist(
        xpub=xpub,
        derivation_path=derivation_path,
        derived_addresses_data=[(0, addr1), (1, addr2)],
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
        derived_addresses_data=[(0, addr1), (1, addr2), (2, addr3), (3, addr4)],
    )

    xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
    derivation_path = 'm/44/0/0'
    xpub_data3 = XpubData(xpub=HDKey.from_xpub(xpub=xpub), derivation_path=derivation_path)
    data.db.add_bitcoin_xpub(xpub_data3)

    return data.db, xpub_data1, xpub_data2, xpub_data3, all_addresses


def test_get_last_xpub_derived_index(setup_db_for_xpub_tests):
    db, xpub1, xpub2, xpub3, _ = setup_db_for_xpub_tests
    # Get index from xpubs existing in the DB that have derived addresses
    assert db.get_last_xpub_derived_index(xpub1) == 1
    assert db.get_last_xpub_derived_index(xpub2) == 3
    # Get index from xpubs existing in the DB that have no derived addresses
    assert db.get_last_xpub_derived_index(xpub3) == 0
    # Get index from unknown xpub (not in DB)
    xpub = 'xpub6D1ZRhLSRWWGowFT22WJYYJx3GH5wxidsHcEm6NYeXfMAGxKWiQ5dQ8hSz7gdJsE86Lrjf1MN7SCKowZU8VxZ45Z1KeNP5CZ514JbCamRdC'  # noqa: E501
    derivation_path = 'm/0/0/0'
    xpub_data = XpubData(xpub=HDKey.from_xpub(xpub=xpub), derivation_path=derivation_path)
    assert db.get_last_xpub_derived_index(xpub_data) == 0


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
