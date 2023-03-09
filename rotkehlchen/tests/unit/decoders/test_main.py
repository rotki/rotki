from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.constants import CPT_KRAKEN
from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDT
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_OPTIMISM_USDT
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_ethereum_event
from rotkehlchen.types import (
    ChainID,
    EvmTransaction,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

# Have to use a constant instead of make_evm_address() because vcr doesn't work otherwise.
ADDRESS_WITHOUT_GENESIS_TX = '0x4bBa290826C253BD854121346c370a9886d1bC26'


def test_decoders_initialization(ethereum_transaction_decoder):
    """Make sure that all decoders we have created are detected and initialized"""
    assert set(ethereum_transaction_decoder.decoders.keys()) == {
        'Aavev1',
        'Aavev2',
        'Airdrops',
        'Balancerv1',
        'Balancerv2',
        'Compound',
        'Curve',
        'Dxdaomesa',
        'Ens',
        'Eth2',
        'Gitcoin',
        'Kyber',
        'Liquity',
        'Makerdao',
        'Makerdaosai',
        'Oneinchv1',
        'Oneinchv2',
        'OptimismBridge',
        'PickleFinance',
        'Sushiswap',
        'Uniswapv1',
        'Uniswapv2',
        'Uniswapv3',
        'Votium',
        'Zksync',
        'Hop',
        'Convex',
        'Weth',
        'Yearn',
    }

    assert ethereum_transaction_decoder.rules.all_counterparties == {
        'kyber legacy',
        'element-finance',
        'badger',
        'makerdao vault',
        '1inch-v2',
        'uniswap',
        'curve',
        'gnosis-chain',
        'gas',
        'ens',
        'liquity',
        'shapeshift',
        'hop-protocol',
        '1inch',
        'gitcoin',
        'makerdao migration',
        'uniswap-v1',
        'uniswap-v2',
        'uniswap-v3',
        'zksync',
        'frax',
        'makerdao dsr',
        'makerdao sai',
        'pickle finance',
        'convex',
        'votium',
        'aave-v1',
        'aave-v2',
        'compound',
        'dxdaomesa',
        '1inch-v1',
        'sushiswap-v2',
        'weth',
        'yearn-v1',
        'yearn-v2',
        'balancer-v1',
        'balancer-v2',
        'optimism',
        'eth2',
    }


@pytest.mark.parametrize('ethereum_accounts', [['0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045']])  # noqa: E501
def test_no_logs_and_zero_eth(
        database,
        ethereum_accounts,
        ethereum_transaction_decoder,
):
    """
    Data taken from
    https://etherscan.io/tx/0x9a95424c48d36bb2f60fb7684a1068c08ec643c64144e7cdfbe5fb3fc820aa7f
    """
    evmhash = deserialize_evm_tx_hash('0x9a95424c48d36bb2f60fb7684a1068c08ec643c64144e7cdfbe5fb3fc820aa7f')  # noqa: E501
    user_address = ethereum_accounts[0]
    sender = '0xF99973C9F33793cb83a4590daF15b36F0ab62228'
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=0,
        block_number=0,
        from_address=sender,
        to_address=user_address,
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[],
    )
    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    events = ethereum_transaction_decoder.decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label=user_address,
            notes=f'Receive 0 ETH from {sender}',
            counterparty=sender,
            identifier=None,
            extra_data=None,
        ),
    ]


@pytest.mark.parametrize(('ethereum_accounts', 'optimism_accounts', 'tether_address', 'chain'), [
    (['0x4bBa290826C253BD854121346c370a9886d1bC26', '0xED2f12B896d0C7BFf4050d3D8c4f95Bd61aAa12d'], [], '0xdAC17F958D2ee523a2206206994597C13D831ec7', ChainID.ETHEREUM),  # noqa: E501
    ([], ['0x4bBa290826C253BD854121346c370a9886d1bC26', '0xED2f12B896d0C7BFf4050d3D8c4f95Bd61aAa12d'], '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58', ChainID.OPTIMISM),  # noqa: E501
])
def test_simple_erc20_transfer(
        database,
        ethereum_accounts,
        optimism_accounts,
        ethereum_transaction_decoder,
        optimism_transaction_decoder,
        tether_address,
        chain,
):
    """
    Data taken from
    https://etherscan.io/tx/0xbb58b36ddc027a1070131e68b915e5f0dca37767b020ed164eda681725b5ca4e
    """
    evmhash = deserialize_evm_tx_hash('0xbb58b36ddc027a1070131e68b915e5f0dca37767b020ed164eda681725b5ca4e')  # noqa: E501
    accounts = ethereum_accounts if chain == ChainID.ETHEREUM else optimism_accounts
    from_address = accounts[0]
    to_address = accounts[1]
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=chain,
        timestamp=0,
        block_number=0,
        from_address=from_address,
        to_address=tether_address,
        value=0,
        gas=45000,
        gas_price=10000000000,
        gas_used=45000,
        input_data=b'',
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=chain,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=73,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000000243de35'),  # noqa: E501
                address=tether_address,
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000004bba290826c253bd854121346c370a9886d1bc26'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000ed2f12b896d0c7bff4050d3d8c4f95bd61aaa12d'),  # noqa: E501
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    tx_decoder = ethereum_transaction_decoder if chain is ChainID.ETHEREUM else optimism_transaction_decoder  # noqa: E501
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    events = tx_decoder.decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=Timestamp(0),
            location=Location.from_chain_id(chain),
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00045')),
            location_label=from_address,
            notes='Burned 0.00045 ETH for gas',
            counterparty='gas',
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=74,
            timestamp=Timestamp(0),
            location=Location.from_chain_id(chain),
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDT if chain is ChainID.ETHEREUM else A_OPTIMISM_USDT,
            balance=Balance(amount=FVal('38.002229')),
            location_label=from_address,
            notes=f'Transfer 38.002229 USDT from {from_address} to {to_address}',
            counterparty=to_address,
            identifier=None,
            extra_data=None,
        ),
    ]


