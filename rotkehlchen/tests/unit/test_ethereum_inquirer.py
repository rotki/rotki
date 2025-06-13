import json
from collections.abc import Callable
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.constants import ETHEREUM_ETHERSCAN_NODE
from rotkehlchen.chain.ethereum.modules.thegraph.constants import CONTRACT_STAKING
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.kyber.constants import KYBER_AGGREGATOR_SWAPPED
from rotkehlchen.chain.evm.decoding.thegraph.constants import GRAPH_DELEGATION_TRANSFER_ABI
from rotkehlchen.chain.evm.node_inquirer import _query_web3_get_logs
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import WeightedNode, string_to_evm_address
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

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


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
        db.add_or_ignore_receipt_data(ChainID.ETHEREUM, result)
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
    rpc_nodes = database.get_rpc_nodes(blockchain=SupportedBlockchain.ETHEREUM, only_active=True)
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
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE, ETHEREUM_ETHERSCAN_NODE)])  # noqa: E501
def test_rpc_request_timeout(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_manager_connect_at_start: list[WeightedNode],
) -> None:
    """Test that rpc timeout errors result in the node being marked as `failed to connect`.
    Regression test for https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=111711513
    """
    wait_until_all_nodes_connected(
        connect_at_start=ethereum_manager_connect_at_start,
        evm_inquirer=ethereum_inquirer,
    )
    yearn_ycrv_vault = ethereum_inquirer.contracts.contract(string_to_evm_address('0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c'))  # noqa: E501

    def make_mock_post(
            timeout_exception: type[requests.ReadTimeout | requests.ConnectTimeout],
    ) -> Callable:
        def mock_post(url, data, **kwargs):
            data_j = json.loads(data)
            if data_j.get('method') == 'eth_call':
                raise timeout_exception

            return requests.post(url, data, **kwargs)
        return mock_post

    for exception in (requests.ReadTimeout, requests.ConnectTimeout):  # test both read and connect timeouts  # noqa: E501
        ethereum_inquirer.failed_to_connect_nodes = set()  # reset failed nodes
        with patch('requests.sessions.Session.post', side_effect=make_mock_post(exception)):
            ethereum_inquirer.call_contract(
                contract_address=yearn_ycrv_vault.address,
                abi=yearn_ycrv_vault.abi,
                method_name='symbol',
            )

        assert ethereum_inquirer.failed_to_connect_nodes == {INFURA_ETH_NODE.node_info.name}


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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_blocknumber_by_time_blockscout(ethereum_inquirer):
    """Queries blockscout api for known block times"""
    _test_get_blocknumber_by_time(ethereum_inquirer)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_blocknumber_by_time_etherscan(ethereum_inquirer):
    """Queries etherscan for known block times"""
    with patch.object(
        ethereum_inquirer.blockscout,
        'get_blocknumber_by_time',
        side_effect=RemoteError('Intentional blockscout remote error to test etherscan'),
    ):
        _test_get_blocknumber_by_time(ethereum_inquirer)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize(*ETHEREUM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
def test_ethereum_nodes_prune_and_archive_status(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_manager_connect_at_start: list[WeightedNode],
):
    """Checks that connecting to a set of ethereum nodes, the capabilities of those nodes are known and stored."""  # noqa: E501
    ethereum_inquirer.maybe_connect_to_nodes(when_tracked_accounts=True)
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
    pruned_node = [ethereum_manager_connect_at_start[0]]
    ethereum_inquirer.connect_to_multiple_nodes(pruned_node)
    wait_until_all_nodes_connected(
        connect_at_start=pruned_node,
        evm_inquirer=ethereum_inquirer,
    )
    assert len(ethereum_inquirer.web3_mapping) == 2
    etherscan_tx_or_tx_receipt_calls = 0

    def mock_etherscan_get_tx(chain_id, tx_hash):
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
    call_order = pruned_node + [ETHEREUM_ETHERSCAN_NODE]
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(), (INFURA_ETH_NODE,)])
def test_get_logs_graph_delegation(ethereum_inquirer, ethereum_manager_connect_at_start):
    """Check that the log events queries are formulated correctly when there is a
    filter given both for etherscan and for web3 node query.

    This is a test for non-anonymous logs and regression test for the specific graph
    delegation query where the ABI was using strings instead of booleans.

    This test also checks that the results are sent and processed correctly.
    """
    call_order = None
    if len(ethereum_manager_connect_at_start) != 0 and ethereum_manager_connect_at_start[0] == INFURA_ETH_NODE:  # noqa: E501
        wait_until_all_nodes_connected(
            connect_at_start=ethereum_manager_connect_at_start,
            evm_inquirer=ethereum_inquirer,
        )
        # by default logs always query etherscan first due to indexing speed.
        # Here we want to check normal web3 query, so force it
        call_order = [INFURA_ETH_NODE]

    user_address, v_from_block, v_to_block, topic0 = '0x9bA6D627fB731F447a68326E61280494C9A5ad02', 20879644, 20881207, '0x231e5cfeff7759a468241d939ab04a60d603b17e359057abbb8f52afc3e4986b'  # noqa: E501

    original_etherscan_query = ethereum_inquirer.etherscan._query

    def mock_etherscan_query(chain_id, module, action, options, timeout):
        """Mock etherscan query to check the options are formulated correctly."""
        assert options == {
            'address': CONTRACT_STAKING,
            'fromBlock': v_from_block, 'toBlock': v_to_block,
            'topic0': topic0, 'topic0_1opr': 'and',
            'topic2': f'0x000000000000000000000000{user_address.lower()[2:]}',
            'topic2_3opr': 'and',
        }
        return original_etherscan_query(chain_id, module, action, options, timeout)

    original_query_web3_get_logs = _query_web3_get_logs

    def mock_query_web3_get_logs(web3, filter_args, from_block, to_block, contract_address, event_name, argument_filters, initial_block_range, log_iteration_cb, log_iteration_cb_arguments):  # noqa: E501
        """Similarly to etherscan let's check the right arguments make it here"""
        assert filter_args == {
            'address': CONTRACT_STAKING,
            'fromBlock': v_from_block, 'toBlock': v_to_block,
            'topics': [
                topic0, None, f'0x000000000000000000000000{user_address.lower()[2:]}',
            ],
        }
        assert argument_filters == {'l2Delegator': '0x9bA6D627fB731F447a68326E61280494C9A5ad02'}
        assert contract_address == CONTRACT_STAKING
        return original_query_web3_get_logs(web3, filter_args, from_block, to_block, contract_address, event_name, argument_filters, initial_block_range, log_iteration_cb, log_iteration_cb_arguments)  # noqa: E501

    etherscan_query_patch = patch.object(ethereum_inquirer.etherscan, '_query', side_effect=mock_etherscan_query, autospec=True)  # noqa: E501
    query_web3_logs_patch = patch('rotkehlchen.chain.evm.node_inquirer._query_web3_get_logs', side_effect=mock_query_web3_get_logs)  # noqa: E501

    expected_logs = [{
        'address': CONTRACT_STAKING,
        'topics': ['0x231e5cfeff7759a468241d939ab04a60d603b17e359057abbb8f52afc3e4986b', '0x0000000000000000000000009ba6d627fb731f447a68326e61280494c9a5ad02', '0x0000000000000000000000009ba6d627fb731f447a68326e61280494c9a5ad02', '0x0000000000000000000000005a8904be09625965d9aec4bffd30d853438a053e'],  # noqa: E501
        'data': '0x0000000000000000000000002f09092aacd80196fc984908c5a9a7ab3ee4f1ce000000000000000000000000000000000000000000000098e6a976f9df23110d',  # noqa: E501
        'blockNumber': 20879646,
        'blockHash': '0xe8681d4fd55ebe77c4632e5ee8743211596f9bd3d8147c7cc182fc10a8c40e78',
        'timeStamp': 1727894171,
        'gasPrice': 26315422572,
        'gasUsed': 234729,
        'logIndex': 412,
        'transactionHash': '0x1ab7a55f3c5c44cbc3361f5f17c00fd95b1c690df48441e17d24372ec900906a',
        'transactionIndex': 62,
    }]
    with etherscan_query_patch, query_web3_logs_patch:
        logs = ethereum_inquirer.get_logs(
            contract_address=CONTRACT_STAKING,
            abi=GRAPH_DELEGATION_TRANSFER_ABI,
            event_name='DelegationTransferredToL2',
            argument_filters={'l2Delegator': user_address},
            from_block=v_from_block,
            to_block=v_to_block,
            call_order=call_order,
        )

    if len(ethereum_manager_connect_at_start) != 0 and ethereum_manager_connect_at_start[0] == INFURA_ETH_NODE:  # noqa: E501
        del expected_logs[0]['gasPrice']
        del expected_logs[0]['gasUsed']
        del expected_logs[0]['timeStamp']
        del logs[0]['removed']

    assert logs == expected_logs


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(), (INFURA_ETH_NODE,)])
def test_get_logs_anonymous(ethereum_inquirer, ethereum_manager_connect_at_start):
    """Check that for anonymous logs the topic0 is not given (bug in web3.py function we use)"""
    call_order = None
    if len(ethereum_manager_connect_at_start) != 0 and ethereum_manager_connect_at_start[0] == INFURA_ETH_NODE:  # noqa: E501
        wait_until_all_nodes_connected(
            connect_at_start=ethereum_manager_connect_at_start,
            evm_inquirer=ethereum_inquirer,
        )
        # by default logs always query etherscan first due to indexing speed.
        # Here we want to check normal web3 query, so force it
        call_order = [INFURA_ETH_NODE]

    proxy_address, pot_address = make_evm_address(), string_to_evm_address('0x197E90f9FAD81970bA7976f33CbD77088E5D7cf7')  # noqa: E501
    makerdao_pot = ethereum_inquirer.contracts.contract(pot_address)
    argument_filters = {
        'sig': '0x049878f3',  # join
        'usr': proxy_address,
    }
    deployment_block, v_to_block, topic0 = 8928160, 8928170, '0x049878f300000000000000000000000000000000000000000000000000000000'  # noqa: E501

    def mock_etherscan_query(chain_id, module, action, options=None, timeout=None):
        """Mock etherscan query to check the options are formulated correctly."""
        if action == 'eth_blockNumber':
            return '0x883baa'  # int: 8928170
        assert options == {
            'address': pot_address,
            'fromBlock': deployment_block, 'toBlock': v_to_block,
            'topic0': topic0, 'topic0_1opr': 'and',
            'topic1': f'0x000000000000000000000000{proxy_address.lower()[2:]}',  # pylint: disable=no-member
            'topic1_2opr': 'and',
        }
        return []  # empty list to make it succeed

    def mock_query_web3_get_logs(web3, filter_args, from_block, to_block, contract_address, event_name, argument_filters, initial_block_range, log_iteration_cb, log_iteration_cb_arguments):  # noqa: E501
        """Similarly to etherscan let's check the right arguments make it here"""
        assert from_block == deployment_block
        assert to_block == 'latest'
        assert filter_args == {
            'address': pot_address,
            'fromBlock': from_block, 'toBlock': 'latest',
            'topics': [
                topic0, f'0x000000000000000000000000{proxy_address.lower()[2:]}',    # pylint: disable=no-member
            ],
        }
        assert argument_filters == {'sig': '0x049878f3', 'usr': proxy_address}
        assert contract_address == pot_address
        return []  # empty list to make it succeed

    etherscan_query_patch = patch.object(ethereum_inquirer.etherscan, '_query', side_effect=mock_etherscan_query, autospec=True)  # noqa: E501
    query_web3_logs_patch = patch('rotkehlchen.chain.evm.node_inquirer._query_web3_get_logs', side_effect=mock_query_web3_get_logs)  # noqa: E501

    with etherscan_query_patch, query_web3_logs_patch:
        ethereum_inquirer.get_logs(
            contract_address=pot_address,
            abi=makerdao_pot.abi,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=makerdao_pot.deployed_block,
            to_block='latest',
            call_order=call_order,
        )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
def test_contract_call_raises_on_non_checksum_token_address(ethereum_inquirer):
    """Check that contract calls fail properly when given a non-checksum token address.

    Validates that a RemoteError is raised with appropriate message when providing
    a non-checksum token address to tokens_balance call.
    """
    token_address = '0x5283d291dbcf85356a21ba090e6db59121208b44'
    with pytest.raises(RemoteError, match=f'non-checksum address {token_address}'):
        ethereum_inquirer.contract_scan.call(
            node_inquirer=ethereum_inquirer,
            method_name='tokens_balance',
            arguments=['0xBCaBdc5eBd28dC9d1629210f92D27171852eBa53', [token_address]],
        )
