from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.chain.evm.constants import GENESIS_HASH
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import EvmAccount, string_to_evm_address
from rotkehlchen.chain.optimism.types import OptimismTransaction
from rotkehlchen.constants.assets import A_ETH, A_SAI
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery, EvmTransactionsFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.optimismtx import DBOptimismTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTransaction,
    EVMTxHash,
    Location,
    SupportedBlockchain,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
    from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
    from rotkehlchen.chain.optimism.transactions import OptimismTransactions
    from rotkehlchen.db.dbhandler import DBHandler


def _add_transactions_to_db(
        db: 'DBHandler',
        ethereum_accounts: list[ChecksumEvmAddress],
) -> tuple[EVMTxHash, EVMTxHash, EVMTxHash]:
    """Add to the database transactions in different optimism and ethereum for testing"""
    evmhash_opt = deserialize_evm_tx_hash('0x063d45910f29e0954a52aee39febba9be784d49af7588a590dc2fd7d156b4665')  # noqa: E501
    evmhash_eth = deserialize_evm_tx_hash('0x3f313e90ed07044fdbb1016ff7986fd26adaeb05e8e9d3252ae0a8318cb8100d')  # noqa: E501
    evmhash_eth_yabir = deserialize_evm_tx_hash('0x91016e7fb9f524449dd1a0b4faef9bc630e9c01c31b6d3383c94975269335afe')  # noqa: E501
    transaction_opt = OptimismTransaction(
        tx_hash=evmhash_opt,
        chain_id=ChainID.OPTIMISM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=ethereum_accounts[0],
        to_address=string_to_evm_address('0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xa9059cbb000000000000000000000000106b62fdd27b748cf2da3bacab91a2cabaee6dca0000000000000000000000000000000000000000000000000000000086959530'),  # noqa: E501
        nonce=507,
        l1_fee=455063072063200,
    )
    transaction_eth = EvmTransaction(
        tx_hash=evmhash_eth,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=ethereum_accounts[0],
        to_address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xa9059cbb000000000000000000000000c5d494aa0cbabd7871af0ef122fb410fa25c3379000000000000000000000000000000000000000000000000000000257a9974a0'),  # noqa: E501
        nonce=507,
    )
    transaction_eth_yabir = EvmTransaction(
        tx_hash=evmhash_eth_yabir,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=ethereum_accounts[1],
        to_address=string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xa9059cbb000000000000000000000000d9e40f3e33f62029172f6f8b691cf09d476bda3c000000000000000000000000000000000000000000000001a055690d9db80000'),  # noqa: E501
        nonce=507,
    )

    dbevmtx = DBEvmTx(db)
    dboptimismtx = DBOptimismTx(db)
    with db.user_write() as cursor:
        dboptimismtx.add_optimism_transactions(cursor, [transaction_opt], relevant_address=ethereum_accounts[0])  # noqa: E501
        dbevmtx.add_evm_transactions(cursor, [transaction_eth], relevant_address=ethereum_accounts[0])  # noqa: E501
        dbevmtx.add_evm_transactions(cursor, [transaction_eth_yabir], relevant_address=ethereum_accounts[1])  # noqa: E501

    return evmhash_eth, evmhash_eth_yabir, evmhash_opt


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
        transactions = dbevmtx.get_evm_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(
                accounts=[EvmAccount(addr1)],
                tx_hash=approve_tx_hash,
                chain_id=ChainID.ETHEREUM,
            ),
            has_premium=True,
        )
    decoder = ethereum_transaction_decoder
    with patch.object(decoder, '_decode_transaction', wraps=decoder._decode_transaction) as decode_mock:  # noqa: E501
        with database.conn.read_ctx() as cursor:
            for tx in transactions:
                receipt = dbevmtx.get_receipt(cursor, tx.tx_hash, ChainID.ETHEREUM)
                assert receipt is not None, 'all receipts should be queried in the test DB'
                events, _ = decoder._get_or_decode_transaction_events(tx, receipt, ignore_cache=False)  # noqa: E501
                if tx.tx_hash == approve_tx_hash:
                    assert len(events) == 2
                    assert_events_equal(events[0], EvmEvent(
                        # The no-member is due to https://github.com/PyCQA/pylint/issues/3162
                        tx_hash=approve_tx_hash,
                        sequence_index=0,
                        timestamp=1569924574000,
                        location=Location.ETHEREUM,
                        location_label=addr1,
                        asset=A_ETH,
                        balance=Balance(amount=FVal('0.000030921')),
                        # The no-member is due to https://github.com/PyCQA/pylint/issues/3162
                        notes='Burned 0.000030921 ETH for gas',
                        event_type=HistoryEventType.SPEND,
                        event_subtype=HistoryEventSubType.FEE,
                        counterparty=CPT_GAS,
                    ))
                    assert_events_equal(events[1], EvmEvent(
                        # The no-member is due to https://github.com/PyCQA/pylint/issues/3162
                        tx_hash=approve_tx_hash,
                        sequence_index=163,
                        timestamp=1569924574000,
                        location=Location.ETHEREUM,
                        location_label=addr1,
                        asset=A_SAI,
                        balance=Balance(amount=1),
                        notes=f'Set SAI spending approval of {addr1} by 0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE to 1',  # noqa: E501
                        event_type=HistoryEventType.INFORMATIONAL,
                        event_subtype=HistoryEventSubType.APPROVE,
                        address='0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE',
                    ))

            assert decode_mock.call_count == len(transactions)
            # now go again, and see that no more decoding happens as it's all pulled from the DB
            for tx in transactions:
                receipt = dbevmtx.get_receipt(cursor, tx.tx_hash, ChainID.ETHEREUM)
                assert receipt is not None, 'all receipts should be queried in the test DB'
                events, _ = decoder._get_or_decode_transaction_events(tx, receipt, ignore_cache=False)  # noqa: E501
        assert decode_mock.call_count == len(transactions)


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
    _, evmhash_eth_yabir, evmhash_opt = _add_transactions_to_db(database, ethereum_accounts)
    dbevmtx = DBEvmTx(database)
    dboptimismtx = DBOptimismTx(database)
    assert len(dbevmtx.get_transaction_hashes_no_receipt(tx_filter_query=None, limit=None)) == 3
    eth_transactions.get_receipts_for_transactions_missing_them(addresses=[ethereum_accounts[0]])
    assert dbevmtx.get_transaction_hashes_no_receipt(tx_filter_query=None, limit=None) == [evmhash_opt, evmhash_eth_yabir]  # noqa: E501
    optimism_transactions.get_receipts_for_transactions_missing_them()
    assert dbevmtx.get_transaction_hashes_no_receipt(tx_filter_query=None, limit=None) == [evmhash_eth_yabir]  # noqa: E501

    # check that the transactions have not been decoded
    hashes = dboptimismtx.get_transaction_hashes_not_decoded(chain_id=ChainID.OPTIMISM, limit=None, addresses=None)  # noqa: E501
    assert len(hashes) == 1
    hashes = dbevmtx.get_transaction_hashes_not_decoded(chain_id=ChainID.ETHEREUM, limit=None, addresses=None)  # noqa: E501
    assert len(hashes) == 1

    # decode evm transactions using the optimism decoder and without providing any tx hash
    optimism_transaction_decoder.decode_transaction_hashes(ignore_cache=False, tx_hashes=None)

    # verify that the optimism transactions got decoded but not the
    # ethereum one (would raise an error if tried)
    hashes = dboptimismtx.get_transaction_hashes_not_decoded(chain_id=ChainID.OPTIMISM, limit=None, addresses=None)  # noqa: E501
    assert len(hashes) == 0
    hashes = dbevmtx.get_transaction_hashes_not_decoded(chain_id=ChainID.ETHEREUM, limit=None, addresses=None)  # noqa: E501
    assert len(hashes) == 1


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x756F45E3FA69347A9A973A725E3C98bC4db0b5a0',
    '0x9328D55ccb3FCe531f199382339f0E576ee840A3',
    '0x4bba290826c253bd854121346c370a9886d1bc26',
]])
def test_genesis_remove_address(
        database: 'DBHandler',
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
):
    """
    Checks that if an address had a genesis transacion:
    1. The decoded event gets deleted when the address is removed
    2. Genesis tx gets removed if it was the last tracked address with a genesis tx
    """
    dbevmtx = DBEvmTx(database)
    dbevents = DBHistoryEvents(database)
    genesis_address_1, genesis_address_2, no_genesis_address = ethereum_accounts

    def get_genesis_events() -> list[EvmEvent]:
        with database.conn.read_ctx() as cursor:
            events = dbevents.get_history_events(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(tx_hashes=[GENESIS_HASH]),
                has_premium=True,
            )

        return events

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
        genesis_tx = dbevmtx.get_evm_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(tx_hash=GENESIS_HASH),
            has_premium=True,
        )

    assert len(genesis_tx) == 0, 'Genesis transaction should have been deleted'