@pytest.mark.parametrize(('ethereum_accounts', 'optimism_accounts', 'chain'), [
    (['0x4bBa290826C253BD854121346c370a9886d1bC26', '0x38C3f1Ab36BdCa29133d8AF7A19811D10B6CA3FC'], [], ChainID.ETHEREUM),  # noqa: E501
    ([], ['0x4bBa290826C253BD854121346c370a9886d1bC26', '0x38C3f1Ab36BdCa29133d8AF7A19811D10B6CA3FC'], ChainID.OPTIMISM),  # noqa: E501
])
def test_eth_transfer(
        database,
        ethereum_accounts,
        optimism_accounts,
        ethereum_transaction_decoder,
        optimism_transaction_decoder,
        chain,
):
    """
    Data taken from
    https://etherscan.io/tx/0x8caa7df2ebebfceb98207605e64691202b9e7498c3cccdbccb41c1600cf16e65
    """
    evmhash = deserialize_evm_tx_hash('0x8caa7df2ebebfceb98207605e64691202b9e7498c3cccdbccb41c1600cf16e65')  # noqa: E501
    accounts = ethereum_accounts if chain is ChainID.ETHEREUM else optimism_accounts
    from_address = accounts[0]
    to_address = accounts[1]
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=chain,
        timestamp=0,
        block_number=0,
        from_address=from_address,
        to_address=to_address,
        value=500000000000000000,
        gas=2e5,
        gas_price=10 * 1e9,  # 10 gwei
        gas_used=1e5,
        input_data=b'',
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=chain,
        contract_address=None,
        status=True,
        type=0,
        logs=[],
    )
    dbevmtx = DBEvmTx(database)
    tx_decoder = ethereum_transaction_decoder if chain is ChainID.ETHEREUM else optimism_transaction_decoder  # noqa: E501
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    events = tx_decoder.decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=Timestamp(0),
            location=Location.from_chain_id(chain),
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.001)),
            location_label=from_address,
            notes='Burned 0.001 ETH for gas',
            counterparty='gas',
            identifier=None,
            extra_data=None,
        ),
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=0,
            location=Location.from_chain_id(chain),
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.5)),
            location_label=from_address,
            notes=f'Transfer 0.5 ETH to {to_address}',
            counterparty=to_address,
            identifier=None,
            extra_data=None,
        ),
    ]


@pytest.mark.parametrize(('ethereum_accounts', 'optimism_accounts', 'chain'), [
    (['0x4bBa290826C253BD854121346c370a9886d1bC26'], [], ChainID.ETHEREUM),
    ([], ['0x4bBa290826C253BD854121346c370a9886d1bC26'], ChainID.OPTIMISM),
])
def test_eth_spend(
        database,
        ethereum_accounts,
        optimism_accounts,
        ethereum_transaction_decoder,
        optimism_transaction_decoder,
        chain,
):
    """
    Data taken from
    https://etherscan.io/tx/0x8caa7df2ebebfceb98207605e64691202b9e7498c3cccdbccb41c1600cf16e65
    """
    evmhash = deserialize_evm_tx_hash('0x8caa7df2ebebfceb98207605e64691202b9e7498c3cccdbccb41c1600cf16e65')  # noqa: E501
    from_address = ethereum_accounts[0] if chain is ChainID.ETHEREUM else optimism_accounts[0]
    to_address = string_to_evm_address('0x38C3f1Ab36BdCa29133d8AF7A19811D10B6CA3FC')
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=chain,
        timestamp=0,
        block_number=0,
        from_address=from_address,
        to_address=to_address,
        value=500000000000000000,
        gas=2e5,
        gas_price=10 * 1e9,  # 10 gwei
        gas_used=1e5,
        input_data=b'',
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=chain,
        contract_address=None,
        status=True,
        type=0,
        logs=[],
    )
    dbevmtx = DBEvmTx(database)
    tx_decoder = ethereum_transaction_decoder if chain is ChainID.ETHEREUM else optimism_transaction_decoder  # noqa: E501
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    events = tx_decoder.decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=Timestamp(0),
            location=Location.from_chain_id(chain),
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.001)),
            location_label=from_address,
            notes='Burned 0.001 ETH for gas',
            counterparty='gas',
            identifier=None,
            extra_data=None,
        ),
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=0,
            location=Location.from_chain_id(chain),
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.5)),
            location_label=from_address,
            notes=f'Send 0.5 ETH to {to_address}',
            counterparty=to_address,
            identifier=None,
            extra_data=None,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0xa4A6A282A7fC7F939e01D62D884355d79f5046C1']])
