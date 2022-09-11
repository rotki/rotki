import os
from unittest.mock import patch

import pytest
from eth_utils import to_checksum_address

from rotkehlchen.chain.ethereum.constants import ETHEREUM_BEGIN, GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.serialization.deserialize import deserialize_evm_transaction
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    BlockchainAccountData,
    EvmInternalTransaction,
    EvmTransaction,
    ExternalService,
    ExternalServiceApiCredentials,
    SupportedBlockchain,
    Timestamp,
    deserialize_evm_tx_hash,
)


@pytest.fixture(scope='function', name='temp_etherscan')
def fixture_temp_etherscan(function_scope_messages_aggregator, tmpdir_factory, sql_vm_instructions_cb):  # noqa: E501
    directory = tmpdir_factory.mktemp('data')
    db = DBHandler(
        user_data_dir=directory,
        password='123',
        msg_aggregator=function_scope_messages_aggregator,
        initial_settings=None,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
    )

    # Test with etherscan API key
    api_key = os.environ.get('ETHERSCAN_API_KEY', None)
    if api_key:
        db.add_external_service_credentials(credentials=[  # pylint: disable=no-value-for-parameter
            ExternalServiceApiCredentials(service=ExternalService.ETHERSCAN, api_key=api_key),
        ])
    etherscan = Etherscan(database=db, msg_aggregator=function_scope_messages_aggregator)
    return etherscan


def patch_etherscan(etherscan):
    count = 0

    def mock_requests_get(_url, timeout):  # pylint: disable=unused-argument
        nonlocal count
        if count == 0:
            response = (
                '{"status":"0","message":"NOTOK",'
                '"result":"Max rate limit reached, please use API Key for higher rate limit"}'
            )
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
    etherscan = temp_etherscan

    etherscan_patch = patch_etherscan(etherscan)

    with etherscan_patch:
        result = etherscan.eth_call(
            '0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4',
            '0xc455279100000000000000000000000027a2eaaa8bebea8d23db486fb49627c165baacb5',
        )

    assert result == '0x1337'


def test_deserialize_transaction_from_etherscan():
    # Make sure that a missing to address due to contract creation is handled
    data = {'blockNumber': 54092, 'timeStamp': 1439048640, 'hash': '0x9c81f44c29ff0226f835cd0a8a2f2a7eca6db52a711f8211b566fd15d3e0e8d4', 'nonce': 0, 'blockHash': '0xd3cabad6adab0b52ea632c386ea19403680571e682c62cb589b5abcd76de2159', 'transactionIndex': 0, 'from': '0x5153493bB1E1642A63A098A65dD3913daBB6AE24', 'to': '', 'value': 11901464239480000000000000, 'gas': 2000000, 'gasPrice': 10000000000000, 'isError': 0, 'txreceipt_status': '', 'input': '0x313233', 'contractAddress': '0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae', 'cumulativeGasUsed': 1436963, 'gasUsed': 1436963, 'confirmations': 8569454}  # noqa: E501
    transaction = deserialize_evm_transaction(data, internal=False, manager=None)
    assert transaction == EvmTransaction(
        tx_hash=deserialize_evm_tx_hash(data['hash']),
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


def test_etherscan_get_transactions_genesis_block(eth_transactions):
    """Test that the genesis transactions are correctly returned"""
    account = to_checksum_address('0xC951900c341aBbb3BAfbf7ee2029377071Dbc36A')
    db = eth_transactions.database
    with db.user_write() as cursor:
        db.add_blockchain_accounts(
            write_cursor=cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            account_data=[
                BlockchainAccountData(address=account),
            ],
        )
    eth_transactions.single_address_query_transactions(
        address=account,
        start_ts=ETHEREUM_BEGIN,
        end_ts=Timestamp(1451606400),
    )
    dbtx = DBEthTx(database=db)
    with db.conn.read_ctx() as cursor:
        regular_tx_in_db = dbtx.get_ethereum_transactions(
            cursor=cursor,
            filter_=ETHTransactionsFilterQuery.make(),
            has_premium=True,
        )
        internal_tx_in_db = dbtx.get_ethereum_internal_transactions(parent_tx_hash=GENESIS_HASH)

    assert regular_tx_in_db == [
        EvmTransaction(
            tx_hash=GENESIS_HASH,
            timestamp=ETHEREUM_BEGIN,
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
            tx_hash=deserialize_evm_tx_hash('0x352b93ac19dfbfd65d4d8385cded959d7a156c3f352a71a5a49560b088e1c8df'),  # noqa: E501
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
            trace_id=0,
            timestamp=ETHEREUM_BEGIN,
            block_number=0,
            from_address=ZERO_ADDRESS,
            to_address='0xC951900c341aBbb3BAfbf7ee2029377071Dbc36A',
            value='327600000000000000000',
        ),
    ]
