from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.chain.bitcoin.xpub import XpubData, XpubDerivedAddressData
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.utils import insert_tag_mappings
from rotkehlchen.types import BlockchainAccountData, SupportedBlockchain
from rotkehlchen.user_messages import MessagesAggregator


def setup_db_for_xpub_tests_impl(data_dir, username, sql_vm_instructions_cb):
    """Setups a test database with xpub data"""
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
