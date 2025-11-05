from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.gitcoin.constants import GITCOIN_GRANTS_OLD1
from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_ACCOUNT_DELEGATION
from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2WithL1FeesTransaction
from rotkehlchen.chain.evm.types import EvmAccount, string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_SAI
from rotkehlchen.db.constants import TX_DECODED, TX_SPAM
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import (
    EvmEventFilterQuery,
    EvmTransactionsFilterQuery,
    EvmTransactionsNotDecodedFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.l2withl1feestx import DBL2WithL1FeesTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.tests.utils.ethereum import INFURA_ETH_NODE, get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTransaction,
    EVMTxHash,
    Location,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
    from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
    from rotkehlchen.chain.optimism.transactions import OptimismTransactions
    from rotkehlchen.db.dbhandler import DBHandler


def _add_transactions_to_db(
        db: 'DBHandler',
        ethereum_accounts: list[ChecksumEvmAddress],
) -> tuple[EVMTxHash, EVMTxHash, EVMTxHash]:
    """Add to the database transactions in different optimism and ethereum for testing"""
    tx_hash_opt = deserialize_evm_tx_hash('0x063d45910f29e0954a52aee39febba9be784d49af7588a590dc2fd7d156b4665')  # noqa: E501
    tx_hash_eth = deserialize_evm_tx_hash('0x3f313e90ed07044fdbb1016ff7986fd26adaeb05e8e9d3252ae0a8318cb8100d')  # noqa: E501
    tx_hash_eth_yabir = deserialize_evm_tx_hash('0x91016e7fb9f524449dd1a0b4faef9bc630e9c01c31b6d3383c94975269335afe')  # noqa: E501
    transaction_opt = L2WithL1FeesTransaction(
        tx_hash=tx_hash_opt,
        chain_id=ChainID.OPTIMISM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=ethereum_accounts[0],
        to_address=string_to_evm_address('0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xa9059cbb000000000000000000000000106b62fdd27b748cf2da3bacab91a2cabaee6dca0000000000000000000000000000000000000000000000000000000086959530'),
        nonce=507,
        l1_fee=455063072063200,
    )
    transaction_eth = EvmTransaction(
        tx_hash=tx_hash_eth,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=ethereum_accounts[0],
        to_address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xa9059cbb000000000000000000000000c5d494aa0cbabd7871af0ef122fb410fa25c3379000000000000000000000000000000000000000000000000000000257a9974a0'),
        nonce=507,
    )
    transaction_eth_yabir = EvmTransaction(
        tx_hash=tx_hash_eth_yabir,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=ethereum_accounts[1],
        to_address=string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xa9059cbb000000000000000000000000d9e40f3e33f62029172f6f8b691cf09d476bda3c000000000000000000000000000000000000000000000001a055690d9db80000'),
        nonce=507,
    )

    dbevmtx = DBEvmTx(db)
    dbl2withl1feestx = DBL2WithL1FeesTx(db)
    with db.user_write() as cursor:
        dbl2withl1feestx.add_transactions(cursor, [transaction_opt], relevant_address=ethereum_accounts[0])  # noqa: E501
        dbevmtx.add_transactions(cursor, [transaction_eth], relevant_address=ethereum_accounts[0])
        dbevmtx.add_transactions(cursor, [transaction_eth_yabir], relevant_address=ethereum_accounts[1])  # noqa: E501

    return tx_hash_eth, tx_hash_eth_yabir, tx_hash_opt


def assert_events_equal(e1: HistoryBaseEntry, e2: HistoryBaseEntry) -> None:
    for a in dir(e1):
        if a.startswith('__') or callable(getattr(e1, a)) or a == 'identifier':
            continue
        e1_value = getattr(e1, a)
        e2_value = getattr(e2, a)
        assert e1_value == e2_value, f'Events differ at {a}. {e1_value} != {e2_value}'


@pytest.mark.parametrize('use_custom_database', ['ethtxs.db'])
def test_tx_decode(ethereum_transaction_decoder, database):
    dbevmtx = DBEvmTx(database)
    addr1 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
    approve_tx_hash = deserialize_evm_tx_hash('0x5cc0e6e62753551313412492296d5e57bea0a9d1ce507cc96aa4aa076c5bde7a')  # noqa: E501
    with database.conn.read_ctx() as cursor:
        transactions = dbevmtx.get_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(
                accounts=[EvmAccount(addr1)],
                tx_hash=approve_tx_hash,
                chain_id=ChainID.ETHEREUM,
            ),
        )
    decoder = ethereum_transaction_decoder
    with patch.object(decoder, '_decode_transaction', wraps=decoder._decode_transaction) as decode_mock:  # noqa: E501
        with database.conn.read_ctx() as cursor:
            for tx in transactions:
                receipt = dbevmtx.get_receipt(cursor, tx.tx_hash, ChainID.ETHEREUM)
                assert receipt is not None, 'all receipts should be queried in the test DB'
                events, _, _ = decoder._get_or_decode_transaction_events(tx, receipt, ignore_cache=False)  # noqa: E501
                if tx.tx_hash == approve_tx_hash:
                    assert len(events) == 2
                    assert_events_equal(events[0], EvmEvent(
                        # The no-member is due to https://github.com/PyCQA/pylint/issues/3162
                        tx_ref=approve_tx_hash,
                        sequence_index=0,
                        timestamp=1569924574000,
                        location=Location.ETHEREUM,
                        location_label=addr1,
                        asset=A_ETH,
                        amount=FVal('0.000030921'),
                        # The no-member is due to https://github.com/PyCQA/pylint/issues/3162
                        notes='Burn 0.000030921 ETH for gas',
                        event_type=HistoryEventType.SPEND,
                        event_subtype=HistoryEventSubType.FEE,
                        counterparty=CPT_GAS,
                    ))
                    assert_events_equal(events[1], EvmEvent(
                        # The no-member is due to https://github.com/PyCQA/pylint/issues/3162
                        tx_ref=approve_tx_hash,
                        sequence_index=163,
                        timestamp=1569924574000,
                        location=Location.ETHEREUM,
                        location_label=addr1,
                        asset=A_SAI,
                        amount=1,
                        notes=f'Set SAI spending approval of {addr1} by {GITCOIN_GRANTS_OLD1} to 1',  # noqa: E501
                        event_type=HistoryEventType.INFORMATIONAL,
                        event_subtype=HistoryEventSubType.APPROVE,
                        address=GITCOIN_GRANTS_OLD1,
                    ))

            assert decode_mock.call_count == len(transactions)
            # now go again, and see that no more decoding happens as it's all pulled from the DB
            for tx in transactions:
                receipt = dbevmtx.get_receipt(cursor, tx.tx_hash, ChainID.ETHEREUM)
                assert receipt is not None, 'all receipts should be queried in the test DB'
                events, _, _ = decoder._get_or_decode_transaction_events(tx, receipt, ignore_cache=False)  # noqa: E501
        assert decode_mock.call_count == len(transactions)

    dbevents = DBHistoryEvents(database)
    # customize one evm event to check that the logic for them works correctly
    with database.user_write() as write_cursor:
        assert dbevents.edit_history_event(write_cursor=write_cursor, event=events[1]) is None

    with database.user_write() as write_cursor:
        assert write_cursor.execute('SELECT COUNT(*) from history_events').fetchone()[0] == 2
        assert write_cursor.execute('SELECT COUNT(*) from chain_events_info').fetchone()[0] == 2
        assert write_cursor.execute('SELECT COUNT(*) from evm_tx_mappings').fetchone()[0] == 1

        dbevents.reset_events_for_redecode(write_cursor, Location.ETHEREUM)
        # after deletion we only keep the customized event
        assert write_cursor.execute('SELECT event_identifier from history_events').fetchall() == [(events[1].event_identifier,)]  # noqa: E501
        assert write_cursor.execute('SELECT identifier from chain_events_info').fetchall() == [(events[1].identifier,)]  # noqa: E501
        assert write_cursor.execute('SELECT COUNT(*) from evm_tx_mappings').fetchone()[0] == 0


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])  # noqa: E501
@pytest.mark.parametrize('optimism_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_query_and_decode_transactions_works_with_different_chains(
        database: 'DBHandler',
        eth_transactions: 'EthereumTransactions',
        optimism_transactions: 'OptimismTransactions',
        ethereum_accounts: list[ChecksumEvmAddress],
        optimism_transaction_decoder: 'OptimismTransactionDecoder',
) -> None:
    """
    Test that the different evm transactions modules only query receipts for their chain
    and the decoding of transactions using an instance of the EVMTransactionDecoder
    only decodes transactions from the correct chain.
    """
    _, tx_hash_eth_yabir, tx_hash_opt = _add_transactions_to_db(database, ethereum_accounts)
    dbevmtx = DBEvmTx(database)
    dbl2withl1feestx = DBL2WithL1FeesTx(database)
    assert len(dbevmtx.get_transaction_hashes_no_receipt(tx_filter_query=None, limit=None)) == 3
    eth_transactions.get_receipts_for_transactions_missing_them(addresses=[ethereum_accounts[0]])
    assert dbevmtx.get_transaction_hashes_no_receipt(tx_filter_query=None, limit=None) == [tx_hash_opt, tx_hash_eth_yabir]  # noqa: E501
    optimism_transactions.get_receipts_for_transactions_missing_them()
    assert dbevmtx.get_transaction_hashes_no_receipt(tx_filter_query=None, limit=None) == [tx_hash_eth_yabir]  # noqa: E501

    hashes = dbl2withl1feestx.get_transaction_hashes_not_decoded(
        filter_query=EvmTransactionsNotDecodedFilterQuery.make(chain_id=ChainID.OPTIMISM, limit=None),  # noqa: E501
    )
    assert len(hashes) == 1
    hashes = dbevmtx.get_transaction_hashes_not_decoded(
        filter_query=EvmTransactionsNotDecodedFilterQuery.make(chain_id=ChainID.ETHEREUM, limit=None),  # noqa: E501
    )
    assert len(hashes) == 1

    # get the receipts for the last address, which should mark 1 more transaction as not decoded
    eth_transactions.get_receipts_for_transactions_missing_them(addresses=[ethereum_accounts[1]])
    hashes = dbevmtx.get_transaction_hashes_not_decoded(
        filter_query=EvmTransactionsNotDecodedFilterQuery.make(chain_id=ChainID.ETHEREUM, limit=None),  # noqa: E501
    )
    assert len(hashes) == 2

    # see that setting the spam attribute alone does not count it as decoded
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
            (3, TX_SPAM),
        )
    hashes = dbevmtx.get_transaction_hashes_not_decoded(
        filter_query=EvmTransactionsNotDecodedFilterQuery.make(chain_id=ChainID.ETHEREUM, limit=None),  # noqa: E501
    )
    assert len(hashes) == 2

    # see that setting the decoded attribute counts properly
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
            (3, TX_DECODED),
        )
    hashes = dbevmtx.get_transaction_hashes_not_decoded(
        filter_query=EvmTransactionsNotDecodedFilterQuery.make(chain_id=ChainID.ETHEREUM, limit=None),  # noqa: E501
    )
    assert len(hashes) == 1


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x756F45E3FA69347A9A973A725E3C98bC4db0b5a0',
    '0x9328D55ccb3FCe531f199382339f0E576ee840A3',
    '0x4bba290826c253bd854121346c370a9886d1bc26',
]])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
def test_genesis_remove_address(
        database: 'DBHandler',
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
):
    """
    Checks that if an address had a genesis transaction:
    1. The decoded event gets deleted when the address is removed
    2. Genesis tx gets removed if it was the last tracked address with a genesis tx
    """
    dbevmtx = DBEvmTx(database)
    dbevents = DBHistoryEvents(database)
    genesis_address_1, genesis_address_2, no_genesis_address = ethereum_accounts

    def get_genesis_events() -> list[EvmEvent]:
        with database.conn.read_ctx() as cursor:
            return dbevents.get_history_events_internal(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(tx_hashes=[GENESIS_HASH]),
            )

    def delete_transactions_for_address(address: ChecksumEvmAddress) -> None:
        with database.user_write() as write_cursor:
            dbevmtx.delete_transactions(
                write_cursor=write_cursor,
                address=address,
                chain=SupportedBlockchain.ETHEREUM,
            )

    ethereum_transaction_decoder.decode_transaction_hashes(
        ignore_cache=True,
        tx_hashes=[GENESIS_HASH],
    )
    all_events = get_genesis_events()
    assert len(all_events) == 2

    delete_transactions_for_address(no_genesis_address)
    assert get_genesis_events() == all_events, 'Events should have not been modified'

    delete_transactions_for_address(genesis_address_1)
    assert get_genesis_events() == [all_events[1]], 'One of the events should have been deleted'

    delete_transactions_for_address(genesis_address_2)
    assert get_genesis_events() == [], 'There should be no events at this point'

    with database.conn.read_ctx() as cursor:
        genesis_tx = dbevmtx.get_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(tx_hash=GENESIS_HASH),
        )

    assert len(genesis_tx) == 0, 'Genesis transaction should have been deleted'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xcBe21204C4b9F1810363D69773b74203376681a2']])
