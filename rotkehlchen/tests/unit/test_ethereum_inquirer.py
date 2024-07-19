from unittest.mock import patch

import pytest

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.constants import ETHEREUM_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.kyber.constants import KYBER_AGGREGATOR_SWAPPED
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.errors.misc import EventNotInABI, RemoteError
from rotkehlchen.tests.utils.checks import assert_serialized_dicts_equal
from rotkehlchen.tests.utils.ethereum import (
    ETHEREUM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED,
    ETHEREUM_NODES_SET_WITH_PRUNED_AND_NOT_ARCHIVED,
    ETHEREUM_TEST_PARAMETERS,
    ETHEREUM_WEB3_AND_ETHERSCAN_TEST_PARAMETERS,
    INFURA_ETH_NODE,
    wait_until_all_nodes_connected,
)
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import ChainID, EvmTransaction, SupportedBlockchain, deserialize_evm_tx_hash
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_block_by_number(ethereum_inquirer, call_order, ethereum_manager_connect_at_start):
    wait_until_all_nodes_connected(
        connect_at_start=ethereum_manager_connect_at_start,
        evm_inquirer=ethereum_inquirer,
    )
    block = ethereum_inquirer.get_block_by_number(10304885, call_order=call_order)
    assert block['timestamp'] == 1592686213
    assert block['number'] == 10304885
    assert block['hash'] == '0xe2217ba1639c6ca2183f40b0f800185b3901faece2462854b3162d4c5077752c'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize(*ETHEREUM_WEB3_AND_ETHERSCAN_TEST_PARAMETERS)
