import pytest

from rotkehlchen.accounting.structures import (
    Balance,
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_ethereum_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import EthereumTransaction, Location, deserialize_evm_tx_hash
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0x0f1a748cDF53Bbad378CE2C4429463d01CcE0C3f']])  # noqa: E501
def test_pickle_deposit(database, ethereum_manager):
    """Data for deposit taken from
    https://etherscan.io/tx/0xba9a52a144d4e79580a557160e9f8269d3e5373ce44bce00ebd609754034b7bd
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0xba9a52a144d4e79580a557160e9f8269d3e5373ce44bce00ebd609754034b7bd'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EthereumTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14318825,
        from_address='0x0f1a748cDF53Bbad378CE2C4429463d01CcE0C3f',
        to_address='0xb4EBc2C371182DeEa04B2264B9ff5AC4F0159C69',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xb6b55f250000000000000000000000000000000000000000000000312ebe013bcd5d6fed'),  # noqa: E501
        nonce=507,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=259,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000312ebe013bcd5d6fed'),  # noqa: E501
                address=string_to_ethereum_address('0xf4d2888d29D722226FafA5d9B24F9164c092421E'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000f1a748cdf53bbad378ce2c4429463d01cce0c3f'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b4ebc2c371182deea04b2264b9ff5ac4f0159c69'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=260,
                data=hexstring_to_bytes('0xfffffffffffffffffffffffffffffffffffffffffffffd80272f24c89e0e4cd9'),  # noqa: E501
                address=string_to_ethereum_address('0xf4d2888d29D722226FafA5d9B24F9164c092421E'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000f1a748cdf53bbad378ce2c4429463d01cce0c3f'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000b4ebc2c371182deea04b2264b9ff5ac4f0159c69'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=261,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001e67da0f130b2d9371'),  # noqa: E501
                address=string_to_ethereum_address('0xb4EBc2C371182DeEa04B2264B9ff5AC4F0159C69'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000f1a748cdf53bbad378ce2c4429463d01cce0c3f'),  # noqa: E501
                ],
            ),
        ],
    )

    dbethtx = DBEthTx(database)
    dbethtx.add_ethereum_transactions([transaction], relevant_address=None)
    decoder = EVMTransactionDecoder(database, ethereum_manager, msg_aggregator)
    events = decoder.decode_transaction(transaction=transaction, tx_receipt=receipt)
    import pprint
    pprint.pprint(events)
    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier='0x75b81b2edd454a7b564cc55a6b676e2441e155401bde99a38d867028081d2c30',
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
            location_label='0x362C51b56D3c8f79aecf367ff301d1aFd42EDCEA',
            notes='Burned 0.00393701451 ETH in gas from 0x362C51b56D3c8f79aecf367ff301d1aFd42EDCEA for transaction 0x75b81b2edd454a7b564cc55a6b676e2441e155401bde99a38d867028081d2c30',  # noqa: E501
            counterparty='gas',
            identifier=None,
            extras=None,
        ), HistoryBaseEntry(
            event_identifier='0x75b81b2edd454a7b564cc55a6b676e2441e155401bde99a38d867028081d2c30',
            sequence_index=351,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=EthereumToken('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0'),
            balance=Balance(amount=FVal('12.369108326706528256'), usd_value=ZERO),
            location_label='0x362C51b56D3c8f79aecf367ff301d1aFd42EDCEA',
            notes='Receive 12.369108326706528256 FXS from votium bribe',
            counterparty='votium',
            identifier=None,
            extras=None,
        )]
    assert events == expected_events
