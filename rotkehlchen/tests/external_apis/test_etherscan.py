import os
from unittest.mock import patch

import pytest
from eth_utils import to_checksum_address

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.constants import ETHEREUM_GENESIS
from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmTransactionsFilterQuery
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.externalapis.etherscan_like import HasChainActivity
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

    return Etherscan(database=db, msg_aggregator=function_scope_messages_aggregator)


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
    Test that we can handle etherscan's rate limit response properly

    Regression test for https://github.com/rotki/rotki/issues/772"
    """
    etherscan_patch = patch_etherscan(
        etherscan=temp_etherscan,
        response_msg='Max calls per sec rate limit reached (5/sec)',
    )

    with etherscan_patch:
        result = temp_etherscan.eth_call(
            SupportedBlockchain.ETHEREUM,
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
            SupportedBlockchain.ETHEREUM,
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
        regular_tx_in_db = dbtx.get_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(),
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
            gas=0,
            gas_used=0,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_has_activity(temp_etherscan: 'Etherscan') -> None:
    """Test to check if an address has any activity on ethereum mainnet"""
    assert temp_etherscan.has_activity(ChainID.ETHEREUM, string_to_evm_address('0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5')) == HasChainActivity.TRANSACTIONS  # noqa: E501
    assert temp_etherscan.has_activity(ChainID.ETHEREUM, string_to_evm_address('0x725E35e01bbEDadd6ac13cE1c4a98bA4Cf00dF21')) == HasChainActivity.TRANSACTIONS  # noqa: E501
    assert temp_etherscan.has_activity(ChainID.ETHEREUM, string_to_evm_address('0x3C69Bc9B9681683890ad82953Fe67d13Cd91D5EE')) == HasChainActivity.BALANCE  # noqa: E501
    assert temp_etherscan.has_activity(ChainID.ETHEREUM, string_to_evm_address('0x014cd0535b2Ea668150a681524392B7633c8681c')) == HasChainActivity.TOKENS  # noqa: E501
    assert temp_etherscan.has_activity(ChainID.ETHEREUM, string_to_evm_address('0x6c66149E65c517605e0a2e4F707550ca342f9c1B')) == HasChainActivity.NONE  # noqa: E501