def test_get_transaction_receipt(
        ethereum_inquirer,
        ethereum_manager_connect_at_start,
        database,
):
    wait_until_all_nodes_connected(
        connect_at_start=ethereum_manager_connect_at_start,
        evm_inquirer=ethereum_inquirer,
    )
    tx_hash = deserialize_evm_tx_hash('0x12d474b6cbba04fd1a14e55ef45b1eb175985612244631b4b70450c888962a89')  # noqa: E501
    result = ethereum_inquirer.get_transaction_receipt(tx_hash)
    block_hash = '0x6f3a7838a8788c3371b88df170c3643d19bad896c915a7368681292882b6ad61'
    assert result['blockHash'] == block_hash
    assert len(result['logs']) == 2
    assert result['gasUsed'] == 144046
    assert result['blockNumber'] == 10840714
    assert result['logs'][0]['blockNumber'] == 10840714
    assert result['logs'][1]['blockNumber'] == 10840714
    assert result['status'] == 1
    assert result['transactionIndex'] == 110
    assert result['logs'][0]['transactionIndex'] == 110
    assert result['logs'][1]['transactionIndex'] == 110
    assert result['logs'][0]['logIndex'] == 235
    assert result['logs'][1]['logIndex'] == 236

    from_addy = make_evm_address()
    to_addy = make_evm_address()
    db = DBEvmTx(database)
    with database.user_write() as cursor:
        database.add_blockchain_accounts(
            cursor,
            account_data=[
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=from_addy),
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=to_addy),
            ],
        )
        db.add_evm_transactions(
            cursor,
            [EvmTransaction(  # need to add the tx first
                tx_hash=tx_hash,
                chain_id=ChainID.ETHEREUM,
                timestamp=1,  # all other fields don't matter for this test
                block_number=1,
                from_address=from_addy,
                to_address=to_addy,
                value=1,
                gas=1,
                gas_price=1,
                gas_used=1,
                input_data=b'',
                nonce=1,
            )],
            relevant_address=from_addy,
        )

        # also test receipt can be stored and retrieved from the DB.
        # This tests that all node types (say openethereum) are processed properly
        db.add_or_ignore_receipt_data(cursor, ChainID.ETHEREUM, result)
        receipt = db.get_receipt(cursor, tx_hash, ChainID.ETHEREUM)

    assert receipt == EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=235,
                data=b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02T\x0b\xe4\x00',
                address='0x5bEaBAEBB3146685Dd74176f68a0721F91297D37',
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00s(*c\xf0\xe3\xd7\xe9`EuB\x0fwsa\xec\xa3\xc8j',
                    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb6 \xf1\x93ME\x84\xdd\xa6\x99\x9e\xdc\xad\xd3)\x81)dj\xa5',  # noqa: E501
                ]), EvmTxReceiptLog(
                    log_index=236,
                    data=b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb6 \xf1\x93ME\x84\xdd\xa6\x99\x9e\xdc\xad\xd3)\x81)dj\xa5\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb6 \xf1\x93ME\x84\xdd\xa6\x99\x9e\xdc\xad\xd3)\x81)dj\xa5\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00[\xea\xba\xeb\xb3\x14f\x85\xddt\x17oh\xa0r\x1f\x91)}7\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02T\x0b\xe4\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\r\xe0\xb6\xb3\xa7d\x00\x00',  # noqa: E501
                    address='0x73282A63F0e3D7e9604575420F777361ecA3C86A',
                    topics=[KYBER_AGGREGATOR_SWAPPED],
            ),
        ])


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_transaction_by_hash(ethereum_inquirer, call_order, ethereum_manager_connect_at_start):
    wait_until_all_nodes_connected(
        connect_at_start=ethereum_manager_connect_at_start,
        evm_inquirer=ethereum_inquirer,
    )
    result, _ = ethereum_inquirer.get_transaction_by_hash(
        hexstring_to_bytes('0x5b180e3dcc19cd29c918b98c876f19393e07b74c07fd728102eb6241db3c2d5c'),
        call_order=call_order,
    )
    expected_tx = EvmTransaction(
        tx_hash=deserialize_evm_tx_hash(b'[\x18\x0e=\xcc\x19\xcd)\xc9\x18\xb9\x8c\x87o\x199>\x07\xb7L\x07\xfdr\x81\x02\xebbA\xdb<-\\'),
        chain_id=ChainID.ETHEREUM,
        timestamp=1633128954,
        block_number=13336285,
        from_address='0x2F6789A208A05C762cA8d142A3df95d29C18b065',
        to_address='0x7Be8076f4EA4A4AD08075C2508e481d6C946D12b',
        value=33000000000000000,
        gas=294144,
        gas_price=66936353558,
        gas_used=218523,
        input_data=b"\xab\x83K\xab\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00{\xe8\x07oN\xa4\xa4\xad\x08\x07\\%\x08\xe4\x81\xd6\xc9F\xd1+\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00/g\x89\xa2\x08\xa0\\v,\xa8\xd1B\xa3\xdf\x95\xd2\x9c\x18\xb0e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00p\x8d\xfa\x06\xdfX\x9a\x1e\x19W9\x1b\x86.\x02\xf7\x17X$\xe9\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00I_\x94rvt\x9c\xe6F\xf6\x8a\xc8\xc2HB\x00E\xcb{^\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00{\xe8\x07oN\xa4\xa4\xad\x08\x07\\%\x08\xe4\x81\xd6\xc9F\xd1+\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00p\x8d\xfa\x06\xdfX\x9a\x1e\x19W9\x1b\x86.\x02\xf7\x17X$\xe9\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00[2V\x96^|<\xf2n\x11\xfc\xaf)m\xfc\x88\x07\xc0\x10s\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00I_\x94rvt\x9c\xe6F\xf6\x8a\xc8\xc2HB\x00E\xcb{^\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\xe2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00u=S=\x96\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00aW\x91\x84\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00C\x96\x18\xf8\xa6p,\x86\xbd?\xcf\x83\x8c3\xd3 \x89\x9f1\xffaX\x1a\r|\xa0\xcb\x12\xad\xbeY\xe9\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\xe2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00u=S=\x96\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00aU\xa9E\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00bDI$\x9d\xc420bKZ\xb5v\x96\xf6\xef\xa0hg\x993\x00\x07y\x07]\x83\xc6\xd2I\x1c\x87\x19\x13\x1e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\n\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\n\xc0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1c\x02\xe0\x9f\xaa\xce\x1aZ\xaf\\'\xb7&\x99l\x10\xe7u4\x11\xc6V\x17\xb3\xb5)z\xd5\x04/7\xd8\x04\x07y\xb1\xa8\xfe\x0c\x1c\xa5\xc9\xc4{e\x07\xa2:\xee\x0f\xb3&\xcf_3[{\xcc\x13]~o\xe9\xd1\xd8\x02\xe0\x9f\xaa\xce\x1aZ\xaf\\'\xb7&\x99l\x10\xe7u4\x11\xc6V\x17\xb3\xb5)z\xd5\x04/7\xd8\x04\x07y\xb1\xa8\xfe\x0c\x1c\xa5\xc9\xc4{e\x07\xa2:\xee\x0f\xb3&\xcf_3[{\xcc\x13]~o\xe9\xd1\xd8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc4\xf2BC*\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00/g\x89\xa2\x08\xa0\\v,\xa8\xd1B\xa3\xdf\x95\xd2\x9c\x18\xb0ep\x8d\xfa\x06\xdfX\x9a\x1e\x19W9\x1b\x86.\x02\xf7\x17X$\xe9\x00\x00\x00\x00\x00\x00\xac\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc4\xf2BC*\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00p\x8d\xfa\x06\xdfX\x9a\x1e\x19W9\x1b\x86.\x02\xf7\x17X$\xe9\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00p\x8d\xfa\x06\xdfX\x9a\x1e\x19W9\x1b\x86.\x02\xf7\x17X$\xe9\x00\x00\x00\x00\x00\x00\xac\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc4\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc4\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",  # noqa: E501
        nonce=204,
    )
    assert result == expected_tx


@pytest.mark.parametrize('ethereum_manager_connect_at_start', ['DEFAULT'])
def test_use_open_nodes(ethereum_inquirer, database):
    """Test that we can connect to and use the open nodes (except from etherscan)

    Note: If this fails with transaction not found probably open nodes started pruning.
    Change test to use a more recent transaction.
    """
    # Wait until all nodes are connected
    rpc_nodes_all = database.get_rpc_nodes(blockchain=SupportedBlockchain.ETHEREUM, only_active=True)  # noqa: E501
    rpc_nodes = [node for node in rpc_nodes_all if node.node_info.name != ETHEREUM_ETHERSCAN_NODE_NAME]  # noqa: E501
    ethereum_inquirer.connect_to_multiple_nodes(rpc_nodes)
    wait_until_all_nodes_connected(
        connect_at_start=rpc_nodes,
        evm_inquirer=ethereum_inquirer,
    )
    result = ethereum_inquirer.get_transaction_receipt(
        '0x76dbd4fd8769af995b3597733ff6bf5daca619cb55a9d7347d8e3ab949ac5984',
        call_order=rpc_nodes,
    )
    block_hash = '0xfd7d2542ce9804f3fc4df304bc6ec259db3934d8e75b4f9228c5395e3083cc47'
    assert result['blockHash'] == block_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize(*ETHEREUM_WEB3_AND_ETHERSCAN_TEST_PARAMETERS)
def test_call_contract(ethereum_inquirer, ethereum_manager_connect_at_start):
    wait_until_all_nodes_connected(
        connect_at_start=ethereum_manager_connect_at_start,
        evm_inquirer=ethereum_inquirer,
    )
    yearn_ycrv_vault = ethereum_inquirer.contracts.contract(string_to_evm_address('0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c'))  # noqa: E501
    result = ethereum_inquirer.call_contract(
        contract_address=yearn_ycrv_vault.address,
        abi=yearn_ycrv_vault.abi,
        method_name='symbol',
    )
    assert result == 'yyDAI+yUSDC+yUSDT+yTUSD'
    # also test that doing contract.call() has the same result
    result2 = yearn_ycrv_vault.call(ethereum_inquirer, 'symbol')
    assert result == result2
    result = ethereum_inquirer.call_contract(
        contract_address=yearn_ycrv_vault.address,
        abi=yearn_ycrv_vault.abi,
        method_name='balanceOf',
        arguments=['0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c'],
    )
    assert result >= 0


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_logs(ethereum_inquirer, call_order, ethereum_manager_connect_at_start):
    wait_until_all_nodes_connected(
        connect_at_start=ethereum_manager_connect_at_start,
        evm_inquirer=ethereum_inquirer,
    )
    yearn_ycrv_vault = ethereum_inquirer.contracts.contract(string_to_evm_address('0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c'))  # noqa: E501
    argument_filters = {
        'from': '0x7780E86699e941254c8f4D9b7eB08FF7e96BBE10',
        'to': yearn_ycrv_vault.address,
    }
    events = ethereum_inquirer.get_logs(
        contract_address='0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8',
        abi=ethereum_inquirer.contracts.abi('ERC20_TOKEN'),
        event_name='Transfer',
        argument_filters=argument_filters,
        from_block=10712531,
        to_block=10712753,
        call_order=call_order,
    )
    assert len(events) == 1
    expected_event = {
        'address': '0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8',
        'blockNumber': 10712731,
        'data': '0x0000000000000000000000000000000000000000000001e3f60028423cff0000',
        'gasPrice': 72000000000,
        'gasUsed': 93339,
        'logIndex': 157,
        'topics': [
            '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef',
            '0x0000000000000000000000007780e86699e941254c8f4d9b7eb08ff7e96bbe10',
            '0x0000000000000000000000005dbcf33d8c2e976c6b560249878e6f1491bca25c',
        ],
        'transactionHash': '0xca33e56e1e529dacc9aa1261c8ba9230927329eb609fbe252e5bd3c2f5f3bcc9',
        'transactionIndex': 85,
    }
    assert_serialized_dicts_equal(
        events[0],
        expected_event,
        same_key_length=False,
        ignore_keys=[
            'timeStamp',  # returned from etherscan
            'blockHash',  # returned from web3
            'removed',  # returned from web3
        ],
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_log_and_receipt_etherscan_bad_tx_index(
        ethereum_inquirer,
        call_order,
        ethereum_manager_connect_at_start,
):
    """
    https://etherscan.io/tx/0x00eea6359d247c9433d32620358555a0fd3265378ff146b9511b7cff1ecb7829
    contains a log entry which in etherscan has transaction index 0x.

    Our code was not handling this well and was raising ValueError.
    This is a regression test for that.
    """
    wait_until_all_nodes_connected(
        connect_at_start=ethereum_manager_connect_at_start,
        evm_inquirer=ethereum_inquirer,
    )

    # Test getting the offending log entry does not raise
    argument_filters = {
        'from': ZERO_ADDRESS,
        'to': '0xbA215F7BE6c620dA3F8240B82741eaF3C5f5D786',
    }
    events = ethereum_inquirer.get_logs(
        contract_address='0xFC4B8ED459e00e5400be803A9BB3954234FD50e3',
        abi=ethereum_inquirer.contracts.abi('ATOKEN'),
        event_name='Transfer',
        argument_filters=argument_filters,
        from_block=10773651,
        to_block=10773653,
        call_order=call_order,
    )
    assert len(events) == 2
    assert events[0]['transactionIndex'] == 0
    assert events[1]['transactionIndex'] == 0

    # Test getting the transaction receipt (also containing the log entries) does not raise
    # They seem to all be 0
    result = ethereum_inquirer.get_transaction_receipt(
        hexstring_to_bytes('0x00eea6359d247c9433d32620358555a0fd3265378ff146b9511b7cff1ecb7829'),
        call_order=call_order,
    )
    assert all(x['transactionIndex'] == 0 for x in result['logs'])

    # Test that trying to query an event name that doesnot exist raises EventNotInABI
    argument_filters = {
        'from': ZERO_ADDRESS,
        'to': '0xbA215F7BE6c620dA3F8240B82741eaF3C5f5D786',
    }
    with pytest.raises(EventNotInABI):
        events = ethereum_inquirer.get_logs(
            contract_address='0xFC4B8ED459e00e5400be803A9BB3954234FD50e3',
            abi=ethereum_inquirer.contracts.abi('ATOKEN'),
            event_name='I_DONT_EXIST',
            argument_filters=argument_filters,
            from_block=10773651,
            to_block=10773653,
        )


def _test_get_blocknumber_by_time(ethereum_inquirer):
    result = ethereum_inquirer.get_blocknumber_by_time(1577836800)
    assert result == 9193265


def test_get_blocknumber_by_time_blockscout(ethereum_inquirer):
    """Queries blockscout api for known block times"""
    with patch(
        'rotkehlchen.externalapis.etherscan.Etherscan.get_blocknumber_by_time',
        side_effect=RemoteError('Mocked failed etherscan api query'),
    ):
        _test_get_blocknumber_by_time(ethereum_inquirer)


def test_get_blocknumber_by_time_etherscan(ethereum_inquirer):
    """Queries etherscan for known block times"""
    _test_get_blocknumber_by_time(ethereum_inquirer)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize(*ETHEREUM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
def test_ethereum_nodes_prune_and_archive_status(
        ethereum_inquirer,
        ethereum_manager_connect_at_start,
):
    """Checks that connecting to a set of ethereum nodes, the capabilities of those nodes are known and stored."""  # noqa: E501
    wait_until_all_nodes_connected(
        connect_at_start=ethereum_manager_connect_at_start,
        evm_inquirer=ethereum_inquirer,
    )
    for node_name, web3_node in ethereum_inquirer.web3_mapping.items():
        if node_name.endpoint == 'https://ethereum.publicnode.com':
            assert web3_node.is_pruned
            assert not web3_node.is_archive
        else:
            assert not web3_node.is_pruned
            assert web3_node.is_archive

    if ethereum_manager_connect_at_start[0].node_info.name == 'etherscan':
        assert len(ethereum_inquirer.web3_mapping) == 0  # excluding etherscan
    else:
        assert len(ethereum_inquirer.web3_mapping) == 1


@pytest.mark.vcr(
    match_on=['uri', 'method', 'raw_body'],
    allow_playback_repeats=True,
    filter_query_parameters=['apikey'],
)
@pytest.mark.parametrize(*ETHEREUM_NODES_SET_WITH_PRUNED_AND_NOT_ARCHIVED)
def test_get_pruned_nodes_behaviour_in_txn_queries(
        ethereum_inquirer,
        ethereum_manager_connect_at_start,
):
    wait_until_all_nodes_connected(
        connect_at_start=ethereum_manager_connect_at_start,
        evm_inquirer=ethereum_inquirer,
    )
    # ensure the pruned node comes first in the call order.
    call_order = ethereum_manager_connect_at_start
    random_evm_tx_hash = deserialize_evm_tx_hash('0x12ef63b6b8a863c028023374e5fb7a30a8b05559072ead2684084c58abbbeb6d')  # noqa: E501
    tx_result = ethereum_inquirer.maybe_get_transaction_by_hash(random_evm_tx_hash, call_order)
    receipt = ethereum_inquirer.maybe_get_transaction_receipt(random_evm_tx_hash, call_order)
    assert not tx_result and not receipt, 'transaction does not exist on-chain'

    # now, try retrieving an old transaction and see that the pruned node isn't called at all.
    # https://etherscan.io/tx/0x5958b93e28657cb34777c5b706b36bf6c72c9d0d704473163ba18cb14ba5a77a
    txn_hash = deserialize_evm_tx_hash('0x5958b93e28657cb34777c5b706b36bf6c72c9d0d704473163ba18cb14ba5a77a')  # noqa: E501

    tx_or_tx_receipt_calls = 0

    def mock_get_tx_or_tx_receipt(web3, tx_hash, must_exist):  # pylint: disable=unused-argument
        nonlocal tx_or_tx_receipt_calls
        assert tx_hash == txn_hash
        assert not web3 or web3.manager.provider.endpoint_uri != 'https://ethereum.publicnode.com'
        tx_or_tx_receipt_calls += 1

    get_tx_patch = patch.object(ethereum_inquirer, '_get_transaction_by_hash', side_effect=mock_get_tx_or_tx_receipt, autospec=True)  # noqa: E501
    get_tx_receipt_patch = patch.object(ethereum_inquirer, '_get_transaction_receipt', side_effect=mock_get_tx_or_tx_receipt, autospec=True)  # noqa: E501
    with get_tx_patch, get_tx_receipt_patch:
        ethereum_inquirer.maybe_get_transaction_by_hash(txn_hash, call_order)
        ethereum_inquirer.maybe_get_transaction_receipt(txn_hash, call_order)
        assert tx_or_tx_receipt_calls == 2

    # now reduce the rpc to just a pruned node & etherscan and see that etherscan is called.
    pruned_node_and_etherscan = [
        ethereum_manager_connect_at_start[0],
        ethereum_manager_connect_at_start[2],
    ]
    call_order = pruned_node_and_etherscan
    ethereum_inquirer.connect_to_multiple_nodes(pruned_node_and_etherscan)
    wait_until_all_nodes_connected(
        connect_at_start=pruned_node_and_etherscan,
        evm_inquirer=ethereum_inquirer,
    )
    assert len(ethereum_inquirer.web3_mapping) == 1

    etherscan_tx_or_tx_receipt_calls = 0

    def mock_etherscan_get_tx(tx_hash):
        nonlocal etherscan_tx_or_tx_receipt_calls
        assert tx_hash == txn_hash
        etherscan_tx_or_tx_receipt_calls += 1

    etherscan_get_tx_patch = patch.object(
        ethereum_inquirer.etherscan,
        'get_transaction_by_hash',
        side_effect=mock_etherscan_get_tx,
        autospec=True,
    )
    etherscan_get_tx_receipt_patch = patch.object(
        ethereum_inquirer.etherscan,
        'get_transaction_receipt',
        side_effect=mock_etherscan_get_tx,
        autospec=True,
    )
    with etherscan_get_tx_patch, etherscan_get_tx_receipt_patch:
        ethereum_inquirer.maybe_get_transaction_by_hash(txn_hash, call_order)
        ethereum_inquirer.maybe_get_transaction_receipt(txn_hash, call_order)
        assert etherscan_tx_or_tx_receipt_calls == 2


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
def test_get_contract_deployed_block(ethereum_inquirer):
    """Test that getting deployed block of a contract address works"""
    assert ethereum_inquirer.get_contract_deployed_block('0x5a464C28D19848f44199D003BeF5ecc87d090F87') == 12251871  # noqa: E501
    assert ethereum_inquirer.get_contract_deployed_block('0x9531C059098e3d194fF87FebB587aB07B30B1306') is None  # noqa: E501
