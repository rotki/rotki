import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDT
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChainID, EvmTransaction, Location, Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


def test_decoders_initialization(ethereum_transaction_decoder):
    """Make sure that all decoders we have created are detected and initialized"""
    assert set(ethereum_transaction_decoder.decoders.keys()) == {
        'Aavev1',
        'Aavev2',
        'Airdrops',
        'Balancer',
        'Compound',
        'Curve',
        'Dxdaomesa',
        'Ens',
        'Gitcoin',
        'Kyber',
        'Liquity',
        'Makerdao',
        'Makerdaosai',
        'Oneinchv1',
        'Oneinchv2',
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

    assert ethereum_transaction_decoder.all_counterparties == {
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
            write_cursor=cursor,
            transaction=transaction,
            tx_receipt=receipt,
        )
    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.BLOCKCHAIN,
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


@pytest.mark.parametrize('ethereum_accounts', [[
    '0x4bBa290826C253BD854121346c370a9886d1bC26',
    '0xED2f12B896d0C7BFf4050d3D8c4f95Bd61aAa12d',
]])
def test_simple_erc20_transfer(
        database,
        ethereum_accounts,
        ethereum_transaction_decoder,
):
    """
    Data taken from
    https://etherscan.io/tx/0xbb58b36ddc027a1070131e68b915e5f0dca37767b020ed164eda681725b5ca4e
    """
    evmhash = deserialize_evm_tx_hash('0xbb58b36ddc027a1070131e68b915e5f0dca37767b020ed164eda681725b5ca4e')  # noqa: E501
    from_address = ethereum_accounts[0]
    to_address = ethereum_accounts[1]
    tether_address = string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=0,
        block_number=0,
        from_address=from_address,
        to_address=tether_address,
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
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        events = ethereum_transaction_decoder.decode_transaction(
            write_cursor=cursor,
            transaction=transaction,
            tx_receipt=receipt,
        )
    assert events == [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=Timestamp(0),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(),
            location_label='0x4bBa290826C253BD854121346c370a9886d1bC26',
            notes='Burned 0 ETH for gas',
            counterparty='gas',
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=74,
            timestamp=Timestamp(0),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDT,
            balance=Balance(amount=FVal('38.002229')),
            location_label=from_address,
            notes=f'Transfer 38.002229 USDT from {from_address} to {to_address}',
            counterparty=to_address,
            identifier=None,
            extra_data=None,
        ),
    ]
