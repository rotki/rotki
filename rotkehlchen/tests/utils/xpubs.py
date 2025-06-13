from typing import TYPE_CHECKING

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.chain.bitcoin.xpub import XpubData, XpubDerivedAddressData
from rotkehlchen.constants import ZERO
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.utils import insert_tag_mappings
from rotkehlchen.types import BTCAddress, HexColorCode, SupportedBlockchain
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from pathlib import Path


def setup_db_for_xpub_tests_impl(
        data_dir: 'Path',
        username: str,
        messages_aggregator: MessagesAggregator,
        sql_vm_instructions_cb: int,
        db_writer_port: int,
):
    """Setups a test database with xpub data"""
    data = DataHandler(
        data_directory=data_dir,
        msg_aggregator=messages_aggregator,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
        db_writer_port=db_writer_port,
    )
    data.unlock(username, '123', create_new=True, resume_from_backup=False)

    with data.db.user_write() as write_cursor:
        data.db.add_tag(write_cursor, 'public', 'foooo', HexColorCode('ffffff'), HexColorCode('000000'))  # noqa: E501
        data.db.add_tag(write_cursor, 'desktop', 'boooo', HexColorCode('ffffff'), HexColorCode('000000'))  # noqa: E501

        xpub = 'xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk'  # noqa: E501
        derivation_path = 'm/0/0/0'
        xpub_data1 = XpubData(
            xpub=HDKey.from_xpub(xpub=xpub, path='m'),
            blockchain=SupportedBlockchain.BITCOIN_CASH,
            derivation_path=derivation_path,
            label='xpub1',
            tags=['public', 'desktop'],
        )
    with data.db.conn.read_ctx() as cursor:
        data.db.ensure_tags_exist(cursor, [xpub_data1], action='adding', data_type='bitcoin cash xpub')  # noqa: E501

    with data.db.user_write() as write_cursor:
        insert_tag_mappings(    # if we got tags add them to the xpub
            write_cursor=write_cursor,
            data=[xpub_data1],
            object_reference_keys=['xpub.xpub', 'derivation_path'],
        )

        data.db.add_bitcoin_xpub(write_cursor, xpub_data1)
        addr1 = BTCAddress('1LZypJUwJJRdfdndwvDmtAjrVYaHko136r')
        addr2 = BTCAddress('1MKSdDCtBSXiE49vik8xUG2pTgTGGh5pqe')
        addr3 = BTCAddress('12wxFzpjdymPk3xnHmdDLCTXUT9keY3XRd')
        addr4 = BTCAddress('16zNpyv8KxChtjXnE5nYcPqcXcrSQXX2JW')
        addr5 = BTCAddress('16zNpyv8KxChtjXnE5oYcPqcXcrSQXX2JJ')
        all_addresses = [addr1, addr2, addr3, addr4, addr5]
        account_data = [BlockchainAccountData(chain=xpub_data1.blockchain, address=x) for x in [addr1, addr2, addr3, addr4, addr5]]  # noqa: E501
        data.db.add_blockchain_accounts(
            write_cursor,
            account_data=account_data,
        )
        insert_tag_mappings(    # if we got tags add them to the existing addresses too
            write_cursor=write_cursor,
            data=account_data,
            object_reference_keys=['address'],
        )
        data.db.ensure_xpub_mappings_exist(
            write_cursor,
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
        data.db.add_bitcoin_xpub(write_cursor, xpub_data2)
        addr1 = BTCAddress('bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5')
        addr2 = BTCAddress('bc1qnus7355ecckmeyrmvv56mlm42lxvwa4wuq5aev')
        addr3 = BTCAddress('bc1qup7f8g5k3h5uqzfjed03ztgn8hhe542w69wc0g')
        addr4 = BTCAddress('bc1qr4r8vryfzexvhjrx5fh5uj0s2ead8awpqspqra')
        addr5 = BTCAddress('bc1qr5r8vryfzexvhjrx5fh5uj0s2ead8awpqspalz')
        all_addresses.extend([addr1, addr2, addr3, addr4, addr5])
        data.db.add_blockchain_accounts(
            write_cursor,
            account_data=[
                BlockchainAccountData(chain=xpub_data2.blockchain, address=x)
                for x in [addr1, addr2, addr3, addr4, addr5]],
        )
        data.db.ensure_xpub_mappings_exist(
            write_cursor,
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
        xpub_data3 = XpubData(
            xpub=HDKey.from_xpub(xpub=xpub, path='m'),
            blockchain=SupportedBlockchain.BITCOIN,
            derivation_path=None,
        )
        data.db.add_bitcoin_xpub(write_cursor, xpub_data3)

    return data.db, xpub_data1, xpub_data2, xpub_data3, all_addresses
