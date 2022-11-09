import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.modules.yearn.constants import CPT_YEARN_V2
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_YFI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    EvmTransaction,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0xb524c787669185E11d01C645D1910631e04Fa5Eb']])  # noqa: E501
def test_deposit_yearn_v2(database, ethereum_manager, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0x5d7e7646e3749fcd575ea76e35763fa8eeb6dfb83c4c242a4448ee1495f695ba
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x5d7e7646e3749fcd575ea76e35763fa8eeb6dfb83c4c242a4448ee1495f695ba'
    user_address = string_to_evm_address('0xb524c787669185E11d01C645D1910631e04Fa5Eb')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0xdb25cA703181E7484a155DD612b06f57E12Be5F0'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xb6b55f25000000000000000000000000000000000000000000000000004de0e34960d000'),  # noqa: E501
        nonce=507,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=154,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000004ce82f9e9559fe'),  # noqa: E501
                address=string_to_evm_address('0xdb25cA703181E7484a155DD612b06f57E12Be5F0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b524c787669185e11d01c645d1910631e04fa5eb'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=120,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000004de0e34960d000'),  # noqa: E501
                address=string_to_evm_address('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b524c787669185e11d01c645d1910631e04fa5eb'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000db25ca703181e7484a155dd612b06f57e12be5f0'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=156,
                data=hexstring_to_bytes('0xffffffffffffffffffffffffffffffffffffffffffffffffffb21f1cb69f2fff'),  # noqa: E501
                address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b524c787669185e11d01c645d1910631e04fa5eb'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000db25ca703181e7484a155dd612b06f57e12be5f0'),  # noqa: E501
                ],
            ),
        ],
    )

    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=121,
            timestamp=TimestampMS(1646375440000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_YFI,
            balance=Balance(amount=FVal('0.02192084'), usd_value=ZERO),
            location_label=user_address,
            notes='Deposit 0.02192084 YFI in YearnV2 vault YFI yVault',
            counterparty=CPT_YEARN_V2,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=155,
            timestamp=TimestampMS(1646375440000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xdb25cA703181E7484a155DD612b06f57E12Be5F0'),
            balance=Balance(amount=FVal('0.02164738945170483'), usd_value=ZERO),
            location_label=user_address,
            notes='Recive 0.02164738945170483 YFI yVault after deposit in YearnV2',
            counterparty=CPT_YEARN_V2,
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x7b33b34D45A395518a4143846Ac40dA78CbcAA91']])  # noqa: E501
def test_withdraw_yearn_v2(database, ethereum_manager, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0xfaf3edf9fc4130e003468787d0d21cad89107bb2d648d3cd810864dd2854b76a
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0xfaf3edf9fc4130e003468787d0d21cad89107bb2d648d3cd810864dd2854b76a'
    user_address = string_to_evm_address('0x7b33b34D45A395518a4143846Ac40dA78CbcAA91')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x2e1a7d4d000000000000000000000000000000000000000000000004ace221a99fa8e6e8'),  # noqa: E501
        nonce=507,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=78,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000004ace221a99fa8e6e8'),  # noqa: E501
                address=string_to_evm_address('0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007b33b34d45a395518a4143846ac40da78cbcaa91'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=79,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000005000a02dde43a18f8'),  # noqa: E501
                address=string_to_evm_address('0x111111111117dC0aa78b770fA6A738034120C302'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b8c3b7a2a618c552c23b1e4701109a9e756bab67'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000007b33b34d45a395518a4143846ac40da78cbcaa91'),  # noqa: E501
                ],
            ),
        ],
    )

    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=79,
            timestamp=TimestampMS(1646375440000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67'),
            balance=Balance(amount=FVal('86.244532826510255848'), usd_value=ZERO),
            location_label=user_address,
            notes='Return 86.244532826510255848 yv1INCH to the YearnV2 vault',
            counterparty=CPT_YEARN_V2,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=80,
            timestamp=TimestampMS(1646375440000),
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0x111111111117dC0aa78b770fA6A738034120C302'),
            balance=Balance(amount=FVal('92.236538270354905336'), usd_value=ZERO),
            location_label=user_address,
            notes='Withdraw 92.236538270354905336 1INCH from YearnV2 contract 1INCH yVault',
            counterparty=CPT_YEARN_V2,
        )]
    assert events == expected_events
