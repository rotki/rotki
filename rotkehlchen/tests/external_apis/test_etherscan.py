import json
import os
from unittest.mock import patch

import pytest
from eth_utils import to_checksum_address

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.constants import ETHEREUM_GENESIS
from rotkehlchen.chain.ethereum.etherscan import EthereumEtherscan
from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.etherscan import HasChainActivity
from rotkehlchen.serialization.deserialize import deserialize_evm_transaction
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    ChainID,
    EvmInternalTransaction,
    EvmTransaction,
    ExternalService,
    ExternalServiceApiCredentials,
    SupportedBlockchain,
    Timestamp,
    deserialize_evm_tx_hash,
)


@pytest.fixture(name='temp_etherscan')
def fixture_temp_etherscan(function_scope_messages_aggregator, tmpdir_factory, sql_vm_instructions_cb):  # noqa: E501
    directory = tmpdir_factory.mktemp('someuserdata')
    db = DBHandler(
        user_data_dir=directory,
        password='123',
        msg_aggregator=function_scope_messages_aggregator,
        initial_settings=None,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
        resume_from_backup=False,
    )

    # Test with etherscan API key
    api_key = os.environ.get('ETHERSCAN_API_KEY', None)
    if not api_key:
        api_key = '8JT7WQBB2VQP5C3416Y8X3S8GBA3CVZKP4'

    with db.user_write() as write_cursor:
        db.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[
                ExternalServiceApiCredentials(service=ExternalService.ETHERSCAN, api_key=api_key),
            ])

    return EthereumEtherscan(database=db, msg_aggregator=function_scope_messages_aggregator)


def patch_etherscan(etherscan, response_msg):
    count = 0

    def mock_requests_get(*args, **kwargs):  # pylint: disable=unused-argument
        nonlocal count
        if count == 0:
            response = f'{{"status":"0","message":"NOTOK","result":"{response_msg}"}}'
        else:
            response = '{"jsonrpc":"2.0","id":1,"result":"0x1337"}'

        count += 1
        return MockResponse(200, response)

    return patch.object(etherscan.session, 'get', wraps=mock_requests_get)


def test_maximum_rate_limit_reached(temp_etherscan, **kwargs):  # pylint: disable=unused-argument
    """
    Test that we can handle etherscan's rate limit repsponse properly

    Regression test for https://github.com/rotki/rotki/issues/772"
    """
    etherscan_patch = patch_etherscan(
        etherscan=temp_etherscan,
        response_msg='Max calls per sec rate limit reached (5/sec)',
    )

    with etherscan_patch:
        result = temp_etherscan.eth_call(
            '0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4',
            '0xc455279100000000000000000000000027a2eaaa8bebea8d23db486fb49627c165baacb5',
        )

    assert result == '0x1337'


def test_maximum_daily_rate_limit_reached(temp_etherscan, **kwargs):  # pylint: disable=unused-argument
    """Test that etherscan's daily rate limit raises a RemoteError"""
    etherscan_patch = patch_etherscan(
        etherscan=temp_etherscan,
        response_msg='Max daily rate limit reached. 110000 (100%) of 100000 day/limit',
    )

    with pytest.raises(RemoteError), etherscan_patch:
        temp_etherscan.eth_call(
            '0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4',
            '0xc455279100000000000000000000000027a2eaaa8bebea8d23db486fb49627c165baacb5',
        )


