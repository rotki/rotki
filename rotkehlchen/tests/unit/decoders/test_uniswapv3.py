import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V3
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import EthereumTransaction, Location, deserialize_evm_tx_hash
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0xb63e0C506dDBa7b0dd106d1937d6D13BE2C62aE2']])  # noqa: E501
def test_uniswap_v3_swap(database, ethereum_manager, eth_transactions):
    """Data for swap
    https://etherscan.io/tx/0x1c50c336329a7ee41f722ce5d848ebd066b72bf44a1eaafcaa92e8c0282049d2
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x1c50c336329a7ee41f722ce5d848ebd066b72bf44a1eaafcaa92e8c0282049d2'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14351442,
        from_address='0xb63e0C506dDBa7b0dd106d1937d6D13BE2C62aE2',
        to_address='0xe592427a0aece92de3edee1f18e0157c05861564',
        value=632989659350357136,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xac9650d800000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000001800000000000000000000000000000000000000000000000000000000000000104db3e2198000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000005a98fcbea516cf06857215779fd812ca3bef1b320000000000000000000000000000000000000000000000000000000000002710000000000000000000000000b63e0c506ddba7b0dd106d1937d6d13be2c62ae2000000000000000000000000000000000000000000000000000000006183617400000000000000000000000000000000000000000000003635c9adc5dea0000000000000000000000000000000000000000000000000000008d4133ec308af39000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000412210e8a00000000000000000000000000000000000000000000000000000000'),  # noqa: E501
        nonce=0,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=485,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000003635c9adc5dea00000'),  # noqa: E501
                address=string_to_evm_address('0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000f4ad61db72f114be877e87d62dc5e7bd52df4d9b'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b63e0c506ddba7b0dd106d1937d6d13be2c62ae2'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=486,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000008c8d4bdd012d490'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e592427a0aece92de3edee1f18e0157c05861564'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=487,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000008c8d4bdd012d490'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e592427a0aece92de3edee1f18e0157c05861564'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000f4ad61db72f114be877e87d62dc5e7bd52df4d9b'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=488,
                data=hexstring_to_bytes('0xffffffffffffffffffffffffffffffffffffffffffffffc9ca36523a2160000000000000000000000000000000000000000000000000000008c8d4bdd012d4900000000000000000000000000000000000000000066b7e70be499b45db3d11c000000000000000000000000000000000000000000000017d945bc30daf7e2f36fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffee008'),  # noqa: E501
                address=string_to_evm_address('0xf4aD61dB72f114Be877E87d62DC5e7bd52DF4d9B'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000e592427a0aece92de3edee1f18e0157c05861564'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b63e0c506ddba7b0dd106d1937d6d13be2c62ae2'),  # noqa: E501
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
            eth_transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x1c50c336329a7ee41f722ce5d848ebd066b72bf44a1eaafcaa92e8c0282049d2',
            ),
            sequence_index=0,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label='0xb63e0C506dDBa7b0dd106d1937d6D13BE2C62aE2',
            notes='Burned 0.00393701451 ETH in gas from 0xb63e0C506dDBa7b0dd106d1937d6D13BE2C62aE2',  # noqa: E501
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x1c50c336329a7ee41f722ce5d848ebd066b72bf44a1eaafcaa92e8c0282049d2',
            ),
            sequence_index=1,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.632989659350357136'), usd_value=ZERO),
            location_label='0xb63e0C506dDBa7b0dd106d1937d6D13BE2C62aE2',
            notes='Swap 0.632989659350357136 ETH in uniswap-v3 from 0xb63e0C506dDBa7b0dd106d1937d6D13BE2C62aE2',  # noqa: E501
            counterparty=CPT_UNISWAP_V3,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x1c50c336329a7ee41f722ce5d848ebd066b72bf44a1eaafcaa92e8c0282049d2',
            ),
            sequence_index=487,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'),
            balance=Balance(amount=FVal('1000'), usd_value=ZERO),
            location_label='0xb63e0C506dDBa7b0dd106d1937d6D13BE2C62aE2',
            notes='Receive 1000 LDO in uniswap-v3 from 0xb63e0C506dDBa7b0dd106d1937d6D13BE2C62aE2',
            counterparty=CPT_UNISWAP_V3,
        ),
    ]
    assert events == expected_events
