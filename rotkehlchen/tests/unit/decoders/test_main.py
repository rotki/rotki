import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.types import EvmTransaction, Location, deserialize_evm_tx_hash


def test_decoders_initialization(evm_transaction_decoder):
    """Make sure that all decoders we have created are detected and initialized"""
    assert set(evm_transaction_decoder.decoders.keys()) == {
        'Aavev1',
        'Airdrops',
        'Compound',
        'Curve',
        'Dxdaomesa',
        'Ens',
        'Gitcoin',
        'Kyber',
        'Liquity',
        'Makerdao',
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
    }

    assert evm_transaction_decoder.all_counterparties == {
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
        'pickle finance',
        'convex',
        'votium',
        'aave-v1',
        'compound',
        'dxdaomesa',
        '1inch-v1',
        'convex',
        'sushiswap-v2',
        'weth',
    }


@pytest.mark.parametrize('ethereum_accounts', [['0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045']])  # noqa: E501
def test_no_logs_and_zero_eth(
        database,
        ethereum_accounts,
        evm_transaction_decoder,
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
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[],
    )
    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        events = evm_transaction_decoder.decode_transaction(
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