def test_token_detection_after_decoding(
        database: 'DBHandler',
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: 'list[ChecksumEvmAddress]',
) -> None:
    """Test that the tokens found in new IN history events are saved as detected tokens."""
    with patch.object(database, 'save_tokens_for_address') as save_tokens_mock:
        get_decoded_events_of_transaction(
            evm_inquirer=ethereum_inquirer,
            tx_hash=deserialize_evm_tx_hash('0x21713730e79832ad0a88c9695745a95cd6e475fe69232f2aa8993ca98e6db92f'),
        )
        assert save_tokens_mock.call_count == 1
        assert save_tokens_mock.call_args_list[0].kwargs['address'] == ethereum_accounts[0]
        assert save_tokens_mock.call_args_list[0].kwargs['blockchain'] == SupportedBlockchain.ETHEREUM  # noqa: E501
        assert save_tokens_mock.call_args_list[0].kwargs['tokens'] == [Asset('eip155:1/erc20:0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c')]  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xf4ae64c5c4fb632D0e0D77097b957941c399d26e']])
def test_eip7702_transaction(ethereum_transaction_decoder, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x42402dcf6658abaf2c47593a7ebe1264fb2f331de918239d1717a7a9d2996abf')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1746615035000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.0002516693954254'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.MESSAGE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            address=user_address,
            notes='Message: hello!',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.DELEGATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            address=string_to_evm_address('0x775c8D470CC8d4530b8F233322480649f4FAb758'),
            notes='Execute account delegation to 0x775c8D470CC8d4530b8F233322480649f4FAb758',
            counterparty=CPT_ACCOUNT_DELEGATION,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x22d094Fb289DD45B02490F97b015891FD9d4C145']])
def test_eip7702_revocation_transaction(ethereum_transaction_decoder, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x8419cf2c21e755a9a3e916749b8356beca49d85fb4fc31f7e5fbb7f36d21fe62')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1746793655000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.0001836334598192'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.DELEGATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            address=ZERO_ADDRESS,
            notes=f'Revoke account delegation for {user_address}',
            counterparty=CPT_ACCOUNT_DELEGATION,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xC5d494aa0CBabD7871af0Ef122fB410Fa25c3379']])
def test_contract_deployment(ethereum_transaction_decoder, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x36d18e69806af47ea9469156917af9e0278fa315256d08a566023dce5df08c70')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1756420055000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.001220261148478126'),
            location_label=(user_address := '0xC5d494aa0CBabD7871af0Ef122fB410Fa25c3379'),
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPLOY,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            address=(contract_address := '0x3337286E850cf01B8A8B6094574f0dd6a2108B16'),
            notes=f'Deploy a new contract at {contract_address}',
        ),
    ]