def test_deserialize_transaction_from_etherscan():
    # Make sure that a missing to address due to contract creation is handled
    data = {'blockNumber': 54092, 'timeStamp': 1439048640, 'hash': '0x9c81f44c29ff0226f835cd0a8a2f2a7eca6db52a711f8211b566fd15d3e0e8d4', 'nonce': 0, 'blockHash': '0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159', 'transactionIndex': 0, 'from': '0x5153493bB1E1642A63A098A65dD3913daBB6AE24', 'to': '', 'value': 11901464239480000000000000, 'gas': 2000000, 'gasPrice': 10000000000000, 'isError': 0, 'txreceipt_status': '', 'input': '0x313233', 'contractAddress': '0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae', 'cumulativeGasUsed': 1436963, 'gasUsed': 1436963, 'confirmations': 8569454}  # noqa: E501
    chain_id = ChainID.ETHEREUM
    transaction, _ = deserialize_evm_transaction(
        data=data,
        internal=False,
        chain_id=chain_id,
        evm_inquirer=None,
    )
    assert transaction == EvmTransaction(
        tx_hash=deserialize_evm_tx_hash(data['hash']),
        chain_id=chain_id,
        timestamp=1439048640,
        block_number=54092,
        from_address='0x5153493bB1E1642A63A098A65dD3913daBB6AE24',
        to_address=None,
        value=11901464239480000000000000,
        gas=2000000,
        gas_price=10000000000000,
        gas_used=1436963,
        input_data=bytes.fromhex(data['input'][2:]),
        nonce=0,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_etherscan_get_transactions_genesis_block(eth_transactions):
    """Test that the genesis transactions are correctly returned"""
    account = to_checksum_address('0xC951900c341aBbb3BAfbf7ee2029377071Dbc36A')
    db = eth_transactions.database
    with db.user_write() as cursor:
        db.add_blockchain_accounts(
            write_cursor=cursor,
            account_data=[
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=account),
            ],
        )
    eth_transactions.single_address_query_transactions(
        address=account,
        start_ts=ETHEREUM_GENESIS,
        end_ts=Timestamp(1451606400),
    )
    dbtx = DBEvmTx(database=db)
    with db.conn.read_ctx() as cursor:
        regular_tx_in_db = dbtx.get_evm_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(),
            has_premium=True,
        )
        internal_tx_in_db = dbtx.get_evm_internal_transactions(
            parent_tx_hash=GENESIS_HASH,
            blockchain=SupportedBlockchain.ETHEREUM,
        )

        assert dbtx.get_evm_internal_transactions(  # filter using from_address
            parent_tx_hash=GENESIS_HASH,
            blockchain=SupportedBlockchain.ETHEREUM,
            from_address=ZERO_ADDRESS,
        ) == dbtx.get_evm_internal_transactions(  # filter using to_address
            parent_tx_hash=GENESIS_HASH,
            blockchain=SupportedBlockchain.ETHEREUM,
            to_address=string_to_evm_address('0xC951900c341aBbb3BAfbf7ee2029377071Dbc36A'),
        ) == dbtx.get_evm_internal_transactions(  # filter using both from_address and to_address
            parent_tx_hash=GENESIS_HASH,
            blockchain=SupportedBlockchain.ETHEREUM,
            from_address=ZERO_ADDRESS,
            to_address=string_to_evm_address('0xC951900c341aBbb3BAfbf7ee2029377071Dbc36A'),
        ) == internal_tx_in_db  # filter using none of from_address and to_address

        assert dbtx.get_evm_internal_transactions(  # filter using different from_address
            parent_tx_hash=GENESIS_HASH,
            blockchain=SupportedBlockchain.ETHEREUM,
            from_address=string_to_evm_address('0xC951900c341aBbb3BAfbf7ee2029377071Dbc36A'),
        ) == dbtx.get_evm_internal_transactions(  # filter using different to_address
            parent_tx_hash=GENESIS_HASH,
            blockchain=SupportedBlockchain.ETHEREUM,
            to_address=ZERO_ADDRESS,
        ) == []

    assert regular_tx_in_db == [
        EvmTransaction(
            tx_hash=GENESIS_HASH,
            chain_id=ChainID.ETHEREUM,
            timestamp=ETHEREUM_GENESIS,
            block_number=0,
            from_address=ZERO_ADDRESS,
            to_address=None,
            value=0,
            gas=0,
            gas_price=0,
            gas_used=0,
            input_data=b'',
            nonce=0,
        ), EvmTransaction(
            tx_hash=deserialize_evm_tx_hash('0x352b93ac19dfbfd65d4d8385cded959d7a156c3f352a71a5a49560b088e1c8df'),
            chain_id=ChainID.ETHEREUM,
            timestamp=Timestamp(1443534531),
            block_number=307793,
            from_address='0xC951900c341aBbb3BAfbf7ee2029377071Dbc36A',
            to_address='0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2',
            value=327400000000000000000,
            gas=50000,
            gas_price=1171602790622,
            gas_used=21612,
            input_data=b'EN06ENDWG',
            nonce=0,
        ),
    ]

    assert internal_tx_in_db == [
        EvmInternalTransaction(
            parent_tx_hash=GENESIS_HASH,
            chain_id=ChainID.ETHEREUM,
            trace_id=0,
            from_address=ZERO_ADDRESS,
            to_address='0xC951900c341aBbb3BAfbf7ee2029377071Dbc36A',
            value=327600000000000000000,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_etherscan_get_contract_abi(temp_etherscan):
    """Test the contract abi fetching from etherscan"""
    abi = temp_etherscan.get_contract_abi('0x5a464C28D19848f44199D003BeF5ecc87d090F87')
    assert abi == json.loads('[{"inputs":[{"internalType":"address","name":"vat_","type":"address"},{"internalType":"address","name":"dog_","type":"address"},{"internalType":"address","name":"cat_","type":"address"},{"internalType":"address","name":"spot_","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"AddIlk","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"usr","type":"address"}],"name":"Deny","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"what","type":"bytes32"},{"indexed":false,"internalType":"address","name":"data","type":"address"}],"name":"File","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"},{"indexed":false,"internalType":"bytes32","name":"what","type":"bytes32"},{"indexed":false,"internalType":"address","name":"data","type":"address"}],"name":"File","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"},{"indexed":false,"internalType":"bytes32","name":"what","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"data","type":"uint256"}],"name":"File","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"},{"indexed":false,"internalType":"bytes32","name":"what","type":"bytes32"},{"indexed":false,"internalType":"string","name":"data","type":"string"}],"name":"File","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"NameError","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"usr","type":"address"}],"name":"Rely","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"RemoveIlk","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"SymbolError","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"UpdateIlk","type":"event"},{"inputs":[{"internalType":"address","name":"adapter","type":"address"}],"name":"add","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"cat","outputs":[{"internalType":"contract CatLike","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"class","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"count","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"dec","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"usr","type":"address"}],"name":"deny","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"dog","outputs":[{"internalType":"contract DogLike","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"},{"internalType":"bytes32","name":"what","type":"bytes32"},{"internalType":"uint256","name":"data","type":"uint256"}],"name":"file","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"},{"internalType":"bytes32","name":"what","type":"bytes32"},{"internalType":"string","name":"data","type":"string"}],"name":"file","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"what","type":"bytes32"},{"internalType":"address","name":"data","type":"address"}],"name":"file","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"},{"internalType":"bytes32","name":"what","type":"bytes32"},{"internalType":"address","name":"data","type":"address"}],"name":"file","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"gem","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"pos","type":"uint256"}],"name":"get","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"name":"ilkData","outputs":[{"internalType":"uint96","name":"pos","type":"uint96"},{"internalType":"address","name":"join","type":"address"},{"internalType":"address","name":"gem","type":"address"},{"internalType":"uint8","name":"dec","type":"uint8"},{"internalType":"uint96","name":"class","type":"uint96"},{"internalType":"address","name":"pip","type":"address"},{"internalType":"address","name":"xlip","type":"address"},{"internalType":"string","name":"name","type":"string"},{"internalType":"string","name":"symbol","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"info","outputs":[{"internalType":"string","name":"name","type":"string"},{"internalType":"string","name":"symbol","type":"string"},{"internalType":"uint256","name":"class","type":"uint256"},{"internalType":"uint256","name":"dec","type":"uint256"},{"internalType":"address","name":"gem","type":"address"},{"internalType":"address","name":"pip","type":"address"},{"internalType":"address","name":"join","type":"address"},{"internalType":"address","name":"xlip","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"join","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"list","outputs":[{"internalType":"bytes32[]","name":"","type":"bytes32[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"start","type":"uint256"},{"internalType":"uint256","name":"end","type":"uint256"}],"name":"list","outputs":[{"internalType":"bytes32[]","name":"","type":"bytes32[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"pip","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"pos","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"_ilk","type":"bytes32"},{"internalType":"address","name":"_join","type":"address"},{"internalType":"address","name":"_gem","type":"address"},{"internalType":"uint256","name":"_dec","type":"uint256"},{"internalType":"uint256","name":"_class","type":"uint256"},{"internalType":"address","name":"_pip","type":"address"},{"internalType":"address","name":"_xlip","type":"address"},{"internalType":"string","name":"_name","type":"string"},{"internalType":"string","name":"_symbol","type":"string"}],"name":"put","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"usr","type":"address"}],"name":"rely","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"remove","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"removeAuth","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"spot","outputs":[{"internalType":"contract SpotLike","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"update","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"vat","outputs":[{"internalType":"contract VatLike","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"wards","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"xlip","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]')  # noqa: E501
    assert temp_etherscan.get_contract_abi('0x9531C059098e3d194fF87FebB587aB07B30B1306') is None


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_has_activity(temp_etherscan):
    """Test to check if an address has any activity on ethereum mainnet"""
    assert temp_etherscan.has_activity('0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5') == HasChainActivity.TRANSACTIONS  # noqa: E501
    assert temp_etherscan.has_activity('0x725E35e01bbEDadd6ac13cE1c4a98bA4Cf00dF21') == HasChainActivity.TRANSACTIONS  # noqa: E501
    assert temp_etherscan.has_activity('0x3C69Bc9B9681683890ad82953Fe67d13Cd91D5EE') == HasChainActivity.BALANCE  # noqa: E501
    assert temp_etherscan.has_activity('0x014cd0535b2Ea668150a681524392B7633c8681c') == HasChainActivity.TOKENS  # noqa: E501
    assert temp_etherscan.has_activity('0x6c66149E65c517605e0a2e4F707550ca342f9c1B') == HasChainActivity.NONE  # noqa: E501