def test_eth_deposit(
        database,
        ethereum_accounts,
        ethereum_transaction_decoder,
):
    """
    Data taken from
    https://etherscan.io/tx/0x8f91a9b98a856282cdad74d9b8a683504c13e3c9d810e4e22bd0ca2eb9d71800
    """
    evmhash = deserialize_evm_tx_hash('0x8f91a9b98a856282cdad74d9b8a683504c13e3c9d810e4e22bd0ca2eb9d71800')  # noqa: E501
    from_address = ethereum_accounts[0]
    to_address = '0xAe2D4617c862309A3d75A0fFB358c7a5009c673F'  # Kraken 10
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=0,
        block_number=0,
        from_address=from_address,
        to_address=to_address,
        value=100000000000000000000,
        gas=2e5,
        gas_price=10 * 1e9,  # 10 gwei
        gas_used=1e5,
        input_data=b'',
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[],
    )
    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    events = ethereum_transaction_decoder.decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=Timestamp(0),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.001)),
            location_label=from_address,
            notes='Burned 0.001 ETH for gas',
            counterparty='gas',
            identifier=None,
            extra_data=None,
        ),
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal(100)),
            location_label=from_address,
            notes='Deposit 100 ETH to kraken',
            counterparty=CPT_KRAKEN,
            identifier=None,
            extra_data=None,
        ),
    ]


def test_maybe_reshuffle_events():
    """
    Tests that `maybe_reshuffle_events` works correctly.
    Especially tests that there are no duplicated indices produced.
    """
    event_a = make_ethereum_event(1)
    event_b = make_ethereum_event(2)
    event_c = make_ethereum_event(3)
    events = [event_a, event_b, event_c]

    maybe_reshuffle_events(event_c, event_a)
    assert events == [event_a, event_b, event_c]  # no change since we just swap indices
    assert [event.sequence_index for event in events] == [3, 2, 1]  # indices swapped

    maybe_reshuffle_events(event_c, event_a, events)
    assert events == [event_c, event_b, event_a]  # events were sorted before swapping indices
    assert [event.sequence_index for event in events] == [1, 3, 2]  # indices swapped


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xA1E4380A3B1f749673E270229993eE55F35663b4',
    '0x756F45E3FA69347A9A973A725E3C98bC4db0b5a0',
]])
def test_genesis_transaction(database, ethereum_inquirer, ethereum_accounts):
    """Test that decoding a genesis transaction is handled correctly"""
    transactions = EthereumTransactions(ethereum_inquirer=ethereum_inquirer, database=database)
    evmhash = deserialize_evm_tx_hash(GENESIS_HASH)
    user_address_1, user_address_2 = ethereum_accounts
    transactions._get_transactions_for_range(
        address=user_address_1,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1676653545),
    )

    query_patch = patch.object(
        transactions,
        '_query_and_save_transactions_for_range',
        wraps=transactions._query_and_save_transactions_for_range,
    )

    with query_patch as query_mock:
        events, _ = get_decoded_events_of_transaction(
            evm_inquirer=ethereum_inquirer,
            database=database,
            tx_hash=evmhash,
            transactions=transactions,
        )
        assert query_mock.call_count == 1, 'Should have been called only once since one of the addresses already had transactions queried'  # noqa: E501

    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1438269973000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal('200')),
            location_label=user_address_2,
            notes=f'Receive 200 ETH from {ZERO_ADDRESS}',
            counterparty=ZERO_ADDRESS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1438269973000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal('2000')),
            location_label=user_address_1,
            notes=f'Receive 2000 ETH from {ZERO_ADDRESS}',
            counterparty=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDRESS_WITHOUT_GENESIS_TX]])
def test_genesis_transaction_no_address(database, ethereum_inquirer):
    """
    Test that decoding a genesis transaction is handled correctly when there is no address tracked
    with a genesis transaction.
    """
    tx_hex = deserialize_evm_tx_hash(GENESIS_HASH)
    with pytest.raises(InputError):
        get_decoded_events_of_transaction(
            evm_inquirer=ethereum_inquirer,
            database=database,
            tx_hash=tx_hex,
        )
